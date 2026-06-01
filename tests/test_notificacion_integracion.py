"""
Tests de integración end-to-end para el sistema de notificaciones internas.

Cubre los flujos completos:
1. Crear ticket con mecánico → verificar notificación TICKET_ASIGNADO en BD
2. Ejecutar verificador → verificar notificaciones RENOVACION_PLAN en BD
3. Endpoint GET /notificaciones/no-leidas responde en < 300ms

Feature: notificaciones-internas-sistema
"""

import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base

# Importar todos los modelos para que SQLAlchemy resuelva las relaciones
from app.modelos.audit_log import AuditLog  # noqa: F401
from app.modelos.configuracion_taller import ConfiguracionTaller  # noqa: F401
from app.modelos.mecanico import Mecanico
from app.modelos.notificacion import Notificacion, TipoNotificacion
from app.modelos.password_reset_token import PasswordResetToken  # noqa: F401
from app.modelos.role import Role
from app.modelos.taller import EstadoTaller, Taller
from app.modelos.ticket import Ticket
from app.modelos.token_blacklist import TokenBlacklist  # noqa: F401
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.modelos.vehiculo import Vehiculo
from app.repositorios.notificacion_repository import NotificacionRepository
from app.servicios.notificacion_service import NotificacionService
from app.servicios.ticket_service import TicketService


# ── Helpers ───────────────────────────────────────────────────────────────────

def uid() -> str:
    return uuid.uuid4().hex[:8]


def crear_taller(db, estado: EstadoTaller = EstadoTaller.ACTIVO, dias_vencimiento: int | None = None) -> Taller:
    fecha_venc = None
    if dias_vencimiento is not None:
        fecha_venc = datetime.now(timezone.utc) + timedelta(days=dias_vencimiento)
    taller = Taller(
        nombre=f"taller_{uid()}",
        activo=True,
        estado=estado,
        fecha_vencimiento_plan=fecha_venc,
    )
    db.add(taller)
    db.flush()
    return taller


def crear_usuario(db, taller_id: int, rol_nombre: str = "MECANICO") -> User:
    nombre = f"user_{uid()}"
    user = User(
        taller_id=taller_id,
        username=nombre,
        email=f"{nombre}@test.com",
        password_hash="hashed_password",
        is_active=True,
        is_migrated=True,
    )
    db.add(user)
    db.flush()

    rol = db.query(Role).filter(Role.name == rol_nombre).first()
    if not rol:
        rol = Role(name=rol_nombre, description=f"Rol {rol_nombre}")
        db.add(rol)
        db.flush()

    user_role = UserRole(user_id=user.id, role_id=rol.id)
    db.add(user_role)
    db.flush()
    return user


def crear_mecanico_con_usuario(db, taller_id: int) -> tuple[Mecanico, User]:
    """Crea un mecánico con su usuario vinculado."""
    user = crear_usuario(db, taller_id, "MECANICO")
    mecanico = Mecanico(
        taller_id=taller_id,
        nombre=f"mecanico_{uid()}",
        activo=True,
    )
    db.add(mecanico)
    db.flush()
    return mecanico, user


def crear_vehiculo(db, taller_id: int) -> Vehiculo:
    vehiculo = Vehiculo(
        taller_id=taller_id,
        placa=f"TST{uid()[:3].upper()}",
        marca="Toyota",
        modelo="Corolla",
        anio=2020,
    )
    db.add(vehiculo)
    db.flush()
    return vehiculo


def crear_ticket(db, taller_id: int, vehiculo_id: int) -> Ticket:
    ticket = Ticket(
        taller_id=taller_id,
        vehiculo_id=vehiculo_id,
        ticket_codigo=f"TK-{uid().upper()}",
        placa=f"TST{uid()[:3].upper()}",
        motivo_visita="Mantenimiento preventivo",
        recepcionado_por="Admin Test",
        estado="ABIERTO",
    )
    db.add(ticket)
    db.flush()
    return ticket


def simular_verificador(db, taller: Taller) -> list[Notificacion]:
    """Replica la lógica del verificador de plan para tests en memoria."""
    if taller.estado in (EstadoTaller.SUSPENDIDO, EstadoTaller.CANCELADO):
        return []
    if taller.fecha_vencimiento_plan is None:
        return []

    ahora = datetime.now(timezone.utc)
    fecha_venc = taller.fecha_vencimiento_plan
    if fecha_venc.tzinfo is None:
        fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)

    dias_restantes = (fecha_venc - ahora).days
    if dias_restantes > 3:
        return []

    repo = NotificacionRepository(db, taller.id)
    if repo.existe_notif_renovacion_reciente(taller.id, horas=24):
        return []

    admins = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            User.taller_id == taller.id,
            User.is_active == True,
            Role.name == "ADMIN",
        )
        .all()
    )
    if not admins:
        return []

    service = NotificacionService(db, taller.id)
    return service.crear_notificaciones_renovacion(taller, admins, dias_restantes)


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Base de datos SQLite en memoria para tests de integración."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ── Test 1: Flujo completo — crear ticket con mecánico → TICKET_ASIGNADO ──────

class TestFlujoAsignacionTicket:
    """
    Test 1: Flujo completo de asignación de ticket a mecánico.
    Verifica que se crea exactamente 1 notificación TICKET_ASIGNADO en BD.
    """

    def test_asignar_mecanico_crea_notificacion_ticket_asignado(self, db_session):
        """
        Flujo completo:
        1. Crear taller, mecánico con user_id, vehículo y ticket
        2. Llamar a TicketService.asignar_mecanico
        3. Verificar que existe exactamente 1 notificación TICKET_ASIGNADO
           con referencia_id == ticket.id
        """
        # Arrange
        taller = crear_taller(db_session)
        mecanico, user_mecanico = crear_mecanico_con_usuario(db_session, taller.id)
        vehiculo = crear_vehiculo(db_session, taller.id)
        ticket = crear_ticket(db_session, taller.id, vehiculo.id)

        # Act — asignar mecánico con su user_id
        service = TicketService(db_session, taller.id)
        service.asignar_mecanico(ticket, mecanico.id, mecanico_user_id=user_mecanico.id)
        db_session.flush()

        # Assert — exactamente 1 notificación TICKET_ASIGNADO en BD
        notifs = (
            db_session.query(Notificacion)
            .filter(
                Notificacion.taller_id == taller.id,
                Notificacion.tipo == TipoNotificacion.TICKET_ASIGNADO,
                Notificacion.destinatario_user_id == user_mecanico.id,
            )
            .all()
        )
        assert len(notifs) == 1, (
            f"Debe existir exactamente 1 notificación TICKET_ASIGNADO, "
            f"se encontraron {len(notifs)}"
        )
        assert notifs[0].referencia_id == ticket.id, (
            f"referencia_id debe ser {ticket.id}, es {notifs[0].referencia_id}"
        )
        assert notifs[0].leida is False, "La notificación debe estar no leída"

    def test_asignar_mecanico_sin_user_id_no_crea_notificacion(self, db_session):
        """
        Si el mecánico no tiene user_id vinculado, no se crea notificación
        y no se lanza error (Req 3.5).
        """
        taller = crear_taller(db_session)
        mecanico, _ = crear_mecanico_con_usuario(db_session, taller.id)
        vehiculo = crear_vehiculo(db_session, taller.id)
        ticket = crear_ticket(db_session, taller.id, vehiculo.id)

        # Asignar sin user_id
        service = TicketService(db_session, taller.id)
        service.asignar_mecanico(ticket, mecanico.id, mecanico_user_id=None)
        db_session.flush()

        # No debe haber notificaciones
        total = (
            db_session.query(Notificacion)
            .filter(Notificacion.tipo == TipoNotificacion.TICKET_ASIGNADO)
            .count()
        )
        assert total == 0, f"No debe haber notificaciones cuando user_id es None, hay {total}"

    def test_reasignar_mecanico_crea_nueva_notificacion(self, db_session):
        """
        Al cambiar el mecánico asignado, se crea una nueva notificación
        para el nuevo mecánico (Req 3.2).
        """
        taller = crear_taller(db_session)
        mecanico1, user1 = crear_mecanico_con_usuario(db_session, taller.id)
        mecanico2, user2 = crear_mecanico_con_usuario(db_session, taller.id)
        vehiculo = crear_vehiculo(db_session, taller.id)
        ticket = crear_ticket(db_session, taller.id, vehiculo.id)

        service = TicketService(db_session, taller.id)

        # Primera asignación
        service.asignar_mecanico(ticket, mecanico1.id, mecanico_user_id=user1.id)
        db_session.flush()

        # Segunda asignación (mecánico diferente)
        service.asignar_mecanico(ticket, mecanico2.id, mecanico_user_id=user2.id)
        db_session.flush()

        # Debe haber 2 notificaciones en total (una por cada asignación)
        total = (
            db_session.query(Notificacion)
            .filter(Notificacion.tipo == TipoNotificacion.TICKET_ASIGNADO)
            .count()
        )
        assert total == 2, f"Debe haber 2 notificaciones (una por asignación), hay {total}"


# ── Test 2: Flujo completo — verificador → RENOVACION_PLAN ───────────────────

class TestFlujoVerificadorPlan:
    """
    Test 2: Flujo completo del verificador de plan.
    Verifica que se crea 1 notificación RENOVACION_PLAN para el ADMIN.
    """

    def test_verificador_crea_notificacion_renovacion_plan(self, db_session):
        """
        Flujo completo:
        1. Crear taller ACTIVO con fecha_vencimiento_plan en 2 días y un ADMIN
        2. Llamar a simular_verificador
        3. Verificar que existe 1 notificación RENOVACION_PLAN en BD para el ADMIN
        """
        # Arrange
        taller = crear_taller(db_session, estado=EstadoTaller.ACTIVO, dias_vencimiento=2)
        admin = crear_usuario(db_session, taller.id, "ADMIN")

        # Act
        notifs = simular_verificador(db_session, taller)
        db_session.flush()

        # Assert
        assert len(notifs) == 1, (
            f"Debe crearse exactamente 1 notificación RENOVACION_PLAN, "
            f"se crearon {len(notifs)}"
        )
        assert notifs[0].tipo == TipoNotificacion.RENOVACION_PLAN
        assert notifs[0].destinatario_user_id == admin.id
        assert notifs[0].taller_id == taller.id
        assert notifs[0].leida is False

        # Verificar en BD directamente
        en_bd = (
            db_session.query(Notificacion)
            .filter(
                Notificacion.taller_id == taller.id,
                Notificacion.tipo == TipoNotificacion.RENOVACION_PLAN,
                Notificacion.destinatario_user_id == admin.id,
            )
            .count()
        )
        assert en_bd == 1, f"Debe haber 1 notificación en BD, hay {en_bd}"

    def test_verificador_no_duplica_notificacion_en_24h(self, db_session):
        """
        Si ya existe una RENOVACION_PLAN en las últimas 24h, no se crea otra (Req 7.2).
        """
        taller = crear_taller(db_session, estado=EstadoTaller.ACTIVO, dias_vencimiento=1)
        crear_usuario(db_session, taller.id, "ADMIN")

        # Primera ejecución
        notifs1 = simular_verificador(db_session, taller)
        db_session.flush()
        assert len(notifs1) == 1

        # Segunda ejecución — debe omitir
        notifs2 = simular_verificador(db_session, taller)
        assert len(notifs2) == 0, "Segunda ejecución no debe crear notificaciones adicionales"

    def test_verificador_omite_taller_sin_fecha_vencimiento(self, db_session):
        """Taller sin fecha_vencimiento_plan no genera notificaciones (Req 7.5)."""
        taller = crear_taller(db_session, estado=EstadoTaller.ACTIVO, dias_vencimiento=None)
        crear_usuario(db_session, taller.id, "ADMIN")

        notifs = simular_verificador(db_session, taller)
        assert len(notifs) == 0, "Taller sin fecha_vencimiento_plan no debe generar notificaciones"


# ── Test 3: Rendimiento — GET /notificaciones/no-leidas < 300ms ───────────────

class TestRendimientoNotificaciones:
    """
    Test 3: El servicio NotificacionService.obtener_no_leidas responde en < 300ms
    con 50 notificaciones para un usuario.
    """

    def test_obtener_no_leidas_responde_en_menos_de_300ms(self, db_session):
        """
        Crea 50 notificaciones para un usuario y mide el tiempo de
        NotificacionService.obtener_no_leidas(user_id).
        Debe completarse en menos de 300ms.
        """
        # Arrange
        taller = crear_taller(db_session)
        user = crear_usuario(db_session, taller.id, "MECANICO")

        # Crear 50 notificaciones no leídas
        for i in range(50):
            notif = Notificacion(
                taller_id=taller.id,
                destinatario_user_id=user.id,
                tipo=TipoNotificacion.TICKET_ASIGNADO,
                titulo=f"Ticket #{i} asignado",
                mensaje=f"Se te ha asignado el ticket #{i}",
                leida=False,
                referencia_id=i + 1,
            )
            db_session.add(notif)
        db_session.flush()

        service = NotificacionService(db_session, taller.id)

        # Act — medir tiempo de respuesta
        inicio = time.perf_counter()
        resultado = service.obtener_no_leidas(user.id)
        fin = time.perf_counter()

        elapsed_ms = (fin - inicio) * 1000

        # Assert
        assert resultado["total"] == 50, (
            f"Debe retornar 50 notificaciones, retornó {resultado['total']}"
        )
        assert elapsed_ms < 300, (
            f"obtener_no_leidas debe responder en < 300ms, tardó {elapsed_ms:.1f}ms"
        )

    def test_obtener_no_leidas_aislamiento_multi_tenant(self, db_session):
        """
        Verifica que obtener_no_leidas solo retorna notificaciones del taller correcto.
        """
        taller_a = crear_taller(db_session)
        taller_b = crear_taller(db_session)
        user_a = crear_usuario(db_session, taller_a.id, "MECANICO")
        user_b = crear_usuario(db_session, taller_b.id, "MECANICO")

        # 3 notificaciones para user_a en taller_a
        for i in range(3):
            db_session.add(Notificacion(
                taller_id=taller_a.id,
                destinatario_user_id=user_a.id,
                tipo=TipoNotificacion.TICKET_ASIGNADO,
                titulo=f"Notif {i}",
                mensaje=f"Mensaje {i}",
                leida=False,
            ))

        # 5 notificaciones para user_b en taller_b
        for i in range(5):
            db_session.add(Notificacion(
                taller_id=taller_b.id,
                destinatario_user_id=user_b.id,
                tipo=TipoNotificacion.TICKET_ASIGNADO,
                titulo=f"Notif {i}",
                mensaje=f"Mensaje {i}",
                leida=False,
            ))
        db_session.flush()

        # Consultar desde el contexto de taller_a
        service_a = NotificacionService(db_session, taller_a.id)
        resultado_a = service_a.obtener_no_leidas(user_a.id)

        assert resultado_a["total"] == 3, (
            f"taller_a debe ver solo 3 notificaciones, ve {resultado_a['total']}"
        )
        for notif in resultado_a["notificaciones"]:
            assert notif.taller_id == taller_a.id, (
                f"Notificación de taller_id={notif.taller_id} no debe aparecer en taller_a"
            )
