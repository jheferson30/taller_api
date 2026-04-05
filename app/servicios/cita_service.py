"""
Servicio de lógica de negocio para Citas.
Requirements: 8.1, 8.2, 8.3
"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modelos.cita import Cita
from app.modelos.vehiculo import Vehiculo
from app.modelos.ticket import Ticket


class CitaService:
    """Servicio de lógica de negocio para citas."""

    def __init__(self, db: Session):
        self.db = db

    def crear_o_actualizar_vehiculo(
        self,
        placa: str,
        marca: str = None,
        modelo: str = None,
        anio: int = None,
        cilindraje: int = None,
        color: str = None,
        nombre_cliente: str = None,
        telefono_cliente: str = None,
    ) -> Vehiculo:
        """
        Crea o actualiza un vehículo al crear una cita.
        Requirements: 8.1, 8.2
        """
        placa_norm = placa.strip().upper()

        # Buscar si el vehículo ya existe
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.placa == placa_norm).first()

        if vehiculo:
            # Vehículo existe - actualizar datos si se proporcionaron
            if marca:
                vehiculo.marca = marca
            if modelo:
                vehiculo.modelo = modelo
            if anio:
                vehiculo.anio = anio
            if cilindraje:
                vehiculo.cilindraje = cilindraje
            if color:
                vehiculo.color = color

            # Actualizar datos del propietario si cambiaron
            if nombre_cliente and nombre_cliente != vehiculo.nombre_propietario:
                vehiculo.nombre_propietario = nombre_cliente
            if telefono_cliente and telefono_cliente != vehiculo.telefono_propietario:
                vehiculo.telefono_propietario = telefono_cliente
        else:
            # Vehículo no existe - crear uno nuevo
            vehiculo = Vehiculo(
                placa=placa_norm,
                marca=marca,
                modelo=modelo,
                anio=anio,
                cilindraje=cilindraje,
                color=color,
                nombre_propietario=nombre_cliente,
                telefono_propietario=telefono_cliente,
            )
            self.db.add(vehiculo)
            self.db.flush()

        return vehiculo

    def validar_editable(self, cita: Cita):
        """
        Valida que una cita pueda ser editada.
        Requirements: 8.3
        """
        if cita.estado == "CONVERTIDA":
            raise HTTPException(
                status_code=400,
                detail="No se puede editar una cita ya convertida en ticket"
            )

    def cancelar_cita(self, cita: Cita):
        """
        Cancela una cita.
        Requirements: 8.3
        """
        if cita.estado == "CONVERTIDA":
            raise HTTPException(
                status_code=400,
                detail="No se puede cancelar una cita ya convertida"
            )

        cita.estado = "CANCELADA"

    def generar_ticket_desde_cita(self, cita: Cita) -> Ticket:
        """
        Convierte una cita en un ticket de ingreso.
        Requirements: 8.1, 8.2, 8.3
        """
        if cita.estado == "CONVERTIDA":
            raise HTTPException(
                status_code=400,
                detail="Esta cita ya fue convertida en ticket"
            )

        if not cita.placa:
            raise HTTPException(
                status_code=400,
                detail="La cita debe tener una placa para generar ticket"
            )

        # El vehículo ya debe existir porque se creó/actualizó al crear la cita
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.placa == cita.placa).first()

        if not vehiculo:
            # Esto no debería pasar, pero por seguridad creamos el vehículo
            vehiculo = Vehiculo(
                placa=cita.placa,
                marca=cita.marca,
                modelo=cita.modelo,
                anio=cita.anio,
                cilindraje=cita.cilindraje,
                color=cita.color,
                nombre_propietario=cita.nombre_cliente,
                telefono_propietario=cita.telefono_cliente,
            )
            self.db.add(vehiculo)
            self.db.flush()
        else:
            # Actualizar vehículo con datos de la cita si están más completos
            if cita.marca and not vehiculo.marca:
                vehiculo.marca = cita.marca
            if cita.modelo and not vehiculo.modelo:
                vehiculo.modelo = cita.modelo
            if cita.anio and not vehiculo.anio:
                vehiculo.anio = cita.anio
            if cita.cilindraje and not vehiculo.cilindraje:
                vehiculo.cilindraje = cita.cilindraje
            if cita.color and not vehiculo.color:
                vehiculo.color = cita.color

        # Generar código de ticket
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        ticket_codigo = f"TK-{cita.placa}-{timestamp}"

        # Crear ticket
        ticket = Ticket(
            vehiculo_id=vehiculo.id,
            ticket_codigo=ticket_codigo,
            placa=cita.placa,
            motivo_visita=cita.motivo,
            observaciones_recepcion=cita.observaciones
            or f"Generado desde cita del {cita.fecha_cita.strftime('%d/%m/%Y %H:%M')}",
            recepcionado_por=cita.creado_por,
        )

        self.db.add(ticket)
        self.db.flush()

        # Actualizar cita
        cita.estado = "CONVERTIDA"
        cita.ticket_id = ticket.id
        cita.ticket_codigo = ticket_codigo

        return ticket
