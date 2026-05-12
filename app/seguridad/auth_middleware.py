"""
Auth Middleware y decoradores para protección de endpoints con JWT.

Este módulo implementa:
- AuthMiddleware: Middleware de FastAPI que valida tokens JWT en cada request
- @require_auth: Decorador para endpoints que requieren autenticación
- @require_role: Decorador para endpoints que requieren roles específicos
"""

from collections.abc import Callable
from functools import wraps

import os

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import joinedload
from starlette.middleware.base import BaseHTTPMiddleware

from app.modelos.taller import EstadoTaller, Taller
from app.modelos.user import User
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.seguridad.token_manager import TokenManager


def _cors_error_response(request: Request, status_code: int, detail: str) -> JSONResponse:
    """
    Construye un JSONResponse de error con los headers CORS necesarios.

    El AuthMiddleware está fuera del CORSMiddleware en la cadena, por lo que
    las respuestas de error que genera no pasan por CORS. Sin estos headers,
    el browser bloquea la respuesta y axios reporta 'Network Error'.
    """
    origin = request.headers.get("origin", "")
    allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "")
    allowed_origins = (
        [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]
        if allowed_origins_raw and allowed_origins_raw != "*"
        else []
    )

    headers = {}
    if origin and (not allowed_origins or origin in allowed_origins):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=headers,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware de FastAPI para validar tokens JWT en requests.

    Intercepta todos los requests y valida autenticación JWT:
    1. Extrae token del header Authorization: Bearer <token>
    2. Decodifica y valida el token usando TokenManager
    3. Verifica que el jti no esté en blacklist
    4. Obtiene el usuario completo con roles
    5. Inyecta user context en request.state.user
    6. Continúa con el request

    Si el token es inválido, expirado o falta, retorna 401.
    """

    def __init__(self, app, token_manager=None, db_session_factory=None):
        """
        Inicializa el middleware.

        Args:
            app: Aplicación FastAPI
            token_manager: TokenManager opcional (para testing)
            db_session_factory: Factory de sesión de BD opcional (para testing)
        """
        super().__init__(app)
        self.token_manager = token_manager or TokenManager()
        self.db_session_factory = db_session_factory

    async def dispatch(self, request: Request, call_next):
        """
        Intercepta requests y valida autenticación JWT.

        Args:
            request: Request de FastAPI
            call_next: Siguiente middleware/handler

        Returns:
            Response del handler o error 401
        """
        # Permitir todas las peticiones OPTIONS (CORS preflight) sin autenticación
        if request.method == "OPTIONS":
            print(f"[AuthMiddleware] OPTIONS request to {request.url.path} - allowing without auth")
            return await call_next(request)

        # Rutas públicas que no requieren autenticación
        public_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/info",
            "/info/conexion-qr",
            "/assets",
            "/auth/login",
            "/auth/refresh",
            "/auth/forgot-password",
            "/auth/reset-password",
        ]

        # Verificar si la ruta es pública
        path = request.url.path

        # Verificar ruta raíz exacta
        if path == "/":
            return await call_next(request)

        # Verificar otras rutas públicas con startswith
        if any(path.startswith(public_path) for public_path in public_paths):
            return await call_next(request)

        # Extraer token del header Authorization
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            # No hay header de autorización, continuar sin user context
            # Los decoradores @require_auth se encargarán de validar
            request.state.user = None
            request.state.taller_id = None
            return await call_next(request)

        # Validar formato "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return _cors_error_response(
                request,
                status.HTTP_401_UNAUTHORIZED,
                "Invalid authorization header format. Expected 'Bearer <token>'",
            )

        token = parts[1]

        try:
            # Decodificar y validar token
            payload = self.token_manager.decode_token(token)

            # Extraer jti del payload
            jti = payload.get("jti")
            user_id = payload.get("user_id")

            if not jti or not user_id:
                return _cors_error_response(
                    request,
                    status.HTTP_401_UNAUTHORIZED,
                    "Invalid token payload",
                )

            # Obtener sesión de base de datos
            # Nota: En middleware, necesitamos crear la sesión manualmente
            if self.db_session_factory:
                # Usar factory de testing (no cerrar la sesión en tests)
                db = self.db_session_factory()
                should_close = False
            else:
                # Usar factory de producción
                from app.configuracion.base_datos import SessionLocal

                db = SessionLocal()
                should_close = True

            try:
                # Verificar que el token no esté en blacklist
                blacklist_repo = TokenBlacklistRepository(db)
                if blacklist_repo.is_blacklisted(jti):
                    return _cors_error_response(
                        request,
                        status.HTTP_401_UNAUTHORIZED,
                        "Token has been revoked",
                    )

                # Obtener usuario completo con roles
                # Usar joinedload para cargar roles en una sola query
                user = (
                    db.query(User)
                    .options(joinedload(User.roles))
                    .filter(User.id == user_id)
                    .first()
                )

                if not user:
                    return _cors_error_response(
                        request,
                        status.HTTP_401_UNAUTHORIZED,
                        "User not found",
                    )

                if not user.is_active:
                    return _cors_error_response(
                        request,
                        status.HTTP_401_UNAUTHORIZED,
                        "User account is inactive",
                    )

                # Verificar que el taller no esté suspendido o cancelado
                # SUPER_ADMIN tiene taller_id=None, se salta esta verificación
                taller_id_from_token = payload.get("taller_id")
                if taller_id_from_token is not None:
                    taller = (
                        db.query(Taller)
                        .filter(Taller.id == taller_id_from_token)
                        .first()
                    )
                    if taller and taller.estado in (EstadoTaller.SUSPENDIDO, EstadoTaller.CANCELADO):
                        mensaje = (
                            "Tu taller está suspendido. Contacta al administrador de la plataforma."
                            if taller.estado == EstadoTaller.SUSPENDIDO
                            else "Tu taller ha sido cancelado. Contacta al administrador de la plataforma."
                        )
                        return _cors_error_response(
                            request,
                            status.HTTP_403_FORBIDDEN,
                            mensaje,
                        )

                # Inyectar user context en request.state
                request.state.user = user
                # Inyectar taller_id desde el JWT payload para RLS
                request.state.taller_id = payload.get("taller_id")

            finally:
                if should_close:
                    db.close()

        except ExpiredSignatureError:
            return _cors_error_response(
                request, status.HTTP_401_UNAUTHORIZED, "Token has expired"
            )
        except InvalidTokenError as e:
            return _cors_error_response(
                request, status.HTTP_401_UNAUTHORIZED, f"Invalid token: {str(e)}"
            )
        except Exception as e:
            return _cors_error_response(
                request, status.HTTP_500_INTERNAL_SERVER_ERROR, f"Authentication error: {str(e)}"
            )

        # Continuar con el request
        response = await call_next(request)
        return response


def require_auth(func: Callable) -> Callable:
    """
    Decorador para endpoints que requieren autenticación.

    Verifica que request.state.user existe (inyectado por AuthMiddleware).
    Si no existe, retorna HTTPException 401.

    Usage:
        @router.get("/protected")
        @require_auth
        async def protected_endpoint(request: Request):
            user = request.state.user
            return {"message": f"Hello {user.username}"}

    Args:
        func: Función del endpoint a proteger

    Returns:
        Función decorada que valida autenticación

    Raises:
        HTTPException 401: Si el usuario no está autenticado
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Buscar el objeto Request en los argumentos
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if not request:
            # Buscar en kwargs
            request = kwargs.get("request")

        if not request:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request object not found in endpoint arguments",
            )

        # Verificar que el usuario esté autenticado
        if not hasattr(request.state, "user") or request.state.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )

        # Llamar a la función original
        return await func(*args, **kwargs)

    return wrapper


def require_role(*roles: str) -> Callable:
    """
    Decorador para endpoints que requieren roles específicos.

    Verifica que el usuario autenticado tiene al menos uno de los roles
    especificados. Si no tiene ninguno, retorna HTTPException 403.

    Este decorador debe usarse junto con @require_auth o después de
    AuthMiddleware para asegurar que request.state.user existe.

    Usage:
        @router.get("/admin")
        @require_auth
        @require_role("ADMIN")
        async def admin_endpoint(request: Request):
            return {"message": "Admin access granted"}

        @router.get("/staff")
        @require_auth
        @require_role("ADMIN", "MECANICO")
        async def staff_endpoint(request: Request):
            return {"message": "Staff access granted"}

    Args:
        *roles: Nombres de roles requeridos (al menos uno debe coincidir)

    Returns:
        Decorador que valida roles del usuario

    Raises:
        HTTPException 401: Si el usuario no está autenticado
        HTTPException 403: Si el usuario no tiene los roles requeridos
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Buscar el objeto Request en los argumentos
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Buscar en kwargs
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found in endpoint arguments",
                )

            # Verificar que el usuario esté autenticado
            if not hasattr(request.state, "user") or request.state.user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            user = request.state.user

            # Obtener roles del usuario
            user_roles = [role.name for role in user.roles] if user.roles else []

            # Verificar que el usuario tiene al menos uno de los roles requeridos
            if not any(role in user_roles for role in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {', '.join(roles)}",
                )

            # Llamar a la función original
            return await func(*args, **kwargs)

        return wrapper

    return decorator
