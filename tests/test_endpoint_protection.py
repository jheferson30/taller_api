"""
Tests de protección de endpoints
Valida que los endpoints protegidos rechazan requests sin token o con tokens inválidos
"""
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.seguridad.token_manager import TokenManager
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository


class TestEndpointProtection:
    """Tests de protección de endpoints (Property 21.1, 21.2, 21.3, 21.4)"""

    def test_protected_endpoint_rejects_no_token(self, client):
        """Test endpoints protegidos rechazan requests sin token (401)"""
        # Intentar acceder a endpoint protegido sin token
        response = client.get("/users")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_protected_endpoint_rejects_expired_token(self, client, db_session):
        """Test tokens expirados son rechazados (401)"""
        token_manager = TokenManager()
        
        # Crear token expirado (expiró hace 1 hora)
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "user_id": 1,
            "username": "testuser",
            "roles": ["ADMIN"],
            "exp": expired_time,
            "iat": expired_time - timedelta(minutes=15),
            "jti": "test-jti-expired"
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

    def test_protected_endpoint_rejects_invalid_signature(self, client):
        """Test tokens con firma inválida son rechazados (401)"""
        # Crear token con firma incorrecta
        payload = {
            "user_id": 1,
            "username": "testuser",
            "roles": ["ADMIN"],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
            "jti": "test-jti-invalid"
        }
        
        invalid_token = jwt.encode(
            payload,
            "wrong-secret-key",  # Firma incorrecta
            algorithm="HS256"
        )
        
        # Intentar acceder con token de firma inválida
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_rejects_blacklisted_token(
        self, client, db_session, test_user
    ):
        """Test tokens en lista negra son rechazados (401)"""
        token_manager = TokenManager()
        blacklist_repo = TokenBlacklistRepository(db_session)
        
        # Generar token válido
        access_token = token_manager.generate_access_token(
            user_id=test_user.id,
            username=test_user.username,
            roles=[role.name for role in test_user.roles]
        )
        
        # Decodificar para obtener jti
        decoded = token_manager.decode_token(access_token)
        jti = decoded["jti"]
        
        # Agregar token a blacklist
        blacklist_repo.add_to_blacklist(
            jti=jti,
            user_id=test_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
        )
        db_session.commit()
        
        # Intentar acceder con token blacklisted
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_accepts_valid_token(
        self, client, db_session, test_user
    ):
        """Test endpoint protegido acepta token válido"""
        token_manager = TokenManager()
        
        # Generar token válido
        access_token = token_manager.generate_access_token(
            user_id=test_user.id,
            username=test_user.username,
            roles=[role.name for role in test_user.roles]
        )
        
        # Acceder con token válido
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        # Debe ser 200 (éxito) o 403 (sin permisos), pero no 401
        assert response.status_code in [200, 403]

    def test_malformed_authorization_header(self, client):
        """Test header Authorization malformado es rechazado"""
        # Sin "Bearer" prefix
        response = client.get(
            "/users",
            headers={"Authorization": "invalid-token"}
        )
        assert response.status_code == 401
        
        # Header vacío
        response = client.get(
            "/users",
            headers={"Authorization": ""}
        )
        assert response.status_code == 401
        
        # Solo "Bearer" sin token
        response = client.get(
            "/users",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401
