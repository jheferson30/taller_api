"""
Auth Middleware y decoradores para protección de endpoints con JWT.

Este módulo implementa:
- AuthMiddleware: Middleware de FastAPI que valida tokens JWT en cada request
- @require_auth: Decorador para endpoints que requieren autenticación
- @require_role: Decorador para endpoints que requieren roles específicos
"""

from functools import wraps
from typing import Callable, List

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.base import BaseHTTPMiddleware

from app.configuracion.base_datos import obtener_db
from app.seguridad.token_manager import TokenManager
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.user_repository import UserRepository
from app.modelos.user import User


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
        # Rutas públicas que no requieren autenticación
        public_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/info",
            "/info/conexion-qr",
            "/assets",
            "/uploads",
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
            return await call_next(request)
        
        # Validar formato "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format. Expected 'Bearer <token>'"}
            )
        
        token = parts[1]
        
        try:
            # Decodificar y validar token
            payload = self.token_manager.decode_token(token)
            
            # Extraer jti del payload
            jti = payload.get("jti")
            user_id = payload.get("user_id")
            
            if not jti or not user_id:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid token payload"}
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
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Token has been revoked"}
                    )
                
                # Obtener usuario completo con roles
                # Usar joinedload para cargar roles en una sola query
                user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).first()
                
                if not user:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "User not found"}
                    )
                
                if not user.is_active:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "User account is inactive"}
                    )
                
                # Inyectar user context en request.state
                request.state.user = user
                
            finally:
                if should_close:
                    db.close()
            
        except ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token has expired"}
            )
        except InvalidTokenError as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Invalid token: {str(e)}"}
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Authentication error: {str(e)}"}
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
                detail="Request object not found in endpoint arguments"
            )
        
        # Verificar que el usuario esté autenticado
        if not hasattr(request.state, "user") or request.state.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
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
                    detail="Request object not found in endpoint arguments"
                )
            
            # Verificar que el usuario esté autenticado
            if not hasattr(request.state, "user") or request.state.user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user = request.state.user
            
            # Obtener roles del usuario
            user_roles = [role.name for role in user.roles] if user.roles else []
            
            # Verificar que el usuario tiene al menos uno de los roles requeridos
            if not any(role in user_roles for role in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {', '.join(roles)}"
                )
            
            # Llamar a la función original
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator
