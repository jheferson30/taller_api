import os
import socket
import threading
import uuid
import time
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv()

from app.configuracion.base_datos import Base, engine
from app.configuracion.limiter import limiter
from app.rutas import (
    economia_ruta, movimiento_caja_ruta, ticket_ruta, upload_ruta,
    vehiculo_ruta, seguridad_ruta, citas_ruta, mobile_api_ruta, configuracion_ruta,
    whatsapp_ruta,
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

    # mDNS
    threading.Thread(target=_anunciar_mdns, daemon=True).start()
    yield


app = FastAPI(title="API Taller Mecanico", lifespan=lifespan)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if _raw_origins and _raw_origins != "*":
    _origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    # Orígenes seguros por defecto (localhost dev + red local)
    _origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"http://192\.168\.\d+\.\d+(:\d+)?",  # red local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
