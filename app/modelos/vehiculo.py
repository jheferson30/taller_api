from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.configuracion.base_datos import Base
from app.utils.pii_encryptor import EncryptedString


class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    taller_id = Column(
        Integer, ForeignKey("talleres.id"), nullable=False, index=True
    )

    placa = Column(String(20), unique=True, index=True, nullable=False)
    marca = Column(String(100), nullable=True)
    modelo = Column(String(100), nullable=True)
    anio = Column(Integer, nullable=True)
    cilindraje = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)

    # Cifrado AES-256-GCM transparente — el valor se almacena como base64(IV||TAG||CIPHERTEXT)
    # en la BD y se descifra automáticamente al cargar el registro (transparente para la capa de servicio).
    nombre_propietario = Column(EncryptedString(500), nullable=True)

    # Cifrado AES-256-GCM transparente — el valor se almacena como base64(IV||TAG||CIPHERTEXT)
    # en la BD y se descifra automáticamente al cargar el registro (transparente para la capa de servicio).
    telefono_propietario = Column(EncryptedString(500), nullable=True)

    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
