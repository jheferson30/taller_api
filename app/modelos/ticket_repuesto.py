from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TicketRepuesto(Base):
    __tablename__ = "ticket_repuestos"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    proceso_id = Column(Integer, ForeignKey("ticket_procesos.id"), nullable=True, index=True)
    nombre = Column(String(150), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    marca_referencia = Column(String(120), nullable=True)
    foto_url = Column(String(500), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
