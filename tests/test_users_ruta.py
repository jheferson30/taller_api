"""
Tests para endpoints de gestión de usuarios.
"""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base, obtener_db
from app.main import app
from app.modelos.role import Role
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.seguridad.password_hasher import PasswordHasher

# Base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override de la dependencia de base de datos para tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[obtener_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    """Fixture que crea una sesión de base de datos limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Fixture que crea un cliente de test."""
    return TestClient(app)


@pytest.fixture
def password_hasher():
    """Fixture que crea un hasher de contraseñas."""
    return PasswordHasher()


def mock_request_state(user):
    """Helper para mockear request.state con un usuario."""
    mock_request = Mock()
    mock_request.state.user = user
    mock_request.client.host = "127.0.0.1"
    mock_request.headers.get = Mock(return_value="test-agent")
    return mock_request


@pytest.fixture
def admin_user(db_session, password_hasher):
    """Fixture que crea un usuario administrador."""
    # Crear rol ADMIN
    admin_role = Role(name="ADMIN", description="Administrator")
    db_session.add(admin_role)
    db_session.commit()

    # Crear usuario admin
    admin = User(
        username="admin",
        email="admin@test.com",
        password_hash=password_hasher.hash_password("Admin123"),
        is_active=True,
        is_migrated=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    # Asignar rol
    user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
    db_session.add(user_role)
    db_session.commit()
    db_session.refresh(admin)

    return admin


@pytest.fixture
def regular_user(db_session, password_hasher):
    """Fixture que crea un usuario regular."""
    # Crear rol USER
    user_role = Role(name="USER", description="Regular user")
    db_session.add(user_role)
    db_session.commit()

    # Crear usuario
    user = User(
        username="user1",
        email="user1@test.com",
        password_hash=password_hasher.hash_password("User123"),
        is_active=True,
        is_migrated=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Asignar rol
    ur = UserRole(user_id=user.id, role_id=user_role.id)
    db_session.add(ur)
    db_session.commit()
    db_session.refresh(user)

    return user


class TestCreateUser:
    """Tests para POST /users"""

    def test_create_user_success(self, client, db_session, admin_user, admin_token):
        """Test: Admin puede crear un nuevo usuario."""
        # Crear rol USER para asignar
        user_role = Role(name="USER", description="Regular user")
        db_session.add(user_role)
        db_session.commit()

        response = client.post(
            "/users",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "NewUser123",
                "roles": ["USER"],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@test.com"
        assert "USER" in data["roles"]
        assert data["is_active"] is True

    def test_create_user_duplicate_username(self, client, db_session, admin_user, admin_token):
        """Test: No se puede crear usuario con username duplicado."""
        response = client.post(
            "/users",
            json={
                "username": "admin",  # Ya existe
                "email": "another@test.com",
                "password": "Test123",
                "roles": ["ADMIN"],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 409
        assert "username" in response.json()["detail"].lower()

    def test_create_user_duplicate_email(self, client, db_session, admin_user, admin_token):
        """Test: No se puede crear usuario con email duplicado."""
        response = client.post(
            "/users",
            json={
                "username": "newuser",
                "email": "admin@test.com",  # Ya existe
                "password": "Test123",
                "roles": ["ADMIN"],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 409
        assert "email" in response.json()["detail"].lower()

    def test_create_user_weak_password(self, client, db_session, admin_user, admin_token):
        """Test: Contraseña débil es rechazada."""
        response = client.post(
            "/users",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "weak",  # No cumple requisitos
                "roles": ["ADMIN"],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        assert "contraseña" in response.json()["detail"].lower()

    def test_create_user_requires_admin(self, client, user_token):
        """Test: Usuario regular no puede crear usuarios."""
        response = client.post(
            "/users",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "Test123",
                "roles": ["USER"],
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403


class TestGetUsers:
    """Tests para GET /users"""

    def test_get_users_success(self, client, db_session, admin_user, admin_token):
        """Test: Admin puede listar usuarios."""
        response = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert len(data["users"]) >= 1  # Al menos el admin

    def test_get_users_pagination(self, client, db_session, admin_user, admin_token):
        """Test: Paginación funciona correctamente."""
        response = client.get(
            "/users?skip=0&limit=10", headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 10

    def test_get_users_requires_admin(self, client, user_token):
        """Test: Usuario regular no puede listar usuarios."""
        response = client.get("/users", headers={"Authorization": f"Bearer {user_token}"})

        assert response.status_code == 403


class TestGetUser:
    """Tests para GET /users/{id}"""

    def test_get_user_own_profile(self, client, regular_user, user_token):
        """Test: Usuario puede ver su propio perfil."""
        response = client.get(
            f"/users/{regular_user.id}", headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == regular_user.id
        assert data["username"] == regular_user.username

    def test_get_user_admin_can_view_any(self, client, regular_user, admin_token):
        """Test: Admin puede ver cualquier usuario."""
        response = client.get(
            f"/users/{regular_user.id}", headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == regular_user.id

    def test_get_user_cannot_view_others(self, client, admin_user, user_token):
        """Test: Usuario regular no puede ver otros perfiles."""
        response = client.get(
            f"/users/{admin_user.id}", headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == 403

    def test_get_user_not_found(self, client, admin_token):
        """Test: Usuario no encontrado retorna 404."""
        response = client.get("/users/99999", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 404


class TestUpdateUser:
    """Tests para PATCH /users/{id}"""

    def test_update_user_email(self, client, db_session, regular_user, admin_token):
        """Test: Admin puede actualizar email de usuario."""
        response = client.patch(
            f"/users/{regular_user.id}",
            json={"email": "newemail@test.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@test.com"

    def test_update_user_roles(self, client, db_session, regular_user, admin_token):
        """Test: Admin puede actualizar roles de usuario."""
        # Crear rol MECANICO
        mecanico_role = Role(name="MECANICO", description="Mechanic")
        db_session.add(mecanico_role)
        db_session.commit()

        response = client.patch(
            f"/users/{regular_user.id}",
            json={"roles": ["USER", "MECANICO"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "MECANICO" in data["roles"]

    def test_update_user_requires_admin(self, client, regular_user, user_token):
        """Test: Usuario regular no puede actualizar usuarios."""
        response = client.patch(
            f"/users/{regular_user.id}",
            json={"email": "newemail@test.com"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    def test_update_user_not_found(self, client, admin_token):
        """Test: Actualizar usuario inexistente retorna 404."""
        response = client.patch(
            "/users/99999",
            json={"email": "test@test.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404


class TestDeleteUser:
    """Tests para DELETE /users/{id}"""

    def test_delete_user_success(self, client, db_session, regular_user, admin_token):
        """Test: Admin puede desactivar usuario."""
        response = client.delete(
            f"/users/{regular_user.id}", headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 204

        # Verificar que el usuario está inactivo
        db_session.refresh(regular_user)
        assert regular_user.is_active is False

    def test_delete_user_requires_admin(self, client, regular_user, user_token):
        """Test: Usuario regular no puede desactivar usuarios."""
        response = client.delete(
            f"/users/{regular_user.id}", headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == 403

    def test_delete_user_not_found(self, client, admin_token):
        """Test: Desactivar usuario inexistente retorna 404."""
        response = client.delete("/users/99999", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 404


class TestChangePassword:
    """Tests para POST /users/me/change-password"""

    def test_change_password_success(
        self, client, db_session, regular_user, user_token, password_hasher
    ):
        """Test: Usuario puede cambiar su contraseña."""
        response = client.post(
            "/users/me/change-password",
            json={"current_password": "User123", "new_password": "NewPassword123"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200
        assert "exitosamente" in response.json()["message"].lower()

        # Verificar que la nueva contraseña funciona
        db_session.refresh(regular_user)
        assert password_hasher.verify_password("NewPassword123", regular_user.password_hash)

    def test_change_password_wrong_current(self, client, user_token):
        """Test: Contraseña actual incorrecta es rechazada."""
        response = client.post(
            "/users/me/change-password",
            json={"current_password": "WrongPassword", "new_password": "NewPassword123"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 400
        assert "incorrecta" in response.json()["detail"].lower()

    def test_change_password_weak_new(self, client, user_token):
        """Test: Nueva contraseña débil es rechazada."""
        response = client.post(
            "/users/me/change-password",
            json={"current_password": "User123", "new_password": "weak"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 400
        assert "contraseña" in response.json()["detail"].lower()

    def test_change_password_requires_auth(self, client):
        """Test: Cambiar contraseña requiere autenticación."""
        response = client.post(
            "/users/me/change-password",
            json={"current_password": "User123", "new_password": "NewPassword123"},
        )

        assert response.status_code == 401
