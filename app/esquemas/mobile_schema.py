from datetime import datetime

from pydantic import BaseModel, Field


class TicketListResponse(BaseModel):
    id: int
    ticket_codigo: str
    placa: str
    motivo_visita: str
    estado: str
    fecha_ingreso: datetime
    nombre_propietario: str | None = None
    telefono_propietario: str | None = None

    class Config:
        from_attributes = True


class TicketDetailResponse(BaseModel):
    id: int
    ticket_codigo: str
    placa: str
    motivo_visita: str
    estado: str
    fecha_ingreso: datetime
    observaciones_recepcion: str | None = None
    kilometraje: int | None = None
    estado_inicial: str | None = None
    anticipo_recibido: int
    total_servicio: int | None = None
    saldo_pendiente: int | None = None
    nombre_propietario: str | None = None
    telefono_propietario: str | None = None

    class Config:
        from_attributes = True


class ProcesoResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    mecanico: str | None = None
    foto_url: str | None = None

    class Config:
        from_attributes = True


class RepuestoResponse(BaseModel):
    id: int
    nombre: str
    cantidad: int
    marca_referencia: str | None = None
    foto_url: str | None = None

    class Config:
        from_attributes = True


class FotoResponse(BaseModel):
    id: int
    tipo: str
    archivo_url: str
    descripcion: str | None = None

    class Config:
        from_attributes = True


class ProcesoCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120)
    descripcion: str | None = Field(None, max_length=400)
    mecanico: str | None = Field(None, max_length=120)


class RepuestoCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    cantidad: int = Field(1, ge=1)
    marca_referencia: str | None = Field(None, max_length=120)
    proceso_id: int | None = None
    foto_url: str | None = Field(None, max_length=500)


class ActualizarEstadoTicket(BaseModel):
    estado: str = Field(..., max_length=20)


class EntregarTicketData(BaseModel):
    confirmado_entrega_por: str = Field(..., max_length=120)
    metodo_pago_final: str | None = Field(None, max_length=50)
    observaciones_finales: str | None = Field(None, max_length=800)
    recomendaciones: str | None = Field(None, max_length=800)
    proximo_mantenimiento: str | None = Field(None, max_length=200)


class CompraResponse(BaseModel):
    id: int
    descripcion: str
    valor: int
    soporte_url: str | None = None
    nota: str | None = None
    responsable: str | None = None

    class Config:
        from_attributes = True


class CompraCreate(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=250)
    valor: int = Field(..., gt=0)
    nota: str | None = Field(None, max_length=500)
    responsable: str | None = Field(None, max_length=120)


class CobroResponse(BaseModel):
    id: int
    concepto: str
    valor: int

    class Config:
        from_attributes = True


class CobroCreate(BaseModel):
    concepto: str = Field(..., min_length=2, max_length=200)
    valor: int = Field(..., gt=0)


class ActualizarFinanzasData(BaseModel):
    total_servicio: int = Field(..., gt=0)
    metodo_pago_final: str | None = Field(None, max_length=50)
    observaciones_finales: str | None = Field(None, max_length=800)
    recomendaciones: str | None = Field(None, max_length=800)
    proximo_mantenimiento: str | None = Field(None, max_length=200)
