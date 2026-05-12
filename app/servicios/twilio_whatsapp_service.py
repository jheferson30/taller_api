import httpx

from app.modelos.configuracion_taller import ConfiguracionTaller
from app.modelos.log_notificacion import LogNotificacion
from app.servicios.whatsapp_service import ResultadoEnvio, TipoEvento, WhatsAppService


class TwilioWhatsAppService(WhatsAppService):
    """
    Implementación concreta de WhatsAppService usando Twilio.
    Lee credenciales de ConfiguracionTaller (id=1) en cada llamada.
    """

    async def enviar_notificacion(
        self,
        tipo: TipoEvento,
        ticket,
        vehiculo,
        db,
    ) -> ResultadoEnvio:
        config = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.id == 1).first()
        taller_id = getattr(ticket, "taller_id", None)

        # 1. WhatsApp deshabilitado
        if config is None or not config.whatsapp_enabled:
            self._persistir_log(
                db=db,
                ticket_id=getattr(ticket, "id", None),
                telefono=None,
                tipo=tipo,
                mensaje=None,
                resultado=ResultadoEnvio.OMITIDO,
                error_detalle=None,
                taller_id=taller_id,
            )
            return ResultadoEnvio.OMITIDO

        # 2. Token vacío o nulo
        if not config.whatsapp_token or not config.whatsapp_token.strip():
            self._persistir_log(
                db=db,
                ticket_id=getattr(ticket, "id", None),
                telefono=None,
                tipo=tipo,
                mensaje=None,
                resultado=ResultadoEnvio.ERROR,
                error_detalle="token_vacio",
                taller_id=taller_id,
            )
            return ResultadoEnvio.ERROR

        # 3. Teléfono del propietario ausente
        telefono = getattr(vehiculo, "telefono_propietario", None)
        if not telefono or not str(telefono).strip():
            self._persistir_log(
                db=db,
                ticket_id=getattr(ticket, "id", None),
                telefono=None,
                tipo=tipo,
                mensaje=None,
                resultado=ResultadoEnvio.OMITIDO,
                error_detalle="sin_telefono",
                taller_id=taller_id,
            )
            return ResultadoEnvio.OMITIDO

        # 4. Construir mensaje y llamar a Twilio API
        mensaje = self._construir_mensaje(tipo, ticket, vehiculo)
        url = f"https://api.twilio.com/2010-04-01/Accounts/{config.whatsapp_phone_id}/Messages.json"
        form_data = {
            "From": f"whatsapp:+{config.whatsapp_phone_id}",
            "To": f"whatsapp:+{telefono}",
            "Body": mensaje,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    data=form_data,
                    auth=(config.whatsapp_phone_id, config.whatsapp_token),
                )

            if response.is_success:
                try:
                    message_sid = response.json().get("sid", "")
                except Exception:
                    message_sid = ""
                self._persistir_log(
                    db=db,
                    ticket_id=getattr(ticket, "id", None),
                    telefono=telefono,
                    tipo=tipo,
                    mensaje=mensaje,
                    resultado=ResultadoEnvio.ENVIADO,
                    error_detalle=message_sid if message_sid else None,
                    taller_id=taller_id,
                )
                return ResultadoEnvio.ENVIADO
            else:
                self._persistir_log(
                    db=db,
                    ticket_id=getattr(ticket, "id", None),
                    telefono=telefono,
                    tipo=tipo,
                    mensaje=mensaje,
                    resultado=ResultadoEnvio.ERROR,
                    error_detalle=f"HTTP {response.status_code}",
                    taller_id=taller_id,
                )
                return ResultadoEnvio.ERROR

        except Exception as exc:
            self._persistir_log(
                db=db,
                ticket_id=getattr(ticket, "id", None),
                telefono=telefono,
                tipo=tipo,
                mensaje=mensaje,
                resultado=ResultadoEnvio.ERROR,
                error_detalle=str(exc),
                taller_id=taller_id,
            )
            return ResultadoEnvio.ERROR

    async def enviar_mensaje_manual(
        self,
        ticket_id: int,
        telefono: str,
        mensaje: str,
        db,
        taller_id=None,
    ) -> dict:
        # 1. Validar longitud del mensaje (req 5.2 / 6.3)
        if len(mensaje) < 1 or len(mensaje) > 1024:
            raise ValueError("El mensaje debe tener entre 1 y 1024 caracteres")

        config = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.id == 1).first()

        # 2. WhatsApp deshabilitado o token vacío (req 1.3 / 1.4)
        if (
            config is None
            or not config.whatsapp_enabled
            or not (config.whatsapp_token or "").strip()
        ):
            self._persistir_log(
                db=db,
                ticket_id=ticket_id,
                telefono=telefono,
                tipo=TipoEvento.MANUAL,
                mensaje=mensaje,
                resultado=ResultadoEnvio.ERROR,
                error_detalle="whatsapp_no_configurado",
                taller_id=taller_id,
            )
            return {"ok": False, "error": "whatsapp_no_configurado"}

        phone_id = config.whatsapp_phone_id
        url = f"https://api.twilio.com/2010-04-01/Accounts/{phone_id}/Messages.json"
        form_data = {
            "From": f"whatsapp:+{phone_id}",
            "To": f"whatsapp:+{telefono}",
            "Body": mensaje,
        }

        # 3. Llamada HTTP a Twilio
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    data=form_data,
                    auth=(phone_id, config.whatsapp_token),
                )

            if response.is_success:
                try:
                    sid = response.json().get("sid", "")
                except Exception:
                    sid = ""
                self._persistir_log(
                    db=db,
                    ticket_id=ticket_id,
                    telefono=telefono,
                    tipo=TipoEvento.MANUAL,
                    mensaje=mensaje,
                    resultado=ResultadoEnvio.ENVIADO,
                    error_detalle=sid if sid else None,
                    taller_id=taller_id,
                )
                return {"ok": True, "message_id": sid}
            else:
                error_detalle = f"HTTP {response.status_code}"
                self._persistir_log(
                    db=db,
                    ticket_id=ticket_id,
                    telefono=telefono,
                    tipo=TipoEvento.MANUAL,
                    mensaje=mensaje,
                    resultado=ResultadoEnvio.ERROR,
                    error_detalle=error_detalle,
                    taller_id=taller_id,
                )
                return {"ok": False, "error": error_detalle}

        except Exception as exc:
            self._persistir_log(
                db=db,
                ticket_id=ticket_id,
                telefono=telefono,
                tipo=TipoEvento.MANUAL,
                mensaje=mensaje,
                resultado=ResultadoEnvio.ERROR,
                error_detalle=str(exc),
                taller_id=taller_id,
            )
            return {"ok": False, "error": str(exc)}

    def _construir_mensaje(self, tipo: TipoEvento, ticket, vehiculo) -> str:
        """Construye el texto del mensaje WhatsApp según el tipo de evento."""
        nombre = getattr(vehiculo, "nombre_propietario", "Cliente")
        placa = getattr(vehiculo, "placa", "")
        ticket_id = getattr(ticket, "id", "")

        if tipo == TipoEvento.RECEPCION:
            motivo = getattr(ticket, "motivo_visita", "")
            return (
                f"Hola {nombre}, tu vehículo {placa} ha ingresado al taller.\n"
                f"Código de ticket: #{ticket_id}\n"
                f"Motivo: {motivo}"
            )

        if tipo == TipoEvento.FINALIZACION:
            total = getattr(ticket, "total", 0) or 0
            saldo = getattr(ticket, "saldo_pendiente", 0) or 0
            if saldo == 0:
                pago_linea = "Servicio completamente pagado."
            else:
                pago_linea = f"Total: ${total} | Saldo pendiente: ${saldo}"
            return (
                f"Hola {nombre}, el servicio de tu vehículo {placa} ha finalizado.\n"
                f"Código de ticket: #{ticket_id}\n"
                f"{pago_linea}"
            )

        if tipo == TipoEvento.ENTREGA:
            recomendaciones = getattr(ticket, "recomendaciones", None)
            base = (
                f"Hola {nombre}, tu vehículo {placa} está listo para retirar.\n"
                f"Código de ticket: #{ticket_id}"
            )
            if recomendaciones and str(recomendaciones).strip():
                base += f"\nRecomendaciones: {recomendaciones}"
            return base

        return ""

    def _persistir_log(
        self,
        db,
        ticket_id,
        telefono,
        tipo: TipoEvento,
        mensaje,
        resultado: ResultadoEnvio,
        error_detalle,
        taller_id=None,
    ) -> None:
        """Persiste un registro en log_notificacion. Nunca propaga excepciones."""
        try:
            log = LogNotificacion(
                taller_id=taller_id,
                ticket_id=ticket_id,
                telefono_destino=telefono,
                tipo_evento=tipo.value,
                mensaje_enviado=mensaje,
                resultado=resultado.value,
                error_detalle=error_detalle,
            )
            db.add(log)
            db.commit()
        except Exception as exc:
            print(f"[TwilioWhatsAppService] Error al persistir log: {exc}")
