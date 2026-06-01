"""
Audit logger estructurado para eventos de rate limiting.

Este módulo proporciona funciones para registrar violaciones de rate limiting,
errores de infraestructura y alertas de alta severidad en formato JSON estructurado.

Todos los logs se emiten al logger "rate_limit" para facilitar su agregación,
análisis y alertas en sistemas de monitoreo externos.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("rate_limit")


def log_rate_limit_violation(
    *,
    ip: str,
    endpoint: str,
    limit_type: str,
    limit_value: int,
    window: str,
    user_agent: str,
    timestamp: str,
    user_id: Optional[int] = None,
    taller_id: Optional[int] = None,
) -> None:
    """
    Emite un log estructurado JSON cuando se excede un límite de rate limiting.

    Este log se usa para:
    - Análisis forense de patrones de ataque
    - Detección de abuso de cuentas comprometidas
    - Métricas de uso del sistema
    - Alertas de seguridad

    Args:
        ip: Dirección IP del cliente que excedió el límite.
        endpoint: Ruta del endpoint que fue limitado (ej: "/upload/foto").
        limit_type: Tipo de límite excedido ("ip" o "user").
        limit_value: Valor numérico del límite (ej: 10 para "10/minute").
        window: Ventana de tiempo del límite ("minute", "hour", "day").
        user_agent: Header User-Agent del request para identificar el cliente.
        timestamp: Timestamp ISO 8601 del evento (con timezone UTC).
        user_id: ID del usuario autenticado (None si no autenticado).
        taller_id: ID del taller del usuario (None si no autenticado).

    Example:
        >>> log_rate_limit_violation(
        ...     ip="203.0.113.42",
        ...     endpoint="/upload/foto",
        ...     limit_type="ip",
        ...     limit_value=10,
        ...     window="minute",
        ...     user_agent="Mozilla/5.0 ...",
        ...     timestamp="2026-05-06T10:30:00.123456Z",
        ... )
    """
    entry = {
        "event": "rate_limit_exceeded",
        "severity": "WARNING",
        "ip": ip,
        "endpoint": endpoint,
        "limit_type": limit_type,
        "limit_value": limit_value,
        "window": window,
        "user_agent": user_agent,
        "timestamp": timestamp,
    }

    # Agregar campos opcionales solo si están presentes
    if user_id is not None:
        entry["user_id"] = user_id
    if taller_id is not None:
        entry["taller_id"] = taller_id

    # Emitir como JSON estructurado para agregadores de logs
    logger.warning(json.dumps(entry))


def log_redis_unavailable(error: Exception) -> None:
    """
    Emite un log CRITICAL cuando Redis no está disponible y se activa fail-open.

    Este log indica que el rate limiting está deshabilitado temporalmente
    porque el backend de Redis no responde. El sistema permite todos los
    requests (fail-open) para no interrumpir el servicio, pero esto debe
    generar una alerta inmediata al equipo de operaciones.

    Args:
        error: La excepción que causó el fallo de conexión a Redis.

    Example:
        >>> try:
        ...     redis_client.ping()
        ... except Exception as e:
        ...     log_redis_unavailable(e)
    """
    entry = {
        "event": "rate_limiter_redis_unavailable",
        "severity": "CRITICAL",
        "error": str(error),
        "action": "fail_open",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Emitir como JSON estructurado
    logger.critical(json.dumps(entry))


def check_and_alert_high_severity(ip: str, redis_client) -> None:
    """
    Verifica si una IP acumuló más de 10 violaciones en 5 minutos y emite alerta HIGH.

    Esta función implementa detección de ataques de fuerza bruta o abuso sistemático:
    - Incrementa un contador separado en Redis con TTL de 5 minutos
    - Si el contador supera 10, emite un log de alta severidad
    - Si Redis no está disponible, falla silenciosamente (no bloquea el handler)

    El contador usa la clave: RL_VIOLATIONS:{ip}:5min

    Args:
        ip: Dirección IP del cliente que excedió un límite.
        redis_client: Cliente de Redis para incrementar el contador.
                      Puede ser None si Redis no está disponible.

    Example:
        >>> from redis import Redis
        >>> redis_client = Redis.from_url("redis://redis:6379")
        >>> check_and_alert_high_severity("203.0.113.42", redis_client)
    """
    if redis_client is None:
        # Redis no disponible — falla silenciosamente
        return

    try:
        # Clave del contador de violaciones con ventana de 5 minutos
        key = f"RL_VIOLATIONS:{ip}:5min"

        # Incrementar el contador y establecer TTL de 300 segundos (5 minutos)
        # INCR es atómico y retorna el nuevo valor
        count = redis_client.incr(key)

        # Si es la primera violación, establecer el TTL
        if count == 1:
            redis_client.expire(key, 300)

        # Si superamos el umbral, emitir alerta HIGH
        if count > 10:
            entry = {
                "event": "rate_limit_high_severity_alert",
                "severity": "HIGH",
                "ip": ip,
                "violation_count": count,
                "window_minutes": 5,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            logger.error(json.dumps(entry))

    except Exception:
        # Si Redis falla durante el check, no interrumpir el handler
        # El log de violación ya se emitió, esta es solo una alerta adicional
        pass
