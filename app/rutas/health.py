"""
Endpoints de health check y información del servicio.
Usados por Docker healthchecks y monitoreo.
"""

import os
import socket
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.configuracion.base_datos import engine

router = APIRouter(tags=["Health"])


def _get_ip_local() -> str:
    public_ip = os.getenv("PUBLIC_IP")
    if public_ip:
        return public_ip
    try:
        import urllib.request

        with urllib.request.urlopen("https://api.ipify.org", timeout=2) as r:
            return r.read().decode().strip()
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@router.get("/health")
async def health_check():
    """
    Health check endpoint para Docker y monitoreo.

    Verifica:
    - API está respondiendo
    - Base de datos está accesible
    - Redis está accesible (opcional)

    Returns:
        dict: Estado de salud del servicio
    """
    health_status = {
        "status": "healthy",
        "service": "mecaapp-api",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }

    # Check database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"

    # Check Redis (opcional - no falla si Redis no está disponible)
    try:
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception:
        # Redis es opcional, no marca como unhealthy
        health_status["checks"]["redis"] = "not_configured"

    return health_status


@router.get("/info")
async def service_info():
    """
    Información del servicio incluyendo IP del servidor para la app móvil.
    """
    ip_local = _get_ip_local()
    return {
        "name": "MecaApp API",
        "version": "2.0.0",
        "description": "Sistema de gestión de taller mecánico",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": "3.11",
        "framework": "FastAPI",
        "database": "PostgreSQL 15",
        "cache": "Redis 7",
        # Campos usados por el frontend para mostrar IP de conexión
        "sistema": "MecaApp",
        "ip_servidor": ip_local,
        "puerto": 8000,
        "url_app_movil": f"http://{ip_local}:8000",
    }


@router.get("/ping")
async def ping():
    """
    Ping simple para verificar que la API está viva.

    Returns:
        dict: Respuesta simple
    """
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}
