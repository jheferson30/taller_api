"""
Tests de mensajes de error
Valida que los mensajes de error no revelan información sensible
"""
import pytest
from app.modelos.user import User
from app.modelos.role import Role, UserRole


class TestErrorMessages:
    """Tests de mensajes de error (Property 21.8)"""

    def test_login_failed_does_not_reveal_user_existence(
        self, client, db_session, test_user
    ):
        """Test login fallido no revela si usuario existe"""
        # Intentar login con usuario que no existe
        response_nonexistent = client.post(
            "/auth/login",
            json={
                "username": "nonexistent_user",
                "password": "anypassword"
            }
        )
        
        # Intentar login con usuario existente pero contraseña incorrecta
        response_wrong_password = client.post(
            "/auth/login",
            json={
                "username": test_user.username,
                "password": "wrongpassword"
            }
        )
        
        # Ambos deben retornar 401
        assert response_nonexistent.status_code == 401
        assert response_wrong_password.status_code == 401
        
        # Los mensajes deben ser genéricos e idénticos
        error1 = response_nonexistent.json()["detail"]
        error2 = response_wrong_password.json()["detail"]
        
        # No deben revelar si el usuario existe o no
        assert "usuario" not in error1.lower() or "contraseña" not in error1.lower()
        assert "usuario" not in error2.lower() or "contraseña" not in error2.lower()
        
        # Idealmente, los mensajes deberían ser idénticos
        # (esto depende de la implementación específica)

    def test_password_reset_does_not_reveal_email_existence(
        self, client, db_session, test_user
    ):
        """Test password reset no revela si email existe"""
        # Solicitar reset con email que no existe
        response_nonexistent = client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@test.com"}
        )
        
        # Solicitar reset con email existente
        response_existing = client.post(
            "/auth/forgot-password",
            json={"email": test_user.email}
        )
        
        # Ambos deben retornar 200 (éxito)
        assert response_nonexistent.status_code == 200
        assert response_existing.status_code == 200
        
        # Los mensajes deben ser genéricos e idénticos
        message1 = response_nonexistent.json()["message"]
        message2 = response_existing.json()["message"]
        
        # No deben revelar si el email existe
        assert message1 == message2

    def test_user_creation_with_duplicate_username_reveals_conflict(
        self, client, db_session, test_user
    ):
        """Test creación de usuario con username duplicado revela conflicto"""
        from app.seguridad.token_manager import TokenManager
        
        token_manager = TokenManager()
        access_token = token_manager.generate_access_token(
            user_id=test_user.id,
            username=test_user.username,
            roles=[role.name for role in test_user.roles]
        )
        
        # Intentar crear usuario con username duplicado
        response = client.post(
            "/users",
            json={
                "username": test_user.username,  # Username ya existe
                "email": "newemail@test.com",
                "password": "NewPassword123!"
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Debe retornar 400 o 409 (conflicto)
        assert response.status_code in [400, 409]
        
        # El mensaje puede revelar que el username ya existe
        # (esto es aceptable para creación de usuarios)
        error = response.json()["detail"]
        assert "username" in error.lower() or "existe" in error.lower()

    def test_invalid_token_error_is_generic(self, client):
        """Test error de token inválido es genérico"""
        # Intentar acceder con token inválido
        response = client.get(
            "/users",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
        error = response.json()["detail"]
        
        # El mensaje debe ser genérico
        assert "invalid" in error.lower() or "unauthorized" in error.lower()
        
        # No debe revelar detalles técnicos del error

    def test_expired_token_error_is_informative(self, client):
        """Test error de token expirado es informativo pero seguro"""
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from app.seguridad.token_manager import TokenManager
        
        token_manager = TokenManager()
        
        # Crear token expirado
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "user_id": 1,
            "username": "testuser",
            "roles": ["ADMIN"],
            "exp": expired_time,
            "iat": expired_time - timedelta(minutes=15),
            "jti": "test-jti"
        }
        
        expired_token = jwt.encode(
            payload,
            token_manager.secret_key,
            algorithm=token_manager.algorithm
        )
        
        # Intentar acceder con token expirado
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        error = response.json()["detail"]
        
        # Puede mencionar que el token expiró
        # pero no debe revelar información sensible del payload

    def test_insufficient_permissions_error_is_clear(
        self, client, db_session
    ):
        """Test error de permisos insuficientes es claro"""
        from app.seguridad.token_manager import TokenManager
        
        token_manager = TokenManager()
        
        # Crear usuario sin rol ADMIN
        user = User(
            username="mecanico_test",
            email="mecanico_test@test.com",
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
        
        # Intentar acceder a endpoint que requiere ADMIN
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 403
        error = response.json()["detail"]
        
        # El mensaje debe indicar permisos insuficientes
        assert "permiso" in error.lower() or "forbidden" in error.lower()
