import json

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db as get_db
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.modelos.role import Role
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.seguridad.auth_middleware import require_auth
from app.seguridad.dependencias import requerir_password_admin as verificar_admin

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class TallerUpdate(BaseModel):
    nombre_taller: str
    direccion: str | None = None
    telefono: str | None = None
    nit: str | None = None


class ProcesosRapidosUpdate(BaseModel):
    procesos: list[str]


class CobrosRapidosUpdate(BaseModel):
    cobros: list[str]


class WhatsAppConfigUpdate(BaseModel):
    whatsapp_token: str | None = None
    whatsapp_phone_id: str | None = None
    whatsapp_enabled: bool = False


class EmailConfigUpdate(BaseModel):
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None


# ── Mecánicos ─────────────────────────────────────────────────────────────────


@router.get("/mecanicos")
@require_auth
async def listar_mecanicos(request: Request, db: Session = Depends(get_db)):
    """
    Devuelve los usuarios con rol MECANICO del taller.
    Los mecánicos son los mismos usuarios del sistema — no existe una entidad separada.
    """
    mecanicos = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            User.taller_id == request.state.taller_id,
            Role.name == "MECANICO",
        )
        .order_by(User.nombre_completo, User.username)
        .all()
    )
    return [
        {
            "id": u.id,
            "nombre": u.nombre_completo or u.username,
            "activo": u.is_active,
        }
        for u in mecanicos
    ]


# ── Configuración del taller ──────────────────────────────────────────────────


def _get_config(db: Session, taller_id: int) -> ConfiguracionTaller:
    """
    Retorna la configuración del taller identificado por taller_id.
    Si no existe, la crea con valores por defecto.
    Invariante multi-tenant: nunca usa id=1 hardcodeado.
    """
    if not taller_id:
        raise ValueError("taller_id requerido para obtener configuración")

    cfg = db.query(ConfiguracionTaller).filter(
        ConfiguracionTaller.taller_id == taller_id
    ).first()
    if not cfg:
        cfg = ConfiguracionTaller(
            taller_id=taller_id,
            nombre_taller="Taller Mecánico",
            procesos_rapidos="[]",
            cobros_rapidos="[]",
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.get("/taller")
@require_auth
async def obtener_config_taller(request: Request, db: Session = Depends(get_db)):
    taller_id = request.state.taller_id
    cfg = _get_config(db, taller_id)
    return {
        "nombre_taller": cfg.nombre_taller,
        "direccion": cfg.direccion or "",
        "telefono": cfg.telefono or "",
        "nit": cfg.nit or "",
    }


@router.put("/taller", dependencies=[Depends(verificar_admin)])
async def actualizar_config_taller(
    request: Request,
    body: TallerUpdate,
    db: Session = Depends(get_db),
):
    taller_id = request.state.taller_id
    cfg = _get_config(db, taller_id)
    cfg.nombre_taller = body.nombre_taller.strip() or "Taller Mecánico"
    cfg.direccion = body.direccion
    cfg.telefono = body.telefono
    cfg.nit = body.nit
    db.commit()
    db.refresh(cfg)
    return {"ok": True}


# ── Procesos rápidos ──────────────────────────────────────────────────────────


@router.get("/procesos-rapidos")
@require_auth
async def obtener_procesos_rapidos(request: Request, db: Session = Depends(get_db)):
    cfg = _get_config(db, request.state.taller_id)
    try:
        procesos = json.loads(cfg.procesos_rapidos or "[]")
    except Exception:
        procesos = []
    return {"procesos": procesos}


@router.put("/procesos-rapidos", dependencies=[Depends(verificar_admin)])
async def actualizar_procesos_rapidos(
    request: Request,
    body: ProcesosRapidosUpdate,
    db: Session = Depends(get_db),
):
    cfg = _get_config(db, request.state.taller_id)
    limpios = [p.strip() for p in body.procesos if p.strip()]
    cfg.procesos_rapidos = json.dumps(limpios, ensure_ascii=False)
    db.commit()
    return {"ok": True, "procesos": limpios}


# ── Cobros rápidos ────────────────────────────────────────────────────────────


@router.get("/cobros-rapidos")
@require_auth
async def obtener_cobros_rapidos(request: Request, db: Session = Depends(get_db)):
    cfg = _get_config(db, request.state.taller_id)
    try:
        cobros = json.loads(cfg.cobros_rapidos or "[]")
    except Exception:
        cobros = []
    return {"cobros": cobros}


@router.put("/cobros-rapidos", dependencies=[Depends(verificar_admin)])
async def actualizar_cobros_rapidos(
    request: Request,
    body: CobrosRapidosUpdate,
    db: Session = Depends(get_db),
):
    cfg = _get_config(db, request.state.taller_id)
    limpios = [c.strip() for c in body.cobros if c.strip()]
    cfg.cobros_rapidos = json.dumps(limpios, ensure_ascii=False)
    db.commit()
    return {"ok": True, "cobros": limpios}


# ── WhatsApp ──────────────────────────────────────────────────────────────────


@router.get("/whatsapp")
@require_auth
async def obtener_config_whatsapp(request: Request, db: Session = Depends(get_db)):
    cfg = _get_config(db, request.state.taller_id)
    return {
        "whatsapp_token": cfg.whatsapp_token or "",
        "whatsapp_phone_id": cfg.whatsapp_phone_id or "",
        "whatsapp_enabled": cfg.whatsapp_enabled or False,
    }


@router.put("/whatsapp", dependencies=[Depends(verificar_admin)])
async def actualizar_config_whatsapp(
    request: Request,
    body: WhatsAppConfigUpdate,
    db: Session = Depends(get_db),
):
    if body.whatsapp_phone_id and not body.whatsapp_phone_id.isdigit():
        raise HTTPException(status_code=422, detail="whatsapp_phone_id debe ser numérico")
    cfg = _get_config(db, request.state.taller_id)
    cfg.whatsapp_token = body.whatsapp_token
    cfg.whatsapp_phone_id = body.whatsapp_phone_id
    cfg.whatsapp_enabled = body.whatsapp_enabled
    db.commit()
    return {"ok": True}


# ── Email / SMTP ──────────────────────────────────────────────────────────────


@router.get("/email")
@require_auth
async def obtener_config_email(request: Request, db: Session = Depends(get_db)):
    cfg = _get_config(db, request.state.taller_id)
    return {
        "smtp_user": cfg.smtp_user or "",
        "smtp_from": cfg.smtp_from or "",
        "smtp_password_set": bool(cfg.smtp_password),
    }


@router.put("/email", dependencies=[Depends(verificar_admin)])
async def actualizar_config_email(
    request: Request,
    body: EmailConfigUpdate,
    db: Session = Depends(get_db),
):
    cfg = _get_config(db, request.state.taller_id)
    if body.smtp_user is not None:
        cfg.smtp_user = body.smtp_user.strip() or None
    if body.smtp_password is not None:
        cfg.smtp_password = body.smtp_password or None
    if body.smtp_from is not None:
        cfg.smtp_from = body.smtp_from.strip() or None
    db.commit()
    return {"ok": True}


# ── Logo del taller ───────────────────────────────────────────────────────────


@router.get("/logo")
@require_auth
async def obtener_logo(request: Request, db: Session = Depends(get_db)):
    import time

    cfg = _get_config(db, request.state.taller_id)
    logo_url = cfg.logo_url or ""

    if logo_url:
        timestamp = str(int(time.time()))
        separator = "&" if "?" in logo_url else "?"
        logo_url = f"{logo_url}{separator}v={timestamp}"

    return {"logo_url": logo_url}


@router.post("/logo", dependencies=[Depends(verificar_admin)])
async def subir_logo(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    import os
    import uuid

    taller_id = request.state.taller_id

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Solo se permiten jpg, png o webp")

    # Ruta aislada por taller: uploads/talleres/{taller_id}/logos/
    logo_dir = os.path.join("uploads", "talleres", str(taller_id), "logos")
    os.makedirs(logo_dir, exist_ok=True)
    filename = f"logo_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(logo_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    logo_url = f"/uploads/talleres/{taller_id}/logos/{filename}"

    cfg = _get_config(db, taller_id)
    cfg.logo_url = logo_url
    db.commit()
    return {"logo_url": logo_url}
