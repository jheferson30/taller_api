"""
CSRF Middleware

Middleware que valida tokens CSRF en todos los endpoints de escritura no exentos.
Implementado usando BaseHTTPMiddleware para garantizar cobertura total sin modificar
ningún route handler existente.

El middleware:
- Valida tokens CSRF solo en métodos de escritura (POST, PUT, PATCH, DELETE)
- Excluye rutas públicas y webhooks externos de la validación
- Lee el token del header X-CSRF-Token
- Retorna HTTP 403 si el token falta o es inválido
- Salta validación para OPTIONS (preflight CORS)

Integración con fastapi-csrf-protect:
El middleware usa CsrfProtect configurado en main.py para validar tokens.
La configuración incluye cookie_samesite=strict, cookie_secure (en producción),
y cookie_httponly=True para máxima seguridad.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# Rutas exentas de validación CSRF
# Incluye endpoints públicos, de autenticación y webhooks externos
CSRF_EXEMPT_PATHS: frozenset[str] = frozenset({
    "/auth/login",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/forgot-password-by-username",
    "/auth/reset-password",
    "/health",
    "/info",
    "/info/conexion-qr",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/whatsapp/webhook",
})

# Métodos HTTP que requieren validación CSRF
# Solo métodos de escritura que modifican estado del sistema
CSRF_WRITE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Valida tokens CSRF en todos los endpoints de escritura no exentos.

    Lee el token del header X-CSRF-Token y lo valida usando fastapi-csrf-protect.
    Retorna HTTP 403 con error "csrf_error" si el token falta o es inválido.

    El middleware se ejecuta después de AuthMiddleware en la cadena de middlewares,
    garantizando que la validación CSRF ocurre antes de llegar al route handler.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Intercepta requests y valida CSRF en métodos de escritura no exentos.

        Args:
            request: Request de FastAPI
            call_next: Siguiente middleware/handler

        Returns:
            Response del handler o error 403 si CSRF es inválido
        """
        # Solo validar métodos de escritura
        if request.method not in CSRF_WRITE_METHODS:
            return await call_next(request)

        # Saltar validación para OPTIONS (preflight CORS)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Obtener path de la request
        path = request.url.path

        # Saltar rutas exentas
        if path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        # Saltar rutas de documentación (pueden tener prefijos)
        if path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Validar que el header X-CSRF-Token esté presente
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            return JSONResponse(
                status_code=403,
                content={"error": "csrf_error", "message": "CSRF token missing or invalid"},
            )

        # Validar token CSRF usando fastapi-csrf-protect
        try:
            from fastapi_csrf_protect import CsrfProtect

            csrf = CsrfProtect()
            await csrf.validate_csrf(request)
        except Exception:
            # Cualquier excepción en la validación significa token inválido
            return JSONResponse(
                status_code=403,
                content={"error": "csrf_error", "message": "CSRF token missing or invalid"},
            )

        # Token válido, continuar con el request
        return await call_next(request)
