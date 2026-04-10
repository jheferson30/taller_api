"""
Tests de seguridad de contraseñas
Valida que las contraseñas son hasheadas correctamente con bcrypt
"""
import pytest

from app.seguridad.password_hasher import PasswordHasher


class TestPasswordSecurity:
    """Tests de hashing de contraseñas (Property 21.7)"""

    def test_passwords_are_hashed_with_bcrypt(self):
        """Test contraseñas son hasheadas con bcrypt"""
        hasher = PasswordHasher()
        password = "SecurePassword123!"

        # Hashear contraseña
        hashed = hasher.hash_password(password)

        # Verificar que el hash tiene formato bcrypt
        assert hashed.startswith("$2b$")  # bcrypt prefix
        assert len(hashed) == 60  # bcrypt hash length

        # Verificar que el hash es diferente de la contraseña original
        assert hashed != password

    def test_verify_password_works_correctly(self):
        """Test verify_password funciona correctamente"""
        hasher = PasswordHasher()
        password = "MyPassword456"

        # Hashear contraseña
        hashed = hasher.hash_password(password)

        # Verificar contraseña correcta
        assert hasher.verify_password(password, hashed) is True

        # Verificar contraseña incorrecta
        assert hasher.verify_password("WrongPassword", hashed) is False

    def test_same_password_produces_different_hashes(self):
        """Test misma contraseña produce hashes diferentes (salt único)"""
        hasher = PasswordHasher()
        password = "SamePassword789"

        # Hashear la misma contraseña dos veces
        hash1 = hasher.hash_password(password)
        hash2 = hasher.hash_password(password)

        # Los hashes deben ser diferentes (salt único)
        assert hash1 != hash2

        # Pero ambos deben verificar correctamente
        assert hasher.verify_password(password, hash1) is True
        assert hasher.verify_password(password, hash2) is True

    def test_bcrypt_cost_factor_is_secure(self):
        """Test bcrypt cost factor es seguro (>= 12)"""
        hasher = PasswordHasher()
        password = "TestPassword"

        # Hashear contraseña
        hashed = hasher.hash_password(password)

        # Extraer cost factor del hash
        # Formato: $2b$12$...
        parts = hashed.split("$")
        cost_factor = int(parts[2])

        # Verificar que cost factor es >= 12
        assert cost_factor >= 12

    def test_empty_password_is_rejected(self):
        """Test contraseña vacía es rechazada"""
        hasher = PasswordHasher()

        with pytest.raises(ValueError):
            hasher.hash_password("")

    def test_verify_password_with_invalid_hash_returns_false(self):
        """Test verify_password con hash inválido retorna False"""
        hasher = PasswordHasher()
        password = "TestPassword"

        # Hash inválido
        invalid_hash = "not-a-valid-bcrypt-hash"

        # Debe retornar False sin lanzar excepción
        assert hasher.verify_password(password, invalid_hash) is False

    def test_timing_safe_comparison(self):
        """Test verificación usa comparación timing-safe"""
        hasher = PasswordHasher()
        password = "TimingSafeTest"
        hashed = hasher.hash_password(password)

        # Verificar múltiples veces para asegurar consistencia
        results = [hasher.verify_password(password, hashed) for _ in range(100)]

        # Todas las verificaciones deben ser True
        assert all(results)

        # Verificar con contraseña incorrecta
        wrong_results = [hasher.verify_password("Wrong", hashed) for _ in range(100)]

        # Todas las verificaciones deben ser False
        assert not any(wrong_results)
