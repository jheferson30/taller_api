import os
import socket
import threading
import uuid
import time
import warnings
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic_settings import BaseSettings

load_dotenv()

# ── CSRF Configuration ────────────────────────────────────────────────────────
class CsrfSettings(BaseSettings):
    """Configuración de protección CSRF"""
    secret_key: str = os.getenv("CSRF_SECRET_KEY", "")
    cookie_samesite: str = "strict"
    cookie_secure: bool = os.getenv("ENVIRONMENT") == "production"
    # httponly=False permite que JavaScript lea el token CSRF
    # Esto es seguro: el token CSRF no es sensible como un JWT
    # Solo valida que la petición viene del mismo origen (protección CSRF)
    cookie_httponly: bool = False
    # Deshabilitar protección automática - solo validar cuando se llama explícitamente
    # Esto evita que OPTIONS (CORS preflight) sean bloqueadas
    methods: list = []  # Lista vacía = no validar automáticamente ningún método

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

# Validar configuración al iniciar
from app.configuracion.config_validator import validate_config, ConfigValidationError
from app.utils.exceptions import (
    DomainException,
    InvalidCredentialsError,
    InsufficientPermissionsError,
    ValidationError,
    ResourceNotFoundError,
    DuplicateError,
    RateLimitExceededError,
    TokenBlacklistedError,
    SecurityAlertError,
    ConflictError,
    ConfigurationError,
)

try:
    validate_config()
except ConfigValidationError as e:
    print(f"\n❌ Error de configuración: {e}")
    print("La aplicación no puede iniciar. Por favor corrija el archivo .env\n")
    exit(1)

from app.configuracion.base_datos import Base, engine
from app.configuracion.limiter import limiter
from app.rutas import (
    economia_ruta, movimiento_caja_ruta, ticket_ruta, upload_ruta,
    vehiculo_ruta, seguridad_ruta, citas_ruta, mobile_api_ruta, configuracion_ruta,
    whatsapp_ruta, auth_ruta, users_ruta, audit_ruta,
)
import app.modelos.mecanico  # noqa
import app.modelos.configuracion_taller  # noqa
import app.modelos.log_notificacion  # noqa

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
    # Validar variables de entorno
    if not os.getenv("PDF_PASSWORD"):
        raise RuntimeError("PDF_PASSWORD env var is required")
    if not os.getenv("ADMIN_PASSWORD"):
        raise RuntimeError("ADMIN_PASSWORD env var is required")

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
            "message": "Error de configuración del sistema" if ENVIRONMENT == "production" else exc.message,
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


@app.exception_handler(CsrfProtectError)
async def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    """
    Maneja errores de validación CSRF (403 Forbidden).
    
    Cuando una petición no incluye un token CSRF válido, se rechaza con 403.
    Las peticiones OPTIONS (CORS preflight) se permiten sin validación CSRF.
    """
    # Permitir peticiones OPTIONS sin validación CSRF (CORS preflight)
    if request.method == "OPTIONS":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "OK"}
        )
    
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "csrf_validation_failed",
            "message": "Token CSRF inválido o ausente. Por favor recargue la página e intente nuevamente.",
            "details": {"csrf_error": str(exc)} if ENVIRONMENT == "development" else {},
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

# ── Auth Middleware ───────────────────────────────────────────────────────────
from app.seguridad.auth_middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# ── HTTPS and Security Middleware (Production Only) ───────────────────────────
if os.getenv("ENVIRONMENT") == "production":
    # Redirigir HTTP → HTTPS automáticamente
    app.add_middleware(HTTPSRedirectMiddleware)
    
    # Validar hosts confiables
    allowed_hosts = os.getenv("ALLOWED_HOSTS", "").strip()
    if allowed_hosts:
        hosts_list = [h.strip() for o in allowed_hosts.split(",") if h.strip()]
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=hosts_list
        )

# ── Directorios y archivos estáticos ─────────────────────────────────────────
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/fotos", exist_ok=True)
os.makedirs("uploads/compras", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

FRONTEND_DIST = os.path.join("frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend-assets")

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
app.include_router(seguridad_ruta.router)
app.include_router(citas_ruta.router)
app.include_router(mobile_api_ruta.router)
app.include_router(configuracion_ruta.router)
app.include_router(whatsapp_ruta.router)


# ── mDNS ──────────────────────────────────────────────────────────────────────
def _anunciar_mdns():
    try:
        from zeroconf import Zeroconf, ServiceInfo
        import socket as _socket
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
            "taller-pulga._http._tcp.local.",
            addresses=[_socket.inet_aton(ip_local)],
            port=8000,
            properties={"path": "/api/mobile"},
            server="taller-pulga.local.",
        )
        zc.register_service(info)
    except Exception as e:
        print(f"[mDNS] No se pudo anunciar: {e}")


# ── Endpoints de info ─────────────────────────────────────────────────────────
def _get_ip_local() -> str:
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
        "sistema": "Taller Manager",
        "version": "1.1.0",
        "ip_servidor": ip_local,
        "puerto": 8000,
        "url_app_movil": f"http://{ip_local}:8000",
        "desarrollador": {
            "nombre": "Jheferson Esney Cely Arango",
            "whatsapp": "3145719752",
            "telefono": "3145719752",
            "correo": "jefersoncely0@gmail.com",
        }
    }


@app.get("/csrf-token")
def get_csrf_token(request: Request, csrf_protect: CsrfProtect = Depends()):
    """
    Endpoint para obtener el token CSRF.
    Genera y envía el token como cookie Y en el response body.
    """
    # Generar el token CSRF
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse(content={
        "message": "CSRF token set",
        "csrf_token": csrf_token  # Enviar también en el body para que el frontend lo use
    })
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@app.get("/info/conexion-qr")
def info_conexion_qr():
    """
    Devuelve un token temporal de un solo uso (TTL 5 min).
    La app móvil usa el token para autenticarse, NO la contraseña real.
    """
    import json, base64
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
        "tickets", "vehiculos", "economia-dia", "movimientos", "upload",
        "seguridad", "citas", "api", "uploads", "configuracion", "info",
    )
    if any(full_path.startswith(p) for p in api_prefixes):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"mensaje": "API del Taller funcionando correctamente"}
