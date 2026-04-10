from datetime import datetime

from pydantic import BaseModel


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
    nombre: str
    descripcion: str | None = None
    mecanico: str | None = None


class RepuestoCreate(BaseModel):
    nombre: str
    cantidad: int = 1
    marca_referencia: str | None = None
    proceso_id: int | None = None


class ActualizarEstadoTicket(BaseModel):
    estado: str


class EntregarTicketData(BaseModel):
    confirmado_entrega_por: str
    observaciones_finales: str | None = None
    recomendaciones: str | None = None
    proximo_mantenimiento: str | None = None


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
    descripcion: str
    valor: int
    nota: str | None = None
    responsable: str | None = None


class CobroResponse(BaseModel):
    id: int
    concepto: str
    valor: int

    class Config:
        from_attributes = True


class CobroCreate(BaseModel):
    concepto: str
    valor: int


class ActualizarFinanzasData(BaseModel):
    total_servicio: int
    metodo_pago_final: str | None = None
