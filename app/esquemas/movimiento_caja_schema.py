from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modelos.movimiento_caja import (
    CategoriaEgreso,
    EstadoTicket,
    TipoMovimiento,
)


class MovimientoCajaCrear(BaseModel):
    tipo: TipoMovimiento = Field(
        ...,
        description="Tipo de movimiento: INGRESO_ANTICIPO, INGRESO_FINAL, INGRESO_RAPIDO, EGRESO",
    )
    ticket_id: int | None = Field(
        None, description="ID del ticket asociado (obligatorio para ingresos)"
    )
    ticket_codigo: str | None = Field(
        None, description="Código del ticket (obligatorio para ingresos)"
    )
    placa: str | None = Field(None, description="Placa del vehículo (obligatorio para ingresos)")
    estado_ticket: EstadoTicket | None = Field(
        None, description="Estado del ticket: ABIERTO, EN_PROCESO, FINALIZADO, ENTREGADO"
    )
    valor: int = Field(..., gt=0, description="Valor del movimiento en pesos colombianos")
    metodo_pago: str | None = Field(
        None, description="Método de pago: EFECTIVO, TRANSFERENCIA, TARJETA, NEQUI, DAVIPLATA"
    )
    categoria_egreso: CategoriaEgreso | None = Field(
        None, description="Categoría del egreso (obligatorio para EGRESO)"
    )
    concepto: str | None = Field(
        None, description="Descripción del movimiento (obligatorio para egresos)"
    )
    responsable: str | None = Field(None, description="Persona responsable del movimiento")
    observacion: str | None = Field(None, description="Observaciones adicionales")
    soporte_url: str | None = Field(None, description="URL del soporte o comprobante")
    creado_por: str | None = Field(None, description="Usuario que creó el movimiento")

    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "INGRESO_ANTICIPO",
                "ticket_id": 123,
                "ticket_codigo": "TK-ABC123-20260406103000",
                "placa": "ABC123",
                "estado_ticket": "ABIERTO",
                "valor": 50000,
                "metodo_pago": "EFECTIVO",
                "responsable": "María González",
                "observacion": "Anticipo recibido al ingreso",
                "creado_por": "admin",
            }
        }


class MovimientoCajaRespuesta(BaseModel):
    id: int = Field(..., description="ID único del movimiento")
    tipo: TipoMovimiento = Field(..., description="Tipo de movimiento")
    ticket_id: int | None = Field(None, description="ID del ticket asociado")
    ticket_codigo: str | None = Field(None, description="Código del ticket")
    placa: str | None = Field(None, description="Placa del vehículo")
    estado_ticket: EstadoTicket | None = Field(None, description="Estado del ticket")
    valor: int = Field(..., description="Valor del movimiento")
    metodo_pago: str | None = Field(None, description="Método de pago utilizado")
    categoria_egreso: CategoriaEgreso | None = Field(None, description="Categoría del egreso")
    concepto: str | None = Field(None, description="Descripción del movimiento")
    responsable: str | None = Field(None, description="Persona responsable")
    observacion: str | None = Field(None, description="Observaciones adicionales")
    soporte_url: str | None = Field(None, description="URL del soporte")
    creado_por: str | None = Field(None, description="Usuario creador")
    fecha_creacion: datetime = Field(..., description="Fecha de creación del movimiento")
    fecha_actualizacion: datetime | None = Field(None, description="Fecha de última actualización")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 456,
                "tipo": "INGRESO_ANTICIPO",
                "ticket_id": 123,
                "ticket_codigo": "TK-ABC123-20260406103000",
                "placa": "ABC123",
                "estado_ticket": "ABIERTO",
                "valor": 50000,
                "metodo_pago": "EFECTIVO",
                "categoria_egreso": None,
                "concepto": None,
                "responsable": "María González",
                "observacion": "Anticipo recibido",
                "soporte_url": None,
                "creado_por": "admin",
                "fecha_creacion": "2026-04-06T10:30:00",
                "fecha_actualizacion": None,
            }
        }


class MovimientoCajaFiltro(BaseModel):
    tipo: TipoMovimiento | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None


class MovimientoCajaCorregir(BaseModel):
    valor: int = Field(..., gt=0, description="Nuevo valor del movimiento")
    observacion: str | None = Field(None, description="Nueva observación")
    motivo: str = Field(..., min_length=3, max_length=200, description="Motivo de la corrección")
    actualizado_por: str | None = Field(None, description="Usuario que realiza la corrección")

    class Config:
        json_schema_extra = {
            "example": {
                "valor": 55000,
                "observacion": "Anticipo corregido",
                "motivo": "Error en el monto inicial",
                "actualizado_por": "admin",
            }
        }


class CambioMovimientoCajaRespuesta(BaseModel):
    id: int
    movimiento_id: int
    motivo: str
    valor_anterior: int
    valor_nuevo: int
    observacion_anterior: str | None
    observacion_nueva: str | None
    actualizado_por: str | None
    fecha_creacion: datetime

    class Config:
        from_attributes = True
