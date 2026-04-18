import json as _json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db as get_db
from app.configuracion.limiter import limiter
from app.esquemas.mobile_schema import (
    ActualizarEstadoTicket,
    ActualizarFinanzasData,
    CobroCreate,
    CobroResponse,
    CompraResponse,
    EntregarTicketData,
    FotoResponse,
    ProcesoResponse,
    RepuestoCreate,
    RepuestoResponse,
    TicketDetailResponse,
    TicketListResponse,
)
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.modelos.mecanico import Mecanico
from app.modelos.movimiento_caja import MovimientoCaja, TipoMovimiento
from app.modelos.ticket import Ticket
from app.modelos.ticket_cobro import TicketCobro
from app.modelos.ticket_compra import TicketCompra
from app.modelos.ticket_foto import TicketFoto
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.ticket_repuesto import TicketRepuesto
from app.modelos.vehiculo import Vehiculo
from app.seguridad.dependencias import requerir_password_admin
from app.servicios.ticket_service import TicketService
from app.servicios.twilio_whatsapp_service import TwilioWhatsAppService
from app.servicios.whatsapp_service import TipoEvento
from app.utils.input_validator import InputSanitizer

FOTOS_DIR = os.path.join("uploads", "fotos")
os.makedirs(FOTOS_DIR, exist_ok=True)

router = APIRouter(
    prefix="/api/mobile", tags=["Mobile API"], dependencies=[Depends(requerir_password_admin)]
)

_whatsapp_service = TwilioWhatsAppService()


# ===== ENDPOINTS =====


@router.get("/tickets", response_model=list[TicketListResponse])
def listar_tickets_mobile(estado: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Ticket)
    if estado:
        query = query.filter(Ticket.estado == estado)
    tickets = query.order_by(Ticket.fecha_ingreso.desc()).all()

    result = []
    for ticket in tickets:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
        result.append(
            TicketListResponse(
                id=ticket.id,
                ticket_codigo=ticket.ticket_codigo,
                placa=ticket.placa,
                motivo_visita=ticket.motivo_visita,
                estado=ticket.estado,
                fecha_ingreso=ticket.fecha_ingreso,
                nombre_propietario=vehiculo.nombre_propietario if vehiculo else None,
                telefono_propietario=vehiculo.telefono_propietario if vehiculo else None,
            )
        )
    return result


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
def obtener_ticket_mobile(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()

    return TicketDetailResponse(
        id=ticket.id,
        ticket_codigo=ticket.ticket_codigo,
        placa=ticket.placa,
        motivo_visita=ticket.motivo_visita,
        estado=ticket.estado,
        fecha_ingreso=ticket.fecha_ingreso,
        observaciones_recepcion=ticket.observaciones_recepcion,
        kilometraje=ticket.kilometraje,
        estado_inicial=ticket.estado_inicial,
        anticipo_recibido=ticket.anticipo_recibido,
        total_servicio=ticket.total_servicio,
        saldo_pendiente=ticket.saldo_pendiente,
        nombre_propietario=vehiculo.nombre_propietario if vehiculo else None,
        telefono_propietario=vehiculo.telefono_propietario if vehiculo else None,
    )


@router.get("/tickets/{ticket_id}/procesos", response_model=list[ProcesoResponse])
def listar_procesos_mobile(ticket_id: int, db: Session = Depends(get_db)):
    """
    Lista todos los procesos de un ticket
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    procesos = db.query(TicketProceso).filter(TicketProceso.ticket_id == ticket_id).all()
    return procesos


@router.post("/tickets/{ticket_id}/procesos", response_model=ProcesoResponse)
async def crear_proceso_mobile(
    ticket_id: int,
    nombre: str = Form(...),
    descripcion: str | None = Form(None),
    mecanico: str | None = Form(None),
    foto_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Crea un nuevo proceso sin foto (usando Form data).
    Para subir con foto, usar el endpoint /tickets/{ticket_id}/procesos/con-foto
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.estado not in ["ABIERTO", "EN_PROCESO"]:
        raise HTTPException(
            status_code=400, detail="No se pueden agregar procesos a un ticket finalizado"
        )

    if not nombre or not str(nombre).strip():
        raise HTTPException(status_code=422, detail="El nombre del proceso es obligatorio")

    nuevo_proceso = TicketProceso(
        ticket_id=ticket_id,
        nombre=str(nombre).strip(),
        descripcion=descripcion,
        mecanico=mecanico,
        foto_url=foto_url,
    )
    db.add(nuevo_proceso)
    db.commit()
    db.refresh(nuevo_proceso)
    return nuevo_proceso


@router.post("/tickets/{ticket_id}/procesos/con-foto", response_model=ProcesoResponse)
async def crear_proceso_con_foto_mobile(
    ticket_id: int,
    nombre: str = Form(...),
    descripcion: str | None = Form(None),
    mecanico: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    """
    Crea un nuevo proceso con foto adjunta (usando multipart/form-data).
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.estado not in ["ABIERTO", "EN_PROCESO"]:
        raise HTTPException(
            status_code=400, detail="No se pueden agregar procesos a un ticket finalizado"
        )

    if not nombre or not str(nombre).strip():
        raise HTTPException(status_code=422, detail="El nombre del proceso es obligatorio")

    # Validar y guardar foto
    foto_url = None
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(status_code=400, detail="Solo se permiten imágenes jpg, png o webp")
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}{ext}"
        filepath = os.path.join(FOTOS_DIR, filename)
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        foto_url = f"/uploads/fotos/{filename}"

    nuevo_proceso = TicketProceso(
        ticket_id=ticket_id,
        nombre=str(nombre).strip(),
        descripcion=descripcion,
        mecanico=mecanico,
        foto_url=foto_url,
    )
    db.add(nuevo_proceso)
    db.commit()
    db.refresh(nuevo_proceso)
    return nuevo_proceso


@router.get("/tickets/{ticket_id}/repuestos", response_model=list[RepuestoResponse])
def listar_repuestos_mobile(ticket_id: int, db: Session = Depends(get_db)):
    """
    Lista todos los repuestos de un ticket
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    repuestos = db.query(TicketRepuesto).filter(TicketRepuesto.ticket_id == ticket_id).all()
    return repuestos


@router.post("/tickets/{ticket_id}/repuestos", response_model=RepuestoResponse)
def crear_repuesto_mobile(ticket_id: int, repuesto: RepuestoCreate, db: Session = Depends(get_db)):
    """
    Agrega un repuesto a un ticket
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    if ticket.estado not in ["ABIERTO", "EN_PROCESO"]:
        raise HTTPException(
            status_code=400, detail="No se pueden agregar repuestos a un ticket finalizado"
        )

    nuevo_repuesto = TicketRepuesto(
        ticket_id=ticket_id,
        nombre=repuesto.nombre,
        cantidad=repuesto.cantidad,
        marca_referencia=repuesto.marca_referencia,
        proceso_id=repuesto.proceso_id,
        foto_url=repuesto.foto_url,
    )

    db.add(nuevo_repuesto)
    db.commit()
    db.refresh(nuevo_repuesto)

    return nuevo_repuesto


@router.get("/tickets/{ticket_id}/fotos", response_model=list[FotoResponse])
def listar_fotos_mobile(ticket_id: int, db: Session = Depends(get_db)):
    """
    Lista todas las fotos de un ticket
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    fotos = db.query(TicketFoto).filter(TicketFoto.ticket_id == ticket_id).all()
    return fotos


TRANSICIONES_VALIDAS = {
    "ABIERTO": ["EN_PROCESO"],
    "EN_PROCESO": ["FINALIZADO"],
    "FINALIZADO": ["ENTREGADO"],
    "ENTREGADO": [],
}


@router.patch("/tickets/{ticket_id}/estado")
@limiter.limit("30/minute")
def actualizar_estado_mobile(
    request: Request, ticket_id: int, data: ActualizarEstadoTicket, db: Session = Depends(get_db)
):
    """
    Actualiza el estado de un ticket.
    Transiciones permitidas:
      ABIERTO → EN_PROCESO
      EN_PROCESO → FINALIZADO
      FINALIZADO → ENTREGADO
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    nuevo_estado = data.estado.upper()
    estado_actual = ticket.estado

    if nuevo_estado == estado_actual:
        return {"message": "Sin cambios", "nuevo_estado": ticket.estado}

    permitidos = TRANSICIONES_VALIDAS.get(estado_actual, [])
    if nuevo_estado not in permitidos:
        raise HTTPException(
            status_code=422,
            detail=f"Transición inválida: {estado_actual} → {nuevo_estado}. "
            f"Desde {estado_actual} solo se puede pasar a: {permitidos or ['ninguno']}",
        )

    ticket.estado = nuevo_estado
    ticket.fecha_actualizacion = datetime.now()

    if nuevo_estado == "FINALIZADO":
        ticket_service = TicketService(db)
        ticket_service.finalizar_ticket(ticket)

    db.commit()
    db.refresh(ticket)

    return {"message": "Estado actualizado correctamente", "nuevo_estado": ticket.estado}


@router.get("/tickets/{ticket_id}/resumen")
def obtener_resumen_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un resumen completo del ticket con contadores
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    resumen = db.query(
        db.query(func.count(TicketProceso.id))
        .filter(TicketProceso.ticket_id == ticket_id)
        .scalar_subquery()
        .label("total_procesos"),
        db.query(func.count(TicketRepuesto.id))
        .filter(TicketRepuesto.ticket_id == ticket_id)
        .scalar_subquery()
        .label("total_repuestos"),
        db.query(func.count(TicketFoto.id))
        .filter(TicketFoto.ticket_id == ticket_id, TicketFoto.tipo != "PROCESO")
        .scalar_subquery()
        .label("total_fotos"),
        db.query(func.count(TicketCompra.id))
        .filter(TicketCompra.ticket_id == ticket_id)
        .scalar_subquery()
        .label("total_compras"),
        db.query(func.coalesce(func.sum(TicketCompra.valor), 0))
        .filter(TicketCompra.ticket_id == ticket_id)
        .scalar_subquery()
        .label("total_egresos"),
        db.query(func.coalesce(func.sum(TicketCobro.valor), 0))
        .filter(TicketCobro.ticket_id == ticket_id)
        .scalar_subquery()
        .label("total_cobros"),
    ).one()

    return {
        "ticket_id": ticket.id,
        "ticket_codigo": ticket.ticket_codigo,
        "placa": ticket.placa,
        "estado": ticket.estado,
        "contadores": {
            "procesos": resumen.total_procesos,
            "repuestos": resumen.total_repuestos,
            "fotos": resumen.total_fotos,
            "compras": resumen.total_compras,
        },
        "finanzas": {
            "anticipo": ticket.anticipo_recibido,
            "total_egresos": resumen.total_egresos,
            "total_cobros": resumen.total_cobros,
            "total_servicio": ticket.total_servicio,
            "saldo_pendiente": ticket.saldo_pendiente,
        },
    }


@router.get("/estadisticas")
def obtener_estadisticas_mobile(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas generales para el dashboard móvil
    """
    total_tickets = db.query(Ticket).count()
    tickets_abiertos = db.query(Ticket).filter(Ticket.estado == "ABIERTO").count()
    tickets_en_proceso = db.query(Ticket).filter(Ticket.estado == "EN_PROCESO").count()
    tickets_finalizados = db.query(Ticket).filter(Ticket.estado == "FINALIZADO").count()
    tickets_entregados = db.query(Ticket).filter(Ticket.estado == "ENTREGADO").count()

    return {
        "total_tickets": total_tickets,
        "por_estado": {
            "abiertos": tickets_abiertos,
            "en_proceso": tickets_en_proceso,
            "finalizados": tickets_finalizados,
            "entregados": tickets_entregados,
        },
    }


@router.post("/tickets/{ticket_id}/fotos")
async def subir_foto_mobile(
    ticket_id: int,
    file: UploadFile = File(...),
    tipo: str = Form(default="OTRA"),
    descripcion: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Sube una foto asociada a un ticket desde la app móvil"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    tipos_validos = {"ANTES", "DESPUES", "OTRA"}
    tipo_final = tipo.upper() if tipo and tipo.upper() in tipos_validos else "OTRA"

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes jpg, png o webp")

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}{ext}"
    filepath = os.path.join(FOTOS_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    foto = TicketFoto(
        ticket_id=ticket_id,
        tipo=tipo_final,
        archivo_url=f"/uploads/fotos/{filename}",
        descripcion=descripcion,
    )
    db.add(foto)
    db.commit()
    db.refresh(foto)

    return {"id": foto.id, "archivo_url": foto.archivo_url, "tipo": foto.tipo}


@router.post("/tickets/{ticket_id}/entregar")
def entregar_ticket_mobile(ticket_id: int, data: EntregarTicketData, db: Session = Depends(get_db)):
    """Marca un ticket como entregado desde la app móvil"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    # Usar servicio para entregar ticket
    ticket_service = TicketService(db)
    ticket_service.entregar_ticket(
        ticket=ticket,
        confirmado_entrega_por=data.confirmado_entrega_por,
        observaciones_finales=data.observaciones_finales,
        recomendaciones=data.recomendaciones,
        proximo_mantenimiento=data.proximo_mantenimiento,
        metodo_pago_final=data.metodo_pago_final,
    )

    db.commit()
    db.refresh(ticket)

    # Fire-and-forget: notificación WhatsApp de entrega (req 4.1)
    try:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
        import asyncio

        loop = asyncio.get_running_loop()
        loop.create_task(
            _whatsapp_service.enviar_notificacion(TipoEvento.ENTREGA, ticket, vehiculo, db)
        )
    except RuntimeError:
        pass  # No hay event loop activo (ej. en tests síncronos)
    except Exception:
        pass
    return {"message": "Ticket entregado correctamente", "estado": ticket.estado}


@router.delete("/tickets/{ticket_id}/fotos/{foto_id}")
def eliminar_foto_mobile(ticket_id: int, foto_id: int, db: Session = Depends(get_db)):
    """Elimina una foto de un ticket"""
    foto = (
        db.query(TicketFoto)
        .filter(TicketFoto.id == foto_id, TicketFoto.ticket_id == ticket_id)
        .first()
    )
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    # Borrar archivo físico si existe
    filepath = foto.archivo_url.lstrip("/")
    if os.path.exists(filepath):
        os.remove(filepath)

    db.delete(foto)
    db.commit()
    return {"message": "Foto eliminada correctamente"}


# ===== COMPRAS =====


@router.get("/tickets/{ticket_id}/compras", response_model=list[CompraResponse])
def listar_compras_mobile(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return db.query(TicketCompra).filter(TicketCompra.ticket_id == ticket_id).all()


@router.post("/tickets/{ticket_id}/compras", response_model=CompraResponse)
async def crear_compra_mobile(
    ticket_id: int,
    descripcion: str = Form(...),
    valor: int = Form(...),
    nota: str | None = Form(default=None),
    responsable: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if valor <= 0:
        raise HTTPException(status_code=400, detail="El valor debe ser mayor a 0")

    soporte_url = None
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
            raise HTTPException(status_code=400, detail="Formato no permitido")
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}{ext}"
        compras_dir = os.path.join("uploads", "compras")
        os.makedirs(compras_dir, exist_ok=True)
        filepath = os.path.join(compras_dir, filename)
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        soporte_url = f"/uploads/compras/{filename}"

    # Usar servicio para crear compra con movimiento
    ticket_service = TicketService(db)
    compra = ticket_service.crear_compra_con_movimiento(
        ticket=ticket,
        descripcion=descripcion,
        valor=valor,
        responsable=responsable,
        nota=nota,
        soporte_url=soporte_url,
    )
    db.commit()
    db.refresh(compra)
    return compra


@router.delete("/tickets/{ticket_id}/compras/{compra_id}")
def eliminar_compra_mobile(ticket_id: int, compra_id: int, db: Session = Depends(get_db)):
    compra = (
        db.query(TicketCompra)
        .filter(TicketCompra.id == compra_id, TicketCompra.ticket_id == ticket_id)
        .first()
    )
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if compra.soporte_url:
        filepath = compra.soporte_url.lstrip("/")
        if os.path.exists(filepath):
            os.remove(filepath)
    db.delete(compra)
    db.commit()
    return {"message": "Compra eliminada"}


# ── Cobros ──────────────────────────────────────────────────────────────────


@router.get("/tickets/{ticket_id}/cobros", response_model=list[CobroResponse])
def listar_cobros_mobile(ticket_id: int, db: Session = Depends(get_db)):
    return db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket_id).all()


@router.post("/tickets/{ticket_id}/cobros", response_model=CobroResponse)
def crear_cobro_mobile(ticket_id: int, data: CobroCreate, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    cobro = TicketCobro(ticket_id=ticket_id, concepto=data.concepto, valor=data.valor)
    db.add(cobro)
    db.commit()
    db.refresh(cobro)
    return cobro


@router.delete("/tickets/{ticket_id}/cobros/{cobro_id}")
def eliminar_cobro_mobile(ticket_id: int, cobro_id: int, db: Session = Depends(get_db)):
    cobro = (
        db.query(TicketCobro)
        .filter(TicketCobro.id == cobro_id, TicketCobro.ticket_id == ticket_id)
        .first()
    )
    if not cobro:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    db.delete(cobro)
    db.commit()


# ── Finanzas ─────────────────────────────────────────────────────────────────


@router.patch("/tickets/{ticket_id}/finanzas")
def actualizar_finanzas_mobile(
    ticket_id: int, data: ActualizarFinanzasData, db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    # Usar servicio para actualizar finanzas
    ticket_service = TicketService(db)
    ticket_service.actualizar_finanzas(
        ticket=ticket,
        total_servicio=data.total_servicio,
        metodo_pago_final=data.metodo_pago_final,
    )

    # Guardar observaciones si se enviaron
    if data.observaciones_finales is not None:
        ticket.observaciones_finales = InputSanitizer.sanitize_html(data.observaciones_finales)
    if data.recomendaciones is not None:
        ticket.recomendaciones = InputSanitizer.sanitize_html(data.recomendaciones)
    if data.proximo_mantenimiento is not None:
        ticket.proximo_mantenimiento = InputSanitizer.sanitize_html(data.proximo_mantenimiento)

    db.commit()
    return {"ok": True, "saldo_pendiente": ticket.saldo_pendiente}


# ── Mecánicos y Procesos Rápidos (para la app móvil) ─────────────────────────


@router.get("/mecanicos")
def listar_mecanicos_mobile(db: Session = Depends(get_db)):
    return db.query(Mecanico).filter(Mecanico.activo == True).order_by(Mecanico.nombre).all()


@router.get("/procesos-rapidos")
def listar_procesos_rapidos_mobile(db: Session = Depends(get_db)):
    cfg = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.id == 1).first()
    if not cfg:
        return {"procesos": []}
    try:
        procesos = _json.loads(cfg.procesos_rapidos or "[]")
    except Exception:
        procesos = []
    return {"procesos": procesos}


@router.get("/cobros-rapidos")
def listar_cobros_rapidos_mobile(db: Session = Depends(get_db)):
    cfg = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.id == 1).first()
    if not cfg:
        return {"cobros": []}
    try:
        cobros = _json.loads(cfg.cobros_rapidos or "[]")
    except Exception:
        cobros = []
    return {"cobros": cobros}


# ── Sincronización por lotes (Modo Offline) ──────────────────────────────────


from typing import Literal

from pydantic import BaseModel, Field


class OperacionOffline(BaseModel):
    """Representa una operación realizada offline que necesita sincronizarse."""

    id: str = Field(..., description="ID único de la operación (UUID generado en cliente)")
    tipo: Literal[
        "crear_proceso", "crear_repuesto", "subir_foto", "crear_compra", "actualizar_estado"
    ] = Field(..., description="Tipo de operación")
    ticket_id: int = Field(..., description="ID del ticket asociado")
    timestamp: datetime = Field(..., description="Timestamp de cuando se realizó la operación")
    datos: dict = Field(..., description="Datos de la operación (varía según el tipo)")


class ResultadoOperacion(BaseModel):
    """Resultado de procesar una operación offline."""

    id: str = Field(..., description="ID de la operación")
    status: Literal["success", "failed", "conflict"] = Field(
        ..., description="Estado del procesamiento"
    )
    message: str = Field(..., description="Mensaje descriptivo")
    resource_id: int | None = Field(None, description="ID del recurso creado (si aplica)")
    details: dict | None = Field(None, description="Detalles adicionales del error o conflicto")


class SyncBatchRequest(BaseModel):
    """Request para sincronización por lotes."""

    operaciones: list[OperacionOffline] = Field(
        ..., description="Lista de operaciones a sincronizar"
    )


class SyncBatchResponse(BaseModel):
    """Response de sincronización por lotes."""

    total: int = Field(..., description="Total de operaciones procesadas")
    exitosas: int = Field(..., description="Operaciones exitosas")
    fallidas: int = Field(..., description="Operaciones fallidas")
    conflictos: int = Field(..., description="Operaciones con conflictos")
    resultados: list[ResultadoOperacion] = Field(
        ..., description="Resultados detallados por operación"
    )


@router.post("/sync/batch", response_model=SyncBatchResponse)
@limiter.limit("10/minute")
def sincronizar_operaciones_batch(
    request: Request, sync_request: SyncBatchRequest, db: Session = Depends(get_db)
):
    """
    Sincroniza múltiples operaciones offline en un solo request.

    Valida:
    - Timestamps no sean demasiado antiguos (>30 días)
    - Procesa operaciones en orden cronológico
    - Detecta conflictos (recurso modificado en servidor)
    - Retorna resultados: success, failed, conflicts

    Requirements: 25.13, 25.14, 25.15
    """
    from datetime import timedelta

    from app.utils.exceptions import ValidationError

    # Validar que no haya demasiadas operaciones
    if len(sync_request.operaciones) > 100:
        raise HTTPException(status_code=400, detail="Máximo 100 operaciones por batch")

    # Validar timestamps
    ahora = datetime.now()
    max_antiguedad = timedelta(days=30)

    for op in sync_request.operaciones:
        if ahora - op.timestamp > max_antiguedad:
            raise HTTPException(
                status_code=400,
                detail=f"Operación {op.id} demasiado antigua (>30 días). No se puede sincronizar.",
            )

    # Ordenar operaciones por timestamp (cronológico)
    operaciones_ordenadas = sorted(sync_request.operaciones, key=lambda x: x.timestamp)

    resultados = []
    exitosas = 0
    fallidas = 0
    conflictos = 0

    for op in operaciones_ordenadas:
        try:
            # Verificar que el ticket existe
            ticket = db.query(Ticket).filter(Ticket.id == op.ticket_id).first()
            if not ticket:
                resultados.append(
                    ResultadoOperacion(
                        id=op.id,
                        status="failed",
                        message=f"Ticket {op.ticket_id} no encontrado",
                        details={"error": "resource_not_found"},
                    )
                )
                fallidas += 1
                continue

            # Detectar conflictos: si el ticket fue modificado después del timestamp de la operación
            if ticket.fecha_actualizacion and ticket.fecha_actualizacion > op.timestamp:
                resultados.append(
                    ResultadoOperacion(
                        id=op.id,
                        status="conflict",
                        message=f"Ticket {op.ticket_id} fue modificado en el servidor después de esta operación",
                        details={
                            "server_updated_at": ticket.fecha_actualizacion.isoformat(),
                            "operation_timestamp": op.timestamp.isoformat(),
                        },
                    )
                )
                conflictos += 1
                continue

            # Procesar según tipo de operación
            if op.tipo == "crear_proceso":
                # Validar datos requeridos
                if "nombre" not in op.datos:
                    raise ValidationError("Campo 'nombre' requerido para crear_proceso")

                nuevo_proceso = TicketProceso(
                    ticket_id=op.ticket_id,
                    nombre=op.datos["nombre"],
                    descripcion=op.datos.get("descripcion"),
                    mecanico=op.datos.get("mecanico"),
                    foto_url=op.datos.get("foto_url"),
                )
                db.add(nuevo_proceso)
                db.flush()

                resultados.append(
                    ResultadoOperacion(
                        id=op.id,
                        status="success",
                        message="Proceso creado exitosamente",
                        resource_id=nuevo_proceso.id,
                    )
                )
                exitosas += 1

            elif op.tipo == "crear_repuesto":
                # Validar datos requeridos
                if "nombre" not in op.datos or "cantidad" not in op.datos:
                    raise ValidationError(
                        "Campos 'nombre' y 'cantidad' requeridos para crear_repuesto"
                    )

                nuevo_repuesto = TicketRepuesto(
                    ticket_id=op.ticket_id,
                    nombre=op.datos["nombre"],
                    cantidad=op.datos["cantidad"],
                    marca_referencia=op.datos.get("marca_referencia"),
                    proceso_id=op.datos.get("proceso_id"),
                )
                db.add(nuevo_repuesto)
                db.flush()

                resultados.append(
                    ResultadoOperacion(
                        id=op.id,
                        status="success",
                        message="Repuesto creado exitosamente",
                        resource_id=nuevo_repuesto.id,
                    )
                )
                exitosas += 1

            elif op.tipo == "subir_foto":
                # Validar datos requeridos
                if "archivo_url" not in op.datos:
                    raise ValidationError("Campo 'archivo_url' requerido para subir_foto")

                nueva_foto = TicketFoto(
                    ticket_id=op.ticket_id,
                    tipo=op.datos.get("tipo", "OTRA"),
                    archivo_url=op.datos["archivo_url"],
                    descripcion=op.datos.get("descripcion"),
                )
                db.add(nueva_foto)
                db.flush()

                resultados.append(
                    ResultadoOperacion(
                        id=op.id,
                        status="success",
                        message="Foto subida exitosamente",
                        resource_id=nueva_foto.id,
                    )
                )
                exitosas += 1

            elif op.tipo == "crear_compra":
                # Validar datos requeridos
                if "descripcion" not in op.datos or "valor" not in op.datos:
                    raise ValidationError(
                        "Campos 'descripcion' y 'valor' requeridos para crear_compra"
                    )

                if op.datos["valor"] <= 0:
                    raise ValidationError("El valor debe ser mayor a 0")

                # Usar servicio para crear compra con movimiento
                ticket_service = TicketService(db)
                compra = ticket_service.crear_compra_con_movimiento(
                    ticket=ticket,
                    descripcion=op.datos["descripcion"],
                    valor=op.datos["valor"],
                    responsable=op.datos.get("responsable"),
                    nota=op.datos.get("nota"),
                    soporte_url=op.datos.get("soporte_url"),
                )
                db.flush()

                resultados.append(
                    ResultadoOperacion(
                        id=op.id,
                        status="success",
                        message="Compra creada exitosamente",
                        resource_id=compra.id,
                    )
                )
                exitosas += 1

            elif op.tipo == "actualizar_estado":
                # Validar datos requeridos
                if "estado" not in op.datos:
                    raise ValidationError("Campo 'estado' requerido para actualizar_estado")

                nuevo_estado = op.datos["estado"].upper()
                estado_actual = ticket.estado

                # Validar transición
                permitidos = TRANSICIONES_VALIDAS.get(estado_actual, [])
                if nuevo_estado not in permitidos and nuevo_estado != estado_actual:
                    raise ValidationError(
                        f"Transición inválida: {estado_actual} → {nuevo_estado}. "
                        f"Desde {estado_actual} solo se puede pasar a: {permitidos or ['ninguno']}"
                    )

                if nuevo_estado != estado_actual:
                    ticket.estado = nuevo_estado
                    ticket.fecha_actualizacion = datetime.now()

                    if nuevo_estado == "FINALIZADO":
                        ticket_service = TicketService(db)
                        ticket_service.finalizar_ticket(ticket)

                resultados.append(
                    ResultadoOperacion(
                        id=op.id,
                        status="success",
                        message=f"Estado actualizado a {nuevo_estado}",
                        resource_id=ticket.id,
                    )
                )
                exitosas += 1

            else:
                resultados.append(
                    ResultadoOperacion(
                        id=op.id,
                        status="failed",
                        message=f"Tipo de operación desconocido: {op.tipo}",
                        details={"error": "unknown_operation_type"},
                    )
                )
                fallidas += 1

        except ValidationError as e:
            resultados.append(
                ResultadoOperacion(
                    id=op.id,
                    status="failed",
                    message=str(e),
                    details={"error": "validation_error", "details": e.details},
                )
            )
            fallidas += 1
            db.rollback()

        except Exception as e:
            resultados.append(
                ResultadoOperacion(
                    id=op.id,
                    status="failed",
                    message=f"Error al procesar operación: {str(e)}",
                    details={"error": "processing_error"},
                )
            )
            fallidas += 1
            db.rollback()

    # Commit todas las operaciones exitosas
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar cambios: {str(e)}")

    return SyncBatchResponse(
        total=len(operaciones_ordenadas),
        exitosas=exitosas,
        fallidas=fallidas,
        conflictos=conflictos,
        resultados=resultados,
    )


@router.get("/economia-hoy")
def economia_hoy_mobile(fecha: str | None = None, db: Session = Depends(get_db)):
    """Resumen económico del día para el panel admin móvil."""
    from datetime import date

    if fecha:
        try:
            hoy = date.fromisoformat(fecha)
        except ValueError:
            hoy = date.today()
    else:
        hoy = date.today()

    movimientos = (
        db.query(MovimientoCaja).filter(func.date(MovimientoCaja.fecha_creacion) == hoy).all()
    )

    anticipos = sum(m.valor for m in movimientos if m.tipo == TipoMovimiento.INGRESO_ANTICIPO)
    finales = sum(m.valor for m in movimientos if m.tipo == TipoMovimiento.INGRESO_FINAL)
    rapidos = sum(m.valor for m in movimientos if m.tipo == TipoMovimiento.INGRESO_RAPIDO)
    ingresos = anticipos + finales + rapidos
    gastos = sum(m.valor for m in movimientos if m.tipo == TipoMovimiento.EGRESO)

    tickets_hoy = (
        db.query(Ticket)
        .filter(
            func.date(Ticket.fecha_ingreso) == hoy, Ticket.estado.in_(["FINALIZADO", "ENTREGADO"])
        )
        .count()
    )

    ultimos = sorted(movimientos, key=lambda m: m.fecha_creacion or "", reverse=True)[:5]

    return {
        "fecha": str(hoy),
        "total_ingresos": float(ingresos),
        "total_gastos": float(gastos),
        "saldo_caja": float(ingresos - gastos),
        "tickets_finalizados": tickets_hoy,
        "desglose_ingresos": {
            "anticipos": float(anticipos),
            "finales": float(finales),
            "rapidos": float(rapidos),
        },
        "ultimos_movimientos": [
            {
                "tipo": m.tipo,
                "valor": float(m.valor),
                "concepto": m.concepto or m.tipo,
                "placa": m.placa or "",
            }
            for m in ultimos
        ],
    }
