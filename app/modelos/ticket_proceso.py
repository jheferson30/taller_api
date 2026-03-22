from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TicketProceso(Base):
    __tablename__ = "ticket_procesos"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    nombre = Column(String(120), nullable=False)
    descripcion = Column(String(400), nullable=True)
    mecanico = Column(String(120), nullable=True)
    foto_url = Column(String(500), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
