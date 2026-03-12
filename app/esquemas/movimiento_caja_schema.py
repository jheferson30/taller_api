from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field

from app.modelos.movimiento_caja import (
    TipoMovimiento,
    EstadoTicket,
    CategoriaEgreso,
)


class MovimientoCajaCrear(BaseModel):
    tipo: TipoMovimiento
    ticket_id: Optional[int] = None
    ticket_codigo: Optional[str] = None
    placa: Optional[str] = None
    estado_ticket: Optional[EstadoTicket] = None
    valor: int = Field(..., gt=0)
    metodo_pago: Optional[str] = None
    categoria_egreso: Optional[CategoriaEgreso] = None
    concepto: Optional[str] = None
    responsable: Optional[str] = None
    observacion: Optional[str] = None
    soporte_url: Optional[str] = None
    creado_por: Optional[str] = None


class MovimientoCajaRespuesta(BaseModel):
    id: int
    tipo: TipoMovimiento
    ticket_id: Optional[int]
    ticket_codigo: Optional[str]
    placa: Optional[str]
    estado_ticket: Optional[EstadoTicket]
    valor: int
    metodo_pago: Optional[str]
    categoria_egreso: Optional[CategoriaEgreso]
    concepto: Optional[str]
    responsable: Optional[str]
    observacion: Optional[str]
    soporte_url: Optional[str]
    creado_por: Optional[str]
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime]

    class Config:
        from_attributes = True


class MovimientoCajaFiltro(BaseModel):
    tipo: Optional[TipoMovimiento] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None


class MovimientoCajaCorregir(BaseModel):
    valor: int = Field(..., gt=0)
    observacion: Optional[str] = None
    motivo: str = Field(..., min_length=3, max_length=200)
    actualizado_por: Optional[str] = None


class CambioMovimientoCajaRespuesta(BaseModel):
    id: int
    movimiento_id: int
    motivo: str
    valor_anterior: int
    valor_nuevo: int
    observacion_anterior: Optional[str]
    observacion_nueva: Optional[str]
    actualizado_por: Optional[str]
    fecha_creacion: datetime

    class Config:
        from_attributes = True
