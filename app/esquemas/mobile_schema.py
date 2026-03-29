from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TicketListResponse(BaseModel):
    id: int
    ticket_codigo: str
    placa: str
    motivo_visita: str
    estado: str
    fecha_ingreso: datetime
    nombre_propietario: Optional[str] = None
    telefono_propietario: Optional[str] = None

    class Config:
        from_attributes = True


class TicketDetailResponse(BaseModel):
    id: int
    ticket_codigo: str
    placa: str
    motivo_visita: str
    estado: str
    fecha_ingreso: datetime
    observaciones_recepcion: Optional[str] = None
    kilometraje: Optional[int] = None
    estado_inicial: Optional[str] = None
    anticipo_recibido: int
    total_servicio: Optional[int] = None
    saldo_pendiente: Optional[int] = None
    nombre_propietario: Optional[str] = None
    telefono_propietario: Optional[str] = None

    class Config:
        from_attributes = True


class ProcesoResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    mecanico: Optional[str] = None
    foto_url: Optional[str] = None

    class Config:
        from_attributes = True


class RepuestoResponse(BaseModel):
    id: int
    nombre: str
    cantidad: int
    marca_referencia: Optional[str] = None

    class Config:
        from_attributes = True


class FotoResponse(BaseModel):
    id: int
    tipo: str
    archivo_url: str
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True


class ProcesoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    mecanico: Optional[str] = None


class RepuestoCreate(BaseModel):
    nombre: str
    cantidad: int = 1
    marca_referencia: Optional[str] = None
    proceso_id: Optional[int] = None


class ActualizarEstadoTicket(BaseModel):
    estado: str


class EntregarTicketData(BaseModel):
    confirmado_entrega_por: str
    observaciones_finales: Optional[str] = None
    recomendaciones: Optional[str] = None
    proximo_mantenimiento: Optional[str] = None


class CompraResponse(BaseModel):
    id: int
    descripcion: str
    valor: int
    soporte_url: Optional[str] = None
    nota: Optional[str] = None
    responsable: Optional[str] = None

    class Config:
        from_attributes = True


class CompraCreate(BaseModel):
    descripcion: str
    valor: int
    nota: Optional[str] = None
    responsable: Optional[str] = None


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
    metodo_pago_final: Optional[str] = None
