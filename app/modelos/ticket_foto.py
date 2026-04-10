from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TicketFoto(Base):
    __tablename__ = "ticket_fotos"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False, default="OTRA")
    archivo_url = Column(String(255), nullable=False)
    descripcion = Column(String(250), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
