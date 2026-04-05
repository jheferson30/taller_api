"""
Password hashing and verification using bcrypt.

This module provides secure password hashing with bcrypt (cost factor 12)
and timing-safe password verification.
"""

import bcrypt


class PasswordHasher:
    """
    Maneja hashing y verificación de contraseñas con bcrypt.
    
    Utiliza bcrypt con cost factor 12 para proporcionar seguridad robusta
    contra ataques de fuerza bruta. Cada contraseña se hashea con un salt
    único generado automáticamente.
    """
    
    def __init__(self, cost_factor: int = 12):
        """
        Inicializa el hasher con el cost factor especificado.
        
        Args:
            cost_factor: Factor de costo de bcrypt (default: 12).
                        Valores más altos = más seguro pero más lento.
        """
        self.cost_factor = cost_factor
    
    def hash_password(self, password: str) -> str:
        """
        Hashea una contraseña con bcrypt (cost factor 12).
        Genera un salt único y aleatorio automáticamente.
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            Hash de la contraseña (incluye salt y algoritmo)
            
        Example:
            >>> hasher = PasswordHasher()
            >>> hash_value = hasher.hash_password("mi_contraseña_segura")
            >>> print(hash_value)
            $2b$12$...
        """
        # Convertir la contraseña a bytes
        password_bytes = password.encode('utf-8')
        
        # Generar salt con el cost factor especificado
        salt = bcrypt.gensalt(rounds=self.cost_factor)
        
        # Hashear la contraseña con el salt
        password_hash = bcrypt.hashpw(password_bytes, salt)
        
        # Retornar como string
        return password_hash.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verifica una contraseña contra su hash.
        Usa timing-safe comparison para prevenir timing attacks.
        
        Args:
            password: Contraseña en texto plano
            password_hash: Hash almacenado
            
        Returns:
            True si la contraseña es correcta, False en caso contrario
            
        Example:
            >>> hasher = PasswordHasher()
            >>> hash_value = hasher.hash_password("mi_contraseña")
            >>> hasher.verify_password("mi_contraseña", hash_value)
            True
            >>> hasher.verify_password("contraseña_incorrecta", hash_value)
            False
        """
        # Convertir a bytes
        password_bytes = password.encode('utf-8')
        password_hash_bytes = password_hash.encode('utf-8')
        
        # bcrypt.checkpw usa timing-safe comparison internamente
        return bcrypt.checkpw(password_bytes, password_hash_bytes)
