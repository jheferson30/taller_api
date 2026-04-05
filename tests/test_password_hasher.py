"""
Unit tests for PasswordHasher class.

Tests password hashing and verification functionality with bcrypt.
"""

import pytest
from app.seguridad.password_hasher import PasswordHasher


class TestPasswordHasher:
    """Test suite for PasswordHasher"""
    
    def test_hash_password_bcrypt(self):
        """Test that password is hashed with bcrypt"""
        hasher = PasswordHasher()
        password = "test_password_123"
        
        password_hash = hasher.hash_password(password)
        
        # bcrypt hashes start with $2b$ (bcrypt identifier)
        assert password_hash.startswith("$2b$")
        # bcrypt hash should include cost factor (12)
        assert "$12$" in password_hash
        # Hash should be different from original password
        assert password_hash != password
    
    def test_verify_password_correct(self):
        """Test that correct password returns True"""
        hasher = PasswordHasher()
        password = "correct_password_456"
        
        password_hash = hasher.hash_password(password)
        result = hasher.verify_password(password, password_hash)
        
        assert result is True
    
    def test_verify_password_incorrect(self):
        """Test that incorrect password returns False"""
        hasher = PasswordHasher()
        password = "correct_password"
        wrong_password = "wrong_password"
        
        password_hash = hasher.hash_password(password)
        result = hasher.verify_password(wrong_password, password_hash)
        
        assert result is False
    
    def test_unique_salt_generation(self):
        """Test that hashing the same password twice produces different hashes"""
        hasher = PasswordHasher()
        password = "same_password"
        
        hash1 = hasher.hash_password(password)
        hash2 = hasher.hash_password(password)
        
        # Hashes should be different due to unique salt
        assert hash1 != hash2
        # But both should verify correctly
        assert hasher.verify_password(password, hash1)
        assert hasher.verify_password(password, hash2)
    
    def test_hash_password_with_special_characters(self):
        """Test hashing password with special characters"""
        hasher = PasswordHasher()
        password = "P@ssw0rd!#$%^&*()"
        
        password_hash = hasher.hash_password(password)
        
        assert hasher.verify_password(password, password_hash)
    
    def test_hash_password_with_unicode(self):
        """Test hashing password with unicode characters"""
        hasher = PasswordHasher()
        password = "contraseña_española_ñ_á_é"
        
        password_hash = hasher.hash_password(password)
        
        assert hasher.verify_password(password, password_hash)
    
    def test_cost_factor_configuration(self):
        """Test that cost factor can be configured"""
        hasher = PasswordHasher(cost_factor=10)
        password = "test_password"
        
        password_hash = hasher.hash_password(password)
        
        # Should use cost factor 10
        assert "$10$" in password_hash
        assert hasher.verify_password(password, password_hash)
    
    def test_empty_password(self):
        """Test hashing empty password"""
        hasher = PasswordHasher()
        password = ""
        
        password_hash = hasher.hash_password(password)
        
        assert hasher.verify_password(password, password_hash)
        assert not hasher.verify_password("not_empty", password_hash)
    
    def test_long_password(self):
        """Test hashing long password (up to 72 bytes - bcrypt limit)"""
        hasher = PasswordHasher()
        password = "a" * 72  # 72 character password (bcrypt max)
        
        password_hash = hasher.hash_password(password)
        
        assert hasher.verify_password(password, password_hash)
    
    def test_password_exceeds_bcrypt_limit(self):
        """Test that passwords longer than 72 bytes raise ValueError"""
        hasher = PasswordHasher()
        password = "a" * 73  # Exceeds bcrypt 72-byte limit
        
        with pytest.raises(ValueError, match="password cannot be longer than 72 bytes"):
            hasher.hash_password(password)
