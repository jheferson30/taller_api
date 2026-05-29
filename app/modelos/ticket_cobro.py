from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TicketCobro(Base):
    __tablename__ = "ticket_cobros"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False, index=True)
    concepto = Column(String(200), nullable=False)
    valor = Column(Integer, nullable=False)
    metodo_pago = Column(String(50), nullable=True)  # EFECTIVO, NEQUI, DAVIPLATA, etc.
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
