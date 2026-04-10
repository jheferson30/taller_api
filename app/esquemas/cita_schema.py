from datetime import datetime

from pydantic import BaseModel


class CitaCrear(BaseModel):
    # Datos del vehículo (obligatorios)
    placa: str
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    cilindraje: str | None = None
    color: str | None = None

    # Datos del cliente
    nombre_cliente: str
    telefono_cliente: str

    # Datos de la cita
    fecha_cita: datetime
    motivo: str
    observaciones: str | None = None
    creado_por: str | None = None


class CitaActualizar(BaseModel):
    fecha_cita: datetime | None = None
    motivo: str | None = None
    observaciones: str | None = None
    estado: str | None = None


class CitaRespuesta(BaseModel):
    id: int
    vehiculo_id: int | None
    placa: str | None

    # Datos del vehículo (si están disponibles)
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    cilindraje: str | None = None
    color: str | None = None

    nombre_cliente: str
    telefono_cliente: str
    fecha_cita: datetime
    motivo: str
    observaciones: str | None
    estado: str
    ticket_id: int | None
    ticket_codigo: str | None
    fecha_creacion: datetime

    class Config:
        from_attributes = True
