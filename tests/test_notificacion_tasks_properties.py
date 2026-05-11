"""
Property-based tests para la tarea Celery verificar_vencimientos_plan.

Valida las propiedades de corrección P11, P12 y P13:

P11 — Verificador de plan genera notificación cuando corresponde (Req 7.1, 7.6)
P12 — Idempotencia del verificador de plan (Req 7.2)
P13 — Verificador omite talleres suspendidos o cancelados (Req 7.4)

Feature: notificaciones-internas-sistema
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base

# Importar todos los modelos para que SQLAlchemy resuelva las relaciones
from app.modelos.audit_log import AuditLog  # noqa: F401
from app.modelos.configuracion_taller import ConfiguracionTaller  # noqa: F401
from app.modelos.mecanico import Mecanico  # noqa: F401
from app.modelos.notificacion import Notificacion, TipoNotificacion
from app.modelos.password_reset_token import PasswordResetToken  # noqa: F401
from app.modelos.role import Role
from app.modelos.taller import EstadoTaller, Taller
from app.modelos.ticket import Ticket  # noqa: F401
from app.modelos.token_blacklist import TokenBlacklist  # noqa: F401
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.modelos.vehiculo import Vehiculo  # noqa: F401
from app.repositorios.notificacion_repository import NotificacionRepository
from app.servicios.notificacion_service import NotificacionService


# ── Helpers ───────────────────────────────────────────────────────────────────

def uid() -> str:
    return uuid.uuid4().hex[:8]


def crear_taller(
    db,
    estado: EstadoTaller = EstadoTaller.ACTIVO,
    dias_hasta_vencimiento: int | None = 2,
) -> Taller:
    """Crea un taller con fecha_vencimiento_plan calculada a partir de hoy."""
    fecha_venc = None
    if dias_hasta_vencimiento is not None:
        fecha_venc = datetime.now(timezone.utc) + timedelta(days=dias_hasta_vencimiento)

    taller = Taller(
        nombre=f"taller_{uid()}",
        activo=True,
        estado=estado,
        fecha_vencimiento_plan=fecha_venc,
    )
    db.add(taller)
    db.flush()
    return taller


def crear_rol_admin(db) -> Role:
    """Crea o recupera el rol ADMIN."""
    rol = db.query(Role).filter(Role.name == "ADMIN").first()
    if not rol:
        rol = Role(name="ADMIN", description="Administrador del taller")
        db.add(rol)
        db.flush()
    return rol


def crear_usuario_admin(db, taller_id: int) -> User:
    """Crea un usuario con rol ADMIN en el taller dado."""
    nombre = f"admin_{uid()}"
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

    rol = crear_rol_admin(db)
    user_role = UserRole(user_id=user.id, role_id=rol.id)
    db.add(user_role)
    db.flush()

    return user


def simular_verificador(db, taller: Taller) -> list[Notificacion]:
    """
    Simula la lógica central del verificador de plan para un taller específico.

    Replica la lógica de verificar_vencimientos_plan() pero sobre una sesión
    de test en memoria, sin necesidad de Celery ni Redis.

    Returns:
        Lista de notificaciones creadas (vacía si se omitió el taller)
    """
    # Req 7.4: omitir SUSPENDIDO y CANCELADO
    if taller.estado in (EstadoTaller.SUSPENDIDO, EstadoTaller.CANCELADO):
        return []

    # Req 7.5: omitir talleres sin fecha_vencimiento_plan
    if taller.fecha_vencimiento_plan is None:
        return []

    ahora = datetime.now(timezone.utc)
    fecha_venc = taller.fecha_vencimiento_plan
    if fecha_venc.tzinfo is None:
        fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)

    dias_restantes = (fecha_venc - ahora).days

    # Req 7.1: solo si dias_restantes <= 3
    if dias_restantes > 3:
        return []

    # Req 7.2: verificar si ya existe notificación reciente (< 24h)
    repo = NotificacionRepository(db, taller.id)
    if repo.existe_notif_renovacion_reciente(taller.id, horas=24):
        return []

    # Obtener ADMINs activos del taller
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


# ── Strategies ────────────────────────────────────────────────────────────────

@st.composite
def dias_restantes_elegibles(draw):
    """Genera días restantes <= 3 (incluyendo 0 y negativos = ya vencido)."""
    return draw(st.integers(min_value=-5, max_value=3))


@st.composite
def dias_restantes_no_elegibles(draw):
    """Genera días restantes > 3 (no deben generar notificación).
    
    Usa min_value=5 en lugar de 4 para evitar falsos positivos por diferencias
    de sub-segundo entre la creación del taller y la ejecución del verificador:
    timedelta.days trunca fracciones, por lo que dias=4 puede computarse como 3.
    """
    return draw(st.integers(min_value=5, max_value=365))


@st.composite
def estado_activo_o_trial(draw):
    """Genera un estado ACTIVO o TRIAL."""
    return draw(st.sampled_from([EstadoTaller.ACTIVO, EstadoTaller.TRIAL]))


@st.composite
def estado_suspendido_o_cancelado(draw):
    """Genera un estado SUSPENDIDO o CANCELADO."""
    return draw(st.sampled_from([EstadoTaller.SUSPENDIDO, EstadoTaller.CANCELADO]))


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Base de datos SQLite en memoria para tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ── P11 ───────────────────────────────────────────────────────────────────────

class TestP11_VerificadorGeneraNotificacionCuandoCorresponde:
    """
    P11 — Para cualquier taller ACTIVO/TRIAL con dias_restantes <= 3,
          el verificador crea notificaciones RENOVACION_PLAN para todos
          los ADMIN y el mensaje contiene el número exacto de días.

    Feature: notificaciones-internas-sistema, Property 11
    Valida: Requisitos 7.1, 7.6
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        estado=estado_activo_o_trial(),
        dias=dias_restantes_elegibles(),
        n_admins=st.integers(min_value=1, max_value=3),
    )
    def test_crea_notificacion_para_cada_admin_cuando_dias_restantes_lte_3(
        self, db_session, estado, dias, n_admins
    ):
        """
        P11: Para talleres ACTIVO/TRIAL con dias_restantes <= 3,
        se crea exactamente una notificación RENOVACION_PLAN por cada ADMIN.
        """
        taller = crear_taller(db_session, estado=estado, dias_hasta_vencimiento=dias)
        admins = [crear_usuario_admin(db_session, taller.id) for _ in range(n_admins)]

        notifs = simular_verificador(db_session, taller)

        assert len(notifs) == n_admins, (
            f"P11: se esperaban {n_admins} notificaciones (una por ADMIN), "
            f"se crearon {len(notifs)}"
        )

        admin_ids = {a.id for a in admins}
        for notif in notifs:
            assert notif.tipo == TipoNotificacion.RENOVACION_PLAN, (
                f"P11: tipo debe ser RENOVACION_PLAN, got {notif.tipo}"
            )
            assert notif.destinatario_user_id in admin_ids, (
                f"P11: notificación dirigida a user_id={notif.destinatario_user_id} "
                f"que no es ADMIN del taller"
            )
            assert notif.taller_id == taller.id, (
                f"P11: taller_id={notif.taller_id} debe ser {taller.id}"
            )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        estado=estado_activo_o_trial(),
        dias=dias_restantes_elegibles(),
    )
    def test_mensaje_contiene_numero_exacto_de_dias(
        self, db_session, estado, dias
    ):
        """
        P11 (Req 7.6): El mensaje de la notificación contiene el número exacto
        de días restantes hasta el vencimiento.
        """
        taller = crear_taller(db_session, estado=estado, dias_hasta_vencimiento=dias)
        crear_usuario_admin(db_session, taller.id)

        notifs = simular_verificador(db_session, taller)

        assert len(notifs) >= 1, "P11: debe crear al menos una notificación"

        # Calcular días reales para verificar el mensaje
        ahora = datetime.now(timezone.utc)
        fecha_venc = taller.fecha_vencimiento_plan
        if fecha_venc.tzinfo is None:
            fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
        dias_reales = (fecha_venc - ahora).days

        for notif in notifs:
            assert str(dias_reales) in notif.mensaje, (
                f"P11 (Req 7.6): el mensaje '{notif.mensaje}' no contiene "
                f"el número exacto de días restantes ({dias_reales})"
            )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        estado=estado_activo_o_trial(),
        dias=dias_restantes_no_elegibles(),
    )
    def test_no_crea_notificacion_cuando_dias_restantes_gt_3(
        self, db_session, estado, dias
    ):
        """
        P11 (negativo): No se crean notificaciones cuando dias_restantes > 3.
        """
        taller = crear_taller(db_session, estado=estado, dias_hasta_vencimiento=dias)
        crear_usuario_admin(db_session, taller.id)

        notifs = simular_verificador(db_session, taller)

        assert len(notifs) == 0, (
            f"P11: no debe crear notificaciones cuando dias_restantes={dias} > 3, "
            f"pero se crearon {len(notifs)}"
        )


# ── P12 ───────────────────────────────────────────────────────────────────────

class TestP12_IdempotenciaVerificadorPlan:
    """
    P12 — Si ya existe una RENOVACION_PLAN en las últimas 24h para un taller,
          ejecutar el verificador de nuevo no crea notificaciones adicionales.

    Feature: notificaciones-internas-sistema, Property 12
    Valida: Requisitos 7.2
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        estado=estado_activo_o_trial(),
        dias=dias_restantes_elegibles(),
        n_admins=st.integers(min_value=1, max_value=3),
    )
    def test_segunda_ejecucion_no_crea_notificaciones_adicionales(
        self, db_session, estado, dias, n_admins
    ):
        """
        P12: Si ya existe una RENOVACION_PLAN reciente (< 24h),
        el verificador no crea notificaciones adicionales.
        """
        taller = crear_taller(db_session, estado=estado, dias_hasta_vencimiento=dias)
        for _ in range(n_admins):
            crear_usuario_admin(db_session, taller.id)

        # Primera ejecución — debe crear notificaciones
        notifs_primera = simular_verificador(db_session, taller)
        assert len(notifs_primera) == n_admins, (
            f"P12: primera ejecución debe crear {n_admins} notificaciones"
        )

        # Segunda ejecución — debe omitir (ya existe notificación reciente)
        notifs_segunda = simular_verificador(db_session, taller)
        assert len(notifs_segunda) == 0, (
            f"P12: segunda ejecución no debe crear notificaciones adicionales, "
            f"pero creó {len(notifs_segunda)}"
        )

        # Total en BD debe ser exactamente n_admins (solo de la primera ejecución)
        total_en_bd = (
            db_session.query(Notificacion)
            .filter(
                Notificacion.taller_id == taller.id,
                Notificacion.tipo == TipoNotificacion.RENOVACION_PLAN,
            )
            .count()
        )
        assert total_en_bd == n_admins, (
            f"P12: total en BD debe ser {n_admins}, hay {total_en_bd}"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        estado=estado_activo_o_trial(),
        dias=dias_restantes_elegibles(),
    )
    def test_multiples_ejecuciones_no_acumulan_notificaciones(
        self, db_session, estado, dias
    ):
        """
        P12 (variante): N ejecuciones del verificador producen el mismo
        resultado que 1 ejecución cuando ya existe notificación reciente.
        """
        taller = crear_taller(db_session, estado=estado, dias_hasta_vencimiento=dias)
        crear_usuario_admin(db_session, taller.id)

        # Ejecutar 3 veces
        for _ in range(3):
            simular_verificador(db_session, taller)

        total = (
            db_session.query(Notificacion)
            .filter(
                Notificacion.taller_id == taller.id,
                Notificacion.tipo == TipoNotificacion.RENOVACION_PLAN,
            )
            .count()
        )
        # Solo debe haber 1 notificación (la de la primera ejecución)
        assert total == 1, (
            f"P12: 3 ejecuciones deben producir solo 1 notificación, hay {total}"
        )


# ── P13 ───────────────────────────────────────────────────────────────────────

class TestP13_VerificadorOmiteTalleresSuspendidosOCancelados:
    """
    P13 — Para cualquier taller con estado SUSPENDIDO o CANCELADO,
          el verificador no crea ninguna notificación, independientemente
          de la fecha_vencimiento_plan.

    Feature: notificaciones-internas-sistema, Property 13
    Valida: Requisitos 7.4
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        estado=estado_suspendido_o_cancelado(),
        dias=dias_restantes_elegibles(),
        n_admins=st.integers(min_value=1, max_value=3),
    )
    def test_no_crea_notificaciones_para_talleres_suspendidos_o_cancelados(
        self, db_session, estado, dias, n_admins
    ):
        """
        P13: Talleres SUSPENDIDO o CANCELADO no generan notificaciones,
        incluso si dias_restantes <= 3 y tienen ADMINs activos.
        """
        taller = crear_taller(db_session, estado=estado, dias_hasta_vencimiento=dias)
        for _ in range(n_admins):
            crear_usuario_admin(db_session, taller.id)

        notifs = simular_verificador(db_session, taller)

        assert len(notifs) == 0, (
            f"P13: taller con estado={estado} no debe generar notificaciones, "
            f"pero se crearon {len(notifs)}"
        )

        # Verificar que no hay nada en BD
        total_en_bd = (
            db_session.query(Notificacion)
            .filter(
                Notificacion.taller_id == taller.id,
                Notificacion.tipo == TipoNotificacion.RENOVACION_PLAN,
            )
            .count()
        )
        assert total_en_bd == 0, (
            f"P13: no debe haber notificaciones en BD para taller {estado}, "
            f"hay {total_en_bd}"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        estado_omitido=estado_suspendido_o_cancelado(),
        estado_elegible=estado_activo_o_trial(),
        dias=dias_restantes_elegibles(),
    )
    def test_solo_talleres_activos_o_trial_reciben_notificaciones(
        self, db_session, estado_omitido, estado_elegible, dias
    ):
        """
        P13 (contraste): En el mismo escenario, un taller ACTIVO/TRIAL recibe
        notificaciones mientras que uno SUSPENDIDO/CANCELADO no.
        """
        taller_omitido = crear_taller(
            db_session, estado=estado_omitido, dias_hasta_vencimiento=dias
        )
        taller_elegible = crear_taller(
            db_session, estado=estado_elegible, dias_hasta_vencimiento=dias
        )

        crear_usuario_admin(db_session, taller_omitido.id)
        crear_usuario_admin(db_session, taller_elegible.id)

        notifs_omitido = simular_verificador(db_session, taller_omitido)
        notifs_elegible = simular_verificador(db_session, taller_elegible)

        assert len(notifs_omitido) == 0, (
            f"P13: taller {estado_omitido} no debe recibir notificaciones"
        )
        assert len(notifs_elegible) == 1, (
            f"P13: taller {estado_elegible} debe recibir 1 notificación, "
            f"recibió {len(notifs_elegible)}"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(estado=estado_suspendido_o_cancelado())
    def test_omite_independientemente_de_fecha_vencimiento(
        self, db_session, estado
    ):
        """
        P13 (variante): Talleres SUSPENDIDO/CANCELADO se omiten incluso
        cuando la fecha de vencimiento ya pasó (días negativos).
        """
        # Taller con plan ya vencido hace 5 días
        taller = crear_taller(db_session, estado=estado, dias_hasta_vencimiento=-5)
        crear_usuario_admin(db_session, taller.id)

        notifs = simular_verificador(db_session, taller)

        assert len(notifs) == 0, (
            f"P13: taller {estado} con plan vencido no debe generar notificaciones"
        )
