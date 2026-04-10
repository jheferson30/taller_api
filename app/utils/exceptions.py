"""
Excepciones de dominio personalizadas para el sistema.

Este módulo define excepciones específicas del dominio que representan
errores de negocio y validación. Estas excepciones son capturadas por
el global exception handler y convertidas a respuestas HTTP apropiadas.
"""


class DomainException(Exception):
    """Excepción base para todas las excepciones de dominio."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InvalidCredentialsError(DomainException):
    """
    Se lanza cuando las credenciales de autenticación son inválidas.

    Esto incluye:
    - Usuario no existe
    - Contraseña incorrecta
    - Token inválido o expirado

    Nota: Los mensajes deben ser genéricos para prevenir enumeración de usuarios.
    """

    pass


class InsufficientPermissionsError(DomainException):
    """
    Se lanza cuando un usuario no tiene permisos suficientes para realizar una acción.

    Esto incluye:
    - Usuario no tiene el rol requerido
    - Usuario intenta acceder a recursos de otro usuario
    - Usuario intenta realizar operación administrativa sin permisos
    """

    pass


class ValidationError(DomainException):
    """
    Se lanza cuando los datos de entrada no cumplen con las reglas de validación.

    Esto incluye:
    - Formato de email inválido
    - Contraseña no cumple requisitos de complejidad
    - Campos requeridos faltantes
    - Valores fuera de rango permitido
    """

    pass


class ResourceNotFoundError(DomainException):
    """
    Se lanza cuando un recurso solicitado no existe.

    Esto incluye:
    - Usuario no encontrado
    - Ticket no encontrado
    - Cita no encontrada
    - Cualquier entidad que no existe en la base de datos
    """

    pass


class DuplicateError(DomainException):
    """
    Se lanza cuando se intenta crear un recurso que ya existe.

    Esto incluye:
    - Username duplicado
    - Email duplicado
    - Cualquier violación de constraint UNIQUE
    """

    pass


class RateLimitExceededError(DomainException):
    """
    Se lanza cuando se excede el límite de rate limiting.

    Esto incluye:
    - Demasiados intentos de login
    - Demasiadas solicitudes de password reset
    - Cualquier límite de tasa excedido
    """

    pass


class TokenBlacklistedError(DomainException):
    """
    Se lanza cuando se intenta usar un token que está en la lista negra.

    Esto incluye:
    - Token de usuario que hizo logout
    - Token de usuario desactivado
    - Token revocado manualmente
    """

    pass


class SecurityAlertError(DomainException):
    """
    Se lanza cuando se detecta un evento de seguridad sospechoso.

    Esto incluye:
    - Intento de brute force detectado
    - Intento de reutilización de token
    - Abuso de password reset
    """

    pass


class ConflictError(DomainException):
    """
    Se lanza cuando hay un conflicto en la sincronización de datos.

    Esto incluye:
    - Recurso modificado en servidor durante operación offline
    - Conflicto de versión en sincronización
    """

    pass


class ConfigurationError(DomainException):
    """
    Se lanza cuando hay un error en la configuración del sistema.

    Esto incluye:
    - Variables de entorno faltantes o inválidas
    - Configuración de seguridad incorrecta
    """

    pass
