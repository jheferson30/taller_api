"""
Repositorio para operaciones de acceso a datos de Notificaciones.

Este repositorio implementa el patrón Repository con aislamiento multi-tenant
estricto. Todas las operaciones filtran por taller_id sin excepción.

Requirements: 1.4, 9.2, 9.4
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.modelos.notificacion import Notificacion, TipoNotificacion
from app.repositorios.tenant_repository import TenantRepository


class NotificacionRepository(TenantRepository):
    """
    Repositorio para gestión de notificaciones internas.

    Todas las operaciones incluyen filtro por taller_id automáticamente
    mediante la clase base TenantRepository.
    """

    model = Notificacion

    def __init__(self, db: Session, taller_id: int):
        """
        Inicializa el repositorio con contexto de tenant.

        Args:
            db: Sesión de SQLAlchemy
            taller_id: ID del taller (contexto de tenant)

        Raises:
            MissingTenantContextError: Si taller_id es None o 0
        """
        super().__init__(db, taller_id)

    def get_no_leidas(self, user_id: int) -> list[Notificacion]:
        """
        Obtiene todas las notificaciones no leídas de un usuario.

        Filtra por taller_id (automático), destinatario_user_id y leida=False.

        Args:
            user_id: ID del usuario destinatario

        Returns:
            Lista de notificaciones no leídas del usuario en el taller actual
        """
        return (
            self._base_query()
            .filter(
                Notificacion.destinatario_user_id == user_id,
                Notificacion.leida == False,
            )
            .order_by(Notificacion.fecha_creacion.desc())
            .all()
        )

    def get_by_id_y_usuario(
        self, notif_id: int, user_id: int
    ) -> Notificacion | None:
        """
        Obtiene una notificación por ID solo si pertenece al usuario y taller.

        Implementa opacidad cross-tenant: retorna None si la notificación
        no pertenece al usuario o al taller, sin revelar su existencia.

        Args:
            notif_id: ID de la notificación
            user_id: ID del usuario destinatario

        Returns:
            Notificación si pertenece al usuario y taller, None en caso contrario
        """
        return (
            self._base_query()
            .filter(
                Notificacion.id == notif_id,
                Notificacion.destinatario_user_id == user_id,
            )
            .first()
        )

    def marcar_leida(self, notif_id: int, user_id: int) -> bool:
        """
        Marca una notificación como leída solo si pertenece al usuario y taller.

        Args:
            notif_id: ID de la notificación
            user_id: ID del usuario destinatario

        Returns:
            True si se marcó como leída, False si no pertenece al usuario/taller
        """
        notificacion = self.get_by_id_y_usuario(notif_id, user_id)
        if not notificacion:
            return False

        notificacion.leida = True
        self.db.flush()
        return True

    def get_todas(self, user_id: int) -> list[Notificacion]:
        """
        Obtiene TODAS las notificaciones de un usuario (leídas y no leídas).

        Filtra por taller_id (automático) y destinatario_user_id.

        Args:
            user_id: ID del usuario destinatario

        Returns:
            Lista de todas las notificaciones del usuario en el taller actual
        """
        return (
            self._base_query()
            .filter(Notificacion.destinatario_user_id == user_id)
            .order_by(Notificacion.fecha_creacion.desc())
            .all()
        )

    def marcar_todas_leidas(self, user_id: int) -> int:
        """
        Marca todas las notificaciones no leídas del usuario como leídas.

        Args:
            user_id: ID del usuario destinatario

        Returns:
            Cantidad de notificaciones marcadas como leídas
        """
        cantidad = (
            self._base_query()
            .filter(
                Notificacion.destinatario_user_id == user_id,
                Notificacion.leida == False,
            )
            .update({"leida": True}, synchronize_session=False)
        )
        self.db.flush()
        return cantidad

    def existe_notif_renovacion_reciente(
        self, taller_id: int, horas: int = 24
    ) -> bool:
        """
        Verifica si existe una notificación de renovación reciente para el taller.

        Usado por el verificador de plan para evitar notificaciones duplicadas.

        Args:
            taller_id: ID del taller (debe coincidir con self.taller_id)
            horas: Ventana de tiempo en horas (default: 24)

        Returns:
            True si existe al menos una notificación RENOVACION_PLAN
            creada en las últimas N horas
        """
        # Validar que el taller_id coincida con el contexto
        if taller_id != self.taller_id:
            return False

        fecha_limite = datetime.now() - timedelta(hours=horas)

        existe = (
            self._base_query()
            .filter(
                Notificacion.tipo == TipoNotificacion.RENOVACION_PLAN,
                Notificacion.fecha_creacion >= fecha_limite,
            )
            .first()
        )

        return existe is not None

    def eliminar_leidas_antiguas(self) -> int:
        """
        Elimina notificaciones leídas del taller actual.

        Este método se ejecuta diariamente a medianoche para limpiar
        el historial de notificaciones y evitar acumulación excesiva.

        Solo elimina notificaciones con leida=True. Las no leídas se preservan
        independientemente de su antigüedad.

        Returns:
            Cantidad de notificaciones eliminadas
        """
        cantidad = (
            self._base_query()
            .filter(Notificacion.leida == True)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return cantidad
