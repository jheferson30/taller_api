import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class TipoMovimiento(enum.StrEnum):
    INGRESO_ANTICIPO = "INGRESO_ANTICIPO"
    INGRESO_FINAL = "INGRESO_FINAL"
    INGRESO_RAPIDO = "INGRESO_RAPIDO"
    EGRESO = "EGRESO"


class EstadoTicket(enum.StrEnum):
    ABIERTO = "ABIERTO"
    EN_PROCESO = "EN_PROCESO"
    FINALIZADO = "FINALIZADO"
    ENTREGADO = "ENTREGADO"


class CategoriaEgreso(enum.StrEnum):
    REPUESTO = "REPUESTO"
    PARTE = "PARTE"
    INSUMO = "INSUMO"
    HERRAMIENTA = "HERRAMIENTA"
    OTRO = "OTRO"


class MovimientoCaja(Base):
    __tablename__ = "movimientos_caja"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Enum(TipoMovimiento), nullable=False)
    ticket_id = Column(Integer, nullable=True, index=True)
    ticket_codigo = Column(String(40), nullable=True, index=True)
    placa = Column(String(20), nullable=True, index=True)
    estado_ticket = Column(Enum(EstadoTicket), nullable=True)
    valor = Column(Integer, nullable=False)
    metodo_pago = Column(String)
    categoria_egreso = Column(Enum(CategoriaEgreso), nullable=True)
    concepto = Column(String(200), nullable=True)
    responsable = Column(String(120), nullable=True)
    observacion = Column(Text, nullable=True)
    soporte_url = Column(String(255), nullable=True)
    creado_por = Column(String(120), nullable=True)
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
