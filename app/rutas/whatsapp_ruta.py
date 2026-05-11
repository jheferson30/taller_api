import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.configuracion.limiter import limiter
from app.esquemas.whatsapp_schema import LogNotificacionResponse, MensajeManualRequest
from app.modelos.log_notificacion import LogNotificacion
from app.modelos.ticket import Ticket
from app.modelos.vehiculo import Vehiculo
from app.seguridad.auth_middleware import require_auth
from app.servicios.twilio_whatsapp_service import TwilioWhatsAppService
from app.servicios.whatsapp_service import WebhookRouter

router = APIRouter(tags=["whatsapp"])

whatsapp_service = TwilioWhatsAppService()
logger = logging.getLogger(__name__)


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
@limiter.limit(os.getenv("RATE_LIMIT_WHATSAPP_PER_MINUTE", "5") + "/minute")
async def recibir_webhook(request: Request, db: Session = Depends(obtener_db)):
    """
    Recibe webhooks de Twilio/Meta WhatsApp y los enruta al taller correcto.
    
    Este endpoint es público (sin autenticación) porque es llamado por Twilio.
    Usa WebhookRouter para determinar a qué taller pertenece el mensaje basándose
    en el número de WhatsApp Business que lo recibió.
    
    Requirements: 1.5, 1.6 (C-05)
    """
    try:
        payload = await request.json()
        
        # Usar WebhookRouter para determinar el taller (Requirement 1.5)
        webhook_router = WebhookRouter(db)
        taller_id, phone_number = webhook_router.route_whatsapp_message(payload)
        
        # Si no se puede enrutar, retornar 404 y loguear (Requirement 1.6)
        if taller_id is None:
            logger.warning(
                f"Unrouted WhatsApp message from {phone_number}. "
                f"No taller found with whatsapp_phone_number={phone_number}"
            )
            
            # Loguear mensaje no enrutado para investigación
            log = LogNotificacion(
                taller_id=None,  # Sin taller asignado
                tipo_evento="ENTRANTE",
                resultado="ERROR",
                telefono_destino=phone_number,
                mensaje_enviado=None,
                error_detalle=f"Unrouted message: no taller found for phone {phone_number}",
            )
            db.add(log)
            db.commit()
            
            # Retornar 404 con mensaje genérico (Requirement 1.6)
            return JSONResponse(
                status_code=404,
                content={"status": "unrouted", "message": "Resource not found"}
            )
        
        # Procesar mensaje para el taller identificado
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

                    # Guardar log con taller_id correcto
                    log = LogNotificacion(
                        taller_id=taller_id,  # Asignar al taller correcto
                        tipo_evento="ENTRANTE",
                        resultado="ENVIADO",
                        telefono_destino=telefono,
                        mensaje_enviado=texto,
                    )
                    db.add(log)
                    db.commit()
    except Exception as e:
        logger.error(f"[webhook] Error procesando evento: {e}")
        # No lanzar excepción para no revelar detalles internos a Twilio
        return {"status": "error"}

    return {"status": "ok"}


@router.post("/api/mobile/tickets/{ticket_id}/whatsapp")
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_WHATSAPP_PER_MINUTE", "5") + "/minute")
async def enviar_whatsapp_mobile(
    request: Request,
    ticket_id: int,
    body: MensajeManualRequest,
    db: Session = Depends(obtener_db),
):
    # Extract taller_id from JWT (Requirements 1.1, 1.2)
    taller_id = request.state.taller_id
    
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return {"ok": False, "error": "ticket_no_encontrado"}
    
    # Verify ticket ownership (Requirement 1.7, 1.8 - C-07)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
    if not vehiculo:
        return {"ok": False, "error": "ticket_no_encontrado"}
    
    # Verify vehiculo belongs to authenticated taller (Requirement 1.7, 1.8)
    if vehiculo.taller_id != taller_id:
        # Return 404 to not reveal ticket exists in another taller (Requirement 1.8)
        return {"ok": False, "error": "ticket_no_encontrado"}
    
    telefono = getattr(vehiculo, "telefono_propietario", None) if vehiculo else None
    if not telefono:
        return {"ok": False, "error": "sin_telefono"}
    resultado = await whatsapp_service.enviar_mensaje_manual(ticket_id, telefono, body.mensaje, db)
    return resultado


@router.post("/api/whatsapp/tickets/{ticket_id}/mensaje")
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_WHATSAPP_PER_MINUTE", "5") + "/minute")
async def enviar_whatsapp_web(
    request: Request,
    ticket_id: int,
    body: MensajeManualRequest,
    db: Session = Depends(obtener_db),
):
    # Extract taller_id from JWT (Requirements 1.1, 1.2)
    taller_id = request.state.taller_id
    
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Verify ticket ownership (Requirement 1.7, 1.8 - C-07)
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Verify vehiculo belongs to authenticated taller (Requirement 1.7, 1.8)
    if vehiculo.taller_id != taller_id:
        # Return 404 to not reveal ticket exists in another taller (Requirement 1.8)
        raise HTTPException(status_code=404, detail="Resource not found")
    
    telefono = getattr(vehiculo, "telefono_propietario", None) if vehiculo else None
    if not telefono:
        raise HTTPException(status_code=422, detail="El vehículo no tiene teléfono registrado")
    resultado = await whatsapp_service.enviar_mensaje_manual(ticket_id, telefono, body.mensaje, db)
    if not resultado.get("ok"):
        raise HTTPException(
            status_code=500, detail=resultado.get("error", "Error al enviar mensaje")
        )
    return resultado


@router.get("/api/mobile/whatsapp/logs", response_model=list[LogNotificacionResponse])
@require_auth
async def obtener_logs(
    request: Request,
    ticket_id: int | None = None,
    db: Session = Depends(obtener_db),
):
    # Extract taller_id from JWT (Requirements 1.3, 1.4)
    taller_id = request.state.taller_id
    
    # Apply RLS filter by taller_id
    query = db.query(LogNotificacion).filter(LogNotificacion.taller_id == taller_id)
    if ticket_id is not None:
        query = query.filter(LogNotificacion.ticket_id == ticket_id)
    logs = query.order_by(LogNotificacion.created_at.desc()).limit(100).all()
    return logs
