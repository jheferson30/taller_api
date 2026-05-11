"""
Servicio de despacho de alertas de seguridad a destinos externos.

Soporta tres tipos de destino:
- Slack webhook (hooks.slack.com) → formato Block Kit
- SMTP (smtp:// o smtps://) → email HTML via aiosmtplib
- Webhook genérico → POST JSON con aiohttp

Las alertas HIGH se despachan de forma inmediata; las LOW se acumulan en un
buffer Redis y se envían agrupadas cada 15 minutos por el job de seguridad.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9
"""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal

logger = logging.getLogger(__name__)

# Clave Redis para el buffer de alertas LOW
_REDIS_BUFFER_KEY = "security_alerts_low_buffer"
# TTL del buffer (15 minutos en segundos)
_REDIS_BUFFER_TTL = 900


class SecurityAlertService:
    """
    Servicio de despacho de alertas de seguridad a destinos externos.

    Detecta automáticamente el tipo de destino a partir de la URL configurada
    en ``SECURITY_WEBHOOK_URL`` y formatea el payload de acuerdo al protocolo
    correspondiente (Slack Block Kit, email HTML o JSON genérico).

    Uso:
        service = SecurityAlertService()
        service.dispatch_high_severity({
            "event_type": "cross_tenant_access_threshold_exceeded",
            "severity": "HIGH",
            "resource_id": "user:42",
            "remediation": "Revisar actividad del usuario y considerar suspensión.",
            "timestamp": datetime.now(UTC).isoformat(),
        })
    """

    def dispatch_high_severity(self, alert_details: dict) -> None:
        """
        Despacha una alerta de severidad HIGH de forma inmediata (síncrona).

        Intenta ejecutar el despacho asíncrono en el event loop activo.
        Si no hay loop activo, crea uno temporal para la operación.

        Args:
            alert_details: Diccionario con los campos del evento de seguridad.
                           Debe incluir: event_type, severity, resource_id,
                           remediation y timestamp.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Dentro de un contexto async — crear tarea en el loop activo
                asyncio.ensure_future(self._dispatch_async(alert_details))
            else:
                loop.run_until_complete(self._dispatch_async(alert_details))
        except RuntimeError:
            # No hay event loop — crear uno nuevo
            asyncio.run(self._dispatch_async(alert_details))

    async def enqueue_low_severity(self, alert_details: dict) -> None:
        """
        Encola una alerta de severidad LOW en el buffer Redis.

        Las alertas LOW se acumulan y se envían agrupadas cada 15 minutos
        por el job ``flush_security_alerts``.

        Args:
            alert_details: Diccionario con los campos del evento de seguridad.

        Raises:
            No lanza excepciones — los errores de Redis se loguean y se descartan.
        """
        redis_client = self._get_redis_client()
        if redis_client is None:
            logger.warning(
                "Redis no disponible — alerta LOW descartada: %s",
                alert_details.get("event_type", "unknown"),
            )
            return

        try:
            serialized = json.dumps(alert_details, default=str)
            redis_client.rpush(_REDIS_BUFFER_KEY, serialized)
            # Renovar TTL en cada inserción para mantener la ventana de 15 minutos
            redis_client.expire(_REDIS_BUFFER_KEY, _REDIS_BUFFER_TTL)
            logger.debug(
                "Alerta LOW encolada en buffer Redis: %s",
                alert_details.get("event_type", "unknown"),
            )
        except Exception as exc:
            logger.error(
                "Error al encolar alerta LOW en Redis: %s — alerta: %s",
                exc,
                alert_details.get("event_type", "unknown"),
            )

    async def flush_low_severity_buffer(self) -> None:
        """
        Extrae todas las alertas LOW del buffer Redis y las envía agrupadas.

        Si el buffer está vacío, retorna sin hacer nada.
        Si el despacho falla, registra el fallo en el audit log y descarta.

        Llamado por el job ``flush_security_alerts`` cada 15 minutos.
        """
        redis_client = self._get_redis_client()
        if redis_client is None:
            logger.warning("Redis no disponible — no se puede vaciar el buffer LOW.")
            return

        try:
            # Extraer todos los elementos del buffer atómicamente
            pipeline = redis_client.pipeline()
            pipeline.lrange(_REDIS_BUFFER_KEY, 0, -1)
            pipeline.delete(_REDIS_BUFFER_KEY)
            results = pipeline.execute()
            raw_alerts = results[0]
        except Exception as exc:
            logger.error("Error al leer buffer LOW de Redis: %s", exc)
            return

        if not raw_alerts:
            logger.debug("Buffer de alertas LOW vacío — nada que enviar.")
            return

        # Deserializar alertas
        alerts = []
        for raw in raw_alerts:
            try:
                alerts.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                logger.warning("Alerta LOW con formato inválido descartada: %s", exc)

        if not alerts:
            return

        # Construir payload agrupado
        grouped_payload = {
            "event_type": "low_severity_batch",
            "severity": "LOW",
            "timestamp": datetime.now(UTC).isoformat(),
            "alert_count": len(alerts),
            "alerts": alerts,
            "remediation": (
                f"Se han acumulado {len(alerts)} alerta(s) de baja severidad. "
                "Revisar el listado adjunto para identificar patrones."
            ),
            "resource_id": "security_alert_buffer",
        }

        webhook_url = os.getenv("SECURITY_WEBHOOK_URL")
        if not webhook_url:
            logger.warning(
                "SECURITY_WEBHOOK_URL no configurada — batch de %d alerta(s) LOW descartado.",
                len(alerts),
            )
            return

        await self._deliver_with_retry(grouped_payload, webhook_url)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    async def _dispatch_async(self, alert_details: dict) -> None:
        """
        Ejecuta el despacho asíncrono de una alerta HIGH.

        Detecta el destino configurado, formatea el payload y lo entrega
        con reintentos. Si no hay URL configurada, solo loguea una advertencia.

        Args:
            alert_details: Diccionario con los campos del evento de seguridad.
        """
        webhook_url = os.getenv("SECURITY_WEBHOOK_URL")
        if not webhook_url:
            logger.warning(
                "SECURITY_WEBHOOK_URL no configurada — alerta HIGH no entregada: %s",
                alert_details.get("event_type", "unknown"),
            )
            return

        await self._deliver_with_retry(alert_details, webhook_url)

    async def _deliver_with_retry(self, payload: dict, url: str) -> None:
        """
        Entrega un payload al destino con hasta 3 intentos y backoff exponencial.

        Intentos:
        - Intento 0: inmediato
        - Intento 1: espera 1 segundo (2^0)
        - Intento 2: espera 2 segundos (2^1)

        Si los 3 intentos fallan, registra ``AuditAction.SECURITY_ALERT_FAILED``
        en el audit log y descarta la alerta.

        Args:
            payload: Diccionario con los datos de la alerta.
            url:     URL de destino (Slack, SMTP o webhook genérico).
        """
        last_exception: Exception | None = None

        for attempt in range(3):
            try:
                await self._send(payload, url)
                logger.info(
                    "Alerta entregada exitosamente en intento %d: %s",
                    attempt + 1,
                    payload.get("event_type", "unknown"),
                )
                self._log_delivery_success(payload)
                return
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Intento %d/%d fallido al entregar alerta '%s': %s",
                    attempt + 1,
                    3,
                    payload.get("event_type", "unknown"),
                    exc,
                )
                if attempt < 2:
                    await asyncio.sleep(2**attempt)  # 1s, 2s

        # Todos los intentos agotados — registrar fallo y descartar
        logger.error(
            "Alerta descartada tras 3 intentos fallidos: %s — último error: %s",
            payload.get("event_type", "unknown"),
            last_exception,
        )
        self._log_delivery_failure(payload, last_exception)

    async def _send(self, payload: dict, url: str) -> None:
        """
        Envía el payload al destino detectado.

        Delega al método de envío específico según el tipo de destino:
        Slack, SMTP o webhook genérico.

        Args:
            payload: Diccionario con los datos de la alerta.
            url:     URL de destino.

        Raises:
            Exception: Cualquier error de red o protocolo para que
                       ``_deliver_with_retry`` pueda reintentar.
        """
        destination_type = self._detect_destination_type(url)

        if destination_type == "slack":
            formatted = self._format_slack(payload)
            await self._post_json(formatted, url)
        elif destination_type == "smtp":
            await self._send_email(payload, url)
        else:
            formatted = self._format_webhook(payload)
            await self._post_json(formatted, url)

    @staticmethod
    def _detect_destination_type(url: str) -> Literal["slack", "smtp", "webhook"]:
        """
        Detecta el tipo de destino a partir de la URL.

        Reglas:
        - ``hooks.slack.com`` en la URL → Slack
        - URL que empieza con ``smtp://`` o ``smtps://`` → SMTP
        - Cualquier otra URL → webhook genérico

        Args:
            url: URL del destino de alertas.

        Returns:
            Literal "slack", "smtp" o "webhook".
        """
        if "hooks.slack.com" in url:
            return "slack"
        if url.startswith("smtp://") or url.startswith("smtps://"):
            return "smtp"
        return "webhook"

    @staticmethod
    def _format_slack(payload: dict) -> dict:
        """
        Formatea el payload como un mensaje Slack Block Kit.

        Estructura:
        - Header con emoji 🚨 y título
        - Sección con campos: Tipo, Severidad, Timestamp, Recurso
        - Sección con la acción sugerida (remediación)

        Args:
            payload: Diccionario con los campos del evento de seguridad.

        Returns:
            Diccionario con la estructura Block Kit de Slack.
        """
        event_type = payload.get("event_type", "desconocido")
        severity = payload.get("severity", "UNKNOWN")
        timestamp = payload.get("timestamp", datetime.now(UTC).isoformat())
        resource_id = payload.get("resource_id", "N/A")
        remediation = payload.get("remediation", "Revisar logs del sistema.")

        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Alerta de Seguridad",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Tipo:* {event_type}"},
                        {"type": "mrkdwn", "text": f"*Severidad:* {severity}"},
                        {"type": "mrkdwn", "text": f"*Timestamp:* {timestamp}"},
                        {"type": "mrkdwn", "text": f"*Recurso:* {resource_id}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Acción sugerida:* {remediation}",
                    },
                },
            ]
        }

    @staticmethod
    def _format_webhook(payload: dict) -> dict:
        """
        Formatea el payload como JSON estándar para un webhook genérico.

        Garantiza que todos los campos requeridos estén presentes:
        event_type, severity, timestamp, resource_id y remediation.

        Args:
            payload: Diccionario con los campos del evento de seguridad.

        Returns:
            Diccionario normalizado con todos los campos requeridos.
        """
        return {
            "event_type": payload.get("event_type", "desconocido"),
            "severity": payload.get("severity", "UNKNOWN"),
            "timestamp": payload.get("timestamp", datetime.now(UTC).isoformat()),
            "resource_id": payload.get("resource_id", "N/A"),
            "remediation": payload.get("remediation", "Revisar logs del sistema."),
            **{k: v for k, v in payload.items() if k not in {
                "event_type", "severity", "timestamp", "resource_id", "remediation"
            }},
        }

    @staticmethod
    def _format_email(payload: dict) -> str:
        """
        Formatea el payload como un email HTML.

        Genera un HTML con tabla de campos del evento y sección de remediación,
        listo para enviar via SMTP.

        Args:
            payload: Diccionario con los campos del evento de seguridad.

        Returns:
            String con el cuerpo HTML del email.
        """
        event_type = payload.get("event_type", "desconocido")
        severity = payload.get("severity", "UNKNOWN")
        timestamp = payload.get("timestamp", datetime.now(UTC).isoformat())
        resource_id = payload.get("resource_id", "N/A")
        remediation = payload.get("remediation", "Revisar logs del sistema.")

        # Color de severidad para el encabezado
        severity_color = "#dc2626" if severity == "HIGH" else "#d97706"

        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alerta de Seguridad</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px;">
    <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 8px;
                border: 1px solid #e2e8f0; overflow: hidden;">

        <!-- Encabezado -->
        <div style="background-color: {severity_color}; padding: 20px 24px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 1.4rem;">
                🚨 Alerta de Seguridad
            </h1>
            <p style="color: #fecaca; margin: 4px 0 0; font-size: 0.9rem;">
                Severidad: <strong>{severity}</strong>
            </p>
        </div>

        <!-- Cuerpo -->
        <div style="padding: 24px;">
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 10px 0; color: #64748b; font-weight: bold; width: 35%;">
                        Tipo de evento
                    </td>
                    <td style="padding: 10px 0; color: #1e293b;">{event_type}</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 10px 0; color: #64748b; font-weight: bold;">Severidad</td>
                    <td style="padding: 10px 0; color: #1e293b;">{severity}</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 10px 0; color: #64748b; font-weight: bold;">Timestamp</td>
                    <td style="padding: 10px 0; color: #1e293b;">{timestamp}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; color: #64748b; font-weight: bold;">Recurso</td>
                    <td style="padding: 10px 0; color: #1e293b;">{resource_id}</td>
                </tr>
            </table>

            <!-- Acción sugerida -->
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b;
                        padding: 16px; border-radius: 4px;">
                <p style="margin: 0; font-weight: bold; color: #92400e;">Acción sugerida</p>
                <p style="margin: 8px 0 0; color: #78350f;">{remediation}</p>
            </div>
        </div>

        <!-- Pie -->
        <div style="background-color: #f1f5f9; padding: 16px 24px; text-align: center;">
            <p style="margin: 0; color: #94a3b8; font-size: 0.8rem;">
                Este mensaje fue generado automáticamente por el sistema de seguridad.
            </p>
        </div>
    </div>
</body>
</html>
"""

    async def _send_email(self, payload: dict, smtp_url: str) -> None:
        """
        Envía el payload como email HTML via aiosmtplib.

        Lee la configuración SMTP desde las variables de entorno:
        ``SECURITY_ALERT_SMTP_HOST``, ``SECURITY_ALERT_SMTP_PORT``,
        ``SECURITY_ALERT_SMTP_USER``, ``SECURITY_ALERT_SMTP_PASSWORD``,
        ``SECURITY_ALERT_SMTP_FROM``, ``SECURITY_ALERT_SMTP_TO``.

        Args:
            payload:  Diccionario con los campos del evento de seguridad.
            smtp_url: URL SMTP (smtp:// o smtps://) — usada para detectar TLS.

        Raises:
            RuntimeError: Si las variables SMTP no están configuradas.
            Exception:    Cualquier error de aiosmtplib para que el caller reintente.
        """
        import aiosmtplib

        smtp_host = os.getenv("SECURITY_ALERT_SMTP_HOST", "")
        smtp_port = int(os.getenv("SECURITY_ALERT_SMTP_PORT", "587"))
        smtp_user = os.getenv("SECURITY_ALERT_SMTP_USER", "")
        smtp_password = os.getenv("SECURITY_ALERT_SMTP_PASSWORD", "")
        smtp_from = os.getenv("SECURITY_ALERT_SMTP_FROM", smtp_user)
        smtp_to = os.getenv("SECURITY_ALERT_SMTP_TO", "")

        if not smtp_host or not smtp_user or not smtp_to:
            raise RuntimeError(
                "Variables SMTP no configuradas. "
                "Verificar: SECURITY_ALERT_SMTP_HOST, SECURITY_ALERT_SMTP_USER, "
                "SECURITY_ALERT_SMTP_TO"
            )

        event_type = payload.get("event_type", "Alerta de Seguridad")
        severity = payload.get("severity", "UNKNOWN")
        subject = f"[{severity}] Alerta de Seguridad: {event_type}"

        html_body = self._format_email(payload)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = smtp_from
        message["To"] = smtp_to
        message.attach(MIMEText(html_body, "html", "utf-8"))

        # smtps:// → TLS desde el inicio; smtp:// → STARTTLS
        use_tls = smtp_url.startswith("smtps://")

        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            use_tls=use_tls,
            start_tls=not use_tls,
        )

        logger.info(
            "Email de alerta enviado a %s: %s",
            smtp_to,
            event_type,
        )

    @staticmethod
    async def _post_json(payload: dict, url: str) -> None:
        """
        Realiza un POST JSON al URL especificado via aiohttp.

        Args:
            payload: Diccionario a serializar como JSON en el body.
            url:     URL de destino.

        Raises:
            aiohttp.ClientResponseError: Si el servidor responde con 4xx/5xx.
            aiohttp.ClientError:         Cualquier error de red.
        """
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                logger.debug(
                    "POST JSON entregado a %s — status: %d",
                    url,
                    response.status,
                )

    @staticmethod
    def _get_redis_client():
        """
        Obtiene un cliente Redis síncrono para operaciones de buffer.

        Returns:
            Cliente Redis, o ``None`` si Redis no está disponible.
        """
        try:
            import redis as redis_lib

            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            client = redis_lib.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception as exc:
            logger.warning(
                "Redis no disponible para buffer de alertas LOW (%s).",
                exc,
            )
            return None

    @staticmethod
    def _log_delivery_success(payload: dict) -> None:
        """
        Registra en el audit log que la alerta fue entregada exitosamente.

        Usa ``AuditAction.SECURITY_ALERT_DELIVERED``.

        Args:
            payload: Diccionario con los campos del evento de seguridad.
        """
        try:
            from app.configuracion.base_datos import SessionLocal
            from app.modelos.audit_log import AuditAction, AuditLog

            db = SessionLocal()
            try:
                entry = AuditLog(
                    user_id=None,
                    action=AuditAction.SECURITY_ALERT_DELIVERED,
                    resource_type="security_alert",
                    resource_id=None,
                    ip_address="system",
                    user_agent=None,
                    details={
                        "event_type": payload.get("event_type"),
                        "severity": payload.get("severity"),
                        "timestamp": payload.get("timestamp"),
                        "resource_id": payload.get("resource_id"),
                    },
                )
                db.add(entry)
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.error(
                "No se pudo registrar entrega exitosa de alerta en audit log: %s",
                exc,
            )

    @staticmethod
    def _log_delivery_failure(payload: dict, error: Exception | None) -> None:
        """
        Registra en el audit log que la alerta falló tras 3 reintentos.

        Usa ``AuditAction.SECURITY_ALERT_FAILED`` según el requisito 7.9.

        Args:
            payload: Diccionario con los campos del evento de seguridad.
            error:   Última excepción capturada durante los reintentos.
        """
        try:
            from app.configuracion.base_datos import SessionLocal
            from app.modelos.audit_log import AuditAction, AuditLog

            db = SessionLocal()
            try:
                entry = AuditLog(
                    user_id=None,
                    action=AuditAction.SECURITY_ALERT_FAILED,
                    resource_type="security_alert",
                    resource_id=None,
                    ip_address="system",
                    user_agent=None,
                    details={
                        "delivery_failed": True,
                        "event_type": payload.get("event_type"),
                        "severity": payload.get("severity"),
                        "timestamp": payload.get("timestamp"),
                        "resource_id": payload.get("resource_id"),
                        "error": str(error) if error else None,
                    },
                )
                db.add(entry)
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.error(
                "No se pudo registrar fallo de entrega de alerta en audit log: %s",
                exc,
            )
