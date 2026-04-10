"""
Servicio de lógica de negocio para Vehículos.
Requirements: 8.1, 8.2
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modelos.vehiculo import Vehiculo


class VehiculoService:
    """Servicio de lógica de negocio para vehículos."""

    def __init__(self, db: Session):
        self.db = db

    def validar_placa_unica(self, placa: str, vehiculo_id: int | None = None) -> None:
        """
        Valida que la placa sea única.
        Requirements: 8.1
        """
        placa_norm = placa.strip().upper()
        query = self.db.query(Vehiculo).filter(Vehiculo.placa == placa_norm)

        if vehiculo_id:
            query = query.filter(Vehiculo.id != vehiculo_id)

        if query.first():
            raise HTTPException(
                status_code=400, detail=f"Ya existe un vehículo con la placa {placa_norm}"
            )

    def crear_vehiculo(
        self,
        placa: str,
        marca: str | None = None,
        modelo: str | None = None,
        anio: int | None = None,
        cilindraje: int | None = None,
        color: str | None = None,
        nombre_propietario: str | None = None,
        telefono_propietario: str | None = None,
    ) -> Vehiculo:
        """
        Crea un nuevo vehículo con validaciones.
        Requirements: 8.1, 8.2
        """
        placa_norm = placa.strip().upper()

        # Validar placa única
        self.validar_placa_unica(placa_norm)

        vehiculo = Vehiculo(
            placa=placa_norm,
            marca=marca,
            modelo=modelo,
            anio=anio,
            cilindraje=cilindraje,
            color=color,
            nombre_propietario=nombre_propietario,
            telefono_propietario=telefono_propietario,
        )

        self.db.add(vehiculo)
        self.db.flush()
        return vehiculo

    def actualizar_vehiculo(
        self,
        vehiculo: Vehiculo,
        placa: str | None = None,
        marca: str | None = None,
        modelo: str | None = None,
        anio: int | None = None,
        cilindraje: int | None = None,
        color: str | None = None,
        nombre_propietario: str | None = None,
        telefono_propietario: str | None = None,
    ) -> Vehiculo:
        """
        Actualiza un vehículo existente.
        Requirements: 8.2
        """
        if placa and placa.strip().upper() != vehiculo.placa:
            # Si se cambia la placa, validar que sea única
            self.validar_placa_unica(placa, vehiculo.id)
            vehiculo.placa = placa.strip().upper()

        if marca is not None:
            vehiculo.marca = marca
        if modelo is not None:
            vehiculo.modelo = modelo
        if anio is not None:
            vehiculo.anio = anio
        if cilindraje is not None:
            vehiculo.cilindraje = cilindraje
        if color is not None:
            vehiculo.color = color
        if nombre_propietario is not None:
            vehiculo.nombre_propietario = nombre_propietario
        if telefono_propietario is not None:
            vehiculo.telefono_propietario = telefono_propietario

        self.db.flush()
        return vehiculo
