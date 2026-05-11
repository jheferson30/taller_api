from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.configuracion.base_datos import Base


class ConfiguracionTaller(Base):
    __tablename__ = "configuracion_taller"

    id = Column(Integer, primary_key=True)
    taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False, unique=True, index=True)
    nombre_taller = Column(String(200), nullable=False, default="Taller Mecánico")
    direccion = Column(String(300), nullable=True)
    telefono = Column(String(50), nullable=True)
    nit = Column(String(50), nullable=True)
    procesos_rapidos = Column(Text, default="[]")  # JSON string
    cobros_rapidos = Column(Text, default="[]")  # JSON string
    whatsapp_token = Column(Text, nullable=True)
    whatsapp_phone_id = Column(String(50), nullable=True)
    whatsapp_enabled = Column(Boolean, default=False, nullable=False)
    smtp_user = Column(String(200), nullable=True)
    smtp_password = Column(Text, nullable=True)
    smtp_from = Column(String(200), nullable=True)
    logo_url = Column(String(255), nullable=True)
    moneda = Column(String(3), nullable=False, default="COP")
    idioma = Column(String(2), nullable=False, default="es")
    timezone = Column(String(100), nullable=False, default="America/Bogota")

    # Relación inversa con Taller
    taller = relationship("Taller", back_populates="configuracion")
