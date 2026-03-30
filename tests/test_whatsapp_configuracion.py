"""
Tests: whatsapp_configuracion — envío manual de mensajes
=========================================================
Cubre validación de mensajes manuales y envío exitoso.

Task 26 del spec whatsapp-business-integration.
"""

from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importar TODOS los modelos antes de create_all para que SQLAlchemy resuelva FKs
from app.configuracion.base_datos import Base, obtener_db
import app.modelos.vehiculo          # noqa: F401
import app.modelos.ticket            # noqa: F401
import app.modelos.ticket_cobro      # noqa: F401
import app.modelos.ticket_proceso    # noqa: F401
import app.modelos.ticket_repuesto   # noqa: F401
import app.modelos.ticket_foto       # noqa: F401
import app.modelos.ticket_compra     # noqa: F401
import app.modelos.movimiento_caja   # noqa: F401
import app.modelos.cita              # noqa: F401
import app.modelos.configuracion_seguridad  # noqa: F401
import app.modelos.configuracion_taller     # noqa: F401
import app.modelos.log_notificacion         # noqa: F401

from app.modelos.vehiculo import Vehiculo
from app.modelos.ticket import Ticket
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.rutas.whatsapp_ruta import router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_app():
    """Crea una app FastAPI con SQLite en memoria y el router de WhatsApp."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[obtener_db] = override_db
    return app, TestSession


def _seed_ticket_con_telefono(TestSession):
    """Inserta un vehiculo y ticket con teléfono válido. Retorna ticket_id."""
    db = TestSession()
    try:
        vehiculo = Vehiculo(
            placa="ABC123",
            nombre_propietario="Juan Pérez",
            telefono_propietario="3001234567",
        )
        db.add(vehiculo)
        db.flush()

        ticket = Ticket(
            vehiculo_id=vehiculo.id,
            ticket_codigo="T-001",
            placa="ABC123",
            motivo_visita="Revisión general",
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket.id
    finally:
        db.close()


def _seed_configuracion(TestSession):
    """Inserta ConfiguracionTaller con whatsapp habilitado."""
    db = TestSession()
    try:
        config = ConfiguracionTaller(
            id=1,
            nombre_taller="Taller Test",
            whatsapp_enabled=True,
            whatsapp_token="token_test_123",
            whatsapp_phone_id="15550001111",
        )
        db.add(config)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task 26.1 — mensaje vacío retorna HTTP 422 (req 5.2, 6.3)
# ---------------------------------------------------------------------------

def test_envio_manual_mensaje_vacio_retorna_422_mobile():
    """
    POST /api/mobile/tickets/{id}/whatsapp con mensaje vacío debe retornar 422.
    Validates: Requirements 5.2, 6.3
    """
    app, _ = _make_test_app()
    client = TestClient(app)

    response = client.post(
        "/api/mobile/tickets/1/whatsapp",
        json={"mensaje": ""},
    )

    assert response.status_code == 422


def test_envio_manual_mensaje_vacio_retorna_422_web():
    """
    POST /api/whatsapp/tickets/{id}/mensaje con mensaje vacío debe retornar 422.
    Validates: Requirements 5.2, 6.3
    """
    app, _ = _make_test_app()
    client = TestClient(app)

    response = client.post(
        "/api/whatsapp/tickets/1/mensaje",
        json={"mensaje": ""},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Task 26.2 — mensaje >1024 chars retorna HTTP 422 (req 5.2, 6.3)
# ---------------------------------------------------------------------------

def test_envio_manual_mensaje_largo_retorna_422_mobile():
    """
    POST /api/mobile/tickets/{id}/whatsapp con mensaje >1024 chars debe retornar 422.
    Validates: Requirements 5.2, 6.3
    """
    app, _ = _make_test_app()
    client = TestClient(app)

    mensaje_largo = "x" * 1025

    response = client.post(
        "/api/mobile/tickets/1/whatsapp",
        json={"mensaje": mensaje_largo},
    )

    assert response.status_code == 422


def test_envio_manual_mensaje_largo_retorna_422_web():
    """
    POST /api/whatsapp/tickets/{id}/mensaje con mensaje >1024 chars debe retornar 422.
    Validates: Requirements 5.2, 6.3
    """
    app, _ = _make_test_app()
    client = TestClient(app)

    mensaje_largo = "x" * 1025

    response = client.post(
        "/api/whatsapp/tickets/1/mensaje",
        json={"mensaje": mensaje_largo},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Task 26.3 — envío exitoso retorna message_id (req 5.3, 6.4)
# ---------------------------------------------------------------------------

def test_envio_manual_exitoso_retorna_message_id_mobile():
    """
    POST /api/mobile/tickets/{id}/whatsapp con datos válidos y mock de httpx
    debe retornar {"ok": true, "message_id": "SM123456"}.
    Validates: Requirements 5.3, 6.4
    """
    app, TestSession = _make_test_app()
    ticket_id = _seed_ticket_con_telefono(TestSession)
    _seed_configuracion(TestSession)

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"sid": "SM123456"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    client = TestClient(app)

    with patch("httpx.AsyncClient", return_value=mock_client):
        response = client.post(
            f"/api/mobile/tickets/{ticket_id}/whatsapp",
            json={"mensaje": "Hola, ¿cómo va el trabajo?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["message_id"] == "SM123456"


def test_envio_manual_exitoso_retorna_message_id_web():
    """
    POST /api/whatsapp/tickets/{id}/mensaje con datos válidos y mock de httpx
    debe retornar {"ok": true, "message_id": "SM123456"}.
    Validates: Requirements 5.3, 6.4
    """
    app, TestSession = _make_test_app()
    ticket_id = _seed_ticket_con_telefono(TestSession)
    _seed_configuracion(TestSession)

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"sid": "SM123456"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    client = TestClient(app)

    with patch("httpx.AsyncClient", return_value=mock_client):
        response = client.post(
            f"/api/whatsapp/tickets/{ticket_id}/mensaje",
            json={"mensaje": "Hola, ¿cómo va el trabajo?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["message_id"] == "SM123456"
