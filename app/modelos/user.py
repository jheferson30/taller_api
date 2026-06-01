from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class User(Base):
    """
    Modelo de usuario del sistema con autenticación JWT.

    Almacena usuarios con contraseñas hasheadas usando bcrypt/argon2.
    Relacionado con roles mediante tabla intermedia user_roles.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_migrated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Información personal
    nombre_completo = Column(String(150), nullable=True)
    telefono = Column(String(20), nullable=True)
    direccion = Column(String(255), nullable=True)

    # Relaciones
    taller = relationship("Taller", back_populates="usuarios")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")
    token_blacklist = relationship("TokenBlacklist", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
