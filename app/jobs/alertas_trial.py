"""
Job programado para alertas de vencimiento de trial.

Se ejecuta diariamente a las 09:00 y crea notificaciones RENOVACION_PLAN
para los admins de talleres cuyo trial vence en exactamente 7, 3 o 1 día(s).

Solo crea la notificación si no existe ya una no leída del mismo tipo para
ese taller en las últimas 24 horas, evitando duplicados en caso de reinicios.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.configuracion.base_datos import SessionLocal
from app.modelos.notificacion import Notificacion, TipoNotificacion
from app.modelos.taller import EstadoTaller, Taller
from app.modelos.user import User
from app.modelos.role import Role, UserRole
from app.servicios.notificacion_service import NotificacionService

logger = logging.getLogger(__name__)

# Días en los que se envía alerta (antes del vencimiento)
DIAS_ALERTA = {7, 3, 1}


def _calcular_dias_restantes(taller: Taller, ahora: datetime) -> int | None:
    """Calcula los días restantes del trial. Retorna None si no aplica."""
    if taller.estado != EstadoTaller.TRIAL:
        return None
    if not taller.fecha_inicio_trial or not taller.dias_trial:
        return None

    fecha_fin = taller.fecha_inicio_trial + timedelta(days=taller.dias_trial)
    # Normalizar timezone
    if fecha_fin.tzinfo is None:
        fecha_fin = fecha_fin.replace(tzinfo=timezone.utc)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)

    delta = fecha_fin - ahora
    return max(0, delta.days)


def _ya_notificado_hoy(db: Session, taller_id: int, dias_restantes: int) -> bool:
    """
    Verifica si ya se creó una notificación RENOVACION_PLAN para este taller
    en las últimas 24 horas con el mismo mensaje de días restantes.
    Evita duplicados si el scheduler se reinicia o ejecuta dos veces.
    """
    hace_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    texto_dias = f"en {dias_restantes} día"
    existe = (
        db.query(Notificacion)
        .filter(
            Notificacion.taller_id == taller_id,
            Notificacion.tipo == TipoNotificacion.RENOVACION_PLAN,
            Notificacion.fecha_creacion >= hace_24h,
            Notificacion.mensaje.contains(texto_dias),
        )
        .first()
    )
    return existe is not None


def _obtener_admins_taller(db: Session, taller_id: int) -> list[User]:
    """Retorna los usuarios activos con rol ADMIN del taller."""
    rol_admin = db.query(Role).filter(Role.name == "ADMIN").first()
    if not rol_admin:
        return []

    admin_ids = (
        db.query(UserRole.user_id)
        .filter(UserRole.role_id == rol_admin.id)
        .subquery()
    )
    return (
        db.query(User)
        .filter(
            User.taller_id == taller_id,
            User.is_active == True,
            User.id.in_(admin_ids),
        )
        .all()
    )


def verificar_trials_proximos_a_vencer():
    """
    Detecta talleres en TRIAL con vencimiento en 7, 3 o 1 día(s) y crea
    notificaciones RENOVACION_PLAN para sus admins.

    Proceso:
    1. Obtiene todos los talleres en estado TRIAL
    2. Calcula días restantes para cada uno
    3. Si los días restantes están en {7, 3, 1} y no se notificó hoy, crea notificaciones
    4. Registra estadísticas en logs
    """
    db: Session = SessionLocal()
    try:
        ahora = datetime.now(timezone.utc)
        talleres_trial = (
            db.query(Taller)
            .filter(Taller.estado == EstadoTaller.TRIAL)
            .all()
        )

        notificaciones_creadas = 0
        talleres_alertados = 0

        for taller in talleres_trial:
            try:
                dias = _calcular_dias_restantes(taller, ahora)
                if dias is None or dias not in DIAS_ALERTA:
                    continue

                if _ya_notificado_hoy(db, taller.id, dias):
                    logger.debug(
                        "alertas_trial: taller_id=%d ya notificado hoy (%d días)",
                        taller.id, dias,
                    )
                    continue

                admins = _obtener_admins_taller(db, taller.id)
                if not admins:
                    logger.warning(
                        "alertas_trial: taller_id=%d sin admins activos — notificación omitida",
                        taller.id,
                    )
                    continue

                servicio = NotificacionService(db, taller.id)
                nuevas = servicio.crear_notificaciones_renovacion(taller, admins, dias)
                notificaciones_creadas += len(nuevas)
                talleres_alertados += 1

                logger.info(
                    "alertas_trial: taller_id=%d nombre='%s' dias_restantes=%d "
                    "admins_notificados=%d",
                    taller.id, taller.nombre, dias, len(admins),
                )

            except Exception as e:
                logger.error(
                    "alertas_trial: error procesando taller_id=%d: %s",
                    taller.id, e, exc_info=True,
                )
                # Continuar con el siguiente taller

        db.commit()
        logger.info(
            "alertas_trial completado: talleres_alertados=%d notificaciones_creadas=%d",
            talleres_alertados, notificaciones_creadas,
        )

    except Exception as e:
        logger.error("alertas_trial: error crítico: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
