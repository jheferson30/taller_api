import logging
import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Límites globales aplicados a todos los endpoints por defecto
_DEFAULT_LIMITS = ["100/minute", "1000/hour", "5000/day"]


def _get_redis_url() -> str:
    """
    Lee la URL de Redis desde la variable de entorno REDIS_URL.

    Returns:
        URL de conexión a Redis. Default: redis://redis:6379
    """
    return os.getenv("REDIS_URL", "redis://redis:6379")


def _get_whitelist_ips() -> frozenset:
    """
    Obtiene el conjunto de IPs exentas de rate limiting desde la variable de entorno.

    Lee RATE_LIMIT_WHITELIST_IPS (lista separada por comas).
    Siempre incluye localhost IPv4 e IPv6 como mínimo.

    Returns:
        frozenset de IPs en whitelist (inmutable, seguro para uso concurrente).
    """
    whitelist_str = os.getenv("RATE_LIMIT_WHITELIST_IPS", "")
    ips = {ip.strip() for ip in whitelist_str.split(",") if ip.strip()}
    # Siempre incluir localhost para no bloquear health checks internos
    ips.update({"127.0.0.1", "::1"})
    return frozenset(ips)


def _key_func(request: Request) -> str:
    """
    Determina la clave de rate limiting para el request entrante.

    Prioridad de evaluación:
    1. Requests OPTIONS → "options-exempt" (preflight CORS, sin límite)
    2. IP en whitelist → "whitelist-exempt" (IPs internas/de confianza, sin límite)
    3. Usuario autenticado con JWT → "user:{user_id}" (límite por usuario)
    4. Fallback → IP del cliente (límite por IP)

    La clave "options-exempt" y "whitelist-exempt" son especiales: SlowAPI
    no aplica límites a claves que no coinciden con ningún contador real,
    por lo que actúan como bypass efectivo.

    Args:
        request: El request HTTP entrante de Starlette/FastAPI.

    Returns:
        Clave de rate limiting como string.
    """
    # 1. Excluir preflight CORS — nunca limitar OPTIONS
    if request.method == "OPTIONS":
        return "options-exempt"

    # 2. Obtener IP del cliente para verificar whitelist y como fallback
    client_ip = get_remote_address(request)

    # 3. Verificar whitelist antes de cualquier otra lógica
    if client_ip in _get_whitelist_ips():
        return "whitelist-exempt"

    # 4. Si el usuario está autenticado (JWT procesado por AuthMiddleware),
    #    usar user_id como clave para rate limiting por usuario.
    #    Esto permite que el mismo usuario sea limitado independientemente
    #    de la IP desde la que opere (cuentas comprometidas, VPNs, etc.)
    try:
        user = getattr(request.state, "user", None)
        if user is not None and hasattr(user, "id") and user.id is not None:
            return f"user:{user.id}"
    except Exception:
        # Si hay cualquier error accediendo al estado del request,
        # caer al fallback de IP sin interrumpir el request
        pass

    # 5. Fallback: usar IP del cliente
    return client_ip


def _create_limiter() -> Limiter:
    """
    Crea la instancia del Limiter con Redis como backend.

    Implementa comportamiento fail-open: si Redis no está disponible al
    inicializar, registra un error CRITICAL y crea el limiter con storage
    en memoria como respaldo. Esto garantiza que el sistema siga operando
    aunque Redis esté caído (un taller no puede quedar sin acceso).

    Returns:
        Instancia configurada de Limiter (con Redis o memory:// como fallback).
    """
    redis_url = _get_redis_url()
    try:
        instance = Limiter(
            key_func=_key_func,
            storage_uri=redis_url,
            default_limits=_DEFAULT_LIMITS,
        )
        logger.info(
            "Rate limiter inicializado con Redis: %s | límites globales: %s",
            redis_url,
            _DEFAULT_LIMITS,
        )
        return instance
    except Exception as exc:
        # Importación diferida para evitar dependencia circular en el arranque
        # (rate_limit_logger puede no estar disponible aún en este punto)
        _log_redis_unavailable_fallback(exc, redis_url)
        logger.critical(
            "Rate limiter cayendo a memory:// — Redis no disponible en %s: %s",
            redis_url,
            exc,
        )
        return Limiter(
            key_func=_key_func,
            storage_uri="memory://",
            default_limits=_DEFAULT_LIMITS,
        )


def _log_redis_unavailable_fallback(exc: Exception, redis_url: str) -> None:
    """
    Emite log estructurado CRITICAL cuando Redis no está disponible al inicializar.

    Usa el logger estándar en lugar de rate_limit_logger para evitar
    dependencias circulares durante el arranque del módulo.

    Args:
        exc: La excepción que causó el fallo de conexión.
        redis_url: La URL de Redis que se intentó conectar.
    """
    import json
    from datetime import datetime, timezone

    entry = {
        "event": "rate_limiter_redis_unavailable",
        "severity": "CRITICAL",
        "error": str(exc),
        "redis_url": redis_url,
        "action": "fail_open",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    # Emitir como JSON estructurado para que los agregadores de logs lo procesen
    logging.getLogger("rate_limit").critical(json.dumps(entry))


# Instancia global — importada en main.py y en los decoradores @limiter.limit de las rutas
limiter = _create_limiter()
