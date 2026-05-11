"""
Job programado para limpieza automática de notificaciones leídas.

Este job se ejecuta diariamente a las 00:00 (medianoche) y elimina todas las
notificaciones marcadas como leídas de todos los talleres del sistema.

Las notificaciones NO leídas se preservan indefinidamente hasta que el usuario
las marque como leídas.

Requirements: 8.1, 8.2
"""

import logging

from sqlalchemy.orm import Session

from app.configuracion.base_datos import SessionLocal
from app.modelos.taller import Taller
from app.repositorios.notificacion_repository import NotificacionRepository

logger = logging.getLogger(__name__)


def limpiar_notificaciones_leidas():
    """
    Limpia notificaciones leídas de todos los talleres.

    Este job se ejecuta diariamente a medianoche (00:00) para mantener
    el historial de notificaciones limpio y evitar acumulación excesiva.

    Proceso:
    1. Obtiene lista de todos los talleres activos
    2. Para cada taller, elimina sus notificaciones leídas
    3. Registra estadísticas de limpieza en logs

    Solo elimina notificaciones con leida=True. Las no leídas permanecen
    intactas independientemente de su antigüedad.
    """
    db: Session = SessionLocal()
    try:
        # Obtener todos los talleres activos
        talleres = db.query(Taller).filter(Taller.estado == "ACTIVO").all()

        total_eliminadas = 0
        talleres_procesados = 0

        for taller in talleres:
            try:
                # Crear repositorio con contexto del taller
                repo = NotificacionRepository(db, taller.id)

                # Eliminar notificaciones leídas del taller
                eliminadas = repo.eliminar_leidas_antiguas()

                if eliminadas > 0:
                    logger.info(
                        f"Limpieza notificaciones: taller_id={taller.id}, "
                        f"nombre={taller.nombre}, eliminadas={eliminadas}"
                    )

                total_eliminadas += eliminadas
                talleres_procesados += 1

            except Exception as e:
                logger.error(
                    f"Error al limpiar notificaciones del taller {taller.id}: {e}",
                    exc_info=True,
                )
                # Continuar con el siguiente taller

        # Commit final
        db.commit()

        logger.info(
            f"Limpieza de notificaciones completada: "
            f"talleres_procesados={talleres_procesados}, "
            f"total_eliminadas={total_eliminadas}"
        )

    except Exception as e:
        logger.error(f"Error crítico en limpieza de notificaciones: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
