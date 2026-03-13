from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class Cita(Base):
    __tablename__ = "citas"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=True, index=True)
    placa = Column(String(20), nullable=False, index=True)
    
    # Datos del vehículo (guardados en la cita para referencia)
    marca = Column(String(100), nullable=True)
    modelo = Column(String(100), nullable=True)
    anio = Column(Integer, nullable=True)
    cilindraje = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)
    
    # Datos del cliente (si no tiene vehículo registrado)
    nombre_cliente = Column(String(150), nullable=False)
    telefono_cliente = Column(String(50), nullable=False)
    
    # Datos de la cita
    fecha_cita = Column(DateTime(timezone=True), nullable=False, index=True)
    motivo = Column(String(250), nullable=False)
    observaciones = Column(String(500), nullable=True)
    
    # Estado: PENDIENTE, CONFIRMADA, CANCELADA, CONVERTIDA
    estado = Column(String(20), default="PENDIENTE", nullable=False, index=True)
    
    # Si se convirtió en ticket
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    ticket_codigo = Column(String(40), nullable=True)
    
    # Auditoría
    creado_por = Column(String(120), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
