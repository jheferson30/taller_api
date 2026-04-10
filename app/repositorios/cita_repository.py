"""
Repositorio para operaciones de acceso a datos de Citas.
Requirements: 9.1, 9.2, 9.3
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.modelos.cita import Cita


class CitaRepository:
    """Repositorio para gestión de citas."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, cita_id: int) -> Cita | None:
        """Obtiene una cita por ID."""
        return self.db.query(Cita).filter(Cita.id == cita_id).first()

    def get_all(
        self,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        estado: str | None = None,
    ) -> list[Cita]:
        """
        Lista citas con filtros opcionales.
        Requirements: 9.3
        """
        query = self.db.query(Cita)

        if fecha_desde:
            query = query.filter(Cita.fecha_cita >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Cita.fecha_cita <= fecha_hasta)
        if estado:
            query = query.filter(Cita.estado == estado.upper())

        return query.order_by(Cita.fecha_cita.asc()).all()

    def get_proximas(self, dias: int = 7) -> list[Cita]:
        """
        Lista citas de hoy y los próximos N días.
        Requirements: 9.3
        """
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_limite = hoy + timedelta(days=dias)

        return (
            self.db.query(Cita)
            .filter(
                Cita.fecha_cita >= hoy,
                Cita.fecha_cita <= fecha_limite,
                Cita.estado.in_(["PENDIENTE", "CONFIRMADA"]),
            )
            .order_by(Cita.fecha_cita.asc())
            .all()
        )

    def create(self, cita: Cita) -> Cita:
        """
        Crea una nueva cita.
        Requirements: 9.1
        """
        self.db.add(cita)
        self.db.flush()
        return cita

    def update(self, cita: Cita) -> Cita:
        """
        Actualiza una cita existente.
        Requirements: 9.2
        """
        self.db.flush()
        return cita

    def delete(self, cita: Cita) -> None:
        """Elimina una cita (soft delete cambiando estado)."""
        cita.estado = "CANCELADA"  # type: ignore[assignment]
        self.db.flush()
