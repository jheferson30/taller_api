"""
Property-based tests para PasswordHasher.

Este módulo implementa property tests usando Hypothesis para validar:
- Property 1: Password hashing produces verifiable hashes
- Property 2: Unique salt generation

Valida Requirements: 1.1, 1.2

# Feature: mejoras-seguridad-jwt-auditoria, Property 1: Password hashing produces verifiable hashes
# Feature: mejoras-seguridad-jwt-auditoria, Property 2: Unique salt generation
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from app.seguridad.password_hasher import PasswordHasher


# Estrategias de Hypothesis
@st.composite
def valid_password(draw):
    """
    Genera passwords válidos para testing.
    
    Bcrypt tiene un límite de 72 bytes, así que generamos passwords
    que respeten este límite.
    """
    return draw(st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs", "Cc"),  # Excluir caracteres de control
            min_codepoint=32,  # Espacio en adelante
            max_codepoint=126  # Hasta ~
        ),
        min_size=1,
        max_size=50  # Bien por debajo del límite de 72 bytes
    ))


@pytest.mark.property_test
class TestProperty1_PasswordHashingProducesVerifiableHashes:
    """
    Property 1: Password hashing produces verifiable hashes
    
    **Validates: Requirements 1.1**
    
    Propiedad: FOR ANY password string, WHEN hashed by PasswordHasher,
               THEN the resulting hash MUST be verifiable with the same password
               using the verify_password method.
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(password=valid_password())
    def test_hashed_password_is_verifiable(self, password):
        """
        Property: Cualquier password hasheado debe ser verificable con el mismo password.
        
        Este test valida que:
        1. El hash se genera correctamente
        2. El hash puede ser verificado con el password original
        3. El hash NO verifica con passwords diferentes
        """
        # Create hasher with low cost factor for faster tests
        password_hasher = PasswordHasher(cost_factor=4)
        
        # Hash the password
        password_hash = password_hasher.hash_password(password)
        
        # Verify that the hash is verifiable with the same password
        assert password_hasher.verify_password(password, password_hash), \
            f"Password hash should be verifiable with original password"
        
        # Verify that the hash is a valid bcrypt hash
        assert password_hash.startswith("$2b$"), \
            f"Hash should be a valid bcrypt hash starting with $2b$"
        
        # Verify that the hash is different from the original password
        assert password_hash != password, \
            f"Hash should be different from original password"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        password=valid_password(),
        wrong_password=valid_password()
    )
    def test_hash_rejects_incorrect_passwords(self, password, wrong_password):
        """
        Property: Un hash debe rechazar passwords incorrectos.
        
        Valida que verify_password retorna False para passwords diferentes.
        """
        # Ensure passwords are different
        if password == wrong_password:
            return  # Skip this test case
        
        # Create hasher
        password_hasher = PasswordHasher(cost_factor=4)
        
        # Hash the correct password
        password_hash = password_hasher.hash_password(password)
        
        # Verify that wrong password is rejected
        assert not password_hasher.verify_password(wrong_password, password_hash), \
            f"Hash should reject incorrect password"
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(password=valid_password())
    def test_hash_format_is_consistent(self, password):
        """
        Property: Todos los hashes deben tener formato bcrypt consistente.
        
        Valida que el formato del hash es correcto y contiene el cost factor.
        """
        # Create hasher
        password_hasher = PasswordHasher(cost_factor=4)
        
        password_hash = password_hasher.hash_password(password)
        
        # Verify bcrypt format
        assert password_hash.startswith("$2b$"), \
            f"Hash should start with bcrypt identifier $2b$"
        
        # Verify cost factor is included (bcrypt uses 2-digit format, so 4 becomes 04)
        assert "$04$" in password_hash or "$4$" in password_hash, \
            f"Hash should include cost factor $04$ or $4$"
        
        # Verify hash length (bcrypt hashes are 60 characters)
        assert len(password_hash) == 60, \
            f"Bcrypt hash should be 60 characters, got {len(password_hash)}"


@pytest.mark.property_test
class TestProperty2_UniqueSaltGeneration:
    """
    Property 2: Unique salt generation
    
    **Validates: Requirements 1.2**
    
    Propiedad: FOR ANY password string, hashing it multiple times
               MUST produce different hash values due to unique salt generation.
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(password=valid_password())
    def test_same_password_produces_different_hashes(self, password):
        """
        Property: Hashear el mismo password múltiples veces produce hashes diferentes.
        
        Este test valida que:
        1. Cada hash usa un salt único
        2. Los hashes son diferentes entre sí
        3. Todos los hashes verifican correctamente con el password original
        """
        # Create hasher
        password_hasher = PasswordHasher(cost_factor=4)
        
        # Hash the same password twice
        hash1 = password_hasher.hash_password(password)
        hash2 = password_hasher.hash_password(password)
        
        # Verify that hashes are different (unique salt)
        assert hash1 != hash2, \
            f"Hashing the same password twice should produce different hashes due to unique salt"
        
        # Verify that both hashes verify correctly
        assert password_hasher.verify_password(password, hash1), \
            f"First hash should verify with original password"
        assert password_hasher.verify_password(password, hash2), \
            f"Second hash should verify with original password"
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(password=valid_password())
    def test_multiple_hashes_are_all_unique(self, password):
        """
        Property: Múltiples hashes del mismo password son todos únicos.
        
        Valida que generar N hashes del mismo password produce N valores diferentes.
        """
        # Create hasher
        password_hasher = PasswordHasher(cost_factor=4)
        
        # Generate multiple hashes
        num_hashes = 5
        hashes = [password_hasher.hash_password(password) for _ in range(num_hashes)]
        
        # Verify all hashes are unique
        unique_hashes = set(hashes)
        assert len(unique_hashes) == num_hashes, \
            f"All {num_hashes} hashes should be unique, got {len(unique_hashes)} unique values"
        
        # Verify all hashes verify correctly
        for i, hash_value in enumerate(hashes):
            assert password_hasher.verify_password(password, hash_value), \
                f"Hash {i+1} should verify with original password"
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        password1=valid_password(),
        password2=valid_password()
    )
    def test_different_passwords_produce_different_hashes(self, password1, password2):
        """
        Property: Passwords diferentes producen hashes diferentes.
        
        Valida que el sistema no produce colisiones para passwords diferentes.
        """
        # Ensure passwords are different
        if password1 == password2:
            return  # Skip this test case
        
        # Create hasher
        password_hasher = PasswordHasher(cost_factor=4)
        
        # Hash both passwords
        hash1 = password_hasher.hash_password(password1)
        hash2 = password_hasher.hash_password(password2)
        
        # Verify hashes are different
        assert hash1 != hash2, \
            f"Different passwords should produce different hashes"
        
        # Verify each hash only verifies with its own password
        assert password_hasher.verify_password(password1, hash1), \
            f"Hash1 should verify with password1"
        assert not password_hasher.verify_password(password1, hash2), \
            f"Hash2 should not verify with password1"
        assert password_hasher.verify_password(password2, hash2), \
            f"Hash2 should verify with password2"
        assert not password_hasher.verify_password(password2, hash1), \
            f"Hash1 should not verify with password2"
