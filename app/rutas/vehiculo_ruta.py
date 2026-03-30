from datetime import datetime
from typing import List
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
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
    marca_tiempo = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"TK-{placa}-{marca_tiempo}"


@router.get("/buscar")
def buscar_por_placa(
    placa: str = Query(..., min_length=3, max_length=20),
    db: Session = Depends(obtener_db),
):
    placa_norm = _normalizar_placa(placa)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == placa_norm).first()
    if not vehiculo:
        return {"existe": False, "placa": placa_norm}
    return {"existe": True, "vehiculo": VehiculoRespuesta.model_validate(vehiculo).model_dump()}


@router.post("/", response_model=VehiculoRespuesta)
def crear_vehiculo(
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


@router.get("/", response_model=List[VehiculoRespuesta])
def listar_vehiculos(
    db: Session = Depends(obtener_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return db.query(Vehiculo).order_by(Vehiculo.id.desc()).offset(skip).limit(limit).all()


@router.put("/{placa}", response_model=VehiculoRespuesta)
def actualizar_vehiculo_por_placa(
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


@router.get("/{placa}/ficha", response_model=VehiculoFichaRespuesta)
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


@router.post("/{placa}/ticket-ingreso", response_model=TicketRespuesta)
def crear_ticket_ingreso(
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
