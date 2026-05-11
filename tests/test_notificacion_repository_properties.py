"""
Property-based tests para NotificacionRepository.

Valida las propiedades de corrección 1, 2 y 3 del diseño:

P1 — Aislamiento multi-tenant del repositorio:
     get_no_leidas() retorna SOLO notificaciones del taller del repositorio.

P2 — Invariante de tenant en notificación creada:
     taller_id de la notificación siempre coincide con el taller del destinatario.

P3 — Estado inicial de notificación:
     Toda notificación recién creada tiene leida = False.

Feature: notificaciones-internas-sistema
"""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base

# Importar todos los modelos para que SQLAlchemy resuelva las relaciones
# antes de crear las tablas en la BD de prueba
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
from app.repositorios.notificacion_repository import NotificacionRepository


# ── Helpers ───────────────────────────────────────────────────────────────────

def crear_taller(db, nombre: str) -> Taller:
    """Crea un taller en la BD."""
    import uuid
    # Agregar UUID para garantizar unicidad del nombre
    nombre_unico = f"{nombre}_{uuid.uuid4().hex[:8]}"
    taller = Taller(nombre=nombre_unico, activo=True)
    db.add(taller)
    db.flush()
    return taller


def crear_usuario(db, taller_id: int, username: str) -> User:
    """Crea un usuario asociado a un taller."""
    import uuid
    # Agregar UUID para garantizar unicidad del username y email
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
    """Crea una notificación directamente en la BD."""
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


# ── Estrategias Hypothesis ────────────────────────────────────────────────────

@st.composite
def nombre_valido(draw):
    """Genera nombres válidos para talleres y usuarios."""
    return draw(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz",
            min_size=4,
            max_size=15,
        )
    )


@st.composite
def tipo_notificacion_strategy(draw):
    """Genera un tipo de notificación aleatorio."""
    return draw(st.sampled_from(list(TipoNotificacion)))


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Base de datos SQLite en memoria para tests."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ── P1: Aislamiento multi-tenant del repositorio ──────────────────────────────

class TestP1_AislamientoMultiTenant:
    """
    P1 — Para cualquier conjunto de notificaciones de talleres distintos,
         get_no_leidas() retorna SOLO notificaciones del taller del repositorio.

    Feature: notificaciones-internas-sistema, Property 1: aislamiento multi-tenant del repositorio
    Valida: Requisitos 1.4, 9.2
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        n_propias=st.integers(min_value=1, max_value=5),
        n_ajenas=st.integers(min_value=1, max_value=5),
        nombre_base=nombre_valido(),
    )
    def test_get_no_leidas_nunca_retorna_notificaciones_de_otro_taller(
        self, db_session, n_propias, n_ajenas, nombre_base
    ):
        """
        P1: get_no_leidas() con taller_id=T nunca retorna notificaciones
        cuyo taller_id sea distinto de T.
        """
        # Crear dos talleres distintos
        taller_a = crear_taller(db_session, f"taller_a_{nombre_base}")
        taller_b = crear_taller(db_session, f"taller_b_{nombre_base}")

        # Crear usuarios en cada taller
        user_a = crear_usuario(db_session, taller_a.id, f"user_a_{nombre_base}")
        user_b = crear_usuario(db_session, taller_b.id, f"user_b_{nombre_base}")

        # Crear notificaciones no leídas en taller A
        for i in range(n_propias):
            crear_notificacion(db_session, taller_a.id, user_a.id)

        # Crear notificaciones no leídas en taller B
        for i in range(n_ajenas):
            crear_notificacion(db_session, taller_b.id, user_b.id)

        # Consultar desde el repositorio del taller A
        repo_a = NotificacionRepository(db_session, taller_a.id)
        resultados = repo_a.get_no_leidas(user_a.id)

        # P1: ningún resultado debe pertenecer al taller B
        for notif in resultados:
            assert notif.taller_id == taller_a.id, (
                f"P1 violada: get_no_leidas() retornó notificación con "
                f"taller_id={notif.taller_id} cuando el repositorio tiene "
                f"taller_id={taller_a.id}"
            )

        # Debe retornar exactamente las notificaciones del taller A
        assert len(resultados) == n_propias, (
            f"P1: se esperaban {n_propias} notificaciones del taller A, "
            f"se obtuvieron {len(resultados)}"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        n_usuarios=st.integers(min_value=2, max_value=4),
        nombre_base=nombre_valido(),
    )
    def test_get_no_leidas_filtra_por_usuario_dentro_del_mismo_taller(
        self, db_session, n_usuarios, nombre_base
    ):
        """
        P1 (variante): get_no_leidas() filtra por user_id dentro del mismo taller.
        Un usuario no puede ver notificaciones de otro usuario del mismo taller.
        """
        taller = crear_taller(db_session, f"taller_{nombre_base}")

        # Crear múltiples usuarios en el mismo taller
        usuarios = [
            crear_usuario(db_session, taller.id, f"user_{i}_{nombre_base}")
            for i in range(n_usuarios)
        ]

        # Crear una notificación para cada usuario
        for user in usuarios:
            crear_notificacion(db_session, taller.id, user.id)

        repo = NotificacionRepository(db_session, taller.id)

        # Cada usuario solo debe ver su propia notificación
        for user in usuarios:
            resultados = repo.get_no_leidas(user.id)
            assert len(resultados) == 1, (
                f"P1: usuario {user.id} debería ver 1 notificación, "
                f"pero ve {len(resultados)}"
            )
            assert resultados[0].destinatario_user_id == user.id, (
                f"P1: la notificación retornada pertenece al usuario "
                f"{resultados[0].destinatario_user_id}, no al usuario {user.id}"
            )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_get_no_leidas_excluye_notificaciones_leidas(
        self, db_session, nombre_base
    ):
        """
        P1 (variante): get_no_leidas() solo retorna notificaciones con leida=False.
        """
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")

        # Crear una notificación leída y una no leída
        crear_notificacion(db_session, taller.id, user.id, leida=True)
        crear_notificacion(db_session, taller.id, user.id, leida=False)

        repo = NotificacionRepository(db_session, taller.id)
        resultados = repo.get_no_leidas(user.id)

        assert len(resultados) == 1, (
            f"P1: get_no_leidas() debería retornar 1 notificación no leída, "
            f"pero retornó {len(resultados)}"
        )
        assert resultados[0].leida is False, (
            "P1: get_no_leidas() retornó una notificación con leida=True"
        )


# ── P2: Invariante de tenant en notificación creada ───────────────────────────

class TestP2_InvarianteTenantNotificacion:
    """
    P2 — Para cualquier notificación creada, el taller_id de la notificación
         siempre coincide con el taller_id del usuario destinatario.

    Feature: notificaciones-internas-sistema, Property 2: invariante de tenant en notificación creada
    Valida: Requisitos 1.2
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        tipo=tipo_notificacion_strategy(),
        nombre_base=nombre_valido(),
    )
    def test_notificacion_creada_tiene_taller_id_del_destinatario(
        self, db_session, tipo, nombre_base
    ):
        """
        P2: Al crear una notificación con el repositorio, el taller_id
        de la notificación coincide con el taller_id del repositorio
        (que es el mismo que el del destinatario).
        """
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")

        repo = NotificacionRepository(db_session, taller.id)

        notif = Notificacion(
            destinatario_user_id=user.id,
            tipo=tipo,
            titulo="Test",
            mensaje="Mensaje de prueba",
        )
        notif_creada = repo.create(notif)

        # P2: el taller_id de la notificación debe coincidir con el del repositorio
        assert notif_creada.taller_id == taller.id, (
            f"P2 violada: notificación creada tiene taller_id={notif_creada.taller_id}, "
            f"pero el destinatario pertenece a taller_id={taller.id}"
        )

        # Verificar que el destinatario pertenece al mismo taller
        assert user.taller_id == notif_creada.taller_id, (
            f"P2 violada: taller_id de la notificación ({notif_creada.taller_id}) "
            f"no coincide con el taller_id del destinatario ({user.taller_id})"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_create_sobreescribe_taller_id_inyectado(
        self, db_session, nombre_base
    ):
        """
        P2 (seguridad): Si se intenta crear una notificación con un taller_id
        diferente al del repositorio, el repositorio lo sobreescribe con el
        taller_id del contexto.
        """
        taller_real = crear_taller(db_session, f"taller_real_{nombre_base}")
        taller_falso = crear_taller(db_session, f"taller_falso_{nombre_base}")
        user = crear_usuario(db_session, taller_real.id, f"user_{nombre_base}")

        repo = NotificacionRepository(db_session, taller_real.id)

        # Intentar inyectar un taller_id diferente
        notif = Notificacion(
            taller_id=taller_falso.id,  # intento de inyección cross-tenant
            destinatario_user_id=user.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Test",
            mensaje="Mensaje",
        )
        notif_creada = repo.create(notif)

        # El repositorio debe sobreescribir con su propio taller_id
        assert notif_creada.taller_id == taller_real.id, (
            f"P2 violada: create() permitió taller_id={notif_creada.taller_id} "
            f"en lugar del contexto taller_id={taller_real.id}"
        )
        assert notif_creada.taller_id != taller_falso.id, (
            "P2: create() no debe permitir inyectar un taller_id ajeno"
        )


# ── P3: Estado inicial de notificación ───────────────────────────────────────

class TestP3_EstadoInicialNotificacion:
    """
    P3 — Para cualquier notificación recién creada, el campo leida debe ser False.

    Feature: notificaciones-internas-sistema, Property 3: estado inicial de notificación
    Valida: Requisitos 1.3
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        tipo=tipo_notificacion_strategy(),
        nombre_base=nombre_valido(),
    )
    def test_notificacion_recien_creada_tiene_leida_false(
        self, db_session, tipo, nombre_base
    ):
        """
        P3: Toda notificación recién creada tiene leida=False,
        independientemente del tipo, usuario o taller.
        """
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")

        repo = NotificacionRepository(db_session, taller.id)

        notif = Notificacion(
            destinatario_user_id=user.id,
            tipo=tipo,
            titulo="Notificación nueva",
            mensaje="Mensaje de prueba",
        )
        notif_creada = repo.create(notif)

        assert notif_creada.leida is False, (
            f"P3 violada: notificación de tipo {tipo} creada con leida={notif_creada.leida}, "
            "debería ser False"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        n_notificaciones=st.integers(min_value=1, max_value=10),
        nombre_base=nombre_valido(),
    )
    def test_multiples_notificaciones_creadas_todas_no_leidas(
        self, db_session, n_notificaciones, nombre_base
    ):
        """
        P3 (variante): Múltiples notificaciones creadas en secuencia
        deben tener todas leida=False.
        """
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")

        repo = NotificacionRepository(db_session, taller.id)

        notificaciones_creadas = []
        for i in range(n_notificaciones):
            notif = Notificacion(
                destinatario_user_id=user.id,
                tipo=TipoNotificacion.TICKET_ASIGNADO,
                titulo=f"Notificación {i}",
                mensaje=f"Mensaje {i}",
            )
            notificaciones_creadas.append(repo.create(notif))

        # Todas deben tener leida=False
        for notif in notificaciones_creadas:
            assert notif.leida is False, (
                f"P3 violada: notificación {notif.id} tiene leida={notif.leida}, "
                "debería ser False"
            )

        # Verificar que get_no_leidas retorna todas
        no_leidas = repo.get_no_leidas(user.id)
        assert len(no_leidas) == n_notificaciones, (
            f"P3: se crearon {n_notificaciones} notificaciones, "
            f"pero get_no_leidas retorna {len(no_leidas)}"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_marcar_leida_cambia_estado_correctamente(
        self, db_session, nombre_base
    ):
        """
        P3 (transición): Después de marcar como leída, leida=True.
        Antes de marcar, leida=False (estado inicial).
        """
        taller = crear_taller(db_session, f"taller_{nombre_base}")
        user = crear_usuario(db_session, taller.id, f"user_{nombre_base}")

        repo = NotificacionRepository(db_session, taller.id)

        notif = Notificacion(
            destinatario_user_id=user.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Test",
            mensaje="Mensaje",
        )
        notif_creada = repo.create(notif)

        # Estado inicial: leida=False
        assert notif_creada.leida is False, "P3: estado inicial debe ser leida=False"

        # Marcar como leída
        resultado = repo.marcar_leida(notif_creada.id, user.id)

        assert resultado is True, "marcar_leida() debe retornar True cuando tiene éxito"
        assert notif_creada.leida is True, (
            "P3: después de marcar_leida(), leida debe ser True"
        )

        # Verificar que ya no aparece en no_leidas
        no_leidas = repo.get_no_leidas(user.id)
        assert len(no_leidas) == 0, (
            "P3: después de marcar como leída, get_no_leidas() debe retornar lista vacía"
        )
