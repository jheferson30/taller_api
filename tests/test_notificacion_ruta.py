"""
Tests para endpoints de notificaciones en app/rutas/notificacion_ruta.py.

Valida los endpoints de consulta y marcado de notificaciones internas,
con énfasis en seguridad y aislamiento multi-tenant.

Requirements: 4.1, 4.5, 5.1, 5.2, 9.1, 9.3, 9.4
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base, obtener_db
from app.main import app

# Importar todos los modelos para que SQLAlchemy los registre en Base.metadata
from app.modelos.audit_log import AuditLog  # noqa: F401
from app.modelos.configuracion_taller import ConfiguracionTaller  # noqa: F401
from app.modelos.mecanico import Mecanico  # noqa: F401
from app.modelos.notificacion import Notificacion, TipoNotificacion
from app.modelos.password_reset_token import PasswordResetToken  # noqa: F401
from app.modelos.role import Role
from app.modelos.taller import Taller
from app.modelos.ticket import Ticket  # noqa: F401
from app.modelos.token_blacklist import TokenBlacklist  # noqa: F401
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.modelos.vehiculo import Vehiculo  # noqa: F401
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.token_manager import TokenManager


@pytest.fixture
def db_session():
    """Crea una sesión de base de datos SQLite en memoria para cada test."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    """
    Cliente de test de FastAPI con base de datos de test.

    Sobreescribe obtener_db para que los endpoints usen la BD en memoria.
    Parchea SessionLocal en el middleware para que también use la BD de test.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[obtener_db] = override_get_db

    with patch("app.configuracion.base_datos.SessionLocal", return_value=db_session):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def token_manager():
    """Instancia de TokenManager para tests."""
    return TokenManager()


@pytest.fixture
def taller1(db_session):
    """Crea un taller de test."""
    taller = Taller(
        nombre="Taller 1",
        nit="123456789",
        direccion="Calle 1",
        telefono="1234567",
        activo=True,
    )
    db_session.add(taller)
    db_session.commit()
    db_session.refresh(taller)
    return taller


@pytest.fixture
def taller2(db_session):
    """Crea un segundo taller de test."""
    taller = Taller(
        nombre="Taller 2",
        nit="987654321",
        direccion="Calle 2",
        telefono="7654321",
        activo=True,
    )
    db_session.add(taller)
    db_session.commit()
    db_session.refresh(taller)
    return taller


@pytest.fixture
def admin_role(db_session):
    """Crea el rol ADMIN."""
    role = Role(name="ADMIN", description="Administrador del taller")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def mecanico_role(db_session):
    """Crea el rol MECANICO."""
    role = Role(name="MECANICO", description="Mecánico del taller")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def super_admin_role(db_session):
    """Crea el rol SUPER_ADMIN."""
    role = Role(name="SUPER_ADMIN", description="Administrador de plataforma")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def admin_user_taller1(db_session, taller1, admin_role):
    """Crea un usuario ADMIN del taller 1."""
    user = User(
        username="admin1",
        email="admin1@taller1.com",
        password_hash=PasswordHasher().hash_password("Admin123"),
        is_active=True,
        is_migrated=True,
        taller_id=taller1.id,
    )
    db_session.add(user)
    db_session.commit()

    user_role = UserRole(user_id=user.id, role_id=admin_role.id)
    db_session.add(user_role)
    db_session.commit()

    db_session.refresh(user)
    return user


@pytest.fixture
def mecanico_user_taller1(db_session, taller1, mecanico_role):
    """Crea un usuario MECANICO del taller 1."""
    user = User(
        username="mecanico1",
        email="mecanico1@taller1.com",
        password_hash=PasswordHasher().hash_password("Mecanico123"),
        is_active=True,
        is_migrated=True,
        taller_id=taller1.id,
    )
    db_session.add(user)
    db_session.commit()

    user_role = UserRole(user_id=user.id, role_id=mecanico_role.id)
    db_session.add(user_role)
    db_session.commit()

    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user_taller2(db_session, taller2, admin_role):
    """Crea un usuario ADMIN del taller 2."""
    user = User(
        username="admin2",
        email="admin2@taller2.com",
        password_hash=PasswordHasher().hash_password("Admin123"),
        is_active=True,
        is_migrated=True,
        taller_id=taller2.id,
    )
    db_session.add(user)
    db_session.commit()

    user_role = UserRole(user_id=user.id, role_id=admin_role.id)
    db_session.add(user_role)
    db_session.commit()

    db_session.refresh(user)
    return user


@pytest.fixture
def super_admin_user(db_session, super_admin_role):
    """Crea un usuario SUPER_ADMIN (sin taller_id)."""
    user = User(
        username="superadmin",
        email="superadmin@platform.com",
        password_hash=PasswordHasher().hash_password("SuperAdmin123"),
        is_active=True,
        is_migrated=True,
        taller_id=None,  # SUPER_ADMIN no tiene taller
    )
    db_session.add(user)
    db_session.commit()

    user_role = UserRole(user_id=user.id, role_id=super_admin_role.id)
    db_session.add(user_role)
    db_session.commit()

    db_session.refresh(user)
    return user


def make_token(user: User, roles: list[str]) -> str:
    """Genera un JWT directamente sin pasar por el endpoint de login."""
    import uuid
    from datetime import timedelta
    from datetime import UTC, datetime
    import jwt as pyjwt
    import os

    secret = os.getenv("JWT_SECRET_KEY", "test_secret_key_with_at_least_32_characters_for_security")
    now = datetime.now(UTC)
    payload = {
        "user_id": user.id,
        "username": user.username,
        "roles": roles,
        "taller_id": user.taller_id,
        "exp": now + timedelta(minutes=15),
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


class TestGetNotificacionesNoLeidas:
    """Tests para GET /notificaciones/no-leidas."""

    def test_sin_jwt_retorna_401(self, client):
        """
        Test: endpoint sin JWT retorna 401.
        Valida: Req 4.5, 9.1
        """
        response = client.get("/notificaciones/no-leidas")
        assert response.status_code == 401

    def test_super_admin_retorna_403(self, client, super_admin_user):
        """
        Test: SUPER_ADMIN (taller_id=null) retorna 403.
        Valida: Req 9.3
        """
        tm = TokenManager()
        token = make_token(super_admin_user, ["SUPER_ADMIN"])
        response = client.get(
            "/notificaciones/no-leidas", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert "SUPER_ADMIN" in response.json()["detail"]

    def test_usuario_obtiene_solo_sus_notificaciones_no_leidas(
        self, client, db_session, admin_user_taller1, mecanico_user_taller1, taller1
    ):
        """
        Test: usuario obtiene solo sus notificaciones no leídas del mismo taller.
        Valida: Req 4.1, 4.2
        """
        # Crear notificaciones para admin_user_taller1
        notif1 = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=admin_user_taller1.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket asignado",
            mensaje="Ticket #1",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        notif2 = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=admin_user_taller1.id,
            tipo=TipoNotificacion.RENOVACION_PLAN,
            titulo="Renovación",
            mensaje="Plan vence en 2 días",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        # Notificación leída (no debe aparecer)
        notif3 = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=admin_user_taller1.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket asignado",
            mensaje="Ticket #2",
            leida=True,
            fecha_creacion=datetime.now(UTC),
        )
        # Notificación de otro usuario (no debe aparecer)
        notif4 = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=mecanico_user_taller1.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket asignado",
            mensaje="Ticket #3",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        db_session.add_all([notif1, notif2, notif3, notif4])
        db_session.commit()
        db_session.refresh(notif1)
        db_session.refresh(notif2)
        db_session.refresh(notif3)
        db_session.refresh(notif4)

        tm = TokenManager()
        token = make_token(admin_user_taller1, ["ADMIN"])
        response = client.get(
            "/notificaciones/no-leidas", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Debe retornar solo las 2 notificaciones no leídas del admin
        assert data["total"] == 2
        assert len(data["notificaciones"]) == 2

        # Verificar que son las correctas
        ids = [n["id"] for n in data["notificaciones"]]
        assert notif1.id in ids
        assert notif2.id in ids
        assert notif3.id not in ids  # leída
        assert notif4.id not in ids  # otro usuario

    def test_usuario_no_ve_notificaciones_de_otro_taller(
        self, client, db_session, admin_user_taller1, taller1, taller2
    ):
        """
        Test: usuario no ve notificaciones de otro taller.
        Valida: Req 9.2, 9.3
        """
        # Crear notificación en taller 2
        notif_taller2 = Notificacion(
            taller_id=taller2.id,
            destinatario_user_id=999,  # Usuario ficticio del taller 2
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket asignado",
            mensaje="Ticket del taller 2",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        db_session.add(notif_taller2)
        db_session.commit()

        tm = TokenManager()
        token = make_token(admin_user_taller1, ["ADMIN"])
        response = client.get(
            "/notificaciones/no-leidas", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # No debe ver la notificación del taller 2
        assert data["total"] == 0
        assert len(data["notificaciones"]) == 0


class TestMarcarNotificacionComoLeida:
    """Tests para PATCH /notificaciones/{id}/leer."""

    def test_sin_jwt_retorna_401(self, client):
        """
        Test: endpoint sin JWT retorna 401.
        Valida: Req 4.5, 9.1
        """
        response = client.patch("/notificaciones/1/leer")
        assert response.status_code == 401

    def test_super_admin_retorna_403(self, client, super_admin_user):
        """
        Test: SUPER_ADMIN (taller_id=null) retorna 403.
        Valida: Req 9.3
        """
        tm = TokenManager()
        token = make_token(super_admin_user, ["SUPER_ADMIN"])
        response = client.patch("/notificaciones/1/leer", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert "SUPER_ADMIN" in response.json()["detail"]

    def test_marcar_notificacion_propia_como_leida(
        self, client, db_session, admin_user_taller1, taller1
    ):
        """
        Test: usuario puede marcar su propia notificación como leída.
        Valida: Req 5.1
        """
        # Crear notificación
        notif = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=admin_user_taller1.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket asignado",
            mensaje="Ticket #1",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)

        tm = TokenManager()
        token = make_token(admin_user_taller1, ["ADMIN"])
        response = client.patch(
            f"/notificaciones/{notif.id}/leer", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == notif.id
        assert data["leida"] is True

        # Verificar en BD
        db_session.expire_all()
        notif_actualizada = db_session.get(Notificacion, notif.id)
        assert notif_actualizada.leida is True

    def test_marcar_notificacion_de_otro_usuario_retorna_404(
        self, client, db_session, admin_user_taller1, mecanico_user_taller1, taller1
    ):
        """
        Test: marcar notificación de otro usuario del mismo taller retorna 404.
        Valida: Req 5.2, 5.4, 9.4
        """
        # Crear notificación para mecanico
        notif = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=mecanico_user_taller1.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket asignado",
            mensaje="Ticket #1",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)

        # Admin intenta marcarla como leída
        tm = TokenManager()
        token = make_token(admin_user_taller1, ["ADMIN"])
        response = client.patch(
            f"/notificaciones/{notif.id}/leer", headers={"Authorization": f"Bearer {token}"}
        )

        # Debe retornar 404 (no 403) para no revelar existencia
        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"].lower()

        # Verificar que no se modificó en BD
        db_session.expire_all()
        notif_actual = db_session.get(Notificacion, notif.id)
        assert notif_actual.leida is False

    def test_marcar_notificacion_de_otro_taller_retorna_404(
        self, client, db_session, admin_user_taller1, taller2
    ):
        """
        Test: marcar notificación de otro taller retorna 404.
        Valida: Req 5.2, 9.3, 9.4
        """
        # Crear notificación en taller 2
        notif = Notificacion(
            taller_id=taller2.id,
            destinatario_user_id=999,  # Usuario ficticio del taller 2
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket asignado",
            mensaje="Ticket del taller 2",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)

        # Usuario del taller 1 intenta marcarla
        token = make_token(admin_user_taller1, ["ADMIN"])
        response = client.patch(
            f"/notificaciones/{notif.id}/leer", headers={"Authorization": f"Bearer {token}"}
        )

        # Debe retornar 404 (no 403) para no revelar existencia
        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"].lower()

        # Verificar que no se modificó en BD
        db_session.expire_all()
        notif_actual = db_session.get(Notificacion, notif.id)
        assert notif_actual.leida is False


class TestMarcarTodasComoLeidas:
    """Tests para PATCH /notificaciones/leer-todas."""

    def test_sin_jwt_retorna_401(self, client):
        """
        Test: endpoint sin JWT retorna 401.
        Valida: Req 4.5, 9.1
        """
        response = client.patch("/notificaciones/leer-todas")
        assert response.status_code == 401

    def test_super_admin_retorna_403(self, client, super_admin_user):
        """
        Test: SUPER_ADMIN (taller_id=null) retorna 403.
        Valida: Req 9.3
        """
        token = make_token(super_admin_user, ["SUPER_ADMIN"])
        response = client.patch(
            "/notificaciones/leer-todas", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert "SUPER_ADMIN" in response.json()["detail"]

    def test_marcar_todas_las_notificaciones_propias(
        self, client, db_session, admin_user_taller1, mecanico_user_taller1, taller1
    ):
        """
        Test: marcar todas marca solo las notificaciones del usuario, no de otros.
        Valida: Req 5.3
        """
        # Crear notificaciones para admin
        notif1 = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=admin_user_taller1.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket 1",
            mensaje="Ticket #1",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        notif2 = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=admin_user_taller1.id,
            tipo=TipoNotificacion.RENOVACION_PLAN,
            titulo="Renovación",
            mensaje="Plan vence",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        # Notificación de otro usuario (no debe ser afectada)
        notif3 = Notificacion(
            taller_id=taller1.id,
            destinatario_user_id=mecanico_user_taller1.id,
            tipo=TipoNotificacion.TICKET_ASIGNADO,
            titulo="Ticket 2",
            mensaje="Ticket #2",
            leida=False,
            fecha_creacion=datetime.now(UTC),
        )
        db_session.add_all([notif1, notif2, notif3])
        db_session.commit()

        # Guardar IDs antes del request para evitar DetachedInstanceError
        notif1_id = notif1.id
        notif2_id = notif2.id
        notif3_id = notif3.id

        token = make_token(admin_user_taller1, ["ADMIN"])
        response = client.patch(
            "/notificaciones/leer-todas", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Debe haber marcado 2 notificaciones
        assert data["marcadas"] == 2

        # Verificar en BD — usar IDs guardados previamente para evitar DetachedInstanceError
        db_session.expire_all()
        notif1_actual = db_session.query(Notificacion).filter(Notificacion.id == notif1_id).first()
        notif2_actual = db_session.query(Notificacion).filter(Notificacion.id == notif2_id).first()
        notif3_actual = db_session.query(Notificacion).filter(Notificacion.id == notif3_id).first()

        assert notif1_actual.leida is True
        assert notif2_actual.leida is True
        assert notif3_actual.leida is False  # No debe ser afectada
