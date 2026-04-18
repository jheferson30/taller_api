from datetime import datetime

from pydantic import BaseModel, Field


class TicketIngresoCrear(BaseModel):
    motivo_visita: str = Field(
        ..., min_length=3, max_length=250, description="Razón de la visita al taller"
    )
    observaciones_recepcion: str | None = Field(
        None, max_length=500, description="Observaciones iniciales del recepcionista"
    )
    kilometraje: int | None = Field(None, ge=0, description="Kilometraje actual del vehículo")
    estado_inicial: str | None = Field(
        None, max_length=300, description="Estado general del vehículo al ingreso"
    )
    anticipo_recibido: int = Field(0, ge=0, description="Monto del anticipo pagado")
    metodo_pago_anticipo: str | None = Field(
        None,
        max_length=50,
        description="Método de pago del anticipo (EFECTIVO, TRANSFERENCIA, etc.)",
    )
    recepcionado_por: str | None = Field(
        None, max_length=120, description="Nombre del recepcionista"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "motivo_visita": "Cambio de aceite y revisión general",
                "observaciones_recepcion": "Cliente reporta ruido en el motor",
                "kilometraje": 15000,
                "estado_inicial": "Buen estado general, llantas desgastadas",
                "anticipo_recibido": 50000,
                "metodo_pago_anticipo": "EFECTIVO",
                "recepcionado_por": "María González",
            }
        }


class TicketRespuesta(BaseModel):
    id: int
    ticket_codigo: str
    vehiculo_id: int
    placa: str
    fecha_ingreso: datetime
    motivo_visita: str
    observaciones_recepcion: str | None
    kilometraje: int | None
    estado_inicial: str | None
    anticipo_recibido: int
    metodo_pago_anticipo: str | None
    recepcionado_por: str | None
    estado: str
    total_servicio: int | None
    saldo_pendiente: int | None
    metodo_pago_final: str | None
    observaciones_finales: str | None
    recomendaciones: str | None
    proximo_mantenimiento: str | None
    confirmado_entrega_por: str | None
    firma_entrega_url: str | None
    comprobante_pdf_url: str | None
    fecha_cierre: datetime | None
    fecha_entrega: datetime | None
    fecha_actualizacion: datetime | None

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
    cilindraje: str | None
    color: str | None
    nombre_propietario: str | None
    telefono_propietario: str | None
    historial_visitas: list[TicketHistorialItem]

    class Config:
        from_attributes = True


class TicketProcesoCrear(BaseModel):
    nombre: str = Field(
        ..., min_length=2, max_length=120, description="Nombre del proceso realizado"
    )
    descripcion: str | None = Field(
        None, max_length=400, description="Descripción detallada del proceso"
    )
    mecanico: str | None = Field(
        None, max_length=120, description="Nombre del mecánico que realizó el proceso"
    )
    foto_url: str | None = Field(None, max_length=500, description="URL de la foto del proceso")

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Cambio de aceite",
                "descripcion": "Cambio de aceite 20W50 sintético, filtro nuevo",
                "mecanico": "Carlos Méndez",
                "foto_url": "/uploads/fotos/proceso_123.jpg",
            }
        }


class TicketProcesoRespuesta(BaseModel):
    id: int
    ticket_id: int
    nombre: str
    descripcion: str | None
    mecanico: str | None
    foto_url: str | None
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketRepuestoCrear(BaseModel):
    proceso_id: int | None = Field(None, description="ID del proceso al que pertenece el repuesto")
    nombre: str = Field(..., min_length=2, max_length=150, description="Nombre del repuesto")
    cantidad: int = Field(1, ge=1, description="Cantidad de repuestos")
    marca_referencia: str | None = Field(
        None, max_length=120, description="Marca y referencia del repuesto"
    )
    foto_url: str | None = Field(None, max_length=500, description="URL de la foto del repuesto")

    class Config:
        json_schema_extra = {
            "example": {
                "proceso_id": 1,
                "nombre": "Filtro de aceite",
                "cantidad": 1,
                "marca_referencia": "Bosch F026407124",
                "foto_url": "/uploads/fotos/repuesto_456.jpg",
            }
        }


class TicketRepuestoRespuesta(BaseModel):
    id: int
    ticket_id: int
    proceso_id: int | None
    nombre: str
    cantidad: int
    marca_referencia: str | None
    foto_url: str | None
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketFotoCrear(BaseModel):
    tipo: str = Field("OTRA", max_length=30)
    archivo_url: str = Field(..., max_length=255)
    descripcion: str | None = Field(None, max_length=250)


class TicketFotoRespuesta(BaseModel):
    id: int
    ticket_id: int
    tipo: str
    archivo_url: str
    descripcion: str | None
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketCompraCrear(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=250)
    valor: int = Field(..., gt=0)
    soporte_url: str | None = Field(None, max_length=255)
    nota: str | None = Field(None, max_length=500)
    responsable: str | None = Field(None, max_length=120)


class TicketCompraRespuesta(BaseModel):
    id: int
    ticket_id: int
    descripcion: str
    valor: int
    soporte_url: str | None
    nota: str | None
    responsable: str | None
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class TicketFinanzasActualizar(BaseModel):
    total_servicio: int = Field(..., gt=0, description="Monto total del servicio")
    metodo_pago_final: str | None = Field(
        None,
        max_length=50,
        description="Método de pago final (EFECTIVO, TRANSFERENCIA, TARJETA, etc.)",
    )
    observaciones_finales: str | None = Field(None, max_length=800)
    recomendaciones: str | None = Field(None, max_length=800)
    proximo_mantenimiento: str | None = Field(None, max_length=200)

    class Config:
        json_schema_extra = {
            "example": {"total_servicio": 150000, "metodo_pago_final": "TRANSFERENCIA"}
        }


class TicketObservacionesFinalesActualizar(BaseModel):
    observaciones_finales: str | None = Field(None, max_length=800)
    recomendaciones: str | None = Field(None, max_length=800)
    proximo_mantenimiento: str | None = Field(None, max_length=200)


class TicketEntregarPayload(BaseModel):
    confirmado_entrega_por: str | None = Field(None, max_length=120)
    firma_entrega_url: str | None = Field(None, max_length=255)
    metodo_pago_final: str | None = Field(None, max_length=50)
    observaciones_finales: str | None = Field(None, max_length=800)
    recomendaciones: str | None = Field(None, max_length=800)
    proximo_mantenimiento: str | None = Field(None, max_length=200)


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
    procesos: list[TicketProcesoRespuesta]
    repuestos: list[TicketRepuestoRespuesta]
    fotos: list[TicketFotoRespuesta]
    compras: list[TicketCompraRespuesta]
    cobros: list[TicketCobroRespuesta]
