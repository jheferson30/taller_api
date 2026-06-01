"""
Property-based tests para NotificacionService.

Valida las propiedades de corrección P6, P7, P8, P9 y P10:

P6  — Notificación generada al asignar mecánico (Req 3.1, 3.4)
P7  — Idempotencia de notificación de asignación (Req 3.3)
P8  — Aislamiento de consulta de notificaciones no leídas (Req 4.1, 4.2)
P9  — Aislamiento de escritura al marcar como leída (Req 5.1, 5.2, 5.4)
P10 — Leer-todas marca exactamente las notificaciones del usuario (Req 5.3)

Feature: notificaciones-internas-sistema
"""

import pytest
from types import SimpleNamespace
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base

# Import all models so SQLAlchemy resolves relationships
from app.modelos.audit_log import AuditLog  # noqa: F401
from app.modelos.configuracion_taller import ConfiguracionTaller  # noqa: F401
from app.modelos.mecanico import Mecanico  # noqa: F401
from app.modelos.notificacion import Notificacion, TipoNotificacion
from app.modelos.password_reset_token import PasswordResetToken  # noqa: F401
from app.modelos.role import Role  # noqa: F401
from app.modelos.taller import Taller
from app.modelos.ticket import Ticket  # noqa: F401
from app.modelos.token_blacklist import TokenBlacklist  # noqa: F401
from app.modelos.user import User
from app.modelos.user_role import UserRole  # noqa: F401
from app.modelos.vehiculo import Vehiculo  # noqa: F401
from app.servicios.notificacion_service import NotificacionService


# ── Helpers ───────────────────────────────────────────────────────────────────

def crear_taller(db, nombre: str) -> Taller:
    import uuid
    nombre_unico = f"{nombre}_{uuid.uuid4().hex[:8]}"
    taller = Taller(nombre=nombre_unico, activo=True)
    db.add(taller)
    db.flush()
    return taller


def crear_usuario(db, taller_id: int, username: str) -> User:
    import uuid
    username_unico = f"{username}_{uuid.uuid4().hex[:8]}"
    user = User(
        taller_id=taller_id,
        username=username_unico,
        email=f"{username_unico}@test.com",
        password_hash="hashed_password",
        is_active=True,
        is_migrated=True,
    )
    db.add(user)
    db.flush()
    return user


def crear_notificacion(
    db,
    taller_id: int,
    user_id: int,
    tipo: TipoNotificacion = TipoNotificacion.TICKET_ASIGNADO,
    leida: bool = False,
    referencia_id: int | None = None,
) -> Notificacion:
    notif = Notificacion(
        taller_id=taller_id,
        destinatario_user_id=user_id,
        tipo=tipo,
        titulo="Título de prueba",
        mensaje="Mensaje de prueba",
        leida=leida,
        referencia_id=referencia_id,
    )
    db.add(notif)
    db.flush()
    return notif


def crear_ticket_mock(ticket_id: int, taller_id: int, ticket_codigo: str = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=ticket_id,
        ticket_codigo=ticket_codigo or f"T-{ticket_id:04d}",
        taller_id=taller_id,
    )


# ── Strategies ────────────────────────────────────────────────────────────────

@st.composite
def nombre_valido(draw):
    return draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=4, max_size=15))


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ── P6 ────────────────────────────────────────────────────────────────────────

class TestP6_NotificacionGeneradaAlAsignarMecanico:
    """
    P6 — Para cualquier ticket con mecanico_user_id válido,
         crear_notificacion_asignacion() crea exactamente una TICKET_ASIGNADO
         con referencia_id == ticket.id para ese mecanico_user_id.

    Feature: notificaciones-internas-sistema, Property 6
    Valida: Requisitos 3.1, 3.4
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        ticket_id=st.integers(min_value=1, max_value=9999),
        nombre_base=nombre_valido(),
    )
    def test_crea_exactamente_una_notificacion_ticket_asignado(
        self, db_session, ticket_id, nombre_base
    ):
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        mecanico_user = crear_usuario(db_session, taller.id, f"mec_{nombre_base}")
        ticket = crear_ticket_mock(ticket_id, taller.id)

        service = NotificacionService(db_session, taller.id)
        notif = service.crear_notificacion_asignacion(ticket, mecanico_user.id)

        assert notif is not None, "P6: debe crear una notificación cuando mecanico_user_id es válido"
        assert notif.tipo == TipoNotificacion.TICKET_ASIGNADO, (
            f"P6: tipo debe ser TICKET_ASIGNADO, got {notif.tipo}"
        )
        assert notif.referencia_id == ticket.id, (
            f"P6: referencia_id={notif.referencia_id} debe ser ticket.id={ticket.id}"
        )
        assert notif.destinatario_user_id == mecanico_user.id, (
            f"P6: destinatario_user_id={notif.destinatario_user_id} debe ser {mecanico_user.id}"
        )

        # Verificar que existe exactamente una en la BD
        total = (
            db_session.query(Notificacion)
            .filter(
                Notificacion.taller_id == taller.id,
                Notificacion.tipo == TipoNotificacion.TICKET_ASIGNADO,
                Notificacion.referencia_id == ticket.id,
                Notificacion.destinatario_user_id == mecanico_user.id,
            )
            .count()
        )
        assert total == 1, f"P6: debe existir exactamente 1 notificación TICKET_ASIGNADO, hay {total}"

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_retorna_none_cuando_mecanico_user_id_es_none(self, db_session, nombre_base):
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        ticket = crear_ticket_mock(1, taller.id)

        service = NotificacionService(db_session, taller.id)
        resultado = service.crear_notificacion_asignacion(ticket, None)

        assert resultado is None, "P6: debe retornar None cuando mecanico_user_id es None"

        total = db_session.query(Notificacion).filter(
            Notificacion.taller_id == taller.id
        ).count()
        assert total == 0, "P6: no debe crear notificación cuando mecanico_user_id es None"


# ── P7 ────────────────────────────────────────────────────────────────────────

class TestP7_IdempotenciaNotificacionAsignacion:
    """
    P7 — El servicio crea una notificación por llamada. La idempotencia
         es responsabilidad del llamador (TicketService): solo debe llamar
         a crear_notificacion_asignacion cuando mecanico_asignado_id cambia.

    Feature: notificaciones-internas-sistema, Property 7
    Valida: Requisitos 3.3
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        ticket_id=st.integers(min_value=1, max_value=9999),
        nombre_base=nombre_valido(),
    )
    def test_una_llamada_crea_exactamente_una_notificacion(
        self, db_session, ticket_id, nombre_base
    ):
        """P7: una sola llamada crea exactamente 1 notificación."""
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        mecanico_user = crear_usuario(db_session, taller.id, f"mec_{nombre_base}")
        ticket = crear_ticket_mock(ticket_id, taller.id)

        service = NotificacionService(db_session, taller.id)
        service.crear_notificacion_asignacion(ticket, mecanico_user.id)

        total = db_session.query(Notificacion).filter(
            Notificacion.taller_id == taller.id,
            Notificacion.tipo == TipoNotificacion.TICKET_ASIGNADO,
            Notificacion.referencia_id == ticket.id,
        ).count()
        assert total == 1, f"P7: una llamada debe crear exactamente 1 notificación, hay {total}"

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        ticket_id=st.integers(min_value=1, max_value=9999),
        nombre_base=nombre_valido(),
    )
    def test_el_llamador_debe_controlar_idempotencia(
        self, db_session, ticket_id, nombre_base
    ):
        """
        P7: el servicio NO deduplica por sí solo — si el llamador invoca
        crear_notificacion_asignacion dos veces con el mismo ticket+mecanico,
        se crean 2 notificaciones. La idempotencia debe ser controlada por
        TicketService (tarea 5.1) verificando si mecanico_asignado_id cambió.
        """
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        mecanico_user = crear_usuario(db_session, taller.id, f"mec_{nombre_base}")
        ticket = crear_ticket_mock(ticket_id, taller.id)

        service = NotificacionService(db_session, taller.id)
        service.crear_notificacion_asignacion(ticket, mecanico_user.id)
        service.crear_notificacion_asignacion(ticket, mecanico_user.id)

        total = db_session.query(Notificacion).filter(
            Notificacion.taller_id == taller.id,
            Notificacion.tipo == TipoNotificacion.TICKET_ASIGNADO,
            Notificacion.referencia_id == ticket.id,
        ).count()
        # El servicio crea una por llamada — el llamador es responsable de no llamar dos veces
        assert total == 2, (
            f"P7: el servicio crea 1 notificación por llamada (total esperado=2, got={total}). "
            "La idempotencia debe ser controlada por TicketService."
        )


# ── P8 ────────────────────────────────────────────────────────────────────────

class TestP8_AislamientoConsultaNoLeidas:
    """
    P8 — obtener_no_leidas() retorna solo notificaciones del user_id y taller_id
         del servicio con leida=False. total == len(notificaciones).

    Feature: notificaciones-internas-sistema, Property 8
    Valida: Requisitos 4.1, 4.2
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        n_propias=st.integers(min_value=1, max_value=5),
        n_ajenas=st.integers(min_value=1, max_value=5),
        nombre_base=nombre_valido(),
    )
    def test_retorna_solo_notificaciones_del_usuario_y_taller(
        self, db_session, n_propias, n_ajenas, nombre_base
    ):
        taller_a = crear_taller(db_session, f"taller_a_{nombre_base}")
        taller_b = crear_taller(db_session, f"taller_b_{nombre_base}")
        user_a = crear_usuario(db_session, taller_a.id, f"user_a_{nombre_base}")
        user_b = crear_usuario(db_session, taller_b.id, f"user_b_{nombre_base}")

        for _ in range(n_propias):
            crear_notificacion(db_session, taller_a.id, user_a.id)
        for _ in range(n_ajenas):
            crear_notificacion(db_session, taller_b.id, user_b.id)

        service = NotificacionService(db_session, taller_a.id)
        resultado = service.obtener_no_leidas(user_a.id)

        assert resultado["total"] == n_propias, (
            f"P8: total={resultado['total']} debe ser {n_propias}"
        )
        assert len(resultado["notificaciones"]) == n_propias, (
            f"P8: len(notificaciones)={len(resultado['notificaciones'])} debe ser {n_propias}"
        )
        assert resultado["total"] == len(resultado["notificaciones"]), (
            "P8: total debe ser igual a len(notificaciones)"
        )
        for notif in resultado["notificaciones"]:
            assert notif.destinatario_user_id == user_a.id
            assert notif.taller_id == taller_a.id
            assert notif.leida is False

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        n_leidas=st.integers(min_value=1, max_value=5),
        n_no_leidas=st.integers(min_value=1, max_value=5),
        nombre_base=nombre_valido(),
    )
    def test_excluye_notificaciones_leidas(
        self, db_session, n_leidas, n_no_leidas, nombre_base
    ):
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")

        for _ in range(n_leidas):
            crear_notificacion(db_session, taller.id, user.id, leida=True)
        for _ in range(n_no_leidas):
            crear_notificacion(db_session, taller.id, user.id, leida=False)

        service = NotificacionService(db_session, taller.id)
        resultado = service.obtener_no_leidas(user.id)

        assert resultado["total"] == n_no_leidas
        assert resultado["total"] == len(resultado["notificaciones"])
        for notif in resultado["notificaciones"]:
            assert notif.leida is False


# ── P9 ────────────────────────────────────────────────────────────────────────

class TestP9_AislamientoEscrituraMarcarLeida:
    """
    P9 — marcar_como_leida() solo marca notificaciones del user_id y taller_id
         del servicio. Intentar marcar una notificación de otro usuario/taller
         retorna HTTP 404 sin modificar el estado.

    Feature: notificaciones-internas-sistema, Property 9
    Valida: Requisitos 5.1, 5.2, 5.4
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_no_puede_marcar_notificacion_de_otro_usuario_mismo_taller(
        self, db_session, nombre_base
    ):
        """P9: un usuario no puede marcar como leída una notificación de otro usuario del mismo taller."""
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user_a = crear_usuario(db_session, taller.id, f"user_a_{nombre_base}")
        user_b = crear_usuario(db_session, taller.id, f"user_b_{nombre_base}")

        # Crear notificación para user_b
        notif = crear_notificacion(db_session, taller.id, user_b.id)

        service = NotificacionService(db_session, taller.id)

        # user_a intenta marcar la notificación de user_b
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            service.marcar_como_leida(notif.id, user_a.id)

        assert exc_info.value.status_code == 404, (
            f"P9: debe retornar HTTP 404, got {exc_info.value.status_code}"
        )

        # Verificar que la notificación NO fue modificada
        db_session.refresh(notif)
        assert notif.leida is False, "P9: la notificación no debe ser modificada"

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_no_puede_marcar_notificacion_de_otro_taller(
        self, db_session, nombre_base
    ):
        """P9: un usuario no puede marcar como leída una notificación de otro taller."""
        taller_a = crear_taller(db_session, f"taller_a_{nombre_base}")
        taller_b = crear_taller(db_session, f"taller_b_{nombre_base}")
        user_a = crear_usuario(db_session, taller_a.id, f"user_a_{nombre_base}")
        user_b = crear_usuario(db_session, taller_b.id, f"user_b_{nombre_base}")

        # Crear notificación para user_b en taller_b
        notif = crear_notificacion(db_session, taller_b.id, user_b.id)

        # Servicio del taller_a intenta marcar notificación del taller_b
        service = NotificacionService(db_session, taller_a.id)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            service.marcar_como_leida(notif.id, user_a.id)

        assert exc_info.value.status_code == 404, (
            f"P9: debe retornar HTTP 404, got {exc_info.value.status_code}"
        )

        # Verificar que la notificación NO fue modificada
        db_session.refresh(notif)
        assert notif.leida is False, "P9: la notificación no debe ser modificada"

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_puede_marcar_su_propia_notificacion(
        self, db_session, nombre_base
    ):
        """P9: un usuario SÍ puede marcar como leída su propia notificación."""
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")

        notif = crear_notificacion(db_session, taller.id, user.id)

        service = NotificacionService(db_session, taller.id)
        resultado = service.marcar_como_leida(notif.id, user.id)

        assert resultado.id == notif.id
        assert resultado.leida is True, "P9: la notificación debe ser marcada como leída"


# ── P10 ───────────────────────────────────────────────────────────────────────

class TestP10_LeerTodasMarcaExactamenteLasDelUsuario:
    """
    P10 — Tras marcar_todas_como_leidas(user_id), el usuario tiene 0 no leídas.
          Las notificaciones de otros usuarios del mismo taller no se ven afectadas.

    Feature: notificaciones-internas-sistema, Property 10
    Valida: Requisitos 5.3
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        n_user=st.integers(min_value=1, max_value=5),
        n_otro=st.integers(min_value=1, max_value=5),
        nombre_base=nombre_valido(),
    )
    def test_marcar_todas_no_afecta_otros_usuarios(
        self, db_session, n_user, n_otro, nombre_base
    ):
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")
        otro_user = crear_usuario(db_session, taller.id, f"otro_{nombre_base}")

        for _ in range(n_user):
            crear_notificacion(db_session, taller.id, user.id)
        for _ in range(n_otro):
            crear_notificacion(db_session, taller.id, otro_user.id)

        service = NotificacionService(db_session, taller.id)
        marcadas = service.marcar_todas_como_leidas(user.id)

        assert marcadas == n_user, f"P10: marcadas={marcadas} debe ser {n_user}"

        # El usuario tiene 0 no leídas
        resultado = service.obtener_no_leidas(user.id)
        assert resultado["total"] == 0, "P10: el usuario debe tener 0 no leídas tras marcar todas"

        # El otro usuario no fue afectado
        resultado_otro = service.obtener_no_leidas(otro_user.id)
        assert resultado_otro["total"] == n_otro, (
            f"P10: el otro usuario debe seguir teniendo {n_otro} no leídas, "
            f"tiene {resultado_otro['total']}"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_marcar_todas_con_cero_no_leidas_retorna_cero(
        self, db_session, nombre_base
    ):
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")

        service = NotificacionService(db_session, taller.id)
        marcadas = service.marcar_todas_como_leidas(user.id)

        assert marcadas == 0, "P10: sin notificaciones, marcar_todas debe retornar 0"
