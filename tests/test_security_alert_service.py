"""
Tests unitarios para SecurityAlertService.

Cubre:
- Detección de tipo de destino (Slack, SMTP, webhook)
- Formato de payload para Slack Block Kit
- Formato de payload para webhook genérico
- Formato de email HTML
- Retry exitoso tras fallo inicial
- Retry fallido → SECURITY_ALERT_FAILED en audit log
- Buffer LOW: enqueue y flush
- Sin SECURITY_WEBHOOK_URL → solo warning, no error

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9**
"""

import json
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.servicios.security_alert_service import SecurityAlertService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def alert_payload():
    """Payload de alerta de prueba con todos los campos requeridos."""
    return {
        "event_type": "cross_tenant_access_threshold_exceeded",
        "severity": "HIGH",
        "timestamp": datetime.now(UTC).isoformat(),
        "resource_id": "user:42",
        "remediation": "Revisar actividad del usuario y considerar suspensión.",
    }


@pytest.fixture
def service():
    """Instancia de SecurityAlertService."""
    return SecurityAlertService()


# ---------------------------------------------------------------------------
# Tests de _detect_destination_type
# ---------------------------------------------------------------------------


class TestDetectDestinationType:
    """Tests para la detección del tipo de destino."""

    def test_detecta_slack_webhook(self, service):
        """URLs de Slack deben ser detectadas como 'slack'."""
        url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        assert service._detect_destination_type(url) == "slack"

    def test_detecta_smtp_con_prefijo_smtp(self, service):
        """URLs con prefijo smtp:// deben ser detectadas como 'smtp'."""
        url = "smtp://smtp.gmail.com:587"
        assert service._detect_destination_type(url) == "smtp"

    def test_detecta_smtp_con_prefijo_smtps(self, service):
        """URLs con prefijo smtps:// deben ser detectadas como 'smtp'."""
        url = "smtps://smtp.gmail.com:465"
        assert service._detect_destination_type(url) == "smtp"

    def test_detecta_webhook_generico(self, service):
        """URLs que no son Slack ni SMTP deben ser detectadas como 'webhook'."""
        url = "https://api.example.com/webhooks/security"
        assert service._detect_destination_type(url) == "webhook"

    def test_detecta_webhook_localhost(self, service):
        """URLs localhost deben ser detectadas como 'webhook'."""
        url = "http://localhost:8080/alerts"
        assert service._detect_destination_type(url) == "webhook"


# ---------------------------------------------------------------------------
# Tests de _format_slack
# ---------------------------------------------------------------------------


class TestFormatSlack:
    """Tests para el formato Slack Block Kit."""

    def test_formato_slack_tiene_estructura_block_kit(self, service, alert_payload):
        """El payload formateado debe tener la estructura Block Kit de Slack."""
        formatted = service._format_slack(alert_payload)

        assert "blocks" in formatted
        assert isinstance(formatted["blocks"], list)
        assert len(formatted["blocks"]) == 3  # header, fields, remediation

    def test_formato_slack_tiene_header_con_emoji(self, service, alert_payload):
        """El primer bloque debe ser un header con emoji 🚨."""
        formatted = service._format_slack(alert_payload)
        header = formatted["blocks"][0]

        assert header["type"] == "header"
        assert "🚨" in header["text"]["text"]
        assert "Alerta de Seguridad" in header["text"]["text"]

    def test_formato_slack_tiene_campos_requeridos(self, service, alert_payload):
        """El segundo bloque debe contener los campos Tipo, Severidad, Timestamp, Recurso."""
        formatted = service._format_slack(alert_payload)
        fields_section = formatted["blocks"][1]

        assert fields_section["type"] == "section"
        assert "fields" in fields_section
        fields = fields_section["fields"]

        # Verificar que los 4 campos estén presentes
        assert len(fields) == 4
        field_texts = [f["text"] for f in fields]

        assert any("Tipo:" in text for text in field_texts)
        assert any("Severidad:" in text for text in field_texts)
        assert any("Timestamp:" in text for text in field_texts)
        assert any("Recurso:" in text for text in field_texts)

    def test_formato_slack_tiene_seccion_remediacion(self, service, alert_payload):
        """El tercer bloque debe contener la acción sugerida."""
        formatted = service._format_slack(alert_payload)
        remediation_section = formatted["blocks"][2]

        assert remediation_section["type"] == "section"
        assert "Acción sugerida:" in remediation_section["text"]["text"]
        assert alert_payload["remediation"] in remediation_section["text"]["text"]

    def test_formato_slack_con_campos_faltantes_usa_defaults(self, service):
        """Si faltan campos, debe usar valores por defecto."""
        minimal_payload = {}
        formatted = service._format_slack(minimal_payload)

        # No debe lanzar excepción — debe usar defaults
        assert "blocks" in formatted
        assert len(formatted["blocks"]) == 3


# ---------------------------------------------------------------------------
# Tests de _format_webhook
# ---------------------------------------------------------------------------


class TestFormatWebhook:
    """Tests para el formato de webhook genérico."""

    def test_formato_webhook_incluye_campos_requeridos(self, service, alert_payload):
        """El payload debe incluir todos los campos requeridos."""
        formatted = service._format_webhook(alert_payload)

        assert "event_type" in formatted
        assert "severity" in formatted
        assert "timestamp" in formatted
        assert "resource_id" in formatted
        assert "remediation" in formatted

    def test_formato_webhook_preserva_valores_originales(self, service, alert_payload):
        """Los valores de los campos deben preservarse sin modificación."""
        formatted = service._format_webhook(alert_payload)

        assert formatted["event_type"] == alert_payload["event_type"]
        assert formatted["severity"] == alert_payload["severity"]
        assert formatted["resource_id"] == alert_payload["resource_id"]

    def test_formato_webhook_con_campos_faltantes_usa_defaults(self, service):
        """Si faltan campos, debe usar valores por defecto."""
        minimal_payload = {}
        formatted = service._format_webhook(minimal_payload)

        assert formatted["event_type"] == "desconocido"
        assert formatted["severity"] == "UNKNOWN"
        assert formatted["resource_id"] == "N/A"
        assert "timestamp" in formatted

    def test_formato_webhook_preserva_campos_adicionales(self, service, alert_payload):
        """Campos adicionales no estándar deben preservarse en el payload."""
        alert_payload["custom_field"] = "custom_value"
        alert_payload["user_id"] = 42

        formatted = service._format_webhook(alert_payload)

        assert formatted["custom_field"] == "custom_value"
        assert formatted["user_id"] == 42


# ---------------------------------------------------------------------------
# Tests de _format_email
# ---------------------------------------------------------------------------


class TestFormatEmail:
    """Tests para el formato de email HTML."""

    def test_formato_email_retorna_html_valido(self, service, alert_payload):
        """El email debe ser HTML válido con estructura DOCTYPE."""
        html = service._format_email(alert_payload)

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_formato_email_incluye_campos_requeridos(self, service, alert_payload):
        """El HTML debe incluir todos los campos del evento."""
        html = service._format_email(alert_payload)

        assert alert_payload["event_type"] in html
        assert alert_payload["severity"] in html
        assert alert_payload["resource_id"] in html
        assert alert_payload["remediation"] in html

    def test_formato_email_tiene_encabezado_con_emoji(self, service, alert_payload):
        """El email debe tener un encabezado con emoji 🚨."""
        html = service._format_email(alert_payload)

        assert "🚨" in html
        assert "Alerta de Seguridad" in html

    def test_formato_email_usa_color_rojo_para_high_severity(self, service, alert_payload):
        """Alertas HIGH deben usar color rojo (#dc2626) en el encabezado."""
        alert_payload["severity"] = "HIGH"
        html = service._format_email(alert_payload)

        assert "#dc2626" in html

    def test_formato_email_usa_color_naranja_para_low_severity(self, service, alert_payload):
        """Alertas LOW deben usar color naranja (#d97706) en el encabezado."""
        alert_payload["severity"] = "LOW"
        html = service._format_email(alert_payload)

        assert "#d97706" in html

    def test_formato_email_con_campos_faltantes_usa_defaults(self, service):
        """Si faltan campos, debe usar valores por defecto sin lanzar excepción."""
        minimal_payload = {}
        html = service._format_email(minimal_payload)

        assert "desconocido" in html
        assert "UNKNOWN" in html
        assert "N/A" in html


# ---------------------------------------------------------------------------
# Tests de _deliver_with_retry
# ---------------------------------------------------------------------------


class TestDeliverWithRetry:
    """Tests para el mecanismo de reintentos."""

    @pytest.mark.asyncio
    async def test_retry_exitoso_en_primer_intento(self, service, alert_payload):
        """Si el primer intento es exitoso, no debe reintentar."""
        with patch.object(service, "_send", new_callable=AsyncMock) as mock_send:
            with patch.object(service, "_log_delivery_success") as mock_log_success:
                await service._deliver_with_retry(alert_payload, "https://example.com")

                mock_send.assert_called_once()
                mock_log_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_exitoso_en_segundo_intento(self, service, alert_payload):
        """Si el primer intento falla pero el segundo es exitoso, debe registrar éxito."""
        with patch.object(service, "_send", new_callable=AsyncMock) as mock_send:
            # Primer intento falla, segundo es exitoso
            mock_send.side_effect = [Exception("Network error"), None]

            with patch.object(service, "_log_delivery_success") as mock_log_success:
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    await service._deliver_with_retry(alert_payload, "https://example.com")

                    assert mock_send.call_count == 2
                    mock_log_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_con_backoff_exponencial(self, service, alert_payload):
        """Los reintentos deben usar backoff exponencial: 1s, 2s."""
        with patch.object(service, "_send", new_callable=AsyncMock) as mock_send:
            # Primeros 2 intentos fallan, tercero es exitoso
            mock_send.side_effect = [
                Exception("Error 1"),
                Exception("Error 2"),
                None,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await service._deliver_with_retry(alert_payload, "https://example.com")

                # Verificar que se llamó sleep con 1s y 2s
                assert mock_sleep.call_count == 2
                mock_sleep.assert_has_calls([call(1), call(2)])

    @pytest.mark.asyncio
    async def test_retry_fallido_registra_security_alert_failed(self, service, alert_payload):
        """Si los 3 intentos fallan, debe registrar SECURITY_ALERT_FAILED."""
        with patch.object(service, "_send", new_callable=AsyncMock) as mock_send:
            # Todos los intentos fallan
            mock_send.side_effect = [
                Exception("Error 1"),
                Exception("Error 2"),
                Exception("Error 3"),
            ]

            with patch.object(service, "_log_delivery_failure") as mock_log_failure:
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    await service._deliver_with_retry(alert_payload, "https://example.com")

                    assert mock_send.call_count == 3
                    mock_log_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_fallido_descarta_alerta(self, service, alert_payload):
        """Tras 3 intentos fallidos, la alerta debe descartarse (no reintentar más)."""
        with patch.object(service, "_send", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Persistent error")

            with patch.object(service, "_log_delivery_failure"):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    # No debe lanzar excepción — debe descartar silenciosamente
                    await service._deliver_with_retry(alert_payload, "https://example.com")

                    # Exactamente 3 intentos
                    assert mock_send.call_count == 3


# ---------------------------------------------------------------------------
# Tests de enqueue_low_severity y flush_low_severity_buffer
# ---------------------------------------------------------------------------


class TestLowSeverityBuffer:
    """Tests para el buffer de alertas LOW."""

    @pytest.mark.asyncio
    async def test_enqueue_low_severity_agrega_a_redis(self, service, alert_payload):
        """enqueue_low_severity debe agregar la alerta al buffer Redis."""
        mock_redis = MagicMock()

        with patch.object(service, "_get_redis_client", return_value=mock_redis):
            await service.enqueue_low_severity(alert_payload)

            mock_redis.rpush.assert_called_once()
            # Verificar que se serializó como JSON
            call_args = mock_redis.rpush.call_args[0]
            assert call_args[0] == "security_alerts_low_buffer"
            serialized = call_args[1]
            deserialized = json.loads(serialized)
            assert deserialized["event_type"] == alert_payload["event_type"]

    @pytest.mark.asyncio
    async def test_enqueue_low_severity_renueva_ttl(self, service, alert_payload):
        """enqueue_low_severity debe renovar el TTL del buffer en cada inserción."""
        mock_redis = MagicMock()

        with patch.object(service, "_get_redis_client", return_value=mock_redis):
            await service.enqueue_low_severity(alert_payload)

            mock_redis.expire.assert_called_once_with("security_alerts_low_buffer", 900)

    @pytest.mark.asyncio
    async def test_enqueue_sin_redis_loguea_warning(self, service, alert_payload):
        """Si Redis no está disponible, debe loguear warning y descartar."""
        with patch.object(service, "_get_redis_client", return_value=None):
            with patch("app.servicios.security_alert_service.logger") as mock_logger:
                await service.enqueue_low_severity(alert_payload)

                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_buffer_vacio_no_envia_nada(self, service):
        """Si el buffer está vacío, flush_low_severity_buffer no debe enviar nada."""
        mock_redis = MagicMock()
        mock_redis.pipeline.return_value.execute.return_value = [[], None]

        with patch.object(service, "_get_redis_client", return_value=mock_redis):
            with patch.object(service, "_deliver_with_retry", new_callable=AsyncMock) as mock_deliver:
                await service.flush_low_severity_buffer()

                mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    async def test_flush_buffer_envia_alertas_agrupadas(self, service, alert_payload):
        """flush_low_severity_buffer debe enviar todas las alertas en un solo payload."""
        alert1 = {**alert_payload, "event_type": "event_1"}
        alert2 = {**alert_payload, "event_type": "event_2"}
        alert3 = {**alert_payload, "event_type": "event_3"}

        serialized = [json.dumps(a) for a in [alert1, alert2, alert3]]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value.execute.return_value = [serialized, None]

        with patch.object(service, "_get_redis_client", return_value=mock_redis):
            with patch.object(service, "_deliver_with_retry", new_callable=AsyncMock) as mock_deliver:
                with patch.dict(os.environ, {"SECURITY_WEBHOOK_URL": "https://example.com"}):
                    await service.flush_low_severity_buffer()

                    mock_deliver.assert_called_once()
                    grouped_payload = mock_deliver.call_args[0][0]

                    assert grouped_payload["event_type"] == "low_severity_batch"
                    assert grouped_payload["alert_count"] == 3
                    assert len(grouped_payload["alerts"]) == 3

    @pytest.mark.asyncio
    async def test_flush_buffer_sin_webhook_url_loguea_warning(self, service, alert_payload):
        """Si SECURITY_WEBHOOK_URL no está configurada, debe loguear warning."""
        serialized = [json.dumps(alert_payload)]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value.execute.return_value = [serialized, None]

        with patch.object(service, "_get_redis_client", return_value=mock_redis):
            with patch.dict(os.environ, {"SECURITY_WEBHOOK_URL": ""}, clear=True):
                with patch("app.servicios.security_alert_service.logger") as mock_logger:
                    await service.flush_low_severity_buffer()

                    # Debe loguear warning sobre URL no configurada
                    assert any(
                        "SECURITY_WEBHOOK_URL" in str(call_args)
                        for call_args in mock_logger.warning.call_args_list
                    )


# ---------------------------------------------------------------------------
# Tests de dispatch_high_severity
# ---------------------------------------------------------------------------


class TestDispatchHighSeverity:
    """Tests para el despacho de alertas HIGH."""

    def test_dispatch_high_sin_webhook_url_loguea_warning(self, service, alert_payload):
        """Si SECURITY_WEBHOOK_URL no está configurada, debe loguear warning."""
        with patch.dict(os.environ, {"SECURITY_WEBHOOK_URL": ""}, clear=True):
            with patch("app.servicios.security_alert_service.logger") as mock_logger:
                service.dispatch_high_severity(alert_payload)

                # Debe loguear warning sobre URL no configurada
                assert any(
                    "SECURITY_WEBHOOK_URL" in str(call_args)
                    for call_args in mock_logger.warning.call_args_list
                )

    def test_dispatch_high_con_webhook_url_llama_deliver(self, service, alert_payload):
        """Si SECURITY_WEBHOOK_URL está configurada, debe llamar a _deliver_with_retry."""
        with patch.dict(os.environ, {"SECURITY_WEBHOOK_URL": "https://example.com"}):
            with patch.object(service, "_deliver_with_retry", new_callable=AsyncMock) as mock_deliver:
                with patch("asyncio.run") as mock_run:
                    service.dispatch_high_severity(alert_payload)

                    # Debe haber intentado ejecutar el despacho asíncrono
                    assert mock_run.called or mock_deliver.called


# ---------------------------------------------------------------------------
# Tests de _log_delivery_success y _log_delivery_failure
# ---------------------------------------------------------------------------


class TestAuditLogging:
    """Tests para el registro en audit log."""

    def test_log_delivery_success_registra_security_alert_delivered(self, service, alert_payload):
        """_log_delivery_success debe registrar SECURITY_ALERT_DELIVERED."""
        mock_db = MagicMock()
        mock_session_local = MagicMock(return_value=mock_db)
        mock_audit_log_class = MagicMock()
        mock_audit_log_instance = MagicMock()
        mock_audit_log_class.return_value = mock_audit_log_instance

        with patch("app.configuracion.base_datos.SessionLocal", mock_session_local):
            with patch("app.modelos.audit_log.AuditLog", mock_audit_log_class):
                service._log_delivery_success(alert_payload)

                mock_db.add.assert_called_once_with(mock_audit_log_instance)
                mock_db.commit.assert_called_once()

                # Verificar que se creó un AuditLog con la acción correcta
                call_kwargs = mock_audit_log_class.call_args[1]
                assert call_kwargs["action"] == "SECURITY_ALERT_DELIVERED"

    def test_log_delivery_failure_registra_security_alert_failed(self, service, alert_payload):
        """_log_delivery_failure debe registrar SECURITY_ALERT_FAILED."""
        mock_db = MagicMock()
        mock_session_local = MagicMock(return_value=mock_db)
        mock_audit_log_class = MagicMock()
        mock_audit_log_instance = MagicMock()
        mock_audit_log_class.return_value = mock_audit_log_instance

        error = Exception("Network timeout")

        with patch("app.configuracion.base_datos.SessionLocal", mock_session_local):
            with patch("app.modelos.audit_log.AuditLog", mock_audit_log_class):
                service._log_delivery_failure(alert_payload, error)

                mock_db.add.assert_called_once_with(mock_audit_log_instance)
                mock_db.commit.assert_called_once()

                # Verificar que se creó un AuditLog con la acción correcta
                call_kwargs = mock_audit_log_class.call_args[1]
                assert call_kwargs["action"] == "SECURITY_ALERT_FAILED"
                assert call_kwargs["details"]["delivery_failed"] is True

    def test_log_delivery_failure_incluye_error_en_details(self, service, alert_payload):
        """_log_delivery_failure debe incluir el mensaje de error en details."""
        mock_db = MagicMock()
        mock_session_local = MagicMock(return_value=mock_db)
        mock_audit_log_class = MagicMock()
        mock_audit_log_instance = MagicMock()
        mock_audit_log_class.return_value = mock_audit_log_instance

        error = Exception("Connection refused")

        with patch("app.configuracion.base_datos.SessionLocal", mock_session_local):
            with patch("app.modelos.audit_log.AuditLog", mock_audit_log_class):
                service._log_delivery_failure(alert_payload, error)

                call_kwargs = mock_audit_log_class.call_args[1]
                assert "Connection refused" in call_kwargs["details"]["error"]


# ---------------------------------------------------------------------------
# Tests de integración — _send
# ---------------------------------------------------------------------------


class TestSendIntegration:
    """Tests de integración para el método _send."""

    @pytest.mark.asyncio
    async def test_send_detecta_slack_y_formatea_correctamente(self, service, alert_payload):
        """_send debe detectar Slack y formatear como Block Kit."""
        slack_url = "https://hooks.slack.com/services/T00/B00/XXX"

        with patch.object(service, "_post_json", new_callable=AsyncMock) as mock_post:
            await service._send(alert_payload, slack_url)

            mock_post.assert_called_once()
            posted_payload = mock_post.call_args[0][0]

            # Verificar que se formateó como Block Kit
            assert "blocks" in posted_payload

    @pytest.mark.asyncio
    async def test_send_detecta_webhook_y_formatea_correctamente(self, service, alert_payload):
        """_send debe detectar webhook genérico y formatear como JSON estándar."""
        webhook_url = "https://api.example.com/alerts"

        with patch.object(service, "_post_json", new_callable=AsyncMock) as mock_post:
            await service._send(alert_payload, webhook_url)

            mock_post.assert_called_once()
            posted_payload = mock_post.call_args[0][0]

            # Verificar que se formateó como JSON estándar
            assert "event_type" in posted_payload
            assert "severity" in posted_payload
            assert "blocks" not in posted_payload  # No es Block Kit

    @pytest.mark.asyncio
    async def test_send_detecta_smtp_y_envia_email(self, service, alert_payload):
        """_send debe detectar SMTP y enviar email HTML."""
        smtp_url = "smtp://smtp.gmail.com:587"

        with patch.object(service, "_send_email", new_callable=AsyncMock) as mock_email:
            await service._send(alert_payload, smtp_url)

            mock_email.assert_called_once()
