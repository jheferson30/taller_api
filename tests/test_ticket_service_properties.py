"""
Property-based tests para TicketService (extensión de asignación de mecánico).

Valida las propiedades de corrección P4 y P5:

P4 — Aislamiento de asignación de mecánico (Req 2.2, 2.3, 2.4)
P5 — No interferencia de campos en Ticket (Req 2.5)

Feature: notificaciones-internas-sistema
"""

import pytest
from types import SimpleNamespace
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.configuracion.base_datos import Base

# Import all models so SQLAlchemy resolves relationships
from app.modelos.audit_log import AuditLog  # noqa: F401
from app.modelos.configuracion_taller import ConfiguracionTaller  # noqa: F401
from app.modelos.mecanico import Mecanico
from app.modelos.notificacion import Notificacion  # noqa: F401
from app.modelos.password_reset_token import PasswordResetToken  # noqa: F401
from app.modelos.role import Role  # noqa: F401
from app.modelos.taller import Taller
from app.modelos.ticket import Ticket
from app.modelos.token_blacklist import TokenBlacklist  # noqa: F401
from app.modelos.user import User  # noqa: F401
from app.modelos.user_role import UserRole  # noqa: F401
from app.modelos.vehiculo import Vehiculo
from app.servicios.ticket_service import TicketService


# ── Helpers ───────────────────────────────────────────────────────────────────

def crear_taller(db, nombre: str) -> Taller:
    import uuid
    nombre_unico = f"{nombre}_{uuid.uuid4().hex[:8]}"
    taller = Taller(nombre=nombre_unico, activo=True)
    db.add(taller)
    db.flush()
    return taller


def crear_mecanico(db, taller_id: int, nombre: str) -> Mecanico:
    import uuid
    nombre_unico = f"{nombre}_{uuid.uuid4().hex[:8]}"
    mecanico = Mecanico(
        taller_id=taller_id,
        nombre=nombre_unico,
        activo=True,
    )
    db.add(mecanico)
    db.flush()
    return mecanico


def crear_vehiculo(db, taller_id: int, placa: str) -> Vehiculo:
    vehiculo = Vehiculo(
        taller_id=taller_id,
        placa=placa,
        marca="Toyota",
        modelo="Corolla",
        anio=2020,
    )
    db.add(vehiculo)
    db.flush()
    return vehiculo


def crear_ticket(
    db,
    taller_id: int,
    vehiculo_id: int,
    placa: str,
    recepcionado_por: str = "Admin Test",
    mecanico_asignado_id: int | None = None,
) -> Ticket:
    import uuid
    codigo = f"T-{uuid.uuid4().hex[:8].upper()}"
    ticket = Ticket(
        taller_id=taller_id,
        vehiculo_id=vehiculo_id,
        ticket_codigo=codigo,
        placa=placa,
        motivo_visita="Mantenimiento preventivo",
        recepcionado_por=recepcionado_por,
        estado="ABIERTO",
        mecanico_asignado_id=mecanico_asignado_id,
    )
    db.add(ticket)
    db.flush()
    return ticket


# ── Strategies ────────────────────────────────────────────────────────────────

@st.composite
def nombre_valido(draw):
    """Genera nombres válidos para talleres y mecánicos."""
    return draw(st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")), min_size=3, max_size=20))


@st.composite
def placa_valida(draw):
    """Genera placas válidas."""
    return draw(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=6, max_size=6))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Crea una sesión de BD en memoria para cada test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ── Tests de Propiedades ──────────────────────────────────────────────────────

class TestTicketServiceAsignacionMecanico:
    """
    Tests de propiedades para la asignación de mecánico en TicketService.
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        nombre_taller_a=nombre_valido(),
        nombre_taller_b=nombre_valido(),
        nombre_mecanico=nombre_valido(),
        placa=placa_valida(),
    )
    def test_p4_aislamiento_asignacion_mecanico(
        self,
        db_session,
        nombre_taller_a,
        nombre_taller_b,
        nombre_mecanico,
        placa,
    ):
        """
        Feature: notificaciones-internas-sistema, Property 4: Aislamiento de asignación de mecánico
        
        Valida: Requisitos 2.2, 2.3, 2.4
        
        Propiedad: Para cualquier intento de asignar un mecanico_asignado_id a un ticket,
        si el mecánico pertenece a un taller_id diferente al del servicio, la operación
        debe ser rechazada con HTTP 404 y el ticket no debe ser modificado.
        """
        # Crear dos talleres distintos
        taller_a = crear_taller(db_session, nombre_taller_a)
        taller_b = crear_taller(db_session, nombre_taller_b)
        
        # Crear mecánico en taller B
        mecanico_b = crear_mecanico(db_session, taller_b.id, nombre_mecanico)
        
        # Crear vehículo y ticket en taller A
        vehiculo_a = crear_vehiculo(db_session, taller_a.id, placa)
        ticket_a = crear_ticket(db_session, taller_a.id, vehiculo_a.id, placa)
        
        # Guardar el estado original del ticket
        mecanico_original = ticket_a.mecanico_asignado_id
        
        # Intentar asignar mecánico de taller B a ticket de taller A
        service_a = TicketService(db_session, taller_a.id)
        
        with pytest.raises(HTTPException) as exc_info:
            service_a.asignar_mecanico(ticket_a, mecanico_b.id)
        
        # Verificar que retorna HTTP 404
        assert exc_info.value.status_code == 404, (
            f"P4: Debe retornar HTTP 404 al asignar mecánico de otro taller, "
            f"pero retornó {exc_info.value.status_code}"
        )
        
        # Verificar que el ticket no fue modificado
        db_session.refresh(ticket_a)
        assert ticket_a.mecanico_asignado_id == mecanico_original, (
            f"P4: El ticket no debe ser modificado al rechazar asignación cross-tenant. "
            f"Original: {mecanico_original}, Actual: {ticket_a.mecanico_asignado_id}"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        nombre_taller=nombre_valido(),
        nombre_mecanico=nombre_valido(),
        placa=placa_valida(),
        recepcionado_por=st.text(min_size=3, max_size=50),
    )
    def test_p5_no_interferencia_campos_ticket(
        self,
        db_session,
        nombre_taller,
        nombre_mecanico,
        placa,
        recepcionado_por,
    ):
        """
        Feature: notificaciones-internas-sistema, Property 5: No interferencia de campos en Ticket
        
        Valida: Requisitos 2.5
        
        Propiedad: Para cualquier ticket con recepcionado_por definido, asignar o cambiar
        mecanico_asignado_id no debe modificar el valor de recepcionado_por.
        """
        # Crear taller, mecánico, vehículo y ticket
        taller = crear_taller(db_session, nombre_taller)
        mecanico = crear_mecanico(db_session, taller.id, nombre_mecanico)
        vehiculo = crear_vehiculo(db_session, taller.id, placa)
        ticket = crear_ticket(
            db_session,
            taller.id,
            vehiculo.id,
            placa,
            recepcionado_por=recepcionado_por,
        )
        
        # Guardar el valor original de recepcionado_por
        recepcionado_original = ticket.recepcionado_por
        
        # Asignar mecánico
        service = TicketService(db_session, taller.id)
        service.asignar_mecanico(ticket, mecanico.id)
        
        # Verificar que recepcionado_por no cambió
        assert ticket.recepcionado_por == recepcionado_original, (
            f"P5: recepcionado_por no debe cambiar al asignar mecánico. "
            f"Original: {recepcionado_original}, Actual: {ticket.recepcionado_por}"
        )
        
        # Crear otro mecánico y cambiar la asignación
        mecanico2 = crear_mecanico(db_session, taller.id, f"{nombre_mecanico}_2")
        service.asignar_mecanico(ticket, mecanico2.id)
        
        # Verificar nuevamente que recepcionado_por no cambió
        assert ticket.recepcionado_por == recepcionado_original, (
            f"P5: recepcionado_por no debe cambiar al cambiar mecánico asignado. "
            f"Original: {recepcionado_original}, Actual: {ticket.recepcionado_por}"
        )
        
        # Desasignar mecánico (None)
        service.asignar_mecanico(ticket, None)
        
        # Verificar una vez más que recepcionado_por no cambió
        assert ticket.recepcionado_por == recepcionado_original, (
            f"P5: recepcionado_por no debe cambiar al desasignar mecánico. "
            f"Original: {recepcionado_original}, Actual: {ticket.recepcionado_por}"
        )
