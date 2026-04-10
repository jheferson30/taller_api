from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base


class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)

    placa = Column(String(20), unique=True, index=True, nullable=False)
    marca = Column(String(100), nullable=True)
    modelo = Column(String(100), nullable=True)
    anio = Column(Integer, nullable=True)
    cilindraje = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)

    nombre_propietario = Column(String(150), nullable=True)
    telefono_propietario = Column(String(20), nullable=True)

    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
