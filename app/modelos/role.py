from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class Role(Base):
    """
    Modelo de roles del sistema.
    
    Define roles como ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA.
    Relacionado con usuarios mediante tabla intermedia user_roles.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    users = relationship("User", secondary="user_roles", back_populates="roles")
