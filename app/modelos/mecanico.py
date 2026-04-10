from sqlalchemy import Boolean, Column, Integer, String

from app.configuracion.base_datos import Base


class Mecanico(Base):
    __tablename__ = "mecanicos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
