from sqlalchemy import Column, Integer, String, Text
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
