import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, Request, status


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


def requerir_password_admin(request: Request, admin_password: Optional[str] = Header(None, alias="X-Admin-Password")):
    """
    Dependencia que acepta autenticación JWT (nuevo) o X-Admin-Password (legacy).
    Prioriza JWT si el usuario está autenticado via middleware.
    """
    # Primero verificar si hay usuario autenticado via JWT (nuevo sistema)
    if hasattr(request.state, "user") and request.state.user is not None:
        return True

    # Fallback: verificar X-Admin-Password (sistema legacy)
    password_esperada = os.getenv("ADMIN_PASSWORD") or os.getenv("PDF_PASSWORD")
    if not password_esperada:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_PASSWORD env var is required",
        )
    if not admin_password or not hmac.compare_digest(admin_password.encode("utf-8"), password_esperada.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacion requerida",
        )
    return True


def require_jwt_auth(request: Request):
    """
    Dependencia FastAPI para proteger rutas con JWT.
    Úsala con Depends() en routers o endpoints.
    """
    if not hasattr(request.state, "user") or request.state.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return request.state.user
