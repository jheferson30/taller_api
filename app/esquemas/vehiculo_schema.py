from datetime import datetime

from pydantic import BaseModel, Field


class VehiculoBase(BaseModel):
    placa: str = Field(..., description="Placa del vehículo (6 caracteres)")
    marca: str | None = Field(None, description="Marca del vehículo (ej: Yamaha, Honda)")
    modelo: str | None = Field(None, description="Modelo del vehículo (ej: FZ16, CBR)")
    anio: int | None = Field(None, description="Año del vehículo")
    cilindraje: str | None = Field(None, description="Cilindraje del motor (ej: 150cc, 250cc)")
    color: str | None = Field(None, description="Color del vehículo")
    nombre_propietario: str | None = Field(None, description="Nombre completo del propietario")
    telefono_propietario: str | None = Field(
        None, description="Teléfono de contacto del propietario"
    )


class VehiculoCrear(VehiculoBase):
    class Config:
        json_schema_extra = {
            "example": {
                "placa": "ABC123",
                "marca": "Yamaha",
                "modelo": "FZ16",
                "anio": 2020,
                "cilindraje": "150cc",
                "color": "Negro",
                "nombre_propietario": "Juan Pérez",
                "telefono_propietario": "3001234567",
            }
        }


class VehiculoActualizar(BaseModel):
    marca: str | None = Field(None, description="Nueva marca del vehículo")
    modelo: str | None = Field(None, description="Nuevo modelo del vehículo")
    anio: int | None = Field(None, description="Nuevo año del vehículo")
    cilindraje: str | None = Field(None, description="Nuevo cilindraje")
    color: str | None = Field(None, description="Nuevo color")
    nombre_propietario: str | None = Field(None, description="Nuevo nombre del propietario")
    telefono_propietario: str | None = Field(None, description="Nuevo teléfono del propietario")

    class Config:
        json_schema_extra = {"example": {"telefono_propietario": "3109876543", "color": "Rojo"}}


class VehiculoRespuesta(VehiculoBase):
    id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None

    class Config:
        from_attributes = True
