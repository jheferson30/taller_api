"""
Property-based tests para TokenManager.

Este módulo implementa property tests usando Hypothesis para validar:
- Property 3: Access token expiration time
- Property 4: Refresh token expiration time
- Property 5: JWT token verification round-trip
- Property 6: JWT payload completeness
- Property 48: Unique JWT ID

Valida Requirements: 1.3, 1.4, 1.5, 1.6, 20.6

# Feature: mejoras-seguridad-jwt-auditoria, Property 3: Access token expiration time
# Feature: mejoras-seguridad-jwt-auditoria, Property 4: Refresh token expiration time
# Feature: mejoras-seguridad-jwt-auditoria, Property 5: JWT token verification round-trip
# Feature: mejoras-seguridad-jwt-auditoria, Property 6: JWT payload completeness
# Feature: mejoras-seguridad-jwt-auditoria, Property 48: Unique JWT ID
"""

import os
import pytest
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import MagicMock

from app.seguridad.token_manager import TokenManager
from app.modelos.user import User
from app.modelos.role import Role


# Estrategias de Hypothesis
@st.composite
def valid_user(draw):
    """
    Genera usuarios válidos para testing.
    
    Crea objetos User con datos aleatorios pero válidos,
    incluyendo roles opcionales.
    """
    user_id = draw(st.integers(min_value=1, max_value=1000000))
    username = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            min_codepoint=48,
            max_codepoint=122
        ),
        min_size=3,
        max_size=20
    ))
    
    # Crear usuario mock
    user = MagicMock(spec=User)
    user.id = user_id
    user.username = username
    
    # Generar roles aleatorios
    num_roles = draw(st.integers(min_value=0, max_value=4))
    roles = []
    role_names = ["ADMIN", "MECANICO", "RECEPCIONISTA", "SOLO_LECTURA"]
    
    for _ in range(num_roles):
        role_name = draw(st.sampled_from(role_names))
        role = MagicMock(spec=Role)
        role.name = role_name
        roles.append(role)
    
    user.roles = roles
    
    return user


@st.composite
def valid_secret_key(draw):
    """
    Genera claves secretas válidas para JWT (mínimo 32 caracteres).
    """
    return draw(st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs", "Cc"),
            min_codepoint=33,
            max_codepoint=126
        ),
        min_size=32,
        max_size=64
    ))


@pytest.mark.property_test
class TestProperty3_AccessTokenExpirationTime:
    """
    Property 3: Access token expiration time
    
    **Validates: Requirements 1.3**
    
    Propiedad: FOR ANY successful authentication, the generated access token
               MUST have an expiration time (exp claim) that is exactly 15 minutes
               after the issued time (iat claim).
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_access_token_expires_in_15_minutes(self, user, secret_key):
        """
        Property: El access token debe expirar exactamente 15 minutos después de su emisión.
        
        Este test valida que:
        1. El token contiene claims exp e iat
        2. La diferencia entre exp e iat es exactamente 15 minutos (900 segundos)
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar access token
        access_token = token_manager.generate_access_token(user)
        
        # Decodificar token
        payload = token_manager.decode_token(access_token)
        
        # Verificar que contiene exp e iat
        assert "exp" in payload, "Access token debe contener claim 'exp'"
        assert "iat" in payload, "Access token debe contener claim 'iat'"
        
        # Calcular diferencia en segundos
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        
        # La diferencia debe ser exactamente 15 minutos (900 segundos)
        expected_diff = 15 * 60  # 900 segundos
        actual_diff = exp_timestamp - iat_timestamp
        
        assert actual_diff == expected_diff, \
            f"Access token debe expirar en 15 minutos (900s), pero expira en {actual_diff}s"


@pytest.mark.property_test
class TestProperty4_RefreshTokenExpirationTime:
    """
    Property 4: Refresh token expiration time
    
    **Validates: Requirements 1.4**
    
    Propiedad: FOR ANY successful authentication, the generated refresh token
               MUST have an expiration time (exp claim) that is exactly 7 days
               after the issued time (iat claim).
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_refresh_token_expires_in_7_days(self, user, secret_key):
        """
        Property: El refresh token debe expirar exactamente 7 días después de su emisión.
        
        Este test valida que:
        1. El token contiene claims exp e iat
        2. La diferencia entre exp e iat es exactamente 7 días (604800 segundos)
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(user)
        
        # Decodificar token
        payload = token_manager.decode_token(refresh_token)
        
        # Verificar que contiene exp e iat
        assert "exp" in payload, "Refresh token debe contener claim 'exp'"
        assert "iat" in payload, "Refresh token debe contener claim 'iat'"
        
        # Calcular diferencia en segundos
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        
        # La diferencia debe ser exactamente 7 días (604800 segundos)
        expected_diff = 7 * 24 * 60 * 60  # 604800 segundos
        actual_diff = exp_timestamp - iat_timestamp
        
        assert actual_diff == expected_diff, \
            f"Refresh token debe expirar en 7 días (604800s), pero expira en {actual_diff}s"


@pytest.mark.property_test
class TestProperty5_JWTTokenVerificationRoundTrip:
    """
    Property 5: JWT token verification round-trip
    
    **Validates: Requirements 1.5**
    
    Propiedad: FOR ANY valid JWT token, decoding it with the correct secret key
               MUST successfully extract the payload, and the signature MUST be valid.
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_access_token_round_trip_verification(self, user, secret_key):
        """
        Property: Un access token generado debe poder ser decodificado exitosamente.
        
        Este test valida que:
        1. El token puede ser decodificado sin errores
        2. El payload contiene los datos originales del usuario
        3. La firma es válida
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar access token
        access_token = token_manager.generate_access_token(user)
        
        # Decodificar token (esto valida la firma automáticamente)
        payload = token_manager.decode_token(access_token)
        
        # Verificar que el payload contiene los datos correctos
        assert payload["user_id"] == user.id, \
            f"Payload debe contener user_id correcto"
        assert payload["username"] == user.username, \
            f"Payload debe contener username correcto"
        
        # Verificar que los roles están presentes
        expected_roles = [role.name for role in user.roles]
        assert payload["roles"] == expected_roles, \
            f"Payload debe contener roles correctos"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_refresh_token_round_trip_verification(self, user, secret_key):
        """
        Property: Un refresh token generado debe poder ser decodificado exitosamente.
        
        Este test valida que:
        1. El token puede ser decodificado sin errores
        2. El payload contiene el user_id original
        3. La firma es válida
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(user)
        
        # Decodificar token (esto valida la firma automáticamente)
        payload = token_manager.decode_token(refresh_token)
        
        # Verificar que el payload contiene los datos correctos
        assert payload["user_id"] == user.id, \
            f"Payload debe contener user_id correcto"
        assert payload["token_type"] == "refresh", \
            f"Payload debe indicar token_type='refresh'"
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        user=valid_user(),
        secret_key=valid_secret_key(),
        wrong_secret_key=valid_secret_key()
    )
    def test_token_with_wrong_key_fails_verification(self, user, secret_key, wrong_secret_key):
        """
        Property: Un token decodificado con clave incorrecta debe fallar.
        
        Este test valida que la verificación de firma funciona correctamente.
        """
        # Asegurar que las claves son diferentes
        if secret_key == wrong_secret_key:
            return  # Skip this test case
        
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager con clave correcta
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar access token
        access_token = token_manager.generate_access_token(user)
        
        # Crear TokenManager con clave incorrecta
        wrong_token_manager = TokenManager(secret_key=wrong_secret_key)
        
        # Intentar decodificar con clave incorrecta debe fallar
        from jwt.exceptions import InvalidTokenError
        with pytest.raises(InvalidTokenError):
            wrong_token_manager.decode_token(access_token)


@pytest.mark.property_test
class TestProperty6_JWTPayloadCompleteness:
    """
    Property 6: JWT payload completeness
    
    **Validates: Requirements 1.6**
    
    Propiedad: FOR ANY generated JWT token, decoding it MUST reveal a payload
               containing all required fields: user_id, username, roles, exp, iat, and jti.
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_access_token_contains_all_required_fields(self, user, secret_key):
        """
        Property: El access token debe contener todos los campos requeridos.
        
        Este test valida que el payload contiene:
        - user_id
        - username
        - roles
        - exp
        - iat
        - jti
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar access token
        access_token = token_manager.generate_access_token(user)
        
        # Decodificar token
        payload = token_manager.decode_token(access_token)
        
        # Verificar que contiene todos los campos requeridos
        required_fields = ["user_id", "username", "roles", "exp", "iat", "jti"]
        
        for field in required_fields:
            assert field in payload, \
                f"Access token payload debe contener campo '{field}'"
        
        # Verificar tipos de datos
        assert isinstance(payload["user_id"], int), \
            "user_id debe ser un entero"
        assert isinstance(payload["username"], str), \
            "username debe ser un string"
        assert isinstance(payload["roles"], list), \
            "roles debe ser una lista"
        assert isinstance(payload["exp"], (int, float)), \
            "exp debe ser un timestamp numérico"
        assert isinstance(payload["iat"], (int, float)), \
            "iat debe ser un timestamp numérico"
        assert isinstance(payload["jti"], str), \
            "jti debe ser un string (UUID)"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_refresh_token_contains_required_fields(self, user, secret_key):
        """
        Property: El refresh token debe contener los campos requeridos.
        
        Este test valida que el payload contiene:
        - user_id
        - jti
        - exp
        - iat
        - token_type
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(user)
        
        # Decodificar token
        payload = token_manager.decode_token(refresh_token)
        
        # Verificar que contiene los campos requeridos para refresh token
        required_fields = ["user_id", "jti", "exp", "iat", "token_type"]
        
        for field in required_fields:
            assert field in payload, \
                f"Refresh token payload debe contener campo '{field}'"
        
        # Verificar tipos de datos
        assert isinstance(payload["user_id"], int), \
            "user_id debe ser un entero"
        assert isinstance(payload["jti"], str), \
            "jti debe ser un string (UUID)"
        assert isinstance(payload["exp"], (int, float)), \
            "exp debe ser un timestamp numérico"
        assert isinstance(payload["iat"], (int, float)), \
            "iat debe ser un timestamp numérico"
        assert payload["token_type"] == "refresh", \
            "token_type debe ser 'refresh'"


@pytest.mark.property_test
class TestProperty48_UniqueJWTID:
    """
    Property 48: Unique JWT ID
    
    **Validates: Requirements 20.6**
    
    Propiedad: FOR ANY generated JWT token, it MUST contain a unique jti (JWT ID)
               claim that is different from all other tokens.
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_access_tokens_have_unique_jti(self, user, secret_key):
        """
        Property: Múltiples access tokens deben tener JTI únicos.
        
        Este test valida que:
        1. Cada token tiene un jti diferente
        2. El jti es un UUID válido
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar múltiples access tokens
        num_tokens = 5
        tokens = [token_manager.generate_access_token(user) for _ in range(num_tokens)]
        
        # Decodificar todos los tokens y extraer jti
        jtis = []
        for token in tokens:
            payload = token_manager.decode_token(token)
            assert "jti" in payload, "Token debe contener jti"
            jtis.append(payload["jti"])
        
        # Verificar que todos los JTI son únicos
        unique_jtis = set(jtis)
        assert len(unique_jtis) == num_tokens, \
            f"Todos los {num_tokens} tokens deben tener JTI únicos, pero solo hay {len(unique_jtis)} únicos"
        
        # Verificar que cada jti parece ser un UUID válido (formato básico)
        import uuid
        for jti in jtis:
            try:
                uuid.UUID(jti)
            except ValueError:
                pytest.fail(f"jti '{jti}' no es un UUID válido")
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_refresh_tokens_have_unique_jti(self, user, secret_key):
        """
        Property: Múltiples refresh tokens deben tener JTI únicos.
        
        Este test valida que:
        1. Cada token tiene un jti diferente
        2. El jti es un UUID válido
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar múltiples refresh tokens
        num_tokens = 5
        tokens = [token_manager.generate_refresh_token(user) for _ in range(num_tokens)]
        
        # Decodificar todos los tokens y extraer jti
        jtis = []
        for token in tokens:
            payload = token_manager.decode_token(token)
            assert "jti" in payload, "Token debe contener jti"
            jtis.append(payload["jti"])
        
        # Verificar que todos los JTI son únicos
        unique_jtis = set(jtis)
        assert len(unique_jtis) == num_tokens, \
            f"Todos los {num_tokens} tokens deben tener JTI únicos, pero solo hay {len(unique_jtis)} únicos"
        
        # Verificar que cada jti parece ser un UUID válido
        import uuid
        for jti in jtis:
            try:
                uuid.UUID(jti)
            except ValueError:
                pytest.fail(f"jti '{jti}' no es un UUID válido")
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(user=valid_user(), secret_key=valid_secret_key())
    def test_access_and_refresh_tokens_have_different_jti(self, user, secret_key):
        """
        Property: Access y refresh tokens generados juntos deben tener JTI diferentes.
        
        Este test valida que incluso tokens generados simultáneamente tienen JTI únicos.
        """
        # Configurar variable de entorno
        os.environ["JWT_SECRET_KEY"] = secret_key
        
        # Crear TokenManager
        token_manager = TokenManager(secret_key=secret_key)
        
        # Generar ambos tokens
        tokens = token_manager.generate_tokens(user)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # Decodificar ambos tokens
        access_payload = token_manager.decode_token(access_token)
        refresh_payload = token_manager.decode_token(refresh_token)
        
        # Verificar que tienen JTI diferentes
        access_jti = access_payload["jti"]
        refresh_jti = refresh_payload["jti"]
        
        assert access_jti != refresh_jti, \
            "Access token y refresh token deben tener JTI diferentes"
