from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.ticket_schema import TicketIngresoCrear, TicketRespuesta, VehiculoFichaRespuesta
from app.esquemas.vehiculo_schema import VehiculoActualizar, VehiculoCrear, VehiculoRespuesta
from app.modelos.movimiento_caja import EstadoTicket, MovimientoCaja, TipoMovimiento
from app.modelos.ticket import Ticket
from app.modelos.vehiculo import Vehiculo
from app.servicios.twilio_whatsapp_service import TwilioWhatsAppService
from app.servicios.whatsapp_service import TipoEvento

router = APIRouter(prefix="/vehiculos", tags=["Vehiculos"])

_whatsapp_service = TwilioWhatsAppService()


def _normalizar_placa(placa: str) -> str:
    return placa.strip().upper()


def _generar_codigo_ticket(placa: str) -> str:
    marca_tiempo = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"TK-{placa}-{marca_tiempo}"


@router.get(
    "/buscar",
    summary="Search vehicle by license plate",
    description="""
    Search for a vehicle by license plate number.

    **Use Case:**
    - Check if vehicle exists before creating ticket
    - Quick vehicle lookup during reception
    - Autocomplete functionality in frontend

    **Plate Normalization:**
    - Automatically converts to uppercase
    - Trims whitespace
    - Minimum 3 characters required

    **Response:**
    - If vehicle exists: returns vehicle data with existe=true
    - If vehicle doesn't exist: returns existe=false with normalized plate

    **Rate Limiting:**
    - 100 requests per minute (standard read limit)
    """,
    responses={
        200: {
            "description": "Search result",
            "content": {
                "application/json": {
                    "examples": {
                        "vehicle_found": {
                            "summary": "Vehicle exists",
                            "value": {
                                "existe": True,
                                "vehiculo": {
                                    "id": 1,
                                    "placa": "ABC123",
                                    "marca": "Yamaha",
                                    "modelo": "FZ16",
                                    "anio": 2020,
                                    "nombre_propietario": "Juan Pérez",
                                    "telefono_propietario": "3001234567",
                                },
                            },
                        },
                        "vehicle_not_found": {
                            "summary": "Vehicle doesn't exist",
                            "value": {"existe": False, "placa": "XYZ789"},
                        },
                    }
                }
            },
        },
        422: {
            "description": "Validation error - plate too short",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "Plate must be at least 3 characters",
                    }
                }
            },
        },
    },
)
def buscar_por_placa(
    placa: str = Query(..., min_length=3, max_length=20),
    db: Session = Depends(obtener_db),
):
    placa_norm = _normalizar_placa(placa)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == placa_norm).first()
    if not vehiculo:
        return {"existe": False, "placa": placa_norm}
    return {"existe": True, "vehiculo": VehiculoRespuesta.model_validate(vehiculo).model_dump()}


@router.post(
    "/",
    response_model=VehiculoRespuesta,
    summary="Create new vehicle",
    description="""
    Register a new vehicle in the system.

    **Use Case:**
    - Register new customer vehicle during first visit
    - Add vehicle before creating ticket

    **Validation:**
    - Plate must be unique (case-insensitive)
    - Plate is automatically normalized (uppercase, trimmed)
    - All fields except plate are optional

    **Duplicate Handling:**
    - Returns 400 if plate already exists
    - Check with /buscar endpoint before creating

    **Rate Limiting:**
    - 30 requests per minute (standard write limit)
    """,
    responses={
        200: {
            "description": "Vehicle created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "placa": "ABC123",
                        "marca": "Yamaha",
                        "modelo": "FZ16",
                        "anio": 2020,
                        "cilindraje": "150cc",
                        "color": "Negro",
                        "nombre_propietario": "Juan Pérez",
                        "telefono_propietario": "3001234567",
                        "fecha_creacion": "2026-04-06T10:30:00",
                        "fecha_actualizacion": None,
                    }
                }
            },
        },
        400: {
            "description": "Plate already registered",
            "content": {
                "application/json": {
                    "example": {
                        "error": "duplicate_resource",
                        "message": "La placa ya esta registrada",
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {"error": "validation_error", "message": "Invalid input data"}
                }
            },
        },
    },
)
async def crear_vehiculo(
    request: Request,
    datos: VehiculoCrear,
    db: Session = Depends(obtener_db),
):
    payload = datos.model_dump()
    payload["placa"] = _normalizar_placa(payload["placa"])

    existente = db.query(Vehiculo).filter(Vehiculo.placa == payload["placa"]).first()
    if existente:
        raise HTTPException(status_code=400, detail="La placa ya esta registrada")

    nuevo = Vehiculo(**payload)
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="La placa ya esta registrada")
    db.refresh(nuevo)
    return nuevo


@router.get(
    "/",
    response_model=list[VehiculoRespuesta],
    summary="List all vehicles",
    description="""
    Retrieve a paginated list of all registered vehicles.

    **Use Case:**
    - Vehicle inventory management
    - Customer database browsing
    - Vehicle search and selection

    **Pagination:**
    - Default: 50 vehicles per page
    - Maximum: 200 vehicles per page
    - Ordered by ID (newest first)

    **Rate Limiting:**
    - 100 requests per minute (standard read limit)
    """,
    responses={
        200: {
            "description": "List of vehicles",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "placa": "ABC123",
                            "marca": "Yamaha",
                            "modelo": "FZ16",
                            "anio": 2020,
                            "cilindraje": "150cc",
                            "color": "Negro",
                            "nombre_propietario": "Juan Pérez",
                            "telefono_propietario": "3001234567",
                            "fecha_creacion": "2026-04-06T10:00:00",
                            "fecha_actualizacion": None,
                        }
                    ]
                }
            },
        }
    },
)
def listar_vehiculos(
    db: Session = Depends(obtener_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return db.query(Vehiculo).order_by(Vehiculo.id.desc()).offset(skip).limit(limit).all()


@router.put("/{placa}", response_model=VehiculoRespuesta)
async def actualizar_vehiculo_por_placa(
    request: Request,
    placa: str,
    datos: VehiculoActualizar,
    db: Session = Depends(obtener_db),
):
    placa_norm = _normalizar_placa(placa)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == placa_norm).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")

    actualizaciones = datos.model_dump(exclude_unset=True)
    for campo, valor in actualizaciones.items():
        setattr(vehiculo, campo, valor)

    db.commit()
    db.refresh(vehiculo)
    return vehiculo


@router.get("/{placa}", response_model=VehiculoRespuesta)
def obtener_vehiculo_por_placa(
    placa: str,
    db: Session = Depends(obtener_db),
):
    placa_norm = _normalizar_placa(placa)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == placa_norm).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
    return vehiculo


@router.get(
    "/{placa}/ficha",
    response_model=VehiculoFichaRespuesta,
    summary="Get vehicle service history card",
    description="""
    Retrieve complete vehicle information including full service history.

    **Use Case:**
    - Customer service inquiries
    - Service history review
    - Vehicle maintenance tracking
    - Customer relationship management

    **Includes:**
    - Vehicle basic information (plate, brand, model, year, etc.)
    - Owner contact information
    - Complete service history (all tickets)
    - Chronological order (newest first)

    **Rate Limiting:**
    - 100 requests per minute (standard read limit)
    """,
    responses={
        200: {
            "description": "Vehicle service history card",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "placa": "ABC123",
                        "marca": "Yamaha",
                        "modelo": "FZ16",
                        "anio": 2020,
                        "cilindraje": "150cc",
                        "color": "Negro",
                        "nombre_propietario": "Juan Pérez",
                        "telefono_propietario": "3001234567",
                        "historial_visitas": [
                            {
                                "ticket_codigo": "TK-ABC123-20260406103000",
                                "fecha_ingreso": "2026-04-06T10:30:00",
                                "motivo_visita": "Cambio de aceite",
                                "estado": "ENTREGADO",
                            },
                            {
                                "ticket_codigo": "TK-ABC123-20260301120000",
                                "fecha_ingreso": "2026-03-01T12:00:00",
                                "motivo_visita": "Revisión general",
                                "estado": "ENTREGADO",
                            },
                        ],
                    }
                }
            },
        },
        404: {
            "description": "Vehicle not found",
            "content": {
                "application/json": {
                    "example": {"error": "resource_not_found", "message": "Vehiculo no encontrado"}
                }
            },
        },
    },
)
def obtener_ficha_vehiculo(
    placa: str,
    db: Session = Depends(obtener_db),
):
    placa_norm = _normalizar_placa(placa)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == placa_norm).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")

    historial = (
        db.query(Ticket)
        .filter(Ticket.vehiculo_id == vehiculo.id)
        .order_by(Ticket.fecha_ingreso.desc())
        .all()
    )

    return {
        "id": vehiculo.id,
        "placa": vehiculo.placa,
        "marca": vehiculo.marca,
        "modelo": vehiculo.modelo,
        "anio": vehiculo.anio,
        "cilindraje": vehiculo.cilindraje,
        "color": vehiculo.color,
        "nombre_propietario": vehiculo.nombre_propietario,
        "telefono_propietario": vehiculo.telefono_propietario,
        "historial_visitas": historial,
    }


@router.post(
    "/{placa}/ticket-ingreso",
    response_model=TicketRespuesta,
    summary="Create service ticket for vehicle",
    description="""
    Create a new service ticket (orden de servicio) for a vehicle.

    **Use Case:**
    - Vehicle check-in at reception
    - Start new service workflow
    - Record initial vehicle condition and customer requirements

    **Process:**
    1. Validates vehicle exists by plate
    2. Generates unique ticket code (TK-{PLACA}-{TIMESTAMP})
    3. Creates ticket with status ABIERTO
    4. Records initial observations and mileage
    5. Registers advance payment if provided
    6. Creates INGRESO_ANTICIPO cash movement for advance
    7. Sends WhatsApp notification to customer (async)

    **Required Information:**
    - motivo_visita: Reason for service (3-250 chars)
    - Optional: kilometraje, observaciones_recepcion, anticipo_recibido

    **Advance Payment:**
    - If anticipo_recibido > 0, creates cash movement
    - Records payment method (EFECTIVO, TRANSFERENCIA, etc.)
    - Links payment to ticket for financial tracking

    **Notifications:**
    - WhatsApp message sent to vehicle owner (async, fire-and-forget)
    - Message includes ticket code and estimated completion time

    **Rate Limiting:**
    - 30 requests per minute (standard write limit)
    """,
    responses={
        200: {
            "description": "Ticket created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 123,
                        "ticket_codigo": "TK-ABC123-20260406103000",
                        "vehiculo_id": 1,
                        "placa": "ABC123",
                        "fecha_ingreso": "2026-04-06T10:30:00",
                        "motivo_visita": "Cambio de aceite y revisión general",
                        "observaciones_recepcion": "Cliente reporta ruido en el motor",
                        "kilometraje": 15000,
                        "estado_inicial": "Buen estado general",
                        "anticipo_recibido": 50000,
                        "metodo_pago_anticipo": "EFECTIVO",
                        "recepcionado_por": "María González",
                        "estado": "ABIERTO",
                        "total_servicio": None,
                        "saldo_pendiente": None,
                    }
                }
            },
        },
        404: {
            "description": "Vehicle not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "resource_not_found",
                        "message": "Vehiculo no encontrado para crear ticket",
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "motivo_visita must be at least 3 characters",
                    }
                }
            },
        },
    },
)
async def crear_ticket_ingreso(
    request: Request,
    placa: str,
    datos: TicketIngresoCrear,
    db: Session = Depends(obtener_db),
):
    placa_norm = _normalizar_placa(placa)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == placa_norm).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado para crear ticket")

    ticket = Ticket(
        vehiculo_id=vehiculo.id,
        ticket_codigo=_generar_codigo_ticket(placa_norm),
        placa=placa_norm,
        motivo_visita=datos.motivo_visita,
        observaciones_recepcion=datos.observaciones_recepcion,
        kilometraje=datos.kilometraje,
        estado_inicial=datos.estado_inicial,
        anticipo_recibido=datos.anticipo_recibido,
        metodo_pago_anticipo=datos.metodo_pago_anticipo,
        recepcionado_por=datos.recepcionado_por,
        estado="ABIERTO",
    )
    db.add(ticket)
    db.flush()

    if datos.anticipo_recibido > 0:
        movimiento = MovimientoCaja(
            tipo=TipoMovimiento.INGRESO_ANTICIPO,
            ticket_id=ticket.id,
            ticket_codigo=ticket.ticket_codigo,
            placa=placa_norm,
            estado_ticket=EstadoTicket.ABIERTO,
            valor=datos.anticipo_recibido,
            metodo_pago=datos.metodo_pago_anticipo,
            responsable=datos.recepcionado_por,
            concepto=f"Anticipo ticket {ticket.ticket_codigo}",
            observacion=datos.observaciones_recepcion,
            creado_por=datos.recepcionado_por,
        )
        db.add(movimiento)

    db.commit()
    db.refresh(ticket)
    # Fire-and-forget: notificación WhatsApp de recepción (req 2.1)
    try:
        import asyncio

        loop = asyncio.get_running_loop()
        loop.create_task(
            _whatsapp_service.enviar_notificacion(TipoEvento.RECEPCION, ticket, vehiculo, db)
        )
    except RuntimeError:
        pass  # No hay event loop activo (ej. en tests síncronos)
    except Exception:
        pass
    return ticket
