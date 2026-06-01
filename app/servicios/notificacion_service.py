"""
Servicio de lógica de negocio para notificaciones internas del sistema.

Gestiona la creación, consulta y marcado de notificaciones internas,
aplicando aislamiento multi-tenant estricto mediante taller_id del JWT.

Requirements: 3.1, 3.4, 3.5, 4.1, 4.2, 5.1, 5.2, 5.3, 7.1, 7.6
"""

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modelos.notificacion import Notificacion, TipoNotificacion
from app.repositorios.notificacion_repository import NotificacionRepository

logger = logging.getLogger(__name__)


class NotificacionService:
    """Servicio de lógica de negocio para notificaciones internas."""

    def __init__(self, db: Session, taller_id: int):
        self.db = db
        self.taller_id = taller_id
        self.repository = NotificacionRepository(db, taller_id)

    def obtener_no_leidas(self, user_id: int) -> dict:
        """
        Obtiene todas las notificaciones no leídas de un usuario.

        Args:
            user_id: ID del usuario destinatario

        Returns:
            Diccionario con 'total' (int) y 'notificaciones' (list)
        """
        notificaciones = self.repository.get_no_leidas(user_id)
        return {
            "total": len(notificaciones),
            "notificaciones": notificaciones,
        }

    def obtener_todas(self, user_id: int) -> dict:
        """
        Obtiene TODAS las notificaciones de un usuario (leídas y no leídas).

        Args:
            user_id: ID del usuario destinatario

        Returns:
            Diccionario con 'total' (int) y 'notificaciones' (list)
        """
        notificaciones = self.repository.get_todas(user_id)
        return {
            "total": len(notificaciones),
            "notificaciones": notificaciones,
        }

    def marcar_como_leida(self, notif_id: int, user_id: int) -> Notificacion:
        notificacion = self.repository.get_by_id_y_usuario(notif_id, user_id)
        if not notificacion:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")

        notificacion.leida = True
        self.db.commit()
        self.db.refresh(notificacion)
        logger.info(
            "marcar_como_leida: notif_id=%d, user_id=%d, taller_id=%d",
            notif_id,
            user_id,
            self.taller_id,
        )
        return notificacion

    def marcar_todas_como_leidas(self, user_id: int) -> int:
        cantidad = self.repository.marcar_todas_leidas(user_id)
        self.db.commit()
        logger.info(
            "marcar_todas_como_leidas: user_id=%d, taller_id=%d, cantidad=%d",
            user_id,
            self.taller_id,
            cantidad,
        )
        return cantidad

    def limpiar_leidas(self) -> int:
        """
        Elimina todas las notificaciones leídas del taller actual.

        Este método se usa para limpieza manual del historial de notificaciones.
        El job nocturno automático ejecuta la misma operación a las 00:00.

        Returns:
            Cantidad de notificaciones eliminadas
        """
        cantidad = self.repository.eliminar_leidas_antiguas()
        self.db.commit()
        logger.info(
            "limpiar_leidas: taller_id=%d, cantidad=%d",
            self.taller_id,
            cantidad,
        )
        return cantidad

    def crear_notificacion_asignacion(
        self, ticket, mecanico_user_id: int | None
    ) -> Notificacion | None:
        """
        Crea una notificación de tipo TICKET_ASIGNADO para el mecánico.

        Si mecanico_user_id es None, registra un warning y retorna None
        sin lanzar error.

        Args:
            ticket: Instancia del ticket asignado
            mecanico_user_id: ID del usuario mecánico destinatario, o None

        Returns:
            La notificación creada, o None si mecanico_user_id es None
        """
        if mecanico_user_id is None:
            logger.warning(
                "crear_notificacion_asignacion: mecanico_user_id es None "
                "para ticket_id=%s — notificación no creada",
                getattr(ticket, "id", None),
            )
            return None

        codigo = getattr(ticket, "ticket_codigo", None) or ticket.id
        notificacion = Notificacion(
            taller_id=self.taller_id,
            destinatario_user_id=mecanico_user_id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket asignado",
            mensaje=f"Se te ha asignado el ticket #{codigo}",
            referencia_id=ticket.id,
        )
        self.db.add(notificacion)
        self.db.flush()
        return notificacion

    def crear_notificaciones_renovacion(
        self, taller, admins: list, dias_restantes: int
    ) -> list[Notificacion]:
        """
        Crea notificaciones de tipo RENOVACION_PLAN para cada admin del taller.

        Args:
            taller: Instancia del taller cuyo plan está próximo a vencer
            admins: Lista de usuarios con rol ADMIN que recibirán la notificación
            dias_restantes: Número exacto de días restantes antes del vencimiento

        Returns:
            Lista de notificaciones creadas (una por admin)
        """
        notificaciones = []
        for admin in admins:
            notificacion = Notificacion(
                taller_id=self.taller_id,
                destinatario_user_id=admin.id,
                tipo=TipoNotificacion.RENOVACION_PLAN,
                titulo="Renovación de plan requerida",
                mensaje=(
                    f"Tu plan vence en {dias_restantes} día(s). "
                    "Renueva para continuar usando el servicio."
                ),
                referencia_id=taller.id,
            )
            self.db.add(notificacion)
            notificaciones.append(notificacion)

        if notificaciones:
            self.db.flush()

        return notificaciones
