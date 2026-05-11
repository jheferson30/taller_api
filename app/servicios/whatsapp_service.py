from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session


class TipoEvento(StrEnum):
    RECEPCION = "RECEPCION"
    FINALIZACION = "FINALIZACION"
    ENTREGA = "ENTREGA"
    MANUAL = "MANUAL"
    ENTRANTE = "ENTRANTE"


class ResultadoEnvio(StrEnum):
    ENVIADO = "ENVIADO"
    ERROR = "ERROR"
    OMITIDO = "OMITIDO"


class WhatsAppService(ABC):
    @abstractmethod
    async def enviar_notificacion(
        self,
        tipo: TipoEvento,
        ticket: Any,  # Ticket SQLAlchemy model
        vehiculo: Any,  # Vehiculo SQLAlchemy model
        db: Session,
    ) -> ResultadoEnvio:
        ...

    @abstractmethod
    async def enviar_mensaje_manual(
        self,
        ticket_id: int,
        telefono: str,
        mensaje: str,
        db: Session,
    ) -> dict:
        ...


class WebhookRouter:
    """
    Determina a qué taller pertenece un mensaje entrante de WhatsApp.
    
    Implementa el routing multi-tenant para webhooks de Twilio/Meta WhatsApp
    usando el número de teléfono de WhatsApp Business que recibió el mensaje.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def route_whatsapp_message(self, payload: dict) -> tuple[int | None, str]:
        """
        Determina qué taller debe recibir un mensaje entrante de WhatsApp.
        
        Extrae el campo 'To' del payload de Twilio (el número de WhatsApp Business
        que recibió el mensaje) y busca el taller que tiene ese número registrado.
        
        Args:
            payload: Payload del webhook de Twilio con estructura:
                {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "metadata": {
                                    "phone_number_id": "...",
                                    "display_phone_number": "+573001234567"
                                },
                                "messages": [...]
                            }
                        }]
                    }]
                }
        
        Returns:
            tuple: (taller_id, phone_number) si se encuentra el taller
                   (None, phone_number) si no se encuentra
        
        Ejemplo:
            >>> router = WebhookRouter(db)
            >>> taller_id, phone = router.route_whatsapp_message(payload)
            >>> if taller_id:
            ...     # Procesar mensaje para ese taller
            ... else:
            ...     # Loguear mensaje no enrutado
        """
        # Extraer el número de teléfono del payload de Twilio/Meta
        phone_number = self._extract_to_field(payload)
        
        if not phone_number:
            return (None, "")
        
        # Buscar el taller por número de WhatsApp Business
        # Usar text() para query SQL directo que funciona con cualquier modelo
        from sqlalchemy import text
        result = self.db.execute(
            text("SELECT id FROM talleres WHERE whatsapp_phone_number = :phone"),
            {"phone": phone_number}
        ).first()
        
        if result:
            return (result[0], phone_number)
        
        return (None, phone_number)
    
    def _extract_to_field(self, payload: dict) -> str | None:
        """
        Extrae el número de teléfono de WhatsApp Business del payload.
        
        El campo 'To' en webhooks de Twilio/Meta está en:
        payload["entry"][0]["changes"][0]["value"]["metadata"]["display_phone_number"]
        
        Args:
            payload: Payload del webhook de Twilio
        
        Returns:
            str: Número de teléfono en formato E.164 (ej: "+573001234567")
            None: Si no se encuentra el campo en el payload
        """
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None
            
            changes = entry[0].get("changes", [])
            if not changes:
                return None
            
            value = changes[0].get("value", {})
            metadata = value.get("metadata", {})
            
            # El número de teléfono de WhatsApp Business que recibió el mensaje
            phone_number = metadata.get("display_phone_number")
            
            return phone_number
        except (IndexError, KeyError, AttributeError):
            return None
