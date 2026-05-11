"""
Clase base para repositorios multi-tenant.
Aplica automáticamente el filtro taller_id en todas las operaciones CRUD.
"""
from sqlalchemy.orm import Session

from app.utils.exceptions import MissingTenantContextError


class TenantRepository:
    """
    Clase base para repositorios de entidades tenant-aware.
    Todas las queries incluyen automáticamente el filtro taller_id.
    """

    model = None  # Subclases deben definir el modelo SQLAlchemy

    def __init__(self, db: Session, taller_id: int):
        if not taller_id:
            raise MissingTenantContextError(
                "taller_id es requerido para operaciones tenant-aware"
            )
        self.db = db
        self.taller_id = taller_id

    def _base_query(self):
        """Query base con filtro de tenant aplicado."""
        return self.db.query(self.model).filter(self.model.taller_id == self.taller_id)

    def get_all(self, skip: int = 0, limit: int = 50):
        return self._base_query().offset(skip).limit(limit).all()

    def get_by_id(self, record_id: int):
        """Retorna None si el registro no pertenece al taller (como si no existiera)."""
        return self._base_query().filter(self.model.id == record_id).first()

    def create(self, record):
        """Asigna taller_id automáticamente antes de persistir."""
        record.taller_id = self.taller_id
        self.db.add(record)
        self.db.flush()
        return record

    def update(self, record):
        self.db.flush()
        return record

    def delete(self, record_id: int) -> bool:
        record = self.get_by_id(record_id)
        if not record:
            return False
        self.db.delete(record)
        self.db.flush()
        return True
