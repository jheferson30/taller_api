from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import socket
import threading
from dotenv import load_dotenv

load_dotenv()

from app.configuracion.base_datos import Base, engine
from app.rutas import economia_ruta, movimiento_caja_ruta, ticket_ruta, upload_ruta, vehiculo_ruta, seguridad_ruta, citas_ruta, mobile_api_ruta, configuracion_ruta
# Importar modelos para que SQLAlchemy los registre
import app.modelos.mecanico  # noqa
import app.modelos.configuracion_taller  # noqa
Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Taller Mecanico")

# Crear directorios necesarios
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/fotos", exist_ok=True)
os.makedirs("uploads/compras", exist_ok=True)

# Archivos estáticos de uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Servir el frontend compilado si existe
FRONTEND_DIST = os.path.join("frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend-assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.on_event("startup")
def validar_variables_entorno():
    if not os.getenv("PDF_PASSWORD"):
        raise RuntimeError("PDF_PASSWORD env var is required")
    if not os.getenv("ADMIN_PASSWORD") and not os.getenv("PDF_PASSWORD"):
        raise RuntimeError("ADMIN_PASSWORD env var is required")
    # Anunciar servidor en la red local via mDNS
    threading.Thread(target=_anunciar_mdns, daemon=True).start()


def _anunciar_mdns():
    """Anuncia el servidor como 'taller-pulga.local' en la red WiFi."""
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


@app.get("/info")
def info_sistema():
    # Obtener IP local de red
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
    except Exception:
        ip_local = "127.0.0.1"
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
    """Devuelve los datos de conexión para generar el QR en el frontend."""
    from app.seguridad.dependencias import requerir_password_admin
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
    except Exception:
        ip_local = "127.0.0.1"
    import json, base64
    payload = json.dumps({"ip": ip_local, "puerto": 8000, "password": os.getenv("ADMIN_PASSWORD", "")})
    encoded = base64.b64encode(payload.encode()).decode()
    return {"qr_data": encoded, "ip": ip_local, "puerto": 8000}


@app.get("/")
def inicio():
    # Si existe el frontend compilado, servirlo
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"mensaje": "API del Taller funcionando correctamente"}


# Catch-all para rutas del frontend (React Router)
@app.get("/{full_path:path}")
def servir_frontend(full_path: str):
    # No interceptar rutas de la API
    api_prefixes = ("tickets", "vehiculos", "economia-dia", "movimientos", "upload",
                    "seguridad", "citas", "api", "uploads", "configuracion")
    if any(full_path.startswith(p) for p in api_prefixes):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"mensaje": "API del Taller funcionando correctamente"}
