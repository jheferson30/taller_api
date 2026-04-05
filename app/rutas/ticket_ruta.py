import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.seguridad.dependencias import requerir_password_admin
from app.esquemas.ticket_schema import (
    TicketCompraCrear,
    TicketCompraRespuesta,
    TicketCobroCrear,
    TicketCobroRespuesta,
    TicketEntregarPayload,
    TicketFinanzasActualizar,
    TicketFotoCrear,
    TicketFotoRespuesta,
    TicketObservacionesFinalesActualizar,
    TicketProcesoCrear,
    TicketProcesoRespuesta,
    TicketRepuestoCrear,
    TicketRepuestoRespuesta,
    TicketRespuesta,
    TicketResumenProcesoRespuesta,
)
from app.modelos.movimiento_caja import (
    CategoriaEgreso,
    EstadoTicket,
    MovimientoCaja,
    TipoMovimiento,
)
from app.modelos.ticket import Ticket
from app.modelos.vehiculo import Vehiculo
from app.modelos.ticket_cobro import TicketCobro
from app.modelos.ticket_compra import TicketCompra
from app.modelos.ticket_foto import TicketFoto
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.ticket_repuesto import TicketRepuesto
from app.servicios.ticket_service import TicketService
from app.utils.pdf_generator import generar_pdf_ticket_completo
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.configuracion.limiter import limiter
from app.servicios.twilio_whatsapp_service import TwilioWhatsAppService
from app.servicios.whatsapp_service import TipoEvento

router = APIRouter(prefix="/tickets", tags=["Tickets"], dependencies=[Depends(requerir_password_admin)])

# Router separado para el PDF del ticket (acepta auth por query param para compatibilidad móvil)
router_pdf = APIRouter(prefix="/tickets", tags=["Tickets"])

_whatsapp_service = TwilioWhatsAppService()

PROCESOS_RAPIDOS = [
    "Cambio de aceite",
    "Lavado de frenos",
    "Ajuste de frenos",
    "Revision general",
    "Cambio de bujia",
    "Ajuste de cadena",
    "Engrase general",
]


def _obtener_ticket_o_404(db: Session, ticket_id: int) -> Ticket:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


def _asegurar_editable(ticket: Ticket):
    if ticket.estado in ("FINALIZADO", "ENTREGADO"):
        raise HTTPException(status_code=400, detail="El ticket ya no permite edicion")


def _actualizar_estado_ticket(ticket: Ticket):
    if ticket.estado == "ABIERTO":
        ticket.estado = "EN_PROCESO"


@router.get("/procesos-rapidos")
def listar_procesos_rapidos():
    return {"items": PROCESOS_RAPIDOS}


@router.get("/abiertos", response_model=List[TicketRespuesta])
def listar_tickets_abiertos(
    db: Session = Depends(obtener_db),
    placa: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    query = db.query(Ticket).filter(Ticket.estado.in_(["ABIERTO", "EN_PROCESO"]))
    if placa:
        query = query.filter(Ticket.placa == placa.strip().upper())
    return query.order_by(Ticket.fecha_ingreso.desc()).offset(skip).limit(limit).all()


@router.get("/buscar", response_model=List[TicketRespuesta])
def buscar_tickets(
    db: Session = Depends(obtener_db),
    ticket_codigo: Optional[str] = Query(None),
    placa: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
):
    query = db.query(Ticket)
    if ticket_codigo:
        query = query.filter(Ticket.ticket_codigo == ticket_codigo.strip().upper())
    if placa:
        query = query.filter(Ticket.placa.ilike(f"%{placa.strip()}%"))
    if estado:
        query = query.filter(Ticket.estado == estado.upper())
    if fecha_desde:
        query = query.filter(Ticket.fecha_ingreso >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        # incluir todo el día hasta
        hasta = datetime.fromisoformat(fecha_hasta).replace(hour=23, minute=59, second=59)
        query = query.filter(Ticket.fecha_ingreso <= hasta)
    return query.order_by(Ticket.fecha_ingreso.desc()).limit(200).all()


@router.get("/{ticket_id}", response_model=TicketRespuesta)
def obtener_ticket(ticket_id: int, db: Session = Depends(obtener_db)):
    return _obtener_ticket_o_404(db, ticket_id)


@router.get("/{ticket_id}/resumen", response_model=TicketResumenProcesoRespuesta)
def obtener_resumen_ticket(ticket_id: int, db: Session = Depends(obtener_db)):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    procesos = db.query(TicketProceso).filter(TicketProceso.ticket_id == ticket_id).order_by(TicketProceso.fecha_creacion.asc()).all()
    repuestos = db.query(TicketRepuesto).filter(TicketRepuesto.ticket_id == ticket_id).order_by(TicketRepuesto.fecha_creacion.asc()).all()
    fotos = db.query(TicketFoto).filter(TicketFoto.ticket_id == ticket_id).order_by(TicketFoto.fecha_creacion.asc()).all()
    compras = db.query(TicketCompra).filter(TicketCompra.ticket_id == ticket_id).order_by(TicketCompra.fecha_creacion.asc()).all()
    cobros = db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket_id).order_by(TicketCobro.fecha_creacion.asc()).all()
    return {
        "ticket": ticket,
        "procesos": procesos,
        "repuestos": repuestos,
        "fotos": fotos,
        "compras": compras,
        "cobros": cobros,
    }


@router.post("/{ticket_id}/procesos", response_model=TicketProcesoRespuesta)
def agregar_proceso(
    ticket_id: int,
    datos: TicketProcesoCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    _actualizar_estado_ticket(ticket)
    proceso = TicketProceso(ticket_id=ticket_id, **datos.model_dump())
    db.add(proceso)
    db.commit()
    db.refresh(proceso)
    return proceso


@router.delete("/{ticket_id}/procesos/{proceso_id}")
def eliminar_proceso(
    ticket_id: int,
    proceso_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    proceso = db.query(TicketProceso).filter(TicketProceso.id == proceso_id, TicketProceso.ticket_id == ticket_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
    db.delete(proceso)
    db.commit()
    return {"ok": True}


@router.post("/{ticket_id}/repuestos", response_model=TicketRepuestoRespuesta)
def agregar_repuesto(
    ticket_id: int,
    datos: TicketRepuestoCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    _actualizar_estado_ticket(ticket)
    repuesto = TicketRepuesto(ticket_id=ticket_id, **datos.model_dump())
    db.add(repuesto)
    db.commit()
    db.refresh(repuesto)
    return repuesto


@router.delete("/{ticket_id}/repuestos/{repuesto_id}")
def eliminar_repuesto(
    ticket_id: int,
    repuesto_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    repuesto = db.query(TicketRepuesto).filter(TicketRepuesto.id == repuesto_id, TicketRepuesto.ticket_id == ticket_id).first()
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    
    # Usar servicio para eliminar repuesto con su compra asociada
    ticket_service = TicketService(db)
    ticket_service.eliminar_repuesto_con_compra(ticket, repuesto)
    db.commit()
    return {"ok": True}


@router.delete("/{ticket_id}/compras/{compra_id}")
def eliminar_compra(
    ticket_id: int,
    compra_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    compra = db.query(TicketCompra).filter(TicketCompra.id == compra_id, TicketCompra.ticket_id == ticket_id).first()
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    db.delete(compra)
    db.commit()
    return {"ok": True}


@router.post("/{ticket_id}/fotos", response_model=TicketFotoRespuesta)
def agregar_foto(
    ticket_id: int,
    datos: TicketFotoCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    _actualizar_estado_ticket(ticket)
    foto = TicketFoto(ticket_id=ticket_id, **datos.model_dump())
    db.add(foto)
    db.commit()
    db.refresh(foto)
    return foto


@router.delete("/{ticket_id}/fotos/{foto_id}")
def eliminar_foto(
    ticket_id: int,
    foto_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    foto = db.query(TicketFoto).filter(TicketFoto.id == foto_id, TicketFoto.ticket_id == ticket_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    db.delete(foto)
    db.commit()
    return {"ok": True}


@router.post("/{ticket_id}/compras", response_model=TicketCompraRespuesta)
def agregar_compra(
    ticket_id: int,
    datos: TicketCompraCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    
    # Usar servicio para crear compra con movimiento
    ticket_service = TicketService(db)
    compra = ticket_service.crear_compra_con_movimiento(
        ticket=ticket,
        descripcion=datos.descripcion,
        valor=datos.valor,
        responsable=datos.responsable,
        nota=datos.nota,
        soporte_url=datos.soporte_url,
    )
    db.commit()
    db.refresh(compra)
    return compra


@router.post("/{ticket_id}/cobros", response_model=TicketCobroRespuesta)
def agregar_cobro(
    ticket_id: int,
    datos: TicketCobroCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    _actualizar_estado_ticket(ticket)

    cobro = TicketCobro(ticket_id=ticket_id, **datos.model_dump())
    db.add(cobro)
    db.commit()
    db.refresh(cobro)
    return cobro


@router.delete("/{ticket_id}/cobros/{cobro_id}")
def eliminar_cobro(
    ticket_id: int,
    cobro_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    cobro = db.query(TicketCobro).filter(TicketCobro.id == cobro_id, TicketCobro.ticket_id == ticket_id).first()
    if not cobro:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    db.delete(cobro)
    db.commit()
    return {"ok": True}


@router.put("/{ticket_id}/finanzas", response_model=TicketRespuesta)
def actualizar_finanzas_ticket(
    ticket_id: int,
    datos: TicketFinanzasActualizar,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    
    # Usar servicio para actualizar finanzas
    ticket_service = TicketService(db)
    ticket_service.actualizar_finanzas(
        ticket=ticket,
        total_servicio=datos.total_servicio,
        metodo_pago_final=datos.metodo_pago_final,
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.put("/{ticket_id}/observaciones-finales", response_model=TicketRespuesta)
def actualizar_observaciones_finales(
    ticket_id: int,
    datos: TicketObservacionesFinalesActualizar,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    _asegurar_editable(ticket)
    payload = datos.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        setattr(ticket, campo, valor)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/finalizar", response_model=TicketRespuesta)
def finalizar_ticket(
    ticket_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    if ticket.estado in ("FINALIZADO", "ENTREGADO"):
        return ticket
    
    # Usar servicio para finalizar ticket
    ticket_service = TicketService(db)
    ticket_service.finalizar_ticket(ticket)
    db.commit()
    db.refresh(ticket)
    
    # Fire-and-forget: notificación WhatsApp de finalización (req 3.1)
    try:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(
            _whatsapp_service.enviar_notificacion(TipoEvento.FINALIZACION, ticket, vehiculo, db)
        )
    except RuntimeError:
        pass  # No hay event loop activo (ej. en tests síncronos)
    except Exception:
        pass
    return ticket


@router_pdf.get("/{ticket_id}/pdf")
@limiter.limit("20/minute")
def generar_pdf_cliente(
    request: Request,
    ticket_id: int,
    token: Optional[str] = Query(None),
    x_admin_password: Optional[str] = Header(None, alias="X-Admin-Password"),
    db: Session = Depends(obtener_db),
):
    # Autenticación: acepta JWT (nuevo) o header X-Admin-Password o query param ?token= (legacy)
    jwt_user = getattr(request.state, "user", None)
    
    if not jwt_user:
        # Fallback legacy: verificar X-Admin-Password o token query param
        password_esperada = os.getenv("ADMIN_PASSWORD") or os.getenv("PDF_PASSWORD")
        admin_token = x_admin_password or token
        if not admin_token or not hmac.compare_digest(admin_token.encode("utf-8"), password_esperada.encode("utf-8")):
            raise HTTPException(status_code=401, detail="Autenticacion requerida")
    ticket = _obtener_ticket_o_404(db, ticket_id)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
    procesos = db.query(TicketProceso).filter(TicketProceso.ticket_id == ticket_id).order_by(TicketProceso.fecha_creacion.asc()).all()
    repuestos = db.query(TicketRepuesto).filter(TicketRepuesto.ticket_id == ticket_id).order_by(TicketRepuesto.fecha_creacion.asc()).all()
    fotos = db.query(TicketFoto).filter(TicketFoto.ticket_id == ticket_id).order_by(TicketFoto.fecha_creacion.asc()).all()
    cobros = db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket_id).order_by(TicketCobro.fecha_creacion.asc()).all()
    compras = db.query(TicketCompra).filter(TicketCompra.ticket_id == ticket_id).order_by(TicketCompra.fecha_creacion.asc()).all()

    # Convertir a diccionarios
    ticket_dict = {
        'ticket_codigo': ticket.ticket_codigo,
        'placa': ticket.placa,
        'estado': ticket.estado,
        'fecha_ingreso': ticket.fecha_ingreso.isoformat() if ticket.fecha_ingreso else None,
        'motivo_visita': ticket.motivo_visita,
        'observaciones_recepcion': ticket.observaciones_recepcion,
        'kilometraje': ticket.kilometraje,
        'estado_inicial': ticket.estado_inicial,
        'nombre_propietario': vehiculo.nombre_propietario if vehiculo else None,
        'telefono_propietario': vehiculo.telefono_propietario if vehiculo else None,
        'total_servicio': ticket.total_servicio or 0,
        'anticipo_recibido': ticket.anticipo_recibido or 0,
        'saldo_pendiente': ticket.saldo_pendiente or 0,
        'metodo_pago_final': ticket.metodo_pago_final,
        'observaciones_finales': ticket.observaciones_finales,
        'recomendaciones': ticket.recomendaciones,
        'proximo_mantenimiento': ticket.proximo_mantenimiento,
    }
    
    procesos_list = [{'nombre': p.nombre, 'mecanico': p.mecanico, 'descripcion': p.descripcion, 'foto_url': p.foto_url} for p in procesos]
    repuestos_list = [{'nombre': r.nombre, 'cantidad': r.cantidad, 'marca_referencia': r.marca_referencia} for r in repuestos]
    fotos_list = [{'tipo': f.tipo, 'archivo_url': f.archivo_url, 'descripcion': f.descripcion} for f in fotos]
    cobros_list = [{'concepto': c.concepto, 'valor': c.valor} for c in cobros]
    compras_list = [{'descripcion': c.descripcion, 'valor': c.valor, 'soporte_url': c.soporte_url, 'responsable': c.responsable} for c in compras]

    # Datos del taller
    cfg = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.id == 1).first()
    taller_data = {
        'nombre_taller': cfg.nombre_taller if cfg else 'Taller Mecánico',
        'direccion': cfg.direccion if cfg else '',
        'telefono': cfg.telefono if cfg else '',
        'nit': cfg.nit if cfg else '',
    }

    # Generar PDF con el nuevo generador
    pdf_bytes = generar_pdf_ticket_completo(ticket_dict, procesos_list, repuestos_list, fotos_list, cobros_list, compras_list, taller_data)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ticket_{ticket.ticket_codigo}.pdf"'},
    )


@router.post("/{ticket_id}/entregar", response_model=TicketRespuesta)
def marcar_entregado(
    ticket_id: int,
    datos: TicketEntregarPayload,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id)
    
    # Usar servicio para entregar ticket
    ticket_service = TicketService(db)
    ticket_service.entregar_ticket(
        ticket=ticket,
        confirmado_entrega_por=datos.confirmado_entrega_por,
        firma_entrega_url=datos.firma_entrega_url,
        observaciones_finales=datos.observaciones_finales,
        recomendaciones=datos.recomendaciones,
        proximo_mantenimiento=datos.proximo_mantenimiento,
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
    return ticket
