from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.modelos.ticket import Ticket
from app.modelos.ticket_foto import TicketFoto
from app.modelos.ticket_proceso import TicketProceso

router = APIRouter(prefix="/mobile/v1", tags=["Mobile API"])


@router.get("/health")
def health_mobile():
    return {"ok": True, "scope": "mobile-v1"}


@router.get("/tickets/activos")
def tickets_activos_mobile(
    db: Session = Depends(obtener_db),
    placa: str | None = Query(None),
):
    # Sin autenticación — endpoint legacy solo para compatibilidad
    # No expone datos sensibles, solo códigos y estados
    query = db.query(Ticket).filter(Ticket.estado.in_(["ABIERTO", "EN_PROCESO"]))
    if placa:
        query = query.filter(Ticket.placa == placa.strip().upper())
    items = query.order_by(Ticket.fecha_ingreso.desc()).limit(100).all()
    return {
        "items": [
            {
                "id": t.id,
                "ticket_codigo": t.ticket_codigo,
                "placa": t.placa,
                "estado": t.estado,
                "motivo_visita": t.motivo_visita,
                "fecha_ingreso": t.fecha_ingreso.isoformat() if t.fecha_ingreso else None,
            }
            for t in items
        ]
    }


@router.get("/tickets/{ticket_id}/timeline")
def timeline_ticket_mobile(
    ticket_id: int,
    db: Session = Depends(obtener_db),
):
    procesos = (
        db.query(TicketProceso)
        .filter(TicketProceso.ticket_id == ticket_id)
        .order_by(TicketProceso.fecha_creacion.asc())
        .all()
    )
    fotos = (
        db.query(TicketFoto)
        .filter(TicketFoto.ticket_id == ticket_id)
        .order_by(TicketFoto.fecha_creacion.asc())
        .all()
    )
    return {
        "procesos": [
            {
                "id": p.id,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "mecanico": p.mecanico,
                "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else None,
            }
            for p in procesos
        ],
        "fotos": [
            {
                "id": f.id,
                "tipo": f.tipo,
                "archivo_url": f.archivo_url,
                "descripcion": f.descripcion,
                "fecha_creacion": f.fecha_creacion.isoformat() if f.fecha_creacion else None,
            }
            for f in fotos
        ],
    }
