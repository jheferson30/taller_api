"""
Scheduler de jobs programados del sistema.

Gestiona la ejecución automática de tareas programadas usando APScheduler.
Actualmente incluye:
- Limpieza diaria de notificaciones leídas (00:00)
- Verificación y rotación automática de clave JWT (diario a las 02:00)
- Flush de alertas de seguridad LOW acumuladas (cada 15 minutos)

Requirements: 8.1, 3.4, 7.7
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.jobs.alertas_trial import verificar_trials_proximos_a_vencer
from app.jobs.limpieza_notificaciones import limpiar_notificaciones_leidas
from app.jobs.security_jobs import check_jwt_rotation, flush_security_alerts

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler: BackgroundScheduler | None = None


def iniciar_scheduler():
    """
    Inicializa y arranca el scheduler de jobs programados.

    Configura los siguientes jobs:
    - Limpieza de notificaciones leídas: diariamente a las 00:00
    - Verificación de rotación JWT: diariamente a las 02:00
    - Flush de alertas LOW: cada 15 minutos

    Este método debe llamarse una sola vez al iniciar la aplicación
    (en el lifespan de FastAPI).
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler ya está inicializado")
        return

    scheduler = BackgroundScheduler(timezone="America/Bogota")

    # Job: Limpieza de notificaciones leídas (diario a medianoche)
    scheduler.add_job(
        func=limpiar_notificaciones_leidas,
        trigger=CronTrigger(hour=0, minute=0),  # 00:00 todos los días
        id="limpieza_notificaciones",
        name="Limpieza de notificaciones leídas",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Job: Alertas de vencimiento de trial (diario a las 09:00)
    scheduler.add_job(
        func=verificar_trials_proximos_a_vencer,
        trigger=CronTrigger(hour=9, minute=0),  # 09:00 todos los días
        id="alertas_trial",
        name="Alertas de vencimiento de trial",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Job: Verificación y rotación automática de clave JWT (diario a las 02:00)
    # Se ejecuta a las 02:00 para evitar solapamiento con la limpieza de medianoche
    # y minimizar el impacto en tráfico de usuarios.
    scheduler.add_job(
        func=check_jwt_rotation,
        trigger=CronTrigger(hour=2, minute=0),  # 02:00 todos los días
        id="check_jwt_rotation",
        name="Verificación de rotación de clave JWT",
        replace_existing=True,
        misfire_grace_time=3600,  # Si falla, puede ejecutarse hasta 1h después
    )

    # Job: Flush de alertas de seguridad LOW (cada 15 minutos)
    scheduler.add_job(
        func=flush_security_alerts,
        trigger=IntervalTrigger(minutes=15),
        id="flush_security_alerts",
        name="Flush de alertas de seguridad LOW",
        replace_existing=True,
        misfire_grace_time=300,  # Si falla, puede ejecutarse hasta 5 min después
    )

    scheduler.start()
    logger.info("✅ Scheduler de jobs iniciado correctamente")
    logger.info("   - Limpieza de notificaciones: diaria a las 00:00")
    logger.info("   - Alertas de vencimiento de trial: diaria a las 09:00")
    logger.info("   - Verificación rotación JWT: diaria a las 02:00")
    logger.info("   - Flush alertas LOW: cada 15 minutos")


def detener_scheduler():
    """
    Detiene el scheduler de forma segura.

    Este método debe llamarse al apagar la aplicación
    (en el lifespan de FastAPI).
    """
    global scheduler

    if scheduler is not None:
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("✅ Scheduler de jobs detenido correctamente")
