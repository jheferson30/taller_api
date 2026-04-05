from sqlalchemy import Column, Integer, String, Text, Boolean
from app.configuracion.base_datos import Base


class ConfiguracionTaller(Base):
    __tablename__ = "configuracion_taller"

    id = Column(Integer, primary_key=True, default=1)
    nombre_taller = Column(String(200), nullable=False, default="Taller Mecánico")
    direccion = Column(String(300), nullable=True)
    telefono = Column(String(50), nullable=True)
    nit = Column(String(50), nullable=True)
    procesos_rapidos = Column(Text, default="[]")  # JSON string
    cobros_rapidos = Column(Text, default="[]")  # JSON string
    whatsapp_token    = Column(Text, nullable=True)
    whatsapp_phone_id = Column(String(50), nullable=True)
    whatsapp_enabled  = Column(Boolean, default=False, nullable=False)
    smtp_user         = Column(String(200), nullable=True)
    smtp_password     = Column(Text, nullable=True)
    smtp_from         = Column(String(200), nullable=True)
