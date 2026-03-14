import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db as get_db
from app.seguridad.dependencias import requerir_password_admin

FOTOS_DIR = os.path.join("uploads", "fotos")
os.makedirs(FOTOS_DIR, exist_ok=True)
from app.modelos.ticket import Ticket

router = APIRouter(prefix="/api/mobile", tags=["Mobile API"], dependencies=[Depends(requerir_password_admin)])


# ===== SCHEMAS PARA MOBILE =====

class TicketListResponse(BaseModel):
    id: int
    ticket_codigo: str
    placa: str
    motivo_visita: str
    estado: str
    fecha_ingreso: datetime
    nombre_propietario: Optional[str] = None
    telefono_propietario: Optional[str] = None
    
    class Config:
        from_attributes = True


class TicketDetailResponse(BaseModel):
    id: int
    ticket_codigo: str
    placa: str
    motivo_visita: str
    estado: str
    fecha_ingreso: datetime
    observaciones_recepcion: Optional[str] = None
    kilometraje: Optional[int] = None
    estado_inicial: Optional[str] = None
    anticipo_recibido: int
    total_servicio: Optional[int] = None
    saldo_pendiente: Optional[int] = None
    nombre_propietario: Optional[str] = None
    telefono_propietario: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProcesoResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    mecanico: Optional[str] = None
    
    class Config:
        from_attributes = True


class RepuestoResponse(BaseModel):
    id: int
    nombre: str
    cantidad: int
    marca_referencia: Optional[str] = None
    
    class Config:
        from_attributes = True


class FotoResponse(BaseModel):
    id: int
    tipo: str
    archivo_url: str
    descripcion: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProcesoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    mecanico: Optional[str] = None


class RepuestoCreate(BaseModel):
    nombre: str
    cantidad: int = 1
    marca_referencia: Optional[str] = None
    proceso_id: Optional[int] = None


class ActualizarEstadoTicket(BaseModel):
    estado: str


# ===== ENDPOINTS =====

@router.get("/tickets", response_model=List[TicketListResponse])
def listar_tickets_mobile(
    estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Ticket)
    if estado:
        query = query.filter(Ticket.estado == estado)
    tickets = query.order_by(Ticket.fecha_ingreso.desc()).all()

    result = []
    for ticket in tickets:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
        result.append(TicketListResponse(
            id=ticket.id,
            ticket_codigo=ticket.ticket_codigo,
            placa=ticket.placa,
            motivo_visita=ticket.motivo_visita,
            estado=ticket.estado,
            fecha_ingreso=ticket.fecha_ingreso,
            nombre_propietario=vehiculo.nombre_propietario if vehiculo else None,
            telefono_propietario=vehiculo.telefono_propietario if vehiculo else None,
        ))
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


@router.get("/tickets/{ticket_id}/procesos", response_model=List[ProcesoResponse])
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
def crear_proceso_mobile(
    ticket_id: int,
    proceso: ProcesoCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo proceso para un ticket
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    if ticket.estado not in ["ABIERTO", "EN_PROCESO"]:
        raise HTTPException(status_code=400, detail="No se pueden agregar procesos a un ticket finalizado")
    
    nuevo_proceso = TicketProceso(
        ticket_id=ticket_id,
        nombre=proceso.nombre,
        descripcion=proceso.descripcion,
        mecanico=proceso.mecanico
    )
    
    db.add(nuevo_proceso)
    db.commit()
    db.refresh(nuevo_proceso)
    
    return nuevo_proceso


@router.get("/tickets/{ticket_id}/repuestos", response_model=List[RepuestoResponse])
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
def crear_repuesto_mobile(
    ticket_id: int,
    repuesto: RepuestoCreate,
    db: Session = Depends(get_db)
):
    """
    Agrega un repuesto a un ticket
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    if ticket.estado not in ["ABIERTO", "EN_PROCESO"]:
        raise HTTPException(status_code=400, detail="No se pueden agregar repuestos a un ticket finalizado")
    
    nuevo_repuesto = TicketRepuesto(
        ticket_id=ticket_id,
        nombre=repuesto.nombre,
        cantidad=repuesto.cantidad,
        marca_referencia=repuesto.marca_referencia,
        proceso_id=repuesto.proceso_id
    )
    
    db.add(nuevo_repuesto)
    db.commit()
    db.refresh(nuevo_repuesto)
    
    return nuevo_repuesto


@router.get("/tickets/{ticket_id}/fotos", response_model=List[FotoResponse])
def listar_fotos_mobile(ticket_id: int, db: Session = Depends(get_db)):
    """
    Lista todas las fotos de un ticket
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    fotos = db.query(TicketFoto).filter(TicketFoto.ticket_id == ticket_id).all()
    return fotos


@router.patch("/tickets/{ticket_id}/estado")
def actualizar_estado_mobile(
    ticket_id: int,
    data: ActualizarEstadoTicket,
    db: Session = Depends(get_db)
):
    """
    Actualiza el estado de un ticket.
    Estados válidos: ABIERTO, EN_PROCESO, FINALIZADO, ENTREGADO
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    estados_validos = ["ABIERTO", "EN_PROCESO", "FINALIZADO", "ENTREGADO"]
    if data.estado not in estados_validos:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Debe ser uno de: {', '.join(estados_validos)}")

    estado_anterior = ticket.estado
    ticket.estado = data.estado
    ticket.fecha_actualizacion = datetime.now()

    # Al finalizar: delegar a la función compartida
    if data.estado == "FINALIZADO" and estado_anterior != "FINALIZADO":
        ticket.estado = estado_anterior  # revert so service sets it
        svc_finalizar_ticket(ticket, db)

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
    
    total_procesos = db.query(TicketProceso).filter(TicketProceso.ticket_id == ticket_id).count()
    total_repuestos = db.query(TicketRepuesto).filter(TicketRepuesto.ticket_id == ticket_id).count()
    total_fotos = db.query(TicketFoto).filter(TicketFoto.ticket_id == ticket_id).count()
    total_compras = db.query(TicketCompra).filter(TicketCompra.ticket_id == ticket_id).count()
    
    # Calcular total de egresos
    compras = db.query(TicketCompra).filter(TicketCompra.ticket_id == ticket_id).all()
    total_egresos = sum(c.valor for c in compras)
    
    # Calcular total de cobros
    cobros = db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket_id).all()
    total_cobros = sum(c.valor for c in cobros)
    
    return {
        "ticket_id": ticket.id,
        "ticket_codigo": ticket.ticket_codigo,
        "placa": ticket.placa,
        "estado": ticket.estado,
        "contadores": {
            "procesos": total_procesos,
            "repuestos": total_repuestos,
            "fotos": total_fotos,
            "compras": total_compras
        },
        "finanzas": {
            "anticipo": ticket.anticipo_recibido,
            "total_egresos": total_egresos,
            "total_cobros": total_cobros,
            "total_servicio": ticket.total_servicio,
            "saldo_pendiente": ticket.saldo_pendiente
        }
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
            "entregados": tickets_entregados
        }
    }


@router.post("/tickets/{ticket_id}/fotos")
async def subir_foto_mobile(
    ticket_id: int,
    file: UploadFile = File(...),
    tipo: str = Form(default="OTRA"),
    descripcion: Optional[str] = Form(default=None),
    db: Session = Depends(get_db)
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


class EntregarTicketData(BaseModel):
    confirmado_entrega_por: str
    observaciones_finales: Optional[str] = None
    recomendaciones: Optional[str] = None
    proximo_mantenimiento: Optional[str] = None


@router.post("/tickets/{ticket_id}/entregar")
def entregar_ticket_mobile(
    ticket_id: int,
    data: EntregarTicketData,
    db: Session = Depends(get_db)
):
    """Marca un ticket como entregado desde la app móvil"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.estado != "FINALIZADO":
        raise HTTPException(status_code=400, detail="Solo se pueden entregar tickets en estado FINALIZADO")

    ticket.estado = "ENTREGADO"
    ticket.confirmado_entrega_por = data.confirmado_entrega_por
    ticket.observaciones_finales = data.observaciones_finales
    ticket.recomendaciones = data.recomendaciones
    ticket.proximo_mantenimiento = data.proximo_mantenimiento
    ticket.fecha_entrega = datetime.now()
    ticket.fecha_actualizacion = datetime.now()

    db.commit()
    db.refresh(ticket)
    return {"message": "Ticket entregado correctamente", "estado": ticket.estado}


@router.delete("/tickets/{ticket_id}/fotos/{foto_id}")
def eliminar_foto_mobile(
    ticket_id: int,
    foto_id: int,
    db: Session = Depends(get_db)
):
    """Elimina una foto de un ticket"""
    foto = db.query(TicketFoto).filter(
        TicketFoto.id == foto_id,
        TicketFoto.ticket_id == ticket_id
    ).first()
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

class CompraResponse(BaseModel):
    id: int
    descripcion: str
    valor: int
    soporte_url: Optional[str] = None
    nota: Optional[str] = None
    responsable: Optional[str] = None

    class Config:
        from_attributes = True


class CompraCreate(BaseModel):
    descripcion: str
    valor: int
    nota: Optional[str] = None
    responsable: Optional[str] = None


@router.get("/tickets/{ticket_id}/compras", response_model=List[CompraResponse])
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
    nota: Optional[str] = Form(default=None),
    responsable: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.estado not in ["ABIERTO", "EN_PROCESO"]:
        raise HTTPException(status_code=400, detail="No se pueden agregar compras a un ticket finalizado")
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

    compra = TicketCompra(
        ticket_id=ticket_id,
        descripcion=descripcion,
        valor=valor,
        nota=nota,
        responsable=responsable,
        soporte_url=soporte_url,
    )
    db.add(compra)
    db.flush()

    movimiento = MovimientoCaja(
        tipo=TipoMovimiento.EGRESO,
        ticket_id=ticket.id,
        ticket_codigo=ticket.ticket_codigo,
        placa=ticket.placa,
        estado_ticket=EstadoTicket.EN_PROCESO,
        valor=valor,
        categoria_egreso=CategoriaEgreso.OTRO,
        concepto=descripcion,
        responsable=responsable,
        observacion=nota,
        soporte_url=soporte_url,
        creado_por=responsable,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(compra)
    return compra


@router.delete("/tickets/{ticket_id}/compras/{compra_id}")
def eliminar_compra_mobile(ticket_id: int, compra_id: int, db: Session = Depends(get_db)):
    compra = db.query(TicketCompra).filter(
        TicketCompra.id == compra_id,
        TicketCompra.ticket_id == ticket_id
    ).first()
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

class CobroResponse(BaseModel):
    id: int
    concepto: str
    valor: int

    class Config:
        from_attributes = True


class CobroCreate(BaseModel):
    concepto: str
    valor: int


@router.get("/tickets/{ticket_id}/cobros", response_model=List[CobroResponse])
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
    cobro = db.query(TicketCobro).filter(
        TicketCobro.id == cobro_id,
        TicketCobro.ticket_id == ticket_id
    ).first()
    if not cobro:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    db.delete(cobro)
    db.commit()


# ── Finanzas ─────────────────────────────────────────────────────────────────

class ActualizarFinanzasData(BaseModel):
    total_servicio: int
    metodo_pago_final: Optional[str] = None


@router.patch("/tickets/{ticket_id}/finanzas")
def actualizar_finanzas_mobile(ticket_id: int, data: ActualizarFinanzasData, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    ticket.total_servicio = data.total_servicio
    ticket.metodo_pago_final = data.metodo_pago_final
    # Recalcular saldo pendiente
    cobros = db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket_id).all()
    total_cobros = sum(c.valor for c in cobros)
    ticket.saldo_pendiente = data.total_servicio - (ticket.anticipo_recibido or 0) - total_cobros
    db.commit()
    return {"ok": True, "saldo_pendiente": ticket.saldo_pendiente}
