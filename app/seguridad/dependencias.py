import hmac
import os

from fastapi import Header, HTTPException, status


def requerir_password_pdf(password_pdf: str = Header(..., alias="X-PDF-Password")):
    password_esperada = os.getenv("PDF_PASSWORD", "1234")
    if not hmac.compare_digest(password_pdf, password_esperada):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contrasena incorrecta para generar el PDF",
        )
    return True


def requerir_password_admin(admin_password: str = Header(..., alias="X-Admin-Password")):
    password_esperada = os.getenv("ADMIN_PASSWORD", os.getenv("PDF_PASSWORD", "1234"))
    if not hmac.compare_digest(admin_password, password_esperada):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contrasena de administrador incorrecta",
        )
    return True
