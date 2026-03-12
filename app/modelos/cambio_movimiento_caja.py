from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class CambioMovimientoCaja(Base):
    __tablename__ = "cambios_movimiento_caja"

    id = Column(Integer, primary_key=True, index=True)
    movimiento_id = Column(Integer, ForeignKey("movimientos_caja.id"), nullable=False, index=True)
    motivo = Column(String(200), nullable=False)
    valor_anterior = Column(Integer, nullable=False)
    valor_nuevo = Column(Integer, nullable=False)
    observacion_anterior = Column(Text, nullable=True)
    observacion_nueva = Column(Text, nullable=True)
    actualizado_por = Column(String(120), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
