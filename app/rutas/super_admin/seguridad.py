"""
Router del Security Dashboard para SUPER_ADMIN.

Expone métricas de seguridad en tiempo real consultando la tabla audit_log.
Las respuestas se cachean en Redis durante 60 segundos para reducir la carga
sobre la base de datos ante consultas frecuentes.

Endpoint:
    GET /super-admin/seguridad/metricas
"""

import json
import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.seguridad_metricas import (
    DailyCount,
    HourlyCount,
    IPViolationEntry,
    SecurityMetricsResponse,
    UserViolationEntry,
)
from app.repositorios.security_metrics_repository import SecurityMetricsRepository
from app.seguridad.auth_middleware import require_auth, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/super-admin", tags=["Super Admin — Seguridad"])

# Configuración del caché Redis
_CACHE_KEY = "security_metrics_cache"
_CACHE_TTL = 60  # segundos


def _get_redis_client():
    """
    Obtiene un cliente Redis síncrono para el caché de métricas.

    Returns:
        Cliente Redis, o ``None`` si Redis no está disponible.
        En ese caso las métricas se calculan en cada request sin caché.
    """
    try:
        import redis as redis_lib

        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        client = redis_lib.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        logger.warning(
            "Redis no disponible para caché de métricas de seguridad (%s). "
            "Las métricas se calcularán sin caché.",
            exc,
        )
        return None


def _compute_metrics(db: Session) -> dict:
    """
    Calcula todas las métricas de seguridad consultando la base de datos.

    Args:
        db: Sesión de SQLAlchemy activa.

    Returns:
        Diccionario serializable con todas las métricas y ``generated_at``.
    """
    repo = SecurityMetricsRepository(db)

    rate_limit_rows = repo.get_rate_limit_violations_24h()
    cross_tenant_rows = repo.get_cross_tenant_attempts_30d()
    failed_auth_rows = repo.get_failed_auth_attempts_24h()
    top_ips = repo.get_top_ips_by_violations(limit=10)
    top_users = repo.get_top_users_by_violations(limit=10)

    return {
        "rate_limit_violations_24h": [
            {"hour": row["hour"].isoformat(), "count": row["count"]}
            for row in rate_limit_rows
        ],
        "cross_tenant_attempts_30d": [
            {"day": row["day"].isoformat(), "count": row["count"]}
            for row in cross_tenant_rows
        ],
        "failed_auth_attempts_24h": [
            {"hour": row["hour"].isoformat(), "count": row["count"]}
            for row in failed_auth_rows
        ],
        "top_ips_by_violations": top_ips,
        "top_users_by_violations": top_users,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _build_response(data: dict, cache_hit: bool) -> SecurityMetricsResponse:
    """
    Construye el objeto ``SecurityMetricsResponse`` a partir del dict de métricas.

    Args:
        data: Diccionario con las métricas (puede venir de caché o de BD).
        cache_hit: True si los datos provienen del caché Redis.

    Returns:
        Instancia de ``SecurityMetricsResponse`` lista para serializar.
    """
    return SecurityMetricsResponse(
        rate_limit_violations_24h=[
            HourlyCount(hour=datetime.fromisoformat(row["hour"]), count=row["count"])
            for row in data["rate_limit_violations_24h"]
        ],
        cross_tenant_attempts_30d=[
            DailyCount(day=datetime.fromisoformat(row["day"]), count=row["count"])
            for row in data["cross_tenant_attempts_30d"]
        ],
        failed_auth_attempts_24h=[
            HourlyCount(hour=datetime.fromisoformat(row["hour"]), count=row["count"])
            for row in data["failed_auth_attempts_24h"]
        ],
        top_ips_by_violations=[
            IPViolationEntry(
                ip_address=entry["ip_address"],
                total_violations=entry["total_violations"],
            )
            for entry in data["top_ips_by_violations"]
        ],
        top_users_by_violations=[
            UserViolationEntry(
                user_id=entry["user_id"],
                total_violations=entry["total_violations"],
            )
            for entry in data["top_users_by_violations"]
        ],
        generated_at=datetime.fromisoformat(data["generated_at"]),
        cache_hit=cache_hit,
    )


@router.get("/seguridad/metricas", response_model=SecurityMetricsResponse)
@require_auth
@require_role("SUPER_ADMIN")
async def get_security_metrics(
    request: Request,
    db: Session = Depends(obtener_db),
) -> SecurityMetricsResponse:
    """
    Retorna métricas de seguridad en tiempo real para el SUPER_ADMIN.

    Las métricas incluyen:
    - Violaciones de rate limit por hora (últimas 24h)
    - Intentos de acceso cross-tenant por día (últimos 30 días)
    - Intentos de autenticación fallidos por hora (últimas 24h)
    - Top 10 IPs con más violaciones de rate limit (últimas 24h)
    - Top 10 usuarios con más violaciones de rate limit (últimas 24h)

    La respuesta se cachea en Redis durante 60 segundos.
    El campo ``cache_hit`` indica si los datos provienen del caché.

    **Autenticación requerida:** Sí (Bearer token)
    **Rol requerido:** SUPER_ADMIN
    """
    redis_client = _get_redis_client()

    # Intentar servir desde caché
    if redis_client is not None:
        try:
            cached = redis_client.get(_CACHE_KEY)
            if cached:
                data = json.loads(cached)
                return _build_response(data, cache_hit=True)
        except Exception as exc:
            # Caché no disponible — continuar calculando desde BD
            logger.warning("Error al leer caché de métricas de seguridad: %s", exc)

    # Calcular métricas desde la base de datos
    try:
        data = _compute_metrics(db)
    except Exception as exc:
        logger.error("Error al calcular métricas de seguridad: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Error al obtener métricas de seguridad",
        )

    # Guardar en caché para las próximas 60 segundas
    if redis_client is not None:
        try:
            redis_client.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(data))
        except Exception as exc:
            # No es crítico — la respuesta ya está calculada
            logger.warning("Error al guardar métricas en caché: %s", exc)

    return _build_response(data, cache_hit=False)
