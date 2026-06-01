# Requirements Document: Seguridad CSRF y Headers HTTP

## Introduction

Este documento define los requisitos para implementar protección CSRF completa y headers de
seguridad HTTP en el sistema SaaS multi-tenant de gestión de talleres mecánicos.

El estado actual del sistema presenta dos brechas de seguridad que este spec resuelve:

1. **Sin protección CSRF**: `fastapi-csrf-protect` no está instalado. Los endpoints de escritura
   (POST, PUT, PATCH, DELETE) aceptan requests sin token CSRF, lo que expone al sistema a ataques
   de Cross-Site Request Forgery.

2. **Sin headers de seguridad HTTP**: Las respuestas no incluyen headers como
   `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy` ni
   `Strict-Transport-Security`, dejando a los usuarios expuestos a ataques de navegador como
   clickjacking, MIME sniffing y XSS.

**Contexto del Sistema:**
- Backend: FastAPI + PostgreSQL
- Frontend: React + Vite con `api.js` como cliente HTTP central (usa axios con
  `withCredentials: true`)
- Autenticación: JWT con access/refresh tokens
- Variable de entorno `ENVIRONMENT=production` controla comportamiento en producción

**Archivos que se modificarán:**
- `app/main.py` — inicializar `CsrfProtect`, registrar `Security_Headers_Middleware`
- `app/seguridad/csrf_middleware.py` — nuevo, lógica de validación CSRF
- `app/seguridad/security_headers_middleware.py` — nuevo, headers de seguridad
- `frontend/src/api.js` — leer cookie CSRF, incluir en headers, retry logic
- `requirements.txt` — agregar `fastapi-csrf-protect` como dependencia pinned

## Glossary

- **CSRF_Protector**: Componente que valida tokens CSRF en todos los endpoints de escritura no
  exentos, implementado en `app/seguridad/csrf_middleware.py`
- **Security_Headers_Middleware**: Middleware ASGI que agrega headers HTTP de seguridad a todas
  las respuestas del sistema, implementado en `app/seguridad/security_headers_middleware.py`
- **Frontend_HTTP_Client**: El módulo `api.js` de React que centraliza todas las llamadas HTTP
  al backend usando axios con `withCredentials: true`
- **Write_Endpoint**: Endpoint que modifica estado del sistema — cualquier endpoint que use los
  métodos HTTP POST, PUT, PATCH o DELETE
- **Exempt_Path**: Ruta excluida de la validación CSRF: `/auth/login`, `/auth/refresh`,
  `/health`, `/docs`, `/openapi.json`, `/whatsapp/webhook`
- **CSRF_Secret_Key**: Clave secreta de al menos 256 bits usada para firmar tokens CSRF, cargada
  desde la variable de entorno `CSRF_SECRET_KEY`
- **csrftoken**: Nombre de la cookie HTTP donde el backend deposita el token CSRF para que el
  frontend lo lea y lo incluya en el header `X-CSRF-Token`

## Requirements

### Requirement 1: Instalar y configurar CSRF Protection

**User Story:** Como administrador de seguridad, quiero que la protección CSRF esté instalada y
configurada con estándares modernos, para prevenir ataques de falsificación de peticiones entre
sitios en todos los endpoints de escritura del sistema.

#### Acceptance Criteria

1. THE `requirements.txt` file SHALL include `fastapi-csrf-protect` as a pinned dependency
2. WHEN `main.py` initializes, THE CSRF_Protector SHALL be configured using `CSRF_SECRET_KEY`
   from environment variables
3. THE CSRF_Protector SHALL generate CSRF tokens with a minimum of 256 bits of entropy
4. THE CSRF_Protector SHALL set the `csrftoken` cookie with `SameSite=Strict` attribute
5. WHILE `ENVIRONMENT=production` is set, THE CSRF_Protector SHALL set the `csrftoken` cookie
   with `Secure=True` attribute
6. THE CSRF_Protector SHALL set the `csrftoken` cookie with `HttpOnly=True` attribute
7. IF the `CSRF_SECRET_KEY` environment variable is not set at application startup, THEN THE
   application SHALL fail to start with a descriptive error message indicating the missing
   variable

### Requirement 2: Validar CSRF token en endpoints de escritura

**User Story:** Como administrador de seguridad, quiero que todos los endpoints de escritura
validen el token CSRF antes de ejecutar, para bloquear automáticamente cualquier request
falsificado que no provenga del frontend legítimo.

#### Acceptance Criteria

1. WHEN a request uses the POST method on any non-exempt endpoint, THE CSRF_Protector SHALL
   validate the CSRF token before the route handler executes
2. WHEN a request uses the PUT method on any non-exempt endpoint, THE CSRF_Protector SHALL
   validate the CSRF token before the route handler executes
3. WHEN a request uses the PATCH method on any non-exempt endpoint, THE CSRF_Protector SHALL
   validate the CSRF token before the route handler executes
4. WHEN a request uses the DELETE method on any non-exempt endpoint, THE CSRF_Protector SHALL
   validate the CSRF token before the route handler executes
5. WHEN a CSRF token is missing from a write request to a non-exempt endpoint, THE CSRF_Protector
   SHALL return HTTP 403 with the message "CSRF token missing or invalid"
6. WHEN a CSRF token is present but invalid or expired on a write request, THE CSRF_Protector
   SHALL return HTTP 403 with the message "CSRF token missing or invalid"
7. THE CSRF_Protector SHALL accept the CSRF token exclusively from the `X-CSRF-Token` request
   header
8. THE CSRF_Protector SHALL NOT validate CSRF tokens for requests to the following Exempt_Paths:
   `/auth/login`, `/auth/refresh`, `/health`, `/docs`, `/openapi.json`, `/whatsapp/webhook`

### Requirement 3: Integrar CSRF token en frontend React (api.js)

**User Story:** Como desarrollador frontend, quiero que `api.js` incluya automáticamente el
token CSRF en todas las requests de escritura y maneje la renovación del token de forma
transparente, para que el frontend funcione correctamente con la protección CSRF del backend
sin requerir cambios en cada llamada individual.

#### Acceptance Criteria

1. WHEN `api.js` initializes, THE Frontend_HTTP_Client SHALL read the CSRF token from the
   `csrftoken` cookie
2. WHEN `api.js` sends a POST request, THE Frontend_HTTP_Client SHALL include the current CSRF
   token in the `X-CSRF-Token` header
3. WHEN `api.js` sends a PUT request, THE Frontend_HTTP_Client SHALL include the current CSRF
   token in the `X-CSRF-Token` header
4. WHEN `api.js` sends a PATCH request, THE Frontend_HTTP_Client SHALL include the current CSRF
   token in the `X-CSRF-Token` header
5. WHEN `api.js` sends a DELETE request, THE Frontend_HTTP_Client SHALL include the current CSRF
   token in the `X-CSRF-Token` header
6. WHEN a write request fails with HTTP 403 and the response indicates a CSRF error, THE
   Frontend_HTTP_Client SHALL refresh the CSRF token from the `csrftoken` cookie and retry the
   original request exactly once
7. IF the retry also fails with HTTP 403, THE Frontend_HTTP_Client SHALL propagate the error to
   the caller without further retries

### Requirement 4: Headers de seguridad HTTP

**User Story:** Como administrador de seguridad, quiero que todas las respuestas HTTP incluyan
los headers de seguridad estándar, para proteger a los usuarios del sistema contra ataques
comunes del navegador como clickjacking, MIME sniffing y XSS.

#### Acceptance Criteria

1. THE Security_Headers_Middleware SHALL add `X-Content-Type-Options: nosniff` to all HTTP
   responses
2. THE Security_Headers_Middleware SHALL add `X-Frame-Options: DENY` to all HTTP responses
3. THE Security_Headers_Middleware SHALL add `X-XSS-Protection: 1; mode=block` to all HTTP
   responses
4. THE Security_Headers_Middleware SHALL add
   `Referrer-Policy: strict-origin-when-cross-origin` to all HTTP responses
5. THE Security_Headers_Middleware SHALL add a `Content-Security-Policy` header with a
   restrictive policy that allows only same-origin scripts, styles, and images by default
6. WHILE `ENVIRONMENT=production` is set, THE Security_Headers_Middleware SHALL add
   `Strict-Transport-Security: max-age=31536000; includeSubDomains` to all HTTP responses
7. THE Security_Headers_Middleware SHALL be registered in `main.py` before any route handler
   middleware, ensuring headers are present on all responses including error responses

## Correctness Properties for Property-Based Testing

### Property 1: CSRF Enforcement en Endpoints de Escritura

Para todo Write_Endpoint no exento y para todo request sin un token CSRF válido, el sistema
retorna HTTP 403.

Formalmente:
`∀ (endpoint, method) donde method ∈ {POST, PUT, PATCH, DELETE} y endpoint ∉ Exempt_Paths:`
`request(endpoint, method, csrf_token=None).status_code == 403`

**Tipo:** Property-based test (Hypothesis, variando endpoint y método HTTP)
**Aplica a:** Requirement 2 — validación CSRF en endpoints de escritura

### Property 2: Presencia de Headers de Seguridad

Para toda respuesta HTTP del sistema, los headers de seguridad requeridos están presentes con
los valores correctos.

Formalmente:
`∀ (endpoint, method, auth_state):`
`response(endpoint, method, auth_state).headers` contiene todos los headers definidos en
Requirement 4 con sus valores exactos

**Tipo:** Property-based test (Hypothesis, variando endpoint, método y estado de autenticación)
**Aplica a:** Requirement 4 — headers de seguridad HTTP
