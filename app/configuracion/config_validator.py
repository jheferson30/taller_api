"""
Validador de configuración del sistema.

Este módulo valida que todas las variables de entorno requeridas estén presentes
y tengan valores válidos al iniciar la aplicación.
"""

import os
import sys
from typing import List, Tuple


class ConfigValidationError(Exception):
    """Excepción lanzada cuando la configuración es inválida."""
    pass


def validate_config() -> None:
    """
    Valida la configuración del sistema.
    
    Verifica que todas las variables de entorno requeridas estén presentes
    y tengan valores válidos. Si la configuración es inválida, lanza
    ConfigValidationError y termina la aplicación.
    
    Raises:
        ConfigValidationError: Si la configuración es inválida
    """
    errors: List[str] = []
    
    # Validar variables requeridas
    required_vars = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            errors.append(f"Variable de entorno requerida no encontrada: {var}")
        elif not value.strip():
            errors.append(f"Variable de entorno vacía: {var}")
    
    # Validar JWT_SECRET_KEY tiene al menos 32 caracteres
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if jwt_secret and len(jwt_secret) < 32:
        errors.append(
            f"JWT_SECRET_KEY debe tener al menos 32 caracteres (actual: {len(jwt_secret)}). "
            "Generar con: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    
    # Validar JWT_SECRET_KEY no es el valor por defecto
    if jwt_secret and "CAMBIAR_EN_PRODUCCION" in jwt_secret:
        errors.append(
            "JWT_SECRET_KEY contiene el valor por defecto. "
            "DEBE cambiarse en producción por seguridad."
        )
    
    # Validar ENVIRONMENT es válido
    environment = os.getenv("ENVIRONMENT", "development")
    valid_environments = ["development", "production"]
    if environment not in valid_environments:
        errors.append(
            f"ENVIRONMENT debe ser uno de {valid_environments} (actual: {environment})"
        )
    
    # Validar BCRYPT_COST_FACTOR es un número válido
    bcrypt_cost = os.getenv("BCRYPT_COST_FACTOR", "12")
    try:
        cost_int = int(bcrypt_cost)
        if cost_int < 4 or cost_int > 31:
            errors.append(
                f"BCRYPT_COST_FACTOR debe estar entre 4 y 31 (actual: {cost_int})"
            )
    except ValueError:
        errors.append(
            f"BCRYPT_COST_FACTOR debe ser un número entero (actual: {bcrypt_cost})"
        )
    
    # Validar JWT_ACCESS_TOKEN_EXPIRE_MINUTES es un número positivo
    access_expire = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    try:
        expire_int = int(access_expire)
        if expire_int <= 0:
            errors.append(
                f"JWT_ACCESS_TOKEN_EXPIRE_MINUTES debe ser positivo (actual: {expire_int})"
            )
    except ValueError:
        errors.append(
            f"JWT_ACCESS_TOKEN_EXPIRE_MINUTES debe ser un número entero (actual: {access_expire})"
        )
    
    # Validar JWT_REFRESH_TOKEN_EXPIRE_DAYS es un número positivo
    refresh_expire = os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    try:
        expire_int = int(refresh_expire)
        if expire_int <= 0:
            errors.append(
                f"JWT_REFRESH_TOKEN_EXPIRE_DAYS debe ser positivo (actual: {expire_int})"
            )
    except ValueError:
        errors.append(
            f"JWT_REFRESH_TOKEN_EXPIRE_DAYS debe ser un número entero (actual: {refresh_expire})"
        )
    
    # Validar PASSWORD_MIN_LENGTH es un número válido
    min_length = os.getenv("PASSWORD_MIN_LENGTH", "8")
    try:
        length_int = int(min_length)
        if length_int < 6:
            errors.append(
                f"PASSWORD_MIN_LENGTH debe ser al menos 6 (actual: {length_int})"
            )
    except ValueError:
        errors.append(
            f"PASSWORD_MIN_LENGTH debe ser un número entero (actual: {min_length})"
        )
    
    # Advertencias (no errores críticos)
    warnings: List[str] = []
    
    # Advertir si ENVIRONMENT es production pero JWT_SECRET_KEY parece débil
    if environment == "production":
        if jwt_secret and len(jwt_secret) < 64:
            warnings.append(
                f"En producción se recomienda JWT_SECRET_KEY de al menos 64 caracteres "
                f"(actual: {len(jwt_secret)})"
            )
        
        # Advertir si ENABLE_LEGACY_AUTH está habilitado en producción
        legacy_auth = os.getenv("ENABLE_LEGACY_AUTH", "false").lower()
        if legacy_auth in ["true", "1", "yes"]:
            warnings.append(
                "ENABLE_LEGACY_AUTH está habilitado en producción. "
                "Considere deshabilitarlo después del período de transición."
            )
    
    # Mostrar advertencias
    if warnings:
        print("\n⚠️  ADVERTENCIAS DE CONFIGURACIÓN:")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    
    # Si hay errores, fallar rápido
    if errors:
        print("\n❌ ERRORES DE CONFIGURACIÓN:")
        for error in errors:
            print(f"  - {error}")
        print("\nLa aplicación no puede iniciar con configuración inválida.")
        print("Por favor corrija los errores en el archivo .env\n")
        raise ConfigValidationError(
            f"Configuración inválida: {len(errors)} error(es) encontrado(s)"
        )
    
    # Configuración válida
    print("✅ Configuración validada correctamente")


def get_config_summary() -> List[Tuple[str, str]]:
    """
    Retorna un resumen de la configuración actual.
    
    Returns:
        Lista de tuplas (nombre_variable, valor) con la configuración actual.
        Los valores sensibles son enmascarados.
    """
    config_vars = [
        ("ENVIRONMENT", os.getenv("ENVIRONMENT", "development")),
        ("DATABASE_URL", _mask_sensitive(os.getenv("DATABASE_URL", ""))),
        ("JWT_SECRET_KEY", _mask_sensitive(os.getenv("JWT_SECRET_KEY", ""))),
        ("JWT_ALGORITHM", os.getenv("JWT_ALGORITHM", "HS256")),
        ("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
        ("JWT_REFRESH_TOKEN_EXPIRE_DAYS", os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        ("BCRYPT_COST_FACTOR", os.getenv("BCRYPT_COST_FACTOR", "12")),
        ("PASSWORD_MIN_LENGTH", os.getenv("PASSWORD_MIN_LENGTH", "8")),
        ("ENABLE_LEGACY_AUTH", os.getenv("ENABLE_LEGACY_AUTH", "true")),
        ("RATE_LIMIT_AUTH_PER_MINUTE", os.getenv("RATE_LIMIT_AUTH_PER_MINUTE", "5")),
        ("RATE_LIMIT_CREATE_PER_MINUTE", os.getenv("RATE_LIMIT_CREATE_PER_MINUTE", "30")),
        ("RATE_LIMIT_READ_PER_MINUTE", os.getenv("RATE_LIMIT_READ_PER_MINUTE", "100")),
    ]
    
    return config_vars


def _mask_sensitive(value: str) -> str:
    """
    Enmascara valores sensibles para logging seguro.
    
    Args:
        value: Valor a enmascarar
        
    Returns:
        Valor enmascarado mostrando solo primeros y últimos caracteres
    """
    if not value or len(value) < 8:
        return "***"
    
    return f"{value[:4]}...{value[-4:]}"


if __name__ == "__main__":
    """Permite ejecutar validación desde línea de comandos."""
    # Cargar variables de entorno desde .env
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        validate_config()
        print("\n📋 Resumen de configuración:")
        for key, value in get_config_summary():
            print(f"  {key}: {value}")
    except ConfigValidationError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
