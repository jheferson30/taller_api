from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CitaCrear(BaseModel):
    # Datos del vehículo (obligatorios)
    placa: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    cilindraje: Optional[str] = None
    color: Optional[str] = None
    
    # Datos del cliente
    nombre_cliente: str
    telefono_cliente: str
    
    # Datos de la cita
    fecha_cita: datetime
    motivo: str
    observaciones: Optional[str] = None
    creado_por: Optional[str] = None


class CitaActualizar(BaseModel):
    fecha_cita: Optional[datetime] = None
    motivo: Optional[str] = None
    observaciones: Optional[str] = None
    estado: Optional[str] = None


class CitaRespuesta(BaseModel):
    id: int
    vehiculo_id: Optional[int]
    placa: Optional[str]
    
    # Datos del vehículo (si están disponibles)
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    cilindraje: Optional[str] = None
    color: Optional[str] = None
    
    nombre_cliente: str
    telefono_cliente: str
    fecha_cita: datetime
    motivo: str
    observaciones: Optional[str]
    estado: str
    ticket_id: Optional[int]
    ticket_codigo: Optional[str]
    fecha_creacion: datetime

    class Config:
        from_attributes = True
