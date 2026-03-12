from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TicketCompra(Base):
    __tablename__ = "ticket_compras"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    descripcion = Column(String(250), nullable=False)
    valor = Column(Integer, nullable=False)
    soporte_url = Column(String(255), nullable=True)
    nota = Column(String(500), nullable=True)
    responsable = Column(String(120), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
