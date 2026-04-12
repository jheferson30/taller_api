import os
import socket
import threading
import time
import traceback
import uuid
import warnings
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv()

# Validar configuración al iniciar
from app.configuracion.config_validator import ConfigValidationError, validate_config
from app.utils.exceptions import (
    ConfigurationError,
    ConflictError,
    DomainException,
    DuplicateError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    RateLimitExceededError,
    ResourceNotFoundError,
    SecurityAlertError,
    TokenBlacklistedError,
    ValidationError,
)

try:
    validate_config()
except ConfigValidationError as e:
    print(f"\n❌ Error de configuración: {e}")
    print("La aplicación no puede iniciar. Por favor corrija el archivo .env\n")
    exit(1)

import app.modelos.configuracion_taller  # noqa
import app.modelos.log_notificacion  # noqa
import app.modelos.mecanico  # noqa
from app.configuracion.base_datos import Base, engine
from app.configuracion.limiter import limiter
from app.rutas import (
    audit_ruta,
    auth_ruta,
    citas_ruta,
    configuracion_ruta,
    economia_ruta,
    mobile_api_ruta,
    movimiento_caja_ruta,
    pdf_ruta,
    seguridad_ruta,
    ticket_ruta,
    upload_ruta,
    users_ruta,
    vehiculo_ruta,
    whatsapp_ruta,
)

Base.metadata.create_all(bind=engine)

# ── Tokens temporales para QR (UUID → expira en 5 min) ──────────────────────
_qr_tokens: dict[str, float] = {}
_QR_TTL = 300  # segundos


def _generar_token_qr() -> str:
    token = str(uuid.uuid4())
    _qr_tokens[token] = time.time() + _QR_TTL
    # Limpiar tokens expirados
    ahora = time.time()
    expirados = [t for t, exp in _qr_tokens.items() if exp < ahora]
    for t in expirados:
        del _qr_tokens[t]
    return token


def validar_token_qr(token: str) -> bool:
    exp = _qr_tokens.get(token)
    if exp and time.time() < exp:
        del _qr_tokens[token]  # un solo uso
        return True
    return False


# ── Ciclo de vida (reemplaza @app.on_event deprecado) ───────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar SecretsManager
    from app.configuracion.secrets_manager import SecretsManager

    secrets_manager = SecretsManager()
    app.state.secrets_manager = secrets_manager

    # Validar variables de entorno
    try:
        secrets_manager.get_secret("pdf-password", fallback_env_var="PDF_PASSWORD")
    except RuntimeError:
        raise RuntimeError("PDF_PASSWORD not found in secrets or environment")

    try:
        secrets_manager.get_secret("admin-password", fallback_env_var="ADMIN_PASSWORD")
    except RuntimeError:
        raise RuntimeError("ADMIN_PASSWORD not found in secrets or environment")

    # CORS warning
    allowed = os.getenv("ALLOWED_ORIGINS", "")
    if not allowed or allowed.strip() == "*":
        warnings.warn(
            "[SEGURIDAD] CORS abierto a todos los orígenes (*). "
            "Define ALLOWED_ORIGINS en .env para producción.",
            stacklevel=2,
        )

    # Inicializar caché Redis
    try:
        from app.configuracion.cache import init_cache

        await init_cache()
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo inicializar caché Redis: {e}")
        print("La aplicación continuará sin caché. Asegúrate de que Redis esté corriendo.")

    # mDNS
    threading.Thread(target=_anunciar_mdns, daemon=True).start()
    yield


app = FastAPI(title="API Taller Mecanico", lifespan=lifespan)


# ── Custom OpenAPI Schema ─────────────────────────────────────────────────────
def custom_openapi():
    """
    Customize OpenAPI schema with comprehensive API documentation.

    Adds:
    - Detailed API description with authentication guide
    - JWT Bearer security scheme
    - Rate limiting documentation
    - Role-based access control information
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title="Taller Mecánico API",
        version="1.1.0",
        description="""
# API de Gestión de Taller Mecánico

Sistema completo para gestión de talleres de motos con control de tickets, vehículos,
procesos, repuestos, pagos y auditoría.

## Características Principales

- **Gestión de Tickets**: Creación y seguimiento de órdenes de servicio
- **Control de Vehículos**: Registro de motos y propietarios
- **Procesos y Repuestos**: Documentación detallada de trabajos realizados
- **Sistema de Pagos**: Control de anticipos, cobros y movimientos de caja
- **Autenticación JWT**: Seguridad con tokens de acceso y refresh
- **Auditoría Completa**: Registro de todos los eventos del sistema
- **Notificaciones WhatsApp**: Alertas automáticas a clientes

## Autenticación

La API usa JWT (JSON Web Tokens) para autenticación:

### 1. Obtener Tokens
```
POST /auth/login
{
  "username": "admin",
  "password": "your_password"
}
```

Respuesta:
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "user": {
    "id": 1,
    "username": "admin",
    "roles": ["ADMIN"]
  }
}
```

### 2. Usar Access Token
Incluir en header de todas las peticiones autenticadas:
```
Authorization: Bearer <access_token>
```

### 3. Refrescar Token
Cuando el access_token expire (15 minutos):
```
POST /auth/refresh
{
  "refresh_token": "eyJhbGci..."
}
```

### 4. Cerrar Sesión
```
POST /auth/logout
{
  "refresh_token": "eyJhbGci..."
}
```

## Roles y Permisos

### ADMIN
- Acceso completo al sistema
- Gestión de usuarios
- Configuración del taller
- Acceso a auditoría

### MECANICO
- Gestión de tickets y procesos
- Agregar repuestos y fotos
- Finalizar trabajos
- Consultar información

### RECEPCIONISTA
- Crear tickets de ingreso
- Registrar vehículos
- Consultar información
- Generar reportes

### SOLO_LECTURA
- Solo consultas
- Sin permisos de escritura

## Rate Limiting

Límites por categoría de endpoint:

### Autenticación
- **Login**: 5 req/min por IP
- **Refresh**: 10 req/min por IP
- **Forgot Password**: 3 req/hora por IP

### Operaciones de Escritura
- **Crear recursos**: 30 req/min por usuario
- **Actualizar recursos**: 30 req/min por usuario
- **Eliminar recursos**: 30 req/min por usuario

### Operaciones de Lectura
- **Consultas generales**: 100 req/min por usuario
- **Búsquedas**: 100 req/min por usuario

### Generación de PDFs
- **PDF de tickets**: 20 req/min por usuario

## Códigos de Estado HTTP

### Éxito
- **200 OK**: Operación exitosa
- **201 Created**: Recurso creado exitosamente
- **204 No Content**: Operación exitosa sin contenido de respuesta

### Errores del Cliente
- **400 Bad Request**: Datos de entrada inválidos
- **401 Unauthorized**: Autenticación requerida o token inválido
- **403 Forbidden**: Permisos insuficientes
- **404 Not Found**: Recurso no encontrado
- **409 Conflict**: Conflicto (ej: placa duplicada)
- **413 Payload Too Large**: Archivo muy grande (>10MB)
- **415 Unsupported Media Type**: Tipo de archivo no permitido
- **422 Unprocessable Entity**: Error de validación de Pydantic
- **429 Too Many Requests**: Rate limit excedido

### Errores del Servidor
- **500 Internal Server Error**: Error interno del servidor

## Formato de Errores

Todos los errores siguen este formato:
```json
{
  "error": "error_code",
  "message": "Descripción del error",
  "details": {}
}
```

## Paginación

Endpoints de listado soportan paginación:
```
GET /tickets/buscar?page=1&per_page=50
```

Respuesta:
```json
{
  "tickets": [...],
  "total": 150,
  "page": 1,
  "per_page": 50,
  "pages": 3
}
```

## Filtros

Muchos endpoints soportan filtros por query params:
```
GET /movimientos-caja/?tipo=INGRESO_ANTICIPO&fecha_desde=2026-04-01&fecha_hasta=2026-04-30
```

## Compresión HTTP

Todas las respuestas >1KB son comprimidas con GZip automáticamente.
Incluir header: `Accept-Encoding: gzip`

## CORS

Configurado para permitir orígenes específicos en producción.
En desarrollo: localhost:5173, localhost:3000

## Seguridad

- Contraseñas hasheadas con bcrypt
- Tokens JWT firmados con HS256
- CSRF protection en endpoints de escritura
- HTTPS forzado en producción
- Rate limiting por IP y usuario
- Auditoría completa de eventos de seguridad

## Soporte

Para soporte técnico:
- Email: jefersoncely0@gmail.com
- WhatsApp: +57 314 571 9752
        """,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtenido del endpoint /auth/login. Formato: Bearer <token>",
        }
    }

    # Add global security requirement (can be overridden per endpoint)
    # Note: Some endpoints like /auth/login don't require auth, they override this
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ── Global Exception Handlers ────────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    """Maneja errores de credenciales inválidas (401 Unauthorized)."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "authentication_failed",
            "message": exc.message,
            "details": exc.details if ENVIRONMENT == "development" else {},
        },
    )


@app.exception_handler(InsufficientPermissionsError)
async def insufficient_permissions_handler(request: Request, exc: InsufficientPermissionsError):
    """Maneja errores de permisos insuficientes (403 Forbidden)."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "insufficient_permissions",
            "message": exc.message,
            "details": exc.details if ENVIRONMENT == "development" else {},
        },
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Maneja errores de validación (400 Bad Request)."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
    """Maneja errores de recurso no encontrado (404 Not Found)."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "resource_not_found",
            "message": exc.message,
            "details": exc.details if ENVIRONMENT == "development" else {},
        },
    )


@app.exception_handler(DuplicateError)
async def duplicate_error_handler(request: Request, exc: DuplicateError):
    """Maneja errores de duplicación (409 Conflict)."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "duplicate_resource",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_exceeded_error_handler(request: Request, exc: RateLimitExceededError):
    """Maneja errores de rate limiting (429 Too Many Requests)."""
    retry_after = exc.details.get("retry_after", 60)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": exc.message,
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


@app.exception_handler(TokenBlacklistedError)
async def token_blacklisted_handler(request: Request, exc: TokenBlacklistedError):
    """Maneja errores de token en lista negra (401 Unauthorized)."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "token_blacklisted",
            "message": exc.message,
            "details": exc.details if ENVIRONMENT == "development" else {},
        },
    )


@app.exception_handler(SecurityAlertError)
async def security_alert_handler(request: Request, exc: SecurityAlertError):
    """Maneja alertas de seguridad (403 Forbidden)."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "security_alert",
            "message": exc.message,
            "details": exc.details if ENVIRONMENT == "development" else {},
        },
    )


@app.exception_handler(ConflictError)
async def conflict_error_handler(request: Request, exc: ConflictError):
    """Maneja errores de conflicto en sincronización (409 Conflict)."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "conflict",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError):
    """Maneja errores de configuración (500 Internal Server Error)."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "configuration_error",
            "message": "Error de configuración del sistema"
            if ENVIRONMENT == "production"
            else exc.message,
            "details": exc.details if ENVIRONMENT == "development" else {},
        },
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    """Maneja excepciones de dominio genéricas (500 Internal Server Error)."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "Error interno del servidor" if ENVIRONMENT == "production" else exc.message,
            "details": exc.details if ENVIRONMENT == "development" else {},
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Maneja todas las excepciones no capturadas.

    En producción: Oculta stack traces y retorna mensaje genérico.
    En desarrollo: Incluye stack trace completo para debugging.
    """
    # Log del error con contexto completo
    error_id = str(uuid.uuid4())
    error_context = {
        "error_id": error_id,
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else "unknown",
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
    }

    if ENVIRONMENT == "development":
        error_context["traceback"] = traceback.format_exc()

    # En producción, esto debería ir a un sistema de logging centralizado
    print(f"[ERROR {error_id}] Unhandled exception: {error_context}")

    # Respuesta al cliente
    if ENVIRONMENT == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "Ha ocurrido un error interno. Por favor contacte al administrador.",
                "error_id": error_id,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": str(exc),
                "error_id": error_id,
                "traceback": traceback.format_exc().split("\n"),
            },
        )


# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS (DEBE IR PRIMERO - se ejecuta último en la cadena) ──────────────────
# IMPORTANTE: En FastAPI, los middlewares se ejecutan en orden inverso al que se agregan.
# El último middleware agregado es el primero en ejecutarse.
# CORS debe ejecutarse PRIMERO para agregar headers antes que cualquier otro middleware.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if _raw_origins and _raw_origins != "*":
    _origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    # En producción, ALLOWED_ORIGINS debe estar configurado explícitamente
    if os.getenv("ENVIRONMENT") == "production":
        raise RuntimeError(
            "ALLOWED_ORIGINS must be set in production environment. "
            "Configure ALLOWED_ORIGINS in .env with specific origins (e.g., https://taller.com,https://app.taller.com)"
        )
    # En desarrollo, usar orígenes seguros por defecto
    _origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# ── GZip Compression Middleware ───────────────────────────────────────────────
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Only compress responses > 1KB
    compresslevel=6,  # Balance between speed and compression ratio (1-9)
)

# ── Auth Middleware ───────────────────────────────────────────────────────────
from app.seguridad.auth_middleware import AuthMiddleware
from app.seguridad.dependencias import require_jwt_auth

app.add_middleware(AuthMiddleware)

# ── HTTPS and Security Middleware (Production Only) ───────────────────────────
if os.getenv("ENVIRONMENT") == "production":
    # Redirigir HTTP → HTTPS automáticamente
    app.add_middleware(HTTPSRedirectMiddleware)

    # Validar hosts confiables
    allowed_hosts = os.getenv("ALLOWED_HOSTS", "").strip()
    if allowed_hosts:
        hosts_list = [h.strip() for h in allowed_hosts.split(",") if h.strip()]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts_list)

# ── Directorios y archivos estáticos ─────────────────────────────────────────
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/fotos", exist_ok=True)
os.makedirs("uploads/compras", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

FRONTEND_DIST = os.path.join("frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="frontend-assets",
    )

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_ruta.router)
app.include_router(users_ruta.router)
app.include_router(audit_ruta.router)
app.include_router(vehiculo_ruta.router)
app.include_router(economia_ruta.router)
app.include_router(movimiento_caja_ruta.router)
app.include_router(ticket_ruta.router)
app.include_router(ticket_ruta.router_pdf)
app.include_router(upload_ruta.router)
app.include_router(pdf_ruta.router)
app.include_router(seguridad_ruta.router)
app.include_router(citas_ruta.router)
app.include_router(mobile_api_ruta.router)
app.include_router(configuracion_ruta.router)
app.include_router(whatsapp_ruta.router)


# ── mDNS ──────────────────────────────────────────────────────────────────────
def _anunciar_mdns():
    try:
        import socket as _socket

        from zeroconf import ServiceInfo, Zeroconf

        zc = Zeroconf()
        try:
            s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
            s.close()
        except Exception:
            ip_local = "127.0.0.1"
        info = ServiceInfo(
            "_http._tcp.local.",
            "taller-mecaapp._http._tcp.local.",
            addresses=[_socket.inet_aton(ip_local)],
            port=8000,
            properties={"path": "/api/mobile"},
            server="taller-mecaapp.local.",
        )
        zc.register_service(info)
    except Exception as e:
        print(f"[mDNS] No se pudo anunciar: {e}")


# ── Endpoints de info ─────────────────────────────────────────────────────────
def _get_ip_local() -> str:
    public_ip = os.getenv("PUBLIC_IP")
    if public_ip:
        return public_ip
    # Intentar obtener IP pública automáticamente
    try:
        import urllib.request

        with urllib.request.urlopen("https://api.ipify.org", timeout=2) as r:
            return r.read().decode().strip()
    except Exception:
        pass
    # Fallback a IP de interfaz de red (red local)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.get("/info")
def info_sistema():
    ip_local = _get_ip_local()
    return {
        "sistema": "MecaApp",
        "version": "1.1.0",
        "ip_servidor": ip_local,
        "puerto": 8000,
        "url_app_movil": f"http://{ip_local}:8000",
    }


@app.get(
    "/admin/sistema-info",
    dependencies=[Depends(require_jwt_auth)],
    summary="Información del sistema (solo ADMIN)",
)
def admin_info_sistema(request: Request):
    """Endpoint protegido con información del desarrollador para soporte técnico."""
    user = request.state.user
    roles = [r.get("nombre") if isinstance(r, dict) else str(r) for r in (user.get("roles") or [])]
    if "ADMIN" not in roles:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=403, detail="Solo administradores pueden ver esta información"
        )
    ip_local = _get_ip_local()
    return {
        "sistema": "MecaApp",
        "version": "1.1.0",
        "ip_servidor": ip_local,
        "puerto": 8000,
        "desarrollador": {
            "empresa": "J&J Soluciones de Software",
            "correo": "jefersoncely0@gmail.com",
        },
    }


@app.get("/info/conexion-qr")
def info_conexion_qr():
    """
    Devuelve un token temporal de un solo uso (TTL 5 min).
    La app móvil usa el token para autenticarse, NO la contraseña real.
    """
    import base64
    import json

    ip_local = _get_ip_local()
    token = _generar_token_qr()
    payload = json.dumps({"ip": ip_local, "puerto": 8000, "token": token})
    encoded = base64.b64encode(payload.encode()).decode()
    return {"qr_data": encoded, "ip": ip_local, "puerto": 8000}


@app.get("/")
def inicio():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"mensaje": "API del Taller funcionando correctamente"}


@app.get("/{full_path:path}")
def servir_frontend(full_path: str):
    api_prefixes = (
        "tickets",
        "vehiculos",
        "economia-dia",
        "movimientos",
        "upload",
        "seguridad",
        "citas",
        "api",
        "uploads",
        "configuracion",
        "info",
    )
    if any(full_path.startswith(p) for p in api_prefixes):
        from fastapi import HTTPException

        raise HTTPException(status_code=404)
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"mensaje": "API del Taller funcionando correctamente"}
