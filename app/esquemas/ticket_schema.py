from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class TicketIngresoCrear(BaseModel):
    motivo_visita: str = Field(..., min_length=3, max_length=250)
    observaciones_recepcion: Optional[str] = Field(None, max_length=500)
    kilometraje: Optional[int] = Field(None, ge=0)
    estado_inicial: Optional[str] = Field(None, max_length=300)
    anticipo_recibido: int = Field(0, ge=0)
    metodo_pago_anticipo: Optional[str] = Field(None, max_length=50)
    recepcionado_por: Optional[str] = Field(None, max_length=120)


class TicketRespuesta(BaseModel):
    id: int
    ticket_codigo: str
    vehiculo_id: int
    placa: str
    fecha_ingreso: datetime
    motivo_visita: str
    observaciones_recepcion: Optional[str]
    kilometraje: Optional[int]
    estado_inicial: Optional[str]
    anticipo_recibido: int
    metodo_pago_anticipo: Optional[str]
    recepcionado_por: Optional[str]
    estado: str
    total_servicio: Optional[int]
    saldo_pendiente: Optional[int]
    metodo_pago_final: Optional[str]
    observaciones_finales: Optional[str]
    recomendaciones: Optional[str]
    proximo_mantenimiento: Optional[str]
    confirmado_entrega_por: Optional[str]
    firma_entrega_url: Optional[str]
    comprobante_pdf_url: Optional[str]
    fecha_cierre: Optional[datetime]
    fecha_entrega: Optional[datetime]
    fecha_actualizacion: Optional[datetime]

    class Config:
        from_attributes = True


class TicketHistorialItem(BaseModel):
    ticket_codigo: str
    fecha_ingreso: datetime
    motivo_visita: str
    estado: str

    class Config:
        from_attributes = True


class VehiculoFichaRespuesta(BaseModel):
    id: int
    placa: str
    marca: str
    modelo: str
    anio: int
    cilindraje: Optional[str]
    color: Optional[str]
    nombre_propietario: Optional[str]
    telefono_propietario: Optional[str]
    historial_visitas: List[TicketHistorialItem]

    class Config:
        from_attributes = True


class TicketProcesoCrear(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120)
    descripcion: Optional[str] = Field(None, max_length=400)
    mecanico: Optional[str] = Field(None, max_length=120)


class TicketProcesoRespuesta(BaseModel):
    id: int
    ticket_id: int
    nombre: str
    descripcion: Optional[str]
    mecanico: Optional[str]
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketRepuestoCrear(BaseModel):
    proceso_id: Optional[int] = None
    nombre: str = Field(..., min_length=2, max_length=150)
    cantidad: int = Field(1, ge=1)
    marca_referencia: Optional[str] = Field(None, max_length=120)


class TicketRepuestoRespuesta(BaseModel):
    id: int
    ticket_id: int
    proceso_id: Optional[int]
    nombre: str
    cantidad: int
    marca_referencia: Optional[str]
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketFotoCrear(BaseModel):
    tipo: str = Field("OTRA", max_length=30)
    archivo_url: str = Field(..., max_length=255)
    descripcion: Optional[str] = Field(None, max_length=250)


class TicketFotoRespuesta(BaseModel):
    id: int
    ticket_id: int
    tipo: str
    archivo_url: str
    descripcion: Optional[str]
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketCompraCrear(BaseModel):
    descripcion: str = Field(..., min_length=3, max_length=250)
    valor: int = Field(..., gt=0)
    soporte_url: Optional[str] = Field(None, max_length=255)
    nota: Optional[str] = Field(None, max_length=500)
    responsable: Optional[str] = Field(None, max_length=120)


class TicketCompraRespuesta(BaseModel):
    id: int
    ticket_id: int
    descripcion: str
    valor: int
    soporte_url: Optional[str]
    nota: Optional[str]
    responsable: Optional[str]
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketFinanzasActualizar(BaseModel):
    total_servicio: int = Field(..., gt=0)
    metodo_pago_final: Optional[str] = Field(None, max_length=50)


class TicketObservacionesFinalesActualizar(BaseModel):
    observaciones_finales: Optional[str] = Field(None, max_length=800)
    recomendaciones: Optional[str] = Field(None, max_length=800)
    proximo_mantenimiento: Optional[str] = Field(None, max_length=200)


class TicketEntregarPayload(BaseModel):
    confirmado_entrega_por: Optional[str] = Field(None, max_length=120)
    firma_entrega_url: Optional[str] = Field(None, max_length=255)


class TicketCobroCrear(BaseModel):
    concepto: str = Field(..., min_length=2, max_length=200)
    valor: int = Field(..., gt=0)


class TicketCobroRespuesta(BaseModel):
    id: int
    ticket_id: int
    concepto: str
    valor: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketResumenProcesoRespuesta(BaseModel):
    ticket: TicketRespuesta
    procesos: List[TicketProcesoRespuesta]
    repuestos: List[TicketRepuestoRespuesta]
    fotos: List[TicketFotoRespuesta]
    compras: List[TicketCompraRespuesta]
    cobros: List[TicketCobroRespuesta]
