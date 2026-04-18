"""
Endpoints de health check y información del servicio.
Usados por Docker healthchecks y monitoreo.
"""

import os
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.configuracion.base_datos import engine

router = APIRouter(tags=["Health"])


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
    Información del servicio.

    Returns:
        dict: Información básica del servicio
    """
    return {
        "name": "MecaApp API",
        "version": "2.0.0",
        "description": "Sistema de gestión de taller mecánico",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": "3.11",
        "framework": "FastAPI",
        "database": "PostgreSQL 15",
        "cache": "Redis 7",
    }


@router.get("/ping")
async def ping():
    """
    Ping simple para verificar que la API está viva.

    Returns:
        dict: Respuesta simple
    """
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}
