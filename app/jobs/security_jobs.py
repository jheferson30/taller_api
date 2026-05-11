"""
Jobs programados de seguridad del sistema.

Contiene dos tareas automáticas:

- ``check_jwt_rotation``: se ejecuta diariamente. Verifica si la clave JWT activa
  supera los 90 días de antigüedad y, de ser así, dispara la rotación automática.

- ``flush_security_alerts``: se ejecuta cada 15 minutos. Vacía el buffer Redis de
  alertas LOW y las envía agrupadas al destino configurado en SECURITY_WEBHOOK_URL.

Ambos jobs son síncronos (APScheduler BackgroundScheduler) y crean su propio
event loop cuando necesitan ejecutar código asíncrono.

Requirements: 3.4, 7.7
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


def check_jwt_rotation() -> None:
    """
    Verifica si la clave JWT activa necesita rotación y la ejecuta si es necesario.

    Lógica:
    1. Consulta ``SecretsManager.check_rotation_needed()``
    2. Si retorna ``True`` (clave con más de 90 días), llama a ``rotate_jwt_key()``
    3. Registra el resultado en el log (rotación ejecutada o no necesaria)

    En caso de error (p. ej. lock Redis tomado por otra instancia), loguea el
    error y termina sin propagar la excepción para no interrumpir el scheduler.

    Este job debe ejecutarse una vez al día (configurado en ``scheduler.py``).
    """
    logger.info("[security_jobs] Verificando si se requiere rotación de clave JWT...")

    try:
        from app.configuracion.secrets_manager import SecretsManager

        secrets_manager = SecretsManager()

        if not secrets_manager.check_rotation_needed():
            logger.info(
                "[security_jobs] Rotación JWT no necesaria — "
                "la clave activa tiene menos de 90 días."
            )
            return

        logger.warning(
            "[security_jobs] Clave JWT activa supera los 90 días. "
            "Iniciando rotación automática..."
        )

        nueva_clave = secrets_manager.rotate_jwt_key()

        # Registrar solo la longitud de la clave, nunca el valor en texto plano
        logger.info(
            "[security_jobs] Rotación JWT completada exitosamente. "
            "Nueva clave generada (%d caracteres).",
            len(nueva_clave),
        )

    except RuntimeError as exc:
        # RuntimeError esperado: lock Redis tomado por otra instancia
        logger.warning(
            "[security_jobs] Rotación JWT no ejecutada: %s", exc
        )
    except Exception as exc:
        logger.error(
            "[security_jobs] Error inesperado durante la verificación de rotación JWT: %s",
            exc,
            exc_info=True,
        )


def flush_security_alerts() -> None:
    """
    Vacía el buffer Redis de alertas LOW y las envía agrupadas al destino configurado.

    Lógica:
    1. Instancia ``SecurityAlertService``
    2. Llama a ``flush_low_severity_buffer()`` (método async)
    3. Si el buffer está vacío, el método retorna sin hacer nada

    El job es síncrono (APScheduler BackgroundScheduler), por lo que ejecuta
    el código asíncrono creando un event loop temporal con ``asyncio.run()``.

    En caso de error, loguea y termina sin propagar la excepción para no
    interrumpir el scheduler.

    Este job debe ejecutarse cada 15 minutos (configurado en ``scheduler.py``).
    """
    logger.debug("[security_jobs] Iniciando flush de alertas LOW de seguridad...")

    try:
        from app.servicios.security_alert_service import SecurityAlertService

        service = SecurityAlertService()
        asyncio.run(service.flush_low_severity_buffer())

        logger.debug("[security_jobs] Flush de alertas LOW completado.")

    except Exception as exc:
        logger.error(
            "[security_jobs] Error durante el flush de alertas LOW: %s",
            exc,
            exc_info=True,
        )
