import os
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.whatsapp_schema import LogNotificacionResponse, MensajeManualRequest
from app.modelos.log_notificacion import LogNotificacion
from app.modelos.ticket import Ticket
from app.modelos.vehiculo import Vehiculo
from app.servicios.twilio_whatsapp_service import TwilioWhatsAppService

router = APIRouter(tags=["whatsapp"])

whatsapp_service = TwilioWhatsAppService()


@router.get("/whatsapp/webhook")
async def verificar_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("/whatsapp/webhook")
async def recibir_webhook(request: Request, db: Session = Depends(obtener_db)):
    try:
        payload = await request.json()

        entry = payload.get("entry", [])
        if entry:
            changes = entry[0].get("changes", [])
            if changes:
                value = changes[0].get("value", {})
                messages = value.get("messages", [])
                if messages:
                    msg = messages[0]
                    telefono = msg.get("from")
                    texto = msg.get("text", {}).get("body") if msg.get("type") == "text" else None

                    log = LogNotificacion(
                        tipo_evento="ENTRANTE",
                        resultado="ENVIADO",
                        telefono_destino=telefono,
                        mensaje_enviado=texto,
                    )
                    db.add(log)
                    db.commit()
    except Exception as e:
        print(f"[webhook] Error procesando evento: {e}")

    return {"status": "ok"}


@router.post("/api/mobile/tickets/{ticket_id}/whatsapp")
async def enviar_whatsapp_mobile(
    ticket_id: int,
    body: MensajeManualRequest,
    db: Session = Depends(obtener_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return {"ok": False, "error": "ticket_no_encontrado"}
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
    telefono = getattr(vehiculo, "telefono_propietario", None) if vehiculo else None
    if not telefono:
        return {"ok": False, "error": "sin_telefono"}
    resultado = await whatsapp_service.enviar_mensaje_manual(ticket_id, telefono, body.mensaje, db)
    return resultado


@router.post("/api/whatsapp/tickets/{ticket_id}/mensaje")
async def enviar_whatsapp_web(
    ticket_id: int,
    body: MensajeManualRequest,
    db: Session = Depends(obtener_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
    telefono = getattr(vehiculo, "telefono_propietario", None) if vehiculo else None
    if not telefono:
        raise HTTPException(status_code=422, detail="El vehículo no tiene teléfono registrado")
    resultado = await whatsapp_service.enviar_mensaje_manual(ticket_id, telefono, body.mensaje, db)
    if not resultado.get("ok"):
        raise HTTPException(status_code=500, detail=resultado.get("error", "Error al enviar mensaje"))
    return resultado


@router.get("/api/mobile/whatsapp/logs", response_model=List[LogNotificacionResponse])
async def obtener_logs(
    ticket_id: Optional[int] = None,
    db: Session = Depends(obtener_db),
):
    query = db.query(LogNotificacion)
    if ticket_id is not None:
        query = query.filter(LogNotificacion.ticket_id == ticket_id)
    logs = query.order_by(LogNotificacion.created_at.desc()).limit(100).all()
    return logs
