"""
Tests de roles y permisos
Valida que el control de acceso basado en roles funciona correctamente
"""
import pytest
from app.seguridad.token_manager import TokenManager
from app.modelos.user import User
from app.modelos.role import Role, UserRole


class TestRolePermissions:
    """Tests de roles y permisos (Property 21.6)"""

    def test_user_without_admin_role_cannot_access_users_endpoint(
        self, client, db_session
    ):
        """Test usuario sin rol ADMIN no puede acceder a /users (403)"""
        token_manager = TokenManager()
        
        # Crear usuario sin rol ADMIN
        user = User(
            username="mecanico1",
            email="mecanico@test.com",
            password_hash="dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.flush()
        
        # Asignar rol MECANICO
        mecanico_role = db_session.query(Role).filter_by(name="MECANICO").first()
        if mecanico_role:
            user_role = UserRole(user_id=user.id, role_id=mecanico_role.id)
            db_session.add(user_role)
        
        db_session.commit()
        
        # Generar token con rol MECANICO
        access_token = token_manager.generate_access_token(
            user_id=user.id,
            username=user.username,
            roles=["MECANICO"]
        )
        
        # Intentar acceder a /users (requiere ADMIN)
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 403
        assert "detail" in response.json()

    def test_user_with_admin_role_can_access_users_endpoint(
        self, client, db_session, test_user
    ):
        """Test usuario con rol ADMIN puede acceder a /users"""
        token_manager = TokenManager()
        
        # test_user ya tiene rol ADMIN por defecto
        access_token = token_manager.generate_access_token(
            user_id=test_user.id,
            username=test_user.username,
            roles=[role.name for role in test_user.roles]
        )
        
        # Acceder a /users con rol ADMIN
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200

    def test_user_can_access_own_profile_without_admin(
        self, client, db_session
    ):
        """Test usuario puede ver su propio perfil sin ser ADMIN"""
        token_manager = TokenManager()
        
        # Crear usuario sin rol ADMIN
        user = User(
            username="mecanico2",
            email="mecanico2@test.com",
            password_hash="dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.flush()
        
        # Asignar rol MECANICO
        mecanico_role = db_session.query(Role).filter_by(name="MECANICO").first()
        if mecanico_role:
            user_role = UserRole(user_id=user.id, role_id=mecanico_role.id)
            db_session.add(user_role)
        
        db_session.commit()
        
        # Generar token
        access_token = token_manager.generate_access_token(
            user_id=user.id,
            username=user.username,
            roles=["MECANICO"]
        )
        
        # Acceder a su propio perfil
        response = client.get(
            f"/users/{user.id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200

    def test_user_cannot_access_other_user_profile_without_admin(
        self, client, db_session, test_user
    ):
        """Test usuario no puede ver perfil de otro usuario sin ser ADMIN"""
        token_manager = TokenManager()
        
        # Crear usuario sin rol ADMIN
        user = User(
            username="mecanico3",
            email="mecanico3@test.com",
            password_hash="dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.flush()
        
        # Asignar rol MECANICO
        mecanico_role = db_session.query(Role).filter_by(name="MECANICO").first()
        if mecanico_role:
            user_role = UserRole(user_id=user.id, role_id=mecanico_role.id)
            db_session.add(user_role)
        
        db_session.commit()
        
        # Generar token
        access_token = token_manager.generate_access_token(
            user_id=user.id,
            username=user.username,
            roles=["MECANICO"]
        )
        
        # Intentar acceder a perfil de otro usuario (test_user)
        response = client.get(
            f"/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 403

    def test_multiple_roles_grant_combined_permissions(
        self, client, db_session
    ):
        """Test usuario con múltiples roles tiene permisos combinados"""
        token_manager = TokenManager()
        
        # Crear usuario con múltiples roles
        user = User(
            username="supervisor",
            email="supervisor@test.com",
            password_hash="dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.flush()
        
        # Asignar roles ADMIN y MECANICO
        admin_role = db_session.query(Role).filter_by(name="ADMIN").first()
        mecanico_role = db_session.query(Role).filter_by(name="MECANICO").first()
        
        if admin_role:
            db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))
        if mecanico_role:
            db_session.add(UserRole(user_id=user.id, role_id=mecanico_role.id))
        
        db_session.commit()
        
        # Generar token con ambos roles
        access_token = token_manager.generate_access_token(
            user_id=user.id,
            username=user.username,
            roles=["ADMIN", "MECANICO"]
        )
        
        # Debe poder acceder a endpoints de ADMIN
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
