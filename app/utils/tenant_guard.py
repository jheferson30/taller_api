"""
Helper centralizado para verificar pertenencia de recursos al taller (tenant isolation).

Este módulo proporciona funciones para validar que los recursos pertenezcan al taller
del usuario autenticado, manteniendo el aislamiento multi-tenant del sistema.

Incluye detección y logging de intentos de acceso cross-tenant con alertas automáticas
cuando un usuario supera el umbral de intentos sospechosos.

Requirements: 1, 5, 11, 12, 20
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any, TypeVar

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Type variable para objetos de modelo SQLAlchemy
T = TypeVar("T")

# Umbral de intentos cross-tenant antes de disparar alerta HIGH
_CROSS_TENANT_ALERT_THRESHOLD = 3

# Clave Redis para el contador de intentos cross-tenant por usuario
_CROSS_TENANT_REDIS_KEY = "CROSS_TENANT:{user_id}"

# TTL del contador Redis (1 hora en segundos)
_CROSS_TENANT_COUNTER_TTL = 3600


def _get_redis_client():
    """
    Obtiene un cliente Redis síncrono para operaciones de contador.

    Returns:
        Cliente Redis, o ``None`` si Redis no está disponible.
        En ese caso las operaciones de contador se omiten silenciosamente.
    """
    try:
        import redis as redis_lib

        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        client = redis_lib.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        logger.warning(
            "Redis no disponible para contador cross-tenant (%s). "
            "El contador de intentos no se actualizará.",
            exc,
        )
        return None


def _log_cross_tenant_attempt(
    request: Request,
    taller_id_real: int,
    taller_id_solicitado: int,
) -> None:
    """
    Registra un intento de acceso cross-tenant en el audit log y actualiza el contador Redis.

    Pasos que ejecuta:
    1. Registra el evento en ``audit_log`` con ``AuditAction.SECURITY_ALERT``.
    2. Incrementa el contador Redis ``CROSS_TENANT:{user_id}`` con TTL de 1 hora.
    3. Si el contador supera el umbral (> 3), dispara una alerta HIGH via SecurityAlertService.

    El fallo de cualquier paso (BD, Redis, alerta) se loguea pero no interrumpe
    el flujo principal — el 404 al cliente siempre se lanza.

    Args:
        request:              Request HTTP de FastAPI con ``state.user`` y ``state.taller_id``.
        taller_id_real:       ``taller_id`` del objeto consultado (el taller al que pertenece).
        taller_id_solicitado: ``taller_id`` del JWT del usuario (el taller que solicitó acceso).

    Security:
        - Usa ``AuditAction.SECURITY_ALERT`` (no ``CROSS_TENANT_ATTEMPT``) para mantener
          compatibilidad con el dashboard de métricas que filtra por este valor.
        - El contador Redis usa TTL deslizante de 1 hora para detectar ataques sostenidos.
        - La alerta HIGH se dispara solo cuando el contador supera el umbral en la ventana.
    """
    user_id: int | None = None
    ip_address = "unknown"
    user_agent: str | None = None
    endpoint = "unknown"

    try:
        user = getattr(request.state, "user", None) or {}
        user_id = user.get("user_id") if isinstance(user, dict) else getattr(user, "id", None)
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")
        endpoint = str(request.url.path)
    except Exception as exc:
        logger.warning("No se pudo extraer contexto del request para audit log: %s", exc)

    # 1. Registrar en audit log
    _write_audit_log(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        taller_id_real=taller_id_real,
        taller_id_solicitado=taller_id_solicitado,
        endpoint=endpoint,
    )

    # 2. Incrementar contador Redis y obtener valor actual
    attempt_count = _increment_cross_tenant_counter(user_id)

    # 3. Disparar alerta HIGH si se supera el umbral
    if attempt_count is not None and attempt_count > _CROSS_TENANT_ALERT_THRESHOLD:
        _dispatch_high_severity_alert(
            user_id=user_id,
            ip_address=ip_address,
            attempt_count=attempt_count,
            taller_id_solicitado=taller_id_solicitado,
            taller_id_real=taller_id_real,
            endpoint=endpoint,
        )


def _write_audit_log(
    user_id: int | None,
    ip_address: str,
    user_agent: str | None,
    taller_id_real: int,
    taller_id_solicitado: int,
    endpoint: str,
) -> None:
    """
    Persiste el evento cross-tenant en la tabla ``audit_log``.

    Usa una sesión de BD independiente para garantizar que el registro
    se persiste incluso si la transacción principal falla.

    Args:
        user_id:              ID del usuario que realizó el intento (puede ser None).
        ip_address:           IP del cliente.
        user_agent:           User-Agent del cliente.
        taller_id_real:       ``taller_id`` del recurso consultado.
        taller_id_solicitado: ``taller_id`` del JWT del usuario.
        endpoint:             Ruta HTTP del endpoint.
    """
    try:
        from app.configuracion.base_datos import SessionLocal
        from app.modelos.audit_log import AuditAction, AuditLog

        db = SessionLocal()
        try:
            entry = AuditLog(
                user_id=user_id,
                action=AuditAction.SECURITY_ALERT,
                resource_type="tenant_isolation",
                resource_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "alert_type": "cross_tenant_access_attempt",
                    "taller_id_solicitado": taller_id_solicitado,
                    "taller_id_real": taller_id_real,
                    "endpoint": endpoint,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        # El fallo del audit log no debe interrumpir el flujo principal
        logger.error(
            "No se pudo registrar intento cross-tenant en audit log "
            "(user_id=%s, taller_solicitado=%s, taller_real=%s): %s",
            user_id,
            taller_id_solicitado,
            taller_id_real,
            exc,
        )


def _increment_cross_tenant_counter(user_id: int | None) -> int | None:
    """
    Incrementa el contador Redis de intentos cross-tenant para el usuario.

    Usa ``INCR`` + ``EXPIRE`` para mantener una ventana deslizante de 1 hora.
    Si el usuario no tiene ID (anónimo), no se incrementa el contador.

    Args:
        user_id: ID del usuario. Si es ``None``, retorna ``None`` sin operar.

    Returns:
        El valor actual del contador tras el incremento, o ``None`` si no se pudo
        actualizar (Redis no disponible o usuario anónimo).
    """
    if user_id is None:
        return None

    redis_client = _get_redis_client()
    if redis_client is None:
        return None

    try:
        redis_key = _CROSS_TENANT_REDIS_KEY.format(user_id=user_id)
        count = redis_client.incr(redis_key)
        # Establecer TTL solo en el primer incremento para no reiniciar la ventana
        if count == 1:
            redis_client.expire(redis_key, _CROSS_TENANT_COUNTER_TTL)
        return int(count)
    except Exception as exc:
        logger.warning(
            "No se pudo incrementar contador cross-tenant para user_id=%s: %s",
            user_id,
            exc,
        )
        return None


def _dispatch_high_severity_alert(
    user_id: int | None,
    ip_address: str,
    attempt_count: int,
    taller_id_solicitado: int,
    taller_id_real: int,
    endpoint: str,
) -> None:
    """
    Dispara una alerta de severidad HIGH via SecurityAlertService.

    Si SecurityAlertService no está disponible (aún no implementado o error de importación),
    loguea la alerta como CRITICAL para que no se pierda el evento.

    Args:
        user_id:              ID del usuario que superó el umbral.
        ip_address:           IP del cliente.
        attempt_count:        Número de intentos acumulados en la ventana de 1 hora.
        taller_id_solicitado: ``taller_id`` del JWT del usuario.
        taller_id_real:       ``taller_id`` del recurso consultado.
        endpoint:             Ruta HTTP del endpoint.
    """
    alert_details = {
        "event_type": "cross_tenant_access_threshold_exceeded",
        "severity": "HIGH",
        "user_id": user_id,
        "ip_address": ip_address,
        "attempt_count": attempt_count,
        "taller_id_solicitado": taller_id_solicitado,
        "taller_id_real": taller_id_real,
        "endpoint": endpoint,
        "timestamp": datetime.now(UTC).isoformat(),
        "remediation": (
            f"El usuario {user_id} ha realizado {attempt_count} intentos de acceso "
            "cross-tenant en la última hora. Revisar actividad y considerar suspensión."
        ),
    }

    try:
        from app.servicios.security_alert_service import SecurityAlertService

        alert_service = SecurityAlertService()
        alert_service.dispatch_high_severity(alert_details)
    except ImportError:
        # SecurityAlertService aún no implementado — loguear como CRITICAL
        logger.critical(
            "ALERTA HIGH — Cross-tenant threshold superado (SecurityAlertService no disponible): %s",
            alert_details,
        )
    except Exception as exc:
        logger.error(
            "Error al despachar alerta HIGH de cross-tenant (user_id=%s, intentos=%s): %s",
            user_id,
            attempt_count,
            exc,
        )


def verificar_pertenencia(
    objeto: Any | None,
    taller_id: int,
    nombre_recurso: str = "Recurso",
    request: Request | None = None,
) -> None:
    """
    Verifica que un objeto pertenezca al taller especificado.

    Esta función centraliza la validación de aislamiento multi-tenant, asegurando
    que los usuarios solo puedan acceder a recursos de su propio taller.

    Cuando se detecta un intento cross-tenant y se proporciona ``request``, registra
    el evento en el audit log, incrementa el contador Redis y dispara alertas si
    el usuario supera el umbral de intentos sospechosos.

    Args:
        objeto:         El objeto a verificar (puede ser None si no se encontró).
        taller_id:      ID del taller al que debe pertenecer el objeto.
        nombre_recurso: Nombre del recurso para el mensaje de error (ej: "Ticket").
        request:        Request HTTP opcional. Si se proporciona, habilita el logging
                        de intentos cross-tenant y las alertas automáticas.

    Raises:
        HTTPException 404: Si el objeto no existe o no pertenece al taller.
                          Usa 404 en lugar de 403 para no revelar la existencia
                          de recursos de otros talleres (seguridad por oscuridad).

    Examples:
        >>> ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        >>> verificar_pertenencia(ticket, taller_id, "Ticket", request)

        >>> mecanico = db.query(Mecanico).filter(Mecanico.id == mecanico_id).first()
        >>> verificar_pertenencia(mecanico, taller_id, "Mecánico")

    Security:
        - Siempre usa HTTP 404 en lugar de 403 para no revelar que el recurso existe.
        - El taller_id debe venir siempre del JWT (request.state.taller_id), nunca del cliente.
        - Con ``request`` provisto, los intentos cross-tenant quedan auditados y alertados.
    """
    if objeto is None:
        raise HTTPException(status_code=404, detail=f"{nombre_recurso} no encontrado")

    # Verificar que el objeto tenga el atributo taller_id
    if not hasattr(objeto, "taller_id"):
        # Si el objeto no tiene taller_id, no podemos verificar pertenencia.
        # Esto puede ser válido para recursos globales (ej: roles, configuración global).
        return

    # Verificar que el taller_id coincida
    if objeto.taller_id != taller_id:
        # Registrar el intento cross-tenant si tenemos contexto del request
        if request is not None:
            _log_cross_tenant_attempt(
                request=request,
                taller_id_real=objeto.taller_id,
                taller_id_solicitado=taller_id,
            )
        # HTTP 404 para no revelar que el recurso existe en otro taller
        raise HTTPException(status_code=404, detail=f"{nombre_recurso} no encontrado")


def obtener_recurso_del_taller(
    db: Session,
    modelo: type[T],
    recurso_id: int,
    taller_id: int,
    nombre_recurso: str = "Recurso",
    request: Request | None = None,
) -> T:
    """
    Obtiene un recurso por ID verificando que pertenezca al taller.

    Esta es una función de conveniencia que combina la consulta y la verificación
    de pertenencia en una sola llamada.

    Cuando se detecta un intento cross-tenant (el recurso existe pero pertenece a otro
    taller) y se proporciona ``request``, registra el evento en el audit log e incrementa
    el contador de intentos sospechosos.

    Args:
        db:             Sesión de base de datos SQLAlchemy.
        modelo:         Clase del modelo SQLAlchemy (ej: Ticket, Vehiculo, Mecanico).
        recurso_id:     ID del recurso a buscar.
        taller_id:      ID del taller al que debe pertenecer el recurso.
        nombre_recurso: Nombre del recurso para el mensaje de error.
        request:        Request HTTP opcional. Si se proporciona, habilita el logging
                        de intentos cross-tenant y las alertas automáticas.

    Returns:
        El objeto encontrado (garantizado que pertenece al taller).

    Raises:
        HTTPException 404: Si el recurso no existe o no pertenece al taller.

    Examples:
        >>> ticket = obtener_recurso_del_taller(db, Ticket, ticket_id, taller_id, "Ticket", request)
        >>> vehiculo = obtener_recurso_del_taller(db, Vehiculo, vehiculo_id, taller_id, "Vehículo")

    Security:
        - Filtra por taller_id en la query para evitar exponer datos de otros talleres.
        - Usa HTTP 404 para no revelar existencia de recursos de otros talleres.
        - Con ``request`` provisto, detecta y registra intentos de acceso cross-tenant.
    """
    # Primero buscar solo por ID para detectar si el recurso existe en otro taller
    # (necesario para el logging de cross-tenant)
    if request is not None:
        recurso_sin_filtro = (
            db.query(modelo)
            .filter(modelo.id == recurso_id)
            .first()
        )

        if recurso_sin_filtro is None:
            # El recurso no existe en absoluto — 404 simple
            raise HTTPException(status_code=404, detail=f"{nombre_recurso} no encontrado")

        if hasattr(recurso_sin_filtro, "taller_id") and recurso_sin_filtro.taller_id != taller_id:
            # El recurso existe pero pertenece a otro taller — intento cross-tenant
            _log_cross_tenant_attempt(
                request=request,
                taller_id_real=recurso_sin_filtro.taller_id,
                taller_id_solicitado=taller_id,
            )
            raise HTTPException(status_code=404, detail=f"{nombre_recurso} no encontrado")

        # El recurso existe y pertenece al taller correcto
        return recurso_sin_filtro  # type: ignore[return-value]

    # Sin request: comportamiento original — query directa con filtro por taller_id
    recurso = (
        db.query(modelo)
        .filter(
            modelo.id == recurso_id,
            modelo.taller_id == taller_id,
        )
        .first()
    )

    if not recurso:
        raise HTTPException(status_code=404, detail=f"{nombre_recurso} no encontrado")

    return recurso
