from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TokenBlacklist(Base):
    """
    Modelo de lista negra de tokens JWT invalidados.
    
    Almacena tokens que han sido invalidados por logout, desactivación de usuario,
    o revocación manual. Los tokens en esta lista no deben ser aceptados.
    """
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(36), unique=True, nullable=False, index=True)
    token_type = Column(String(20), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String(100), nullable=True)
    
    # Relaciones
    user = relationship("User", back_populates="token_blacklist")
