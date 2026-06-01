"""
Tarea Celery Beat para verificar vencimientos de plan SaaS.

Ejecuta diariamente y crea notificaciones RENOVACION_PLAN para los ADMIN
de talleres cuyo plan vence en 3 días o menos.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 9.5
"""

import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.notificacion_tasks.verificar_vencimientos_plan")
def verificar_vencimientos_plan() -> dict:
    """
    Verifica los vencimientos de plan de todos los talleres activos/trial
    y crea notificaciones RENOVACION_PLAN cuando corresponde.

    Lógica:
    - Consulta talleres con estado ACTIVO o TRIAL y fecha_vencimiento_plan IS NOT NULL
    - Para cada taller: calcula días restantes
    - Si dias_restantes <= 3 y no existe notificación reciente (< 24h):
        - Obtiene usuarios con rol ADMIN del taller
        - Crea notificaciones RENOVACION_PLAN para cada ADMIN
        - Registra en audit log
    - Omite talleres SUSPENDIDO o CANCELADO
    - Omite talleres sin fecha_vencimiento_plan
    - Manejo de errores: log por taller fallido, continúa con el siguiente

    Returns:
        dict con estadísticas de la ejecución
    """
    # Importaciones locales para evitar imports circulares en el módulo Celery
    from app.configuracion.base_datos import SessionLocal
    from app.modelos.audit_log import AuditAction, AuditLog
    from app.modelos.taller import EstadoTaller, Taller
    from app.modelos.user import User
    from app.modelos.user_role import UserRole
    from app.modelos.role import Role
    from app.repositorios.notificacion_repository import NotificacionRepository
    from app.servicios.notificacion_service import NotificacionService

    db = SessionLocal()
    talleres_procesados = 0
    notificaciones_creadas = 0
    talleres_omitidos = 0
    errores = 0

    try:
        # Consultar talleres ACTIVO o TRIAL con fecha_vencimiento_plan definida
        # Req 7.4: omitir SUSPENDIDO y CANCELADO
        # Req 7.5: omitir talleres sin fecha_vencimiento_plan
        talleres = (
            db.query(Taller)
            .filter(
                Taller.estado.in_([EstadoTaller.ACTIVO, EstadoTaller.TRIAL]),
                Taller.fecha_vencimiento_plan.isnot(None),
            )
            .all()
        )

        logger.info(
            "verificar_vencimientos_plan: procesando %d talleres elegibles",
            len(talleres),
        )

        ahora = datetime.now(timezone.utc)

        for taller in talleres:
            try:
                # Calcular días restantes
                fecha_venc = taller.fecha_vencimiento_plan
                # Normalizar a timezone-aware si es naive
                if fecha_venc.tzinfo is None:
                    fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)

                delta = fecha_venc - ahora
                dias_restantes = delta.days

                # Req 7.1: solo si dias_restantes <= 3
                if dias_restantes > 3:
                    talleres_omitidos += 1
                    continue

                # Req 7.2: verificar si ya existe notificación reciente (< 24h)
                repo = NotificacionRepository(db, taller.id)
                if repo.existe_notif_renovacion_reciente(taller.id, horas=24):
                    logger.debug(
                        "verificar_vencimientos_plan: taller_id=%d ya tiene "
                        "notificación RENOVACION_PLAN reciente — omitiendo",
                        taller.id,
                    )
                    talleres_omitidos += 1
                    continue

                # Obtener usuarios con rol ADMIN del taller
                admins = (
                    db.query(User)
                    .join(UserRole, UserRole.user_id == User.id)
                    .join(Role, Role.id == UserRole.role_id)
                    .filter(
                        User.taller_id == taller.id,
                        User.is_active == True,
                        Role.name == "ADMIN",
                    )
                    .all()
                )

                if not admins:
                    logger.warning(
                        "verificar_vencimientos_plan: taller_id=%d no tiene "
                        "usuarios ADMIN activos — omitiendo notificación",
                        taller.id,
                    )
                    talleres_omitidos += 1
                    continue

                # Crear notificaciones RENOVACION_PLAN para cada ADMIN
                service = NotificacionService(db, taller.id)
                notifs = service.crear_notificaciones_renovacion(
                    taller, admins, dias_restantes
                )

                # Req 9.5: registrar en audit log
                for notif in notifs:
                    audit_entry = AuditLog(
                        user_id=None,  # acción del sistema, no de un usuario
                        taller_id=taller.id,
                        action=AuditAction.CONFIG_CHANGE,
                        resource_type="notificacion",
                        resource_id=notif.id,
                        ip_address="system",
                        user_agent="celery-beat",
                        details={
                            "tipo": "RENOVACION_PLAN",
                            "taller_id": taller.id,
                            "destinatario_user_id": notif.destinatario_user_id,
                            "dias_restantes": dias_restantes,
                        },
                    )
                    db.add(audit_entry)

                db.commit()

                notificaciones_creadas += len(notifs)
                talleres_procesados += 1

                logger.info(
                    "verificar_vencimientos_plan: taller_id=%d — %d notificaciones "
                    "RENOVACION_PLAN creadas (dias_restantes=%d)",
                    taller.id,
                    len(notifs),
                    dias_restantes,
                )

            except Exception as exc:
                # Req: log de error por taller fallido, continuar con el siguiente
                errores += 1
                logger.error(
                    "verificar_vencimientos_plan: error procesando taller_id=%d — %s",
                    taller.id,
                    str(exc),
                    exc_info=True,
                )
                db.rollback()
                continue

    except Exception as exc:
        logger.error(
            "verificar_vencimientos_plan: error general — %s",
            str(exc),
            exc_info=True,
        )
        db.rollback()
    finally:
        db.close()

    resultado = {
        "status": "completed",
        "talleres_procesados": talleres_procesados,
        "notificaciones_creadas": notificaciones_creadas,
        "talleres_omitidos": talleres_omitidos,
        "errores": errores,
        "ejecutado_en": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("verificar_vencimientos_plan: %s", resultado)
    return resultado
