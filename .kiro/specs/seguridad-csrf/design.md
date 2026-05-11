# Design Document: Seguridad CSRF y Headers HTTP

## Overview

Este documento describe el diseño técnico para implementar protección CSRF y headers de
seguridad HTTP en el sistema SaaS multi-tenant de gestión de talleres mecánicos.

El diseño cubre cuatro cambios concretos y bien delimitados:

1. **CSRF Middleware** (`app/seguridad/csrf_middleware.py`) — valida tokens CSRF en todos los
   endpoints de escritura no exentos usando `fastapi-csrf-protect`
2. **Security Headers Middleware** (`app/seguridad/security_headers_middleware.py`) — agrega
   6 headers de seguridad HTTP a todas las respuestas
3. **Registro en main.py** — inicialización de `CsrfProtect` y registro de ambos middlewares
4. **Integración en api.js** — lectura de cookie CSRF e inclusión automática en headers de
   escritura con retry logic

### Principios de diseño

- **Fail-secure**: si `CSRF_SECRET_KEY` no está configurada, la app no arranca
- **Transparencia**: el frontend no necesita cambios en cada llamada individual — el interceptor
  de axios maneja todo automáticamente
- **Compatibilidad**: los endpoints públicos y el webhook de Twilio quedan exentos para no
  romper integraciones existentes
- **Mínimo cambio**: no se modifica ningún route handler existente — toda la lógica va en
  middlewares y en el interceptor de axios

---

## Architecture

### Flujo de un request de escritura con CSRF

```
Browser/App
    │
    │  POST /tickets/{id}/procesos
    │  Headers: Authorization: Bearer <jwt>
    │           X-CSRF-Token: <csrf_token>
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Middleware Stack (orden de ejecución)           │
│                                                          │
│  1. CORSMiddleware          ← agrega headers CORS        │
│  2. GZipMiddleware          ← compresión                 │
│  3. AuthMiddleware          ← valida JWT, inyecta user   │
│  4. CSRFMiddleware          ← valida X-CSRF-Token        │
│  5. SecurityHeadersMiddleware ← agrega headers seguridad │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Route Handler (solo se ejecuta si CSRF es válido)
```

**Nota sobre el orden de middlewares en FastAPI**: los middlewares se ejecutan en orden
**inverso** al que se agregan con `app.add_middleware()`. El último en agregarse es el primero
en ejecutarse. Por eso `SecurityHeadersMiddleware` debe agregarse **primero** (para que se
ejecute último y pueda agregar headers a cualquier respuesta, incluyendo errores 403 del CSRF).

### Flujo de generación y uso del token CSRF

```
1. Usuario abre la app en el browser
        │
        ▼
2. Backend envía cookie "csrftoken" en cualquier respuesta GET
   (o en un endpoint dedicado GET /auth/csrf-token)
        │
        ▼
3. api.js lee la cookie "csrftoken" via interceptor de axios
        │
        ▼
4. En cada POST/PUT/PATCH/DELETE, axios incluye:
   X-CSRF-Token: <valor de la cookie>
        │
        ▼
5. CSRFMiddleware valida que el header coincide con la cookie
        │
   ┌────┴────┐
   │         │
válido    inválido/ausente
   │         │
   ▼         ▼
continúa   HTTP 403
```

---

## Components and Interfaces

### Componente 1: `app/seguridad/csrf_middleware.py`

Middleware ASGI que valida tokens CSRF en endpoints de escritura.

```python
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Rutas exentas de validación CSRF
CSRF_EXEMPT_PATHS: frozenset[str] = frozenset({
    "/auth/login",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/forgot-password-by-username",
    "/auth/reset-password",
    "/health",
    "/info",
    "/info/conexion-qr",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/whatsapp/webhook",
})

# Métodos HTTP que requieren validación CSRF
CSRF_WRITE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Valida tokens CSRF en todos los endpoints de escritura no exentos.

    Lee el token del header X-CSRF-Token y lo compara con la cookie csrftoken
    usando fastapi-csrf-protect. Retorna HTTP 403 si el token falta o es inválido.
    """

    async def dispatch(self, request: Request, call_next):
        # Solo validar métodos de escritura
        if request.method not in CSRF_WRITE_METHODS:
            return await call_next(request)

        # Saltar rutas exentas
        path = request.url.path
        if path in CSRF_EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Saltar OPTIONS (preflight CORS)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Validar token CSRF
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            return JSONResponse(
                status_code=403,
                content={"error": "csrf_error", "message": "CSRF token missing or invalid"},
            )

        try:
            from fastapi_csrf_protect import CsrfProtect
            csrf = CsrfProtect()
            await csrf.validate_csrf(request)
        except Exception:
            return JSONResponse(
                status_code=403,
                content={"error": "csrf_error", "message": "CSRF token missing or invalid"},
            )

        return await call_next(request)
```

**Decisión de diseño**: usar `BaseHTTPMiddleware` en lugar de un decorador por endpoint para
garantizar cobertura total sin modificar ningún route handler existente.

### Componente 2: `app/seguridad/security_headers_middleware.py`

Middleware ASGI puro (sin `BaseHTTPMiddleware`) para máximo rendimiento.

```python
import os
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import MutableHeaders


# Headers de seguridad que aplican en todos los entornos
SECURITY_HEADERS_ALWAYS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "  # unsafe-inline necesario para Vite en dev
        "img-src 'self' data: blob:; "         # blob: para PDFs generados
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    ),
}

# Headers adicionales solo en producción
SECURITY_HEADERS_PRODUCTION: dict[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware:
    """
    Agrega headers de seguridad HTTP a todas las respuestas.

    Implementado como middleware ASGI puro (no BaseHTTPMiddleware) para
    evitar overhead de buffering y garantizar que los headers se agregan
    incluso en respuestas de streaming.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.is_production = os.getenv("ENVIRONMENT") == "production"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS_ALWAYS.items():
                    headers.append(name, value)
                if self.is_production:
                    for name, value in SECURITY_HEADERS_PRODUCTION.items():
                        headers.append(name, value)
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
```

**Decisión de diseño**: middleware ASGI puro en lugar de `BaseHTTPMiddleware` para evitar el
problema de doble buffering que `BaseHTTPMiddleware` tiene con respuestas de streaming (PDFs).

### Componente 3: Configuración en `app/main.py`

#### 3.1 Validación de `CSRF_SECRET_KEY` al arrancar

Agregar a `_validate_required_secrets()`:

```python
# En _validate_required_secrets(), agregar:
required_secrets = [
    ("jwt-secret-key", "JWT_SECRET_KEY"),
    ("pii-master-key", "PII_MASTER_KEY"),
    ("database-password", "DATABASE_PASSWORD"),
    ("csrf-secret-key", "CSRF_SECRET_KEY"),  # ← NUEVO
]
```

#### 3.2 Configuración de `CsrfProtect`

```python
# Después de load_dotenv(), antes de crear la app FastAPI:
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

@CsrfProtect.load_config
def get_csrf_config():
    is_production = os.getenv("ENVIRONMENT") == "production"
    return [
        ("secret_key", os.getenv("CSRF_SECRET_KEY", "")),
        ("cookie_samesite", "strict"),
        ("cookie_secure", is_production),
        ("cookie_httponly", True),
        ("token_location", "headers"),
        ("header_name", "X-CSRF-Token"),
        ("header_type", ""),  # Sin prefijo "Bearer"
    ]
```

#### 3.3 Registro de middlewares (orden correcto)

```python
# En app/main.py, sección de middlewares:
# IMPORTANTE: add_middleware se ejecuta en orden INVERSO.
# El último en agregarse es el primero en ejecutarse.

# SecurityHeadersMiddleware se agrega PRIMERO → ejecuta ÚLTIMO
# (garantiza headers en todas las respuestas, incluyendo errores)
from app.seguridad.security_headers_middleware import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# CSRFMiddleware se agrega DESPUÉS → ejecuta ANTES que SecurityHeaders
from app.seguridad.csrf_middleware import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

# AuthMiddleware ya existe → ejecuta antes que CSRF
# GZipMiddleware ya existe
# CORSMiddleware ya existe → ejecuta primero de todos
```

#### 3.4 Handler de error CSRF

```python
@app.exception_handler(CsrfProtectError)
async def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=403,
        content={"error": "csrf_error", "message": "CSRF token missing or invalid"},
    )
```

### Componente 4: Integración en `frontend/src/api.js`

#### 4.1 Función helper para leer la cookie CSRF

```javascript
/**
 * Lee el valor de una cookie por nombre.
 * Retorna null si la cookie no existe.
 */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(';').shift();
  }
  return null;
}
```

#### 4.2 Interceptor de axios para CSRF

```javascript
// Agregar ANTES de la función request() existente:

const WRITE_METHODS = new Set(['post', 'put', 'patch', 'delete']);

// Interceptor de request: agrega X-CSRF-Token en métodos de escritura
axios.interceptors.request.use((config) => {
  const method = (config.method || '').toLowerCase();
  if (WRITE_METHODS.has(method)) {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
  }
  return config;
});

// Interceptor de response: retry automático en error CSRF (403)
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Solo reintentar si es 403 por CSRF y no es ya un reintento
    if (
      error.response?.status === 403 &&
      error.response?.data?.error === 'csrf_error' &&
      !originalRequest._csrfRetry
    ) {
      originalRequest._csrfRetry = true;

      // Refrescar el token leyendo la cookie actualizada
      const newCsrfToken = getCookie('csrftoken');
      if (newCsrfToken) {
        originalRequest.headers['X-CSRF-Token'] = newCsrfToken;
        return axios(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);
```

**Decisión de diseño**: usar interceptores de axios en lugar de modificar cada llamada
individual. Esto garantiza cobertura total sin tocar ninguna de las ~50 funciones del objeto
`api` existente.

---

## Data Models

No se requieren cambios en la base de datos. Este spec es puramente de capa HTTP.

---

## Implementation Plan

### Fase 1: Backend — CSRF y Headers (sin romper nada)

**Orden de implementación:**

1. Agregar `fastapi-csrf-protect` a `requirements.txt`
2. Crear `app/seguridad/security_headers_middleware.py`
3. Crear `app/seguridad/csrf_middleware.py`
4. Modificar `app/main.py`:
   - Agregar `CSRF_SECRET_KEY` a `_validate_required_secrets()`
   - Agregar configuración `@CsrfProtect.load_config`
   - Registrar `SecurityHeadersMiddleware` y `CSRFMiddleware`
   - Agregar handler de `CsrfProtectError`
5. Agregar `CSRF_SECRET_KEY` a `.env` local para desarrollo

**Verificación**: `pytest tests/ -x` debe pasar. El servidor debe arrancar sin errores.

### Fase 2: Frontend — Interceptor de axios

1. Agregar función `getCookie()` a `frontend/src/api.js`
2. Agregar interceptor de request (agrega `X-CSRF-Token`)
3. Agregar interceptor de response (retry en 403 CSRF)
4. Verificar que las operaciones existentes siguen funcionando

**Verificación**: abrir la app en el browser, hacer login, crear un ticket — debe funcionar sin
errores de consola.

### Fase 3: Tests

1. `tests/test_csrf_middleware.py` — tests unitarios del middleware
2. `tests/test_security_headers.py` — tests unitarios del middleware de headers
3. `tests/test_csrf_properties.py` — property tests con Hypothesis

---

## Correctness Properties — Implementación

### Property 1: CSRF Enforcement

```python
# tests/test_csrf_properties.py

from hypothesis import given, settings
from hypothesis import strategies as st
from fastapi.testclient import TestClient

# Endpoints de escritura no exentos (muestra representativa)
WRITE_ENDPOINTS = [
    ("POST", "/tickets/1/procesos"),
    ("PUT", "/tickets/1/finanzas"),
    ("PATCH", "/tickets/1/asignar-mecanico"),
    ("DELETE", "/tickets/1/procesos/1"),
    ("POST", "/vehiculos/"),
    ("PUT", "/configuracion/taller"),
    ("POST", "/upload/foto"),
]

@given(
    endpoint=st.sampled_from(WRITE_ENDPOINTS),
)
@settings(max_examples=20, deadline=None)
def test_write_endpoint_without_csrf_returns_403(endpoint):
    """
    Property 1: Para todo Write_Endpoint no exento, un request sin
    X-CSRF-Token retorna HTTP 403.
    """
    method, path = endpoint
    # Request sin X-CSRF-Token (pero con JWT válido)
    response = client.request(
        method,
        path,
        headers={"Authorization": f"Bearer {valid_jwt}"},
        # Sin X-CSRF-Token
    )
    assert response.status_code == 403
    assert response.json()["error"] == "csrf_error"
```

### Property 2: Security Headers

```python
@given(
    endpoint=st.sampled_from(["/", "/health", "/tickets/abiertos", "/auth/login"]),
    method=st.sampled_from(["GET", "POST"]),
)
@settings(max_examples=20, deadline=None)
def test_all_responses_have_security_headers(endpoint, method):
    """
    Property 2: Para toda respuesta HTTP, los headers de seguridad
    requeridos están presentes con los valores correctos.
    """
    response = client.request(method, endpoint)

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers
```

---

## Files to Create / Modify

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `requirements.txt` | Modificar | Agregar `fastapi-csrf-protect==0.5.0` |
| `app/seguridad/csrf_middleware.py` | Crear | Middleware CSRF con lista de exenciones |
| `app/seguridad/security_headers_middleware.py` | Crear | Middleware ASGI puro de headers |
| `app/main.py` | Modificar | Registrar middlewares, configurar CsrfProtect, validar CSRF_SECRET_KEY |
| `frontend/src/api.js` | Modificar | Agregar getCookie(), interceptores de axios |
| `tests/test_csrf_middleware.py` | Crear | Tests unitarios del middleware CSRF |
| `tests/test_security_headers.py` | Crear | Tests unitarios del middleware de headers |
| `tests/test_csrf_properties.py` | Crear | Property tests con Hypothesis |

---

## Consideraciones de Compatibilidad

### App móvil (React Native / Expo)

La app móvil usa autenticación por contraseña de admin (`X-Admin-Password`), no JWT. Los
endpoints de la app móvil (`/api/mobile/*`) también requieren CSRF si usan métodos de escritura.

**Solución**: la app móvil debe incluir `X-CSRF-Token` en sus requests de escritura, igual que
el frontend web. Si la app móvil no puede leer cookies, se puede agregar `/api/mobile/*` a la
lista de exenciones — pero esto reduce la protección. La decisión se toma en la implementación.

### Webhook de Twilio (`/whatsapp/webhook`)

El webhook de Twilio es un POST externo que no puede incluir tokens CSRF. Ya está en la lista
de `CSRF_EXEMPT_PATHS`.

### Endpoints de autenticación

`/auth/login` y `/auth/refresh` están exentos porque son los endpoints que el usuario usa para
obtener su sesión — no tiene sentido requerir CSRF antes de estar autenticado.

### Content-Security-Policy y el frontend Vite

La política CSP incluye `style-src 'self' 'unsafe-inline'` porque Vite inyecta estilos inline
en desarrollo. En producción con el build estático, se puede endurecer a `style-src 'self'`.
