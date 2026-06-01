from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TicketProceso(Base):
    __tablename__ = "ticket_procesos"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False, index=True)
    nombre = Column(String(120), nullable=False)
    descripcion = Column(String(400), nullable=True)
    mecanico = Column(String(120), nullable=True)          # legacy — usado por app mobile
    mecanico_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    foto_url = Column(String(500), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
