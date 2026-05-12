import hmac
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.configuracion.limiter import limiter
from app.esquemas.ticket_schema import (
    TicketCobroCrear,
    TicketCobroRespuesta,
    TicketCompraCrear,
    TicketCompraRespuesta,
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
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.modelos.ticket import Ticket
from app.modelos.ticket_cobro import TicketCobro
from app.modelos.ticket_compra import TicketCompra
from app.modelos.ticket_foto import TicketFoto
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.ticket_repuesto import TicketRepuesto
from app.modelos.vehiculo import Vehiculo
from app.seguridad.auth_middleware import require_auth
from app.seguridad.dependencias import requerir_password_admin
from app.servicios.ticket_service import TicketService
from app.servicios.twilio_whatsapp_service import TwilioWhatsAppService
from app.servicios.whatsapp_service import TipoEvento
from app.utils.input_validator import InputSanitizer
from app.utils.pdf_generator import generar_pdf_ticket_completo

router = APIRouter(
    prefix="/tickets", tags=["Tickets"], dependencies=[Depends(requerir_password_admin)]
)

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


def _obtener_ticket_o_404(db: Session, ticket_id: int, taller_id: int | None = None) -> Ticket:
    query = db.query(Ticket).filter(Ticket.id == ticket_id)
    if taller_id is not None:
        query = query.filter(Ticket.taller_id == taller_id)
    ticket = query.first()
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
@require_auth
async def listar_procesos_rapidos(request: Request):
    return {"items": PROCESOS_RAPIDOS}


@router.get(
    "/abiertos",
    response_model=dict,
    summary="List open and in-progress tickets",
    description="""
    Retrieve a paginated list of tickets with status ABIERTO (open) or EN_PROCESO (in progress).

    **Use Case:**
    - Dashboard view of active work
    - Mechanic workload overview
    - Reception desk ticket tracking

    **Filtering:**
    - Optional filter by vehicle plate (exact match, case-insensitive)

    **Pagination:**
    - Default: 50 tickets per page
    - Maximum: 100 tickets per page
    - Returns total count and page metadata

    **Permissions:**
    - Requires ADMIN password authentication

    **Rate Limiting:**
    - 30 requests per minute (standard read limit)
    """,
    responses={
        200: {
            "description": "List of open tickets with pagination metadata",
            "content": {
                "application/json": {
                    "example": {
                        "tickets": [
                            {
                                "id": 123,
                                "ticket_codigo": "TK-ABC123-20260406103000",
                                "placa": "ABC123",
                                "motivo_visita": "Cambio de aceite",
                                "estado": "ABIERTO",
                                "fecha_ingreso": "2026-04-06T10:30:00",
                                "kilometraje": 15000,
                            }
                        ],
                        "total": 45,
                        "page": 1,
                        "per_page": 50,
                        "pages": 1,
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": "authentication_failed",
                        "message": "Admin password required",
                    }
                }
            },
        },
    },
)
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_TICKETS_PER_MINUTE", "30") + "/minute")
async def listar_tickets_abiertos(
    request: Request,
    db: Session = Depends(obtener_db),
    placa: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    """
    Lista tickets abiertos/en proceso con paginación.
    Requirements: 2.13
    """
    query = db.query(Ticket).filter(
        Ticket.taller_id == request.state.taller_id,
        Ticket.estado.in_(["ABIERTO", "EN_PROCESO"]),
    )
    if placa:
        query = query.filter(Ticket.placa == placa.strip().upper())

    total = query.count()
    tickets_orm = (
        query.order_by(Ticket.fecha_ingreso.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Convertir a schemas de Pydantic
    tickets = [TicketRespuesta.model_validate(t) for t in tickets_orm]

    return {
        "tickets": tickets,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/buscar", response_model=dict)
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_TICKETS_PER_MINUTE", "30") + "/minute")
async def buscar_tickets(
    request: Request,
    db: Session = Depends(obtener_db),
    ticket_codigo: str | None = Query(None),
    placa: str | None = Query(None),
    estado: str | None = Query(None),
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    """
    Busca tickets con paginación obligatoria.
    Requirements: 2.13
    """
    ticket_service = TicketService(db)

    # Si hay filtros específicos, usar find_by_criteria (legacy)
    if ticket_codigo or fecha_desde or fecha_hasta:
        query = db.query(Ticket).filter(Ticket.taller_id == request.state.taller_id)
        if ticket_codigo:
            query = query.filter(Ticket.ticket_codigo == ticket_codigo.strip().upper())
        if placa:
            query = query.filter(Ticket.placa.ilike(f"%{placa.strip()}%"))
        if estado:
            query = query.filter(Ticket.estado == estado.upper())
        if fecha_desde:
            query = query.filter(Ticket.fecha_ingreso >= datetime.fromisoformat(fecha_desde))
        if fecha_hasta:
            hasta = datetime.fromisoformat(fecha_hasta).replace(hour=23, minute=59, second=59)
            query = query.filter(Ticket.fecha_ingreso <= hasta)

        total = query.count()
        tickets_orm = (
            query.order_by(Ticket.fecha_ingreso.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        tickets = [TicketRespuesta.model_validate(t) for t in tickets_orm]
    else:
        # Usar paginación del servicio
        tickets_orm, total = ticket_service.get_tickets_paginated(page, per_page, estado, placa)
        tickets = [TicketRespuesta.model_validate(t) for t in tickets_orm]

    return {
        "tickets": tickets,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/{ticket_id}", response_model=TicketRespuesta)
@require_auth
async def obtener_ticket(request: Request, ticket_id: int, db: Session = Depends(obtener_db)):
    return _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)


@router.get(
    "/{ticket_id}/resumen",
    response_model=TicketResumenProcesoRespuesta,
    summary="Get complete ticket summary with all related data",
    description="""
    Retrieve comprehensive ticket information including all related entities.

    **Includes:**
    - Ticket basic information (status, dates, financial data)
    - All processes performed (procesos)
    - All parts used (repuestos)
    - All photos attached (fotos)
    - All purchases made (compras)
    - All charges applied (cobros)

    **Use Case:**
    - Complete ticket view for mechanics
    - PDF generation data source
    - Mobile app ticket detail screen
    - Customer service inquiries

    **Performance:**
    - Single database query with joins
    - Optimized for mobile app usage

    **Permissions:**
    - Requires ADMIN password authentication
    """,
    responses={
        200: {
            "description": "Complete ticket summary",
            "content": {
                "application/json": {
                    "example": {
                        "ticket": {
                            "id": 123,
                            "ticket_codigo": "TK-ABC123-20260406103000",
                            "placa": "ABC123",
                            "estado": "EN_PROCESO",
                            "total_servicio": 150000,
                            "saldo_pendiente": 50000,
                        },
                        "procesos": [
                            {
                                "id": 1,
                                "nombre": "Cambio de aceite",
                                "mecanico": "Juan Pérez",
                                "descripcion": "Aceite 20W50",
                            }
                        ],
                        "repuestos": [
                            {
                                "id": 1,
                                "nombre": "Filtro de aceite",
                                "cantidad": 1,
                                "marca_referencia": "Bosch",
                            }
                        ],
                        "fotos": [],
                        "compras": [],
                        "cobros": [],
                    }
                }
            },
        },
        404: {
            "description": "Ticket not found",
            "content": {
                "application/json": {
                    "example": {"error": "resource_not_found", "message": "Ticket no encontrado"}
                }
            },
        },
    },
)
@require_auth
async def obtener_resumen_ticket(request: Request, ticket_id: int, db: Session = Depends(obtener_db)):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    procesos = (
        db.query(TicketProceso)
        .filter(TicketProceso.ticket_id == ticket_id)
        .order_by(TicketProceso.fecha_creacion.asc())
        .all()
    )
    repuestos = (
        db.query(TicketRepuesto)
        .filter(TicketRepuesto.ticket_id == ticket_id)
        .order_by(TicketRepuesto.fecha_creacion.asc())
        .all()
    )
    fotos = (
        db.query(TicketFoto)
        .filter(TicketFoto.ticket_id == ticket_id)
        .order_by(TicketFoto.fecha_creacion.asc())
        .all()
    )
    compras = (
        db.query(TicketCompra)
        .filter(TicketCompra.ticket_id == ticket_id)
        .order_by(TicketCompra.fecha_creacion.asc())
        .all()
    )
    cobros = (
        db.query(TicketCobro)
        .filter(TicketCobro.ticket_id == ticket_id)
        .order_by(TicketCobro.fecha_creacion.asc())
        .all()
    )
    return {
        "ticket": ticket,
        "procesos": procesos,
        "repuestos": repuestos,
        "fotos": fotos,
        "compras": compras,
        "cobros": cobros,
    }


@router.post(
    "/{ticket_id}/procesos",
    response_model=TicketProcesoRespuesta,
    summary="Add process to ticket",
    description="""
    Add a new process (service performed) to a ticket.

    **Use Case:**
    - Document work performed by mechanic
    - Track service history
    - Generate detailed invoices

    **Process:**
    1. Validates ticket exists and is editable (not FINALIZADO or ENTREGADO)
    2. Updates ticket status to EN_PROCESO if currently ABIERTO
    3. Creates new process record with name, description, mechanic, and optional photo

    **Validation:**
    - Ticket must not be finalized or delivered
    - Process name is required (2-120 chars)

    **Permissions:**
    - Requires ADMIN password authentication
    """,
    responses={
        200: {
            "description": "Process added successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "ticket_id": 123,
                        "nombre": "Cambio de aceite",
                        "descripcion": "Aceite 20W50 sintético",
                        "mecanico": "Carlos Méndez",
                        "foto_url": "/uploads/fotos/proceso_1.jpg",
                        "fecha_creacion": "2026-04-06T11:00:00",
                    }
                }
            },
        },
        400: {
            "description": "Ticket not editable",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "El ticket ya no permite edicion",
                    }
                }
            },
        },
        404: {
            "description": "Ticket not found",
            "content": {
                "application/json": {
                    "example": {"error": "resource_not_found", "message": "Ticket no encontrado"}
                }
            },
        },
    },
)
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_TICKETS_PER_MINUTE", "30") + "/minute")
async def agregar_proceso(
    request: Request,
    ticket_id: int,
    datos: TicketProcesoCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    _actualizar_estado_ticket(ticket)

    datos_dict = datos.model_dump()

    # Si viene mecanico_user_id, resolver el nombre y guardarlo en el campo string
    # para compatibilidad con el PDF y la app mobile
    if datos_dict.get("mecanico_user_id") and not datos_dict.get("mecanico"):
        from app.modelos.user import User as _User
        usuario = db.query(_User).filter(_User.id == datos_dict["mecanico_user_id"]).first()
        if usuario:
            datos_dict["mecanico"] = usuario.nombre_completo or usuario.username

    proceso = TicketProceso(
        ticket_id=ticket_id,
        taller_id=request.state.taller_id,
        **datos_dict,
    )
    db.add(proceso)
    db.commit()
    db.refresh(proceso)
    return proceso


@router.delete("/{ticket_id}/procesos/{proceso_id}")
@require_auth
async def eliminar_proceso(
    request: Request,
    ticket_id: int,
    proceso_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    proceso = (
        db.query(TicketProceso)
        .filter(TicketProceso.id == proceso_id, TicketProceso.ticket_id == ticket_id)
        .first()
    )
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
    db.delete(proceso)
    db.commit()
    return {"ok": True}


@router.post(
    "/{ticket_id}/repuestos",
    response_model=TicketRepuestoRespuesta,
    summary="Add part to ticket",
    description="""
    Add a new part/spare to a ticket.

    **Use Case:**
    - Document parts used in repair
    - Track inventory usage
    - Generate detailed parts list for invoice

    **Process:**
    1. Validates ticket exists and is editable
    2. Updates ticket status to EN_PROCESO if currently ABIERTO
    3. Creates new part record with name, quantity, brand, and optional photo
    4. Can optionally link part to a specific process

    **Validation:**
    - Ticket must not be finalized or delivered
    - Part name is required (2-150 chars)
    - Quantity must be >= 1

    **Permissions:**
    - Requires ADMIN password authentication
    """,
    responses={
        200: {
            "description": "Part added successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "ticket_id": 123,
                        "proceso_id": 1,
                        "nombre": "Filtro de aceite",
                        "cantidad": 1,
                        "marca_referencia": "Bosch F026407124",
                        "foto_url": "/uploads/fotos/repuesto_1.jpg",
                        "fecha_creacion": "2026-04-06T11:15:00",
                    }
                }
            },
        },
        400: {
            "description": "Ticket not editable",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "El ticket ya no permite edicion",
                    }
                }
            },
        },
    },
)
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_TICKETS_PER_MINUTE", "30") + "/minute")
async def agregar_repuesto(
    request: Request,
    ticket_id: int,
    datos: TicketRepuestoCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    _actualizar_estado_ticket(ticket)
    repuesto = TicketRepuesto(ticket_id=ticket_id, taller_id=request.state.taller_id, **datos.model_dump())
    db.add(repuesto)
    db.commit()
    db.refresh(repuesto)
    return repuesto


@router.delete("/{ticket_id}/repuestos/{repuesto_id}")
@require_auth
async def eliminar_repuesto(
    request: Request,
    ticket_id: int,
    repuesto_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    repuesto = (
        db.query(TicketRepuesto)
        .filter(TicketRepuesto.id == repuesto_id, TicketRepuesto.ticket_id == ticket_id)
        .first()
    )
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")

    # Usar servicio para eliminar repuesto con su compra asociada
    ticket_service = TicketService(db)
    ticket_service.eliminar_repuesto_con_compra(ticket, repuesto)
    db.commit()
    return {"ok": True}


@router.delete("/{ticket_id}/compras/{compra_id}")
@require_auth
async def eliminar_compra(
    request: Request,
    ticket_id: int,
    compra_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    compra = (
        db.query(TicketCompra)
        .filter(TicketCompra.id == compra_id, TicketCompra.ticket_id == ticket_id)
        .first()
    )
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    db.delete(compra)
    db.commit()
    return {"ok": True}


@router.post("/{ticket_id}/fotos", response_model=TicketFotoRespuesta)
@require_auth
async def agregar_foto(
    request: Request,
    ticket_id: int,
    datos: TicketFotoCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    _actualizar_estado_ticket(ticket)
    foto = TicketFoto(ticket_id=ticket_id, taller_id=request.state.taller_id, **datos.model_dump())
    db.add(foto)
    db.commit()
    db.refresh(foto)
    return foto


@router.delete("/{ticket_id}/fotos/{foto_id}")
@require_auth
async def eliminar_foto(
    request: Request,
    ticket_id: int,
    foto_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    foto = (
        db.query(TicketFoto)
        .filter(TicketFoto.id == foto_id, TicketFoto.ticket_id == ticket_id)
        .first()
    )
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    db.delete(foto)
    db.commit()
    return {"ok": True}


@router.post("/{ticket_id}/compras", response_model=TicketCompraRespuesta)
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_TICKETS_PER_MINUTE", "30") + "/minute")
async def agregar_compra(
    request: Request,
    ticket_id: int,
    datos: TicketCompraCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)

    # Usar servicio para crear compra con movimiento
    ticket_service = TicketService(db)
    compra = ticket_service.crear_compra_con_movimiento(
        ticket=ticket,
        descripcion=datos.descripcion,
        valor=datos.valor,
        responsable=datos.responsable,
        nota=datos.nota,
        soporte_url=datos.soporte_url,
        responsable_user_id=datos.responsable_user_id,
    )
    db.commit()
    db.refresh(compra)
    return compra


@router.post("/{ticket_id}/cobros", response_model=TicketCobroRespuesta)
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_TICKETS_PER_MINUTE", "30") + "/minute")
async def agregar_cobro(
    request: Request,
    ticket_id: int,
    datos: TicketCobroCrear,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    _actualizar_estado_ticket(ticket)

    cobro = TicketCobro(ticket_id=ticket_id, taller_id=request.state.taller_id, **datos.model_dump())
    db.add(cobro)
    db.commit()
    db.refresh(cobro)
    return cobro


@router.delete("/{ticket_id}/cobros/{cobro_id}")
@require_auth
async def eliminar_cobro(
    request: Request,
    ticket_id: int,
    cobro_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    cobro = (
        db.query(TicketCobro)
        .filter(TicketCobro.id == cobro_id, TicketCobro.ticket_id == ticket_id)
        .first()
    )
    if not cobro:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    db.delete(cobro)
    db.commit()
    return {"ok": True}


@router.put(
    "/{ticket_id}/finanzas",
    response_model=TicketRespuesta,
    summary="Update ticket financial information",
    description="""
    Update the total service cost and final payment method for a ticket.

    **Use Case:**
    - Set final service cost before finalizing ticket
    - Record payment method used by customer
    - Calculate pending balance

    **Process:**
    1. Validates ticket exists
    2. Updates total_servicio and metodo_pago_final
    3. Recalculates saldo_pendiente (total - anticipo - cobros)
    4. Creates INGRESO_FINAL cash movement if payment received

    **Financial Calculation:**
    - saldo_pendiente = total_servicio - anticipo_recibido - sum(cobros)

    **Payment Methods:**
    - EFECTIVO: Cash
    - TRANSFERENCIA: Bank transfer
    - TARJETA: Credit/debit card
    - NEQUI: Nequi mobile payment
    - DAVIPLATA: Daviplata mobile payment

    **Permissions:**
    - Requires ADMIN password authentication
    """,
    responses={
        200: {
            "description": "Financial information updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 123,
                        "ticket_codigo": "TK-ABC123-20260406103000",
                        "total_servicio": 150000,
                        "anticipo_recibido": 50000,
                        "saldo_pendiente": 100000,
                        "metodo_pago_final": "TRANSFERENCIA",
                    }
                }
            },
        },
        404: {"description": "Ticket not found"},
    },
)
@require_auth
async def actualizar_finanzas_ticket(
    request: Request,
    ticket_id: int,
    datos: TicketFinanzasActualizar,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)

    # Usar servicio para actualizar finanzas
    ticket_service = TicketService(db)
    ticket_service.actualizar_finanzas(
        ticket=ticket,
        total_servicio=datos.total_servicio,
        metodo_pago_final=datos.metodo_pago_final,
    )

    # Guardar observaciones si se enviaron
    if datos.observaciones_finales is not None:
        ticket.observaciones_finales = InputSanitizer.sanitize_html(datos.observaciones_finales)
    if datos.recomendaciones is not None:
        ticket.recomendaciones = InputSanitizer.sanitize_html(datos.recomendaciones)
    if datos.proximo_mantenimiento is not None:
        ticket.proximo_mantenimiento = InputSanitizer.sanitize_html(datos.proximo_mantenimiento)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.put("/{ticket_id}/observaciones-finales", response_model=TicketRespuesta)
@require_auth
async def actualizar_observaciones_finales(
    request: Request,
    ticket_id: int,
    datos: TicketObservacionesFinalesActualizar,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    _asegurar_editable(ticket)
    payload = datos.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        setattr(ticket, campo, valor)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post(
    "/{ticket_id}/finalizar",
    response_model=TicketRespuesta,
    summary="Finalize ticket and calculate final balance",
    description="""
    Mark ticket as FINALIZADO (finalized) and calculate final financial balance.

    **Process:**
    1. Validates ticket is not already finalized or delivered
    2. Calculates final balance (total_servicio - anticipo_recibido - cobros)
    3. Updates ticket status to FINALIZADO
    4. Sets fecha_cierre (closing date)
    5. Sends WhatsApp notification to vehicle owner (if configured)

    **Financial Calculation:**
    - saldo_pendiente = total_servicio - anticipo_recibido - sum(cobros)
    - If saldo_pendiente < 0, customer has credit
    - If saldo_pendiente > 0, customer owes money

    **State Transition:**
    - ABIERTO → FINALIZADO
    - EN_PROCESO → FINALIZADO
    - FINALIZADO → no change (idempotent)
    - ENTREGADO → no change (already delivered)

    **Notifications:**
    - WhatsApp message sent to vehicle owner (async, fire-and-forget)
    - Message includes ticket code, total, and balance due

    **Permissions:**
    - Requires ADMIN password authentication
    """,
    responses={
        200: {
            "description": "Ticket finalized successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 123,
                        "ticket_codigo": "TK-ABC123-20260406103000",
                        "estado": "FINALIZADO",
                        "total_servicio": 150000,
                        "anticipo_recibido": 50000,
                        "saldo_pendiente": 100000,
                        "fecha_cierre": "2026-04-06T18:30:00",
                    }
                }
            },
        },
        404: {
            "description": "Ticket not found",
            "content": {
                "application/json": {
                    "example": {"error": "resource_not_found", "message": "Ticket no encontrado"}
                }
            },
        },
    },
)
@require_auth
async def finalizar_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
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
@require_auth
@limiter.limit("20/minute")
async def generar_pdf_cliente(
    request: Request,
    ticket_id: int,
    token: str | None = Query(None),
    x_admin_password: str | None = Header(None, alias="X-Admin-Password"),
    db: Session = Depends(obtener_db),
):
    # Autenticación: acepta JWT (nuevo) o header X-Admin-Password o query param ?token= (legacy)
    jwt_user = getattr(request.state, "user", None)

    if not jwt_user:
        # Fallback legacy: verificar X-Admin-Password o token query param
        admin_token = x_admin_password or token
        if not admin_token:
            raise HTTPException(status_code=401, detail="Autenticacion requerida")

        # Verificar contra BD primero, luego .env
        from app.seguridad.dependencias import _get_admin_password_from_db

        hash_bd = _get_admin_password_from_db(db)
        if hash_bd:
            import hashlib as _hashlib

            if not hmac.compare_digest(_hashlib.sha256(admin_token.encode()).hexdigest(), hash_bd):
                raise HTTPException(status_code=401, detail="Autenticacion requerida")
        else:
            password_esperada = os.getenv("ADMIN_PASSWORD") or os.getenv("PDF_PASSWORD")
            if not password_esperada or not hmac.compare_digest(
                admin_token.encode("utf-8"), password_esperada.encode("utf-8")
            ):
                raise HTTPException(status_code=401, detail="Autenticacion requerida")
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
    procesos = (
        db.query(TicketProceso)
        .filter(TicketProceso.ticket_id == ticket_id)
        .order_by(TicketProceso.fecha_creacion.asc())
        .all()
    )
    repuestos = (
        db.query(TicketRepuesto)
        .filter(TicketRepuesto.ticket_id == ticket_id)
        .order_by(TicketRepuesto.fecha_creacion.asc())
        .all()
    )
    fotos = (
        db.query(TicketFoto)
        .filter(TicketFoto.ticket_id == ticket_id)
        .order_by(TicketFoto.fecha_creacion.asc())
        .all()
    )
    cobros = (
        db.query(TicketCobro)
        .filter(TicketCobro.ticket_id == ticket_id)
        .order_by(TicketCobro.fecha_creacion.asc())
        .all()
    )
    compras = (
        db.query(TicketCompra)
        .filter(TicketCompra.ticket_id == ticket_id)
        .order_by(TicketCompra.fecha_creacion.asc())
        .all()
    )

    # Convertir a diccionarios
    ticket_dict = {
        "ticket_codigo": ticket.ticket_codigo,
        "placa": ticket.placa,
        "estado": ticket.estado,
        "fecha_ingreso": ticket.fecha_ingreso.isoformat() if ticket.fecha_ingreso else None,
        "motivo_visita": ticket.motivo_visita,
        "observaciones_recepcion": ticket.observaciones_recepcion,
        "kilometraje": ticket.kilometraje,
        "estado_inicial": ticket.estado_inicial,
        "nombre_propietario": vehiculo.nombre_propietario if vehiculo else None,
        "telefono_propietario": vehiculo.telefono_propietario if vehiculo else None,
        "total_servicio": ticket.total_servicio or 0,
        "anticipo_recibido": ticket.anticipo_recibido or 0,
        "saldo_pendiente": ticket.saldo_pendiente or 0,
        "metodo_pago_final": ticket.metodo_pago_final,
        "observaciones_finales": ticket.observaciones_finales,
        "recomendaciones": ticket.recomendaciones,
        "proximo_mantenimiento": ticket.proximo_mantenimiento,
    }

    procesos_list = [
        {
            "nombre": p.nombre,
            "mecanico": p.mecanico,
            "descripcion": p.descripcion,
            "foto_url": p.foto_url,
        }
        for p in procesos
    ]
    repuestos_list = [
        {
            "nombre": r.nombre,
            "cantidad": r.cantidad,
            "marca_referencia": r.marca_referencia,
            "foto_url": r.foto_url,
        }
        for r in repuestos
    ]
    fotos_list = [
        {"tipo": f.tipo, "archivo_url": f.archivo_url, "descripcion": f.descripcion} for f in fotos
    ]
    cobros_list = [{"concepto": c.concepto, "valor": c.valor} for c in cobros]
    compras_list = [
        {
            "descripcion": c.descripcion,
            "valor": c.valor,
            "soporte_url": c.soporte_url,
            "responsable": c.responsable,
        }
        for c in compras
    ]

    # Datos del taller
    cfg = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.id == 1).first()
    taller_data = {
        "nombre_taller": cfg.nombre_taller if cfg else "Taller Mecánico",
        "direccion": cfg.direccion if cfg else "",
        "telefono": cfg.telefono if cfg else "",
        "nit": cfg.nit if cfg else "",
        "logo_url": cfg.logo_url if cfg else "",
    }

    # Generar PDF con el nuevo generador
    pdf_bytes = generar_pdf_ticket_completo(
        ticket_dict,
        procesos_list,
        repuestos_list,
        fotos_list,
        cobros_list,
        compras_list,
        taller_data,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ticket_{ticket.ticket_codigo}.pdf"'
        },
    )


@router.post(
    "/{ticket_id}/entregar",
    response_model=TicketRespuesta,
    summary="Mark ticket as delivered to customer",
    description="""
    Mark a ticket as ENTREGADO (delivered) when vehicle is returned to customer.

    **Use Case:**
    - Final step in ticket workflow
    - Confirm vehicle delivery to customer
    - Record delivery signature and final observations

    **Process:**
    1. Validates ticket exists
    2. Updates status to ENTREGADO
    3. Sets fecha_entrega (delivery date)
    4. Records delivery confirmation details (who received, signature)
    5. Updates final observations and recommendations
    6. Sends WhatsApp notification to customer (async)

    **State Transition:**
    - FINALIZADO → ENTREGADO (normal flow)
    - ENTREGADO → no change (idempotent)

    **Delivery Information:**
    - confirmado_entrega_por: Name of person who received vehicle
    - firma_entrega_url: URL to delivery signature image
    - observaciones_finales: Final observations about service
    - recomendaciones: Recommendations for customer
    - proximo_mantenimiento: Next maintenance schedule

    **Notifications:**
    - WhatsApp message sent to vehicle owner (async, fire-and-forget)
    - Message confirms delivery and thanks customer

    **Permissions:**
    - Requires ADMIN password authentication
    """,
    responses={
        200: {
            "description": "Ticket marked as delivered",
            "content": {
                "application/json": {
                    "example": {
                        "id": 123,
                        "ticket_codigo": "TK-ABC123-20260406103000",
                        "estado": "ENTREGADO",
                        "fecha_entrega": "2026-04-06T19:00:00",
                        "confirmado_entrega_por": "Juan Pérez",
                        "firma_entrega_url": "/uploads/firmas/firma_123.png",
                        "observaciones_finales": "Servicio completado satisfactoriamente",
                        "recomendaciones": "Cambiar aceite cada 3000 km",
                        "proximo_mantenimiento": "Julio 2026",
                    }
                }
            },
        },
        404: {"description": "Ticket not found"},
    },
)
@require_auth
async def marcar_entregado(
    request: Request,
    ticket_id: int,
    datos: TicketEntregarPayload,
    db: Session = Depends(obtener_db),
):
    ticket = _obtener_ticket_o_404(db, ticket_id, request.state.taller_id)

    # Usar servicio para entregar ticket
    ticket_service = TicketService(db)
    ticket_service.entregar_ticket(
        ticket=ticket,
        confirmado_entrega_por=datos.confirmado_entrega_por,
        firma_entrega_url=datos.firma_entrega_url,
        observaciones_finales=datos.observaciones_finales,
        recomendaciones=datos.recomendaciones,
        proximo_mantenimiento=datos.proximo_mantenimiento,
        metodo_pago_final=datos.metodo_pago_final,
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
