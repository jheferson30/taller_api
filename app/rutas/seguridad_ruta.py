import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.configuracion.limiter import limiter
from app.modelos.configuracion_seguridad import ConfiguracionSeguridad

router = APIRouter(prefix="/seguridad", tags=["Seguridad"])


class CrearPasswordPayload(BaseModel):
    password: str
    palabra_clave: str


class ValidarPasswordPayload(BaseModel):
    password: str


class RecuperarPasswordPayload(BaseModel):
    palabra_clave: str
    nueva_password: str


def _hash_password(password: str) -> str:
    """Genera un hash SHA256 de la contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()


def _obtener_config(db: Session, clave: str) -> ConfiguracionSeguridad | None:
    """Obtiene una configuración por clave"""
    return db.query(ConfiguracionSeguridad).filter(ConfiguracionSeguridad.clave == clave).first()


def _guardar_config(db: Session, clave: str, valor: str):
    """Guarda o actualiza una configuración"""
    config = _obtener_config(db, clave)
    valor_hash = _hash_password(valor)

    if config:
        config.valor_hash = valor_hash
    else:
        config = ConfiguracionSeguridad(clave=clave, valor_hash=valor_hash)
        db.add(config)

    db.commit()
    db.refresh(config)
    return config


@router.get("/economia/tiene-password")
def verificar_tiene_password(db: Session = Depends(obtener_db)):
    """Verifica si ya existe una contraseña configurada para economía"""
    config = _obtener_config(db, "economia_password")
    return {"tiene_password": config is not None}


@router.post("/economia/crear-password")
@limiter.limit("10/minute")
async def crear_password_economia(
    request: Request,
    payload: CrearPasswordPayload,
    db: Session = Depends(obtener_db),
):
    """Crea la contraseña inicial para acceder a economía"""
    # Verificar que no exista ya
    if _obtener_config(db, "economia_password"):
        raise HTTPException(status_code=400, detail="Ya existe una contraseña configurada")

    # Validar que la contraseña no esté vacía
    if not payload.password or len(payload.password) < 4:
        raise HTTPException(
            status_code=400, detail="La contraseña debe tener al menos 4 caracteres"
        )

    if not payload.palabra_clave or len(payload.palabra_clave) < 3:
        raise HTTPException(
            status_code=400, detail="La palabra clave debe tener al menos 3 caracteres"
        )

    # Guardar contraseña y palabra clave
    _guardar_config(db, "economia_password", payload.password)
    _guardar_config(db, "economia_palabra_clave", payload.palabra_clave)

    return {"ok": True, "mensaje": "Contraseña creada exitosamente"}


@router.post("/economia/validar-password")
@limiter.limit("10/minute")
async def validar_password_economia(
    request: Request,
    payload: ValidarPasswordPayload,
    db: Session = Depends(obtener_db),
):
    """Valida la contraseña para acceder a economía"""
    config = _obtener_config(db, "economia_password")

    if not config:
        raise HTTPException(status_code=404, detail="No hay contraseña configurada")

    password_hash = _hash_password(payload.password)

    if password_hash != config.valor_hash:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    return {"ok": True, "mensaje": "Contraseña correcta"}


@router.post("/economia/recuperar-password")
@limiter.limit("10/minute")
async def recuperar_password_economia(
    request: Request,
    payload: RecuperarPasswordPayload,
    db: Session = Depends(obtener_db),
):
    """Recupera/cambia la contraseña usando la palabra clave"""
    config_password = _obtener_config(db, "economia_password")
    config_palabra = _obtener_config(db, "economia_palabra_clave")

    if not config_password or not config_palabra:
        raise HTTPException(status_code=404, detail="No hay configuración de seguridad")

    # Validar palabra clave
    palabra_hash = _hash_password(payload.palabra_clave)
    if palabra_hash != config_palabra.valor_hash:
        raise HTTPException(status_code=401, detail="Palabra clave incorrecta")

    # Validar nueva contraseña
    if not payload.nueva_password or len(payload.nueva_password) < 4:
        raise HTTPException(
            status_code=400, detail="La nueva contraseña debe tener al menos 4 caracteres"
        )

    # Actualizar contraseña
    _guardar_config(db, "economia_password", payload.nueva_password)

    return {"ok": True, "mensaje": "Contraseña actualizada exitosamente"}


# ── Contraseña Admin (app móvil) ─────────────────────────────────────────────


class CambiarPasswordAdminPayload(BaseModel):
    password_actual: str
    nueva_password: str


@router.get("/admin/tiene-password-bd")
def verificar_tiene_password_admin_bd(db: Session = Depends(obtener_db)):
    """Verifica si la contraseña admin ya está guardada en BD (vs solo en .env)"""
    config = _obtener_config(db, "admin_password")
    return {"tiene_password_bd": config is not None}


@router.post("/admin/cambiar-password")
@limiter.limit("5/minute")
async def cambiar_password_admin(
    request: Request,
    payload: CambiarPasswordAdminPayload,
    db: Session = Depends(obtener_db),
):
    """
    Cambia la contraseña admin. Solo accesible con JWT de admin.
    Requiere la contraseña actual para confirmar.
    """
    # Solo admins pueden cambiar esta contraseña
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    user_roles = [role.name for role in user.roles] if hasattr(user, "roles") and user.roles else []
    if "ADMIN" not in user_roles:
        raise HTTPException(
            status_code=403, detail="Solo administradores pueden cambiar esta contraseña"
        )

    # Validar contraseña actual — primero BD, luego .env
    config_actual = _obtener_config(db, "admin_password")
    if config_actual:
        if _hash_password(payload.password_actual) != config_actual.valor_hash:
            raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    else:
        # Fallback: comparar con .env
        import hmac as _hmac

        password_env = os.getenv("ADMIN_PASSWORD") or os.getenv("PDF_PASSWORD") or ""
        if not _hmac.compare_digest(payload.password_actual.encode(), password_env.encode()):
            raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")

    # Validar nueva contraseña
    if not payload.nueva_password or len(payload.nueva_password) < 6:
        raise HTTPException(
            status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres"
        )

    # Guardar en BD
    _guardar_config(db, "admin_password", payload.nueva_password)

    return {"ok": True, "mensaje": "Contraseña admin actualizada correctamente"}
