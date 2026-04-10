from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False, index=True)
    ticket_codigo = Column(String(40), unique=True, nullable=False, index=True)
    placa = Column(String(20), nullable=False, index=True)

    fecha_ingreso = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    motivo_visita = Column(String(250), nullable=False)
    observaciones_recepcion = Column(String(500), nullable=True)
    kilometraje = Column(Integer, nullable=True)
    estado_inicial = Column(String(300), nullable=True)

    anticipo_recibido = Column(Integer, default=0, nullable=False)
    metodo_pago_anticipo = Column(String(50), nullable=True)
    recepcionado_por = Column(String(120), nullable=True)

    estado = Column(String(20), default="ABIERTO", nullable=False, index=True)
    total_servicio = Column(Integer, nullable=True)
    saldo_pendiente = Column(Integer, nullable=True)
    metodo_pago_final = Column(String(50), nullable=True)
    observaciones_finales = Column(String(800), nullable=True)
    recomendaciones = Column(String(800), nullable=True)
    proximo_mantenimiento = Column(String(200), nullable=True)
    confirmado_entrega_por = Column(String(120), nullable=True)
    firma_entrega_url = Column(String(255), nullable=True)
    comprobante_pdf_url = Column(String(255), nullable=True)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)
    fecha_entrega = Column(DateTime(timezone=True), nullable=True)
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Note: Relationships are defined dynamically in the repository using joinedload
    # to avoid circular import issues. See ticket_repository.py for eager loading implementation.
