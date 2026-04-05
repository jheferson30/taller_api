from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class UserRole(Base):
    """
    Tabla intermedia para relación many-to-many entre usuarios y roles.
    
    Permite que un usuario tenga múltiples roles y un rol sea asignado
    a múltiples usuarios.
    """
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
