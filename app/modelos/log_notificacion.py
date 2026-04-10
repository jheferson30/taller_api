from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class LogNotificacion(Base):
    __tablename__ = "log_notificacion"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    telefono_destino = Column(String(30), nullable=True)
    tipo_evento = Column(String(20), nullable=False)
    mensaje_enviado = Column(Text, nullable=True)
    resultado = Column(String(10), nullable=False)
    error_detalle = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
