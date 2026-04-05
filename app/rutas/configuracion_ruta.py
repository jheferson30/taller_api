import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.configuracion.base_datos import obtener_db as get_db
from app.modelos.mecanico import Mecanico
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.seguridad.dependencias import requerir_password_admin as verificar_admin

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class MecanicoCreate(BaseModel):
    nombre: str

class TallerUpdate(BaseModel):
    nombre_taller: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    nit: Optional[str] = None

class ProcesosRapidosUpdate(BaseModel):
    procesos: list[str]

class CobrosRapidosUpdate(BaseModel):
    cobros: list[str]

class WhatsAppConfigUpdate(BaseModel):
    whatsapp_token: Optional[str] = None
    whatsapp_phone_id: Optional[str] = None
    whatsapp_enabled: bool = False

class EmailConfigUpdate(BaseModel):
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None


# ── Mecánicos ─────────────────────────────────────────────────────────────────

@router.get("/mecanicos")
def listar_mecanicos(db: Session = Depends(get_db)):
    return db.query(Mecanico).order_by(Mecanico.nombre).all()


@router.post("/mecanicos", dependencies=[Depends(verificar_admin)])
def crear_mecanico(body: MecanicoCreate, db: Session = Depends(get_db)):
    nombre = body.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    existente = db.query(Mecanico).filter(Mecanico.nombre.ilike(nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un mecánico con ese nombre")
    m = Mecanico(nombre=nombre, activo=True)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/mecanicos/{mecanico_id}", dependencies=[Depends(verificar_admin)])
def toggle_mecanico(mecanico_id: int, db: Session = Depends(get_db)):
    m = db.query(Mecanico).filter(Mecanico.id == mecanico_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mecánico no encontrado")
    m.activo = not m.activo
    db.commit()
    db.refresh(m)
    return m


@router.delete("/mecanicos/{mecanico_id}", dependencies=[Depends(verificar_admin)])
def eliminar_mecanico(mecanico_id: int, db: Session = Depends(get_db)):
    m = db.query(Mecanico).filter(Mecanico.id == mecanico_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mecánico no encontrado")
    db.delete(m)
    db.commit()
    return {"ok": True}


# ── Configuración del taller ──────────────────────────────────────────────────

def _get_config(db: Session) -> ConfiguracionTaller:
    cfg = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.id == 1).first()
    if not cfg:
        cfg = ConfiguracionTaller(id=1, nombre_taller="Taller Mecánico", procesos_rapidos="[]")
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.get("/taller")
def obtener_config_taller(db: Session = Depends(get_db)):
    cfg = _get_config(db)
    return {
        "nombre_taller": cfg.nombre_taller,
        "direccion": cfg.direccion or "",
        "telefono": cfg.telefono or "",
        "nit": cfg.nit or "",
    }


@router.put("/taller", dependencies=[Depends(verificar_admin)])
def actualizar_config_taller(body: TallerUpdate, db: Session = Depends(get_db)):
    cfg = _get_config(db)
    cfg.nombre_taller = body.nombre_taller.strip() or "Taller Mecánico"
    cfg.direccion = body.direccion
    cfg.telefono = body.telefono
    cfg.nit = body.nit
    db.commit()
    db.refresh(cfg)
    return {"ok": True}


# ── Procesos rápidos ──────────────────────────────────────────────────────────

@router.get("/procesos-rapidos")
def obtener_procesos_rapidos(db: Session = Depends(get_db)):
    cfg = _get_config(db)
    try:
        procesos = json.loads(cfg.procesos_rapidos or "[]")
    except Exception:
        procesos = []
    return {"procesos": procesos}


@router.put("/procesos-rapidos", dependencies=[Depends(verificar_admin)])
def actualizar_procesos_rapidos(body: ProcesosRapidosUpdate, db: Session = Depends(get_db)):
    cfg = _get_config(db)
    limpios = [p.strip() for p in body.procesos if p.strip()]
    cfg.procesos_rapidos = json.dumps(limpios, ensure_ascii=False)
    db.commit()
    return {"ok": True, "procesos": limpios}


# ── Cobros rápidos ────────────────────────────────────────────────────────────

@router.get("/cobros-rapidos")
def obtener_cobros_rapidos(db: Session = Depends(get_db)):
    cfg = _get_config(db)
    try:
        cobros = json.loads(cfg.cobros_rapidos or "[]")
    except Exception:
        cobros = []
    return {"cobros": cobros}


@router.put("/cobros-rapidos", dependencies=[Depends(verificar_admin)])
def actualizar_cobros_rapidos(body: CobrosRapidosUpdate, db: Session = Depends(get_db)):
    cfg = _get_config(db)
    limpios = [c.strip() for c in body.cobros if c.strip()]
    cfg.cobros_rapidos = json.dumps(limpios, ensure_ascii=False)
    db.commit()
    return {"ok": True, "cobros": limpios}


# ── WhatsApp ──────────────────────────────────────────────────────────────────

@router.get("/whatsapp")
def obtener_config_whatsapp(db: Session = Depends(get_db)):
    cfg = _get_config(db)
    return {
        "whatsapp_token": cfg.whatsapp_token or "",
        "whatsapp_phone_id": cfg.whatsapp_phone_id or "",
        "whatsapp_enabled": cfg.whatsapp_enabled or False,
    }


@router.put("/whatsapp", dependencies=[Depends(verificar_admin)])
def actualizar_config_whatsapp(body: WhatsAppConfigUpdate, db: Session = Depends(get_db)):
    if body.whatsapp_phone_id and not body.whatsapp_phone_id.isdigit():
        raise HTTPException(status_code=422, detail="whatsapp_phone_id debe ser numérico")
    cfg = _get_config(db)
    cfg.whatsapp_token = body.whatsapp_token
    cfg.whatsapp_phone_id = body.whatsapp_phone_id
    cfg.whatsapp_enabled = body.whatsapp_enabled
    db.commit()
    return {"ok": True}


# ── Email / SMTP ──────────────────────────────────────────────────────────────

@router.get("/email")
def obtener_config_email(db: Session = Depends(get_db)):
    cfg = _get_config(db)
    return {
        "smtp_user": cfg.smtp_user or "",
        "smtp_from": cfg.smtp_from or "",
        # nunca devolver la contraseña, solo indicar si está configurada
        "smtp_password_set": bool(cfg.smtp_password),
    }


@router.put("/email", dependencies=[Depends(verificar_admin)])
def actualizar_config_email(body: EmailConfigUpdate, db: Session = Depends(get_db)):
    cfg = _get_config(db)
    if body.smtp_user is not None:
        cfg.smtp_user = body.smtp_user.strip() or None
    if body.smtp_password is not None:
        cfg.smtp_password = body.smtp_password or None
    if body.smtp_from is not None:
        cfg.smtp_from = body.smtp_from.strip() or None
    db.commit()
    return {"ok": True}
