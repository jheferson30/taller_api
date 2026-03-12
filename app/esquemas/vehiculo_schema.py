from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VehiculoBase(BaseModel):
    placa: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    cilindraje: Optional[str] = None
    color: Optional[str] = None
    nombre_propietario: Optional[str] = None
    telefono_propietario: Optional[str] = None


class VehiculoCrear(VehiculoBase):
    pass


class VehiculoActualizar(BaseModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    cilindraje: Optional[str] = None
    color: Optional[str] = None
    nombre_propietario: Optional[str] = None
    telefono_propietario: Optional[str] = None


class VehiculoRespuesta(VehiculoBase):
    id: int
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime]

    class Config:
        from_attributes = True
