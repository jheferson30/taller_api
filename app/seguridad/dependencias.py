import hashlib
import hmac
import os

from fastapi import Header, HTTPException, Request, status
from sqlalchemy.orm import Session


def _get_admin_password_from_db(db: Session) -> str | None:
    """Lee la contraseña admin desde la BD si existe."""
    try:
        from app.modelos.configuracion_seguridad import ConfiguracionSeguridad

        config = (
            db.query(ConfiguracionSeguridad)
            .filter(ConfiguracionSeguridad.clave == "admin_password")
            .first()
        )
        return config.valor_hash if config else None
    except Exception:
        return None


def requerir_password_pdf(password_pdf: str = Header(..., alias="X-PDF-Password")):
    password_esperada = os.getenv("PDF_PASSWORD")
    if not password_esperada:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF_PASSWORD env var is required",
        )
    if not hmac.compare_digest(password_pdf.encode("utf-8"), password_esperada.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contrasena incorrecta para generar el PDF",
        )
    return True


async def requerir_password_admin(
    request: Request,
    admin_password: str | None = Header(None, alias="X-Admin-Password"),
):
    """
    Dependencia que acepta autenticación JWT (nuevo) o X-Admin-Password (legacy).
    Prioriza JWT si el usuario está autenticado via middleware.
    La contraseña se lee de la BD si existe, con fallback al .env.
    """
    # Primero verificar si hay usuario autenticado via JWT
    if hasattr(request.state, "user") and request.state.user is not None:
        return True

    # Fallback: verificar X-Admin-Password
    if not admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacion requerida",
        )

    # Verificar contra BD primero
    from app.configuracion.base_datos import SessionLocal

    db = SessionLocal()
    try:
        hash_bd = _get_admin_password_from_db(db)
    finally:
        db.close()

    if hash_bd:
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        if not hmac.compare_digest(password_hash, hash_bd):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticacion requerida",
            )
        return True

    # Fallback: verificar contra .env
    password_esperada = os.getenv("ADMIN_PASSWORD") or os.getenv("PDF_PASSWORD")
    if not password_esperada:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_PASSWORD env var is required",
        )
    if not hmac.compare_digest(admin_password.encode("utf-8"), password_esperada.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacion requerida",
        )
    return True


def require_jwt_auth(request: Request):
    """
    Dependencia FastAPI para proteger rutas con JWT.
    """
    if not hasattr(request.state, "user") or request.state.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return request.state.user
