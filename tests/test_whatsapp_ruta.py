"""
Tests: whatsapp_ruta — webhook y logs
======================================
Cubre los endpoints del router de WhatsApp Business.

Task 25 del spec whatsapp-business-integration.
"""

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.modelos.cita  # noqa: F401
import app.modelos.configuracion_seguridad  # noqa: F401
import app.modelos.configuracion_taller  # noqa: F401
import app.modelos.log_notificacion  # noqa: F401
import app.modelos.movimiento_caja  # noqa: F401
import app.modelos.ticket  # noqa: F401
import app.modelos.ticket_cobro  # noqa: F401
import app.modelos.ticket_compra  # noqa: F401
import app.modelos.ticket_foto  # noqa: F401
import app.modelos.ticket_proceso  # noqa: F401
import app.modelos.ticket_repuesto  # noqa: F401
import app.modelos.vehiculo  # noqa: F401

# Importar TODOS los modelos antes de create_all para que SQLAlchemy resuelva FKs
from app.configuracion.base_datos import Base, obtener_db
from app.modelos.log_notificacion import LogNotificacion
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


# ---------------------------------------------------------------------------
# Task 25.1 — GET /whatsapp/webhook responde al challenge correctamente (req 8.1)
# ---------------------------------------------------------------------------


def test_webhook_get_responde_challenge():
    """
    GET /whatsapp/webhook con token correcto debe retornar 200 y el challenge.
    Validates: Requirements 8.1
    """
    os.environ["WHATSAPP_VERIFY_TOKEN"] = "test_token"
    app, _ = _make_test_app()
    client = TestClient(app)

    response = client.get(
        "/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_token",
            "hub.challenge": "my_challenge",
        },
    )

    assert response.status_code == 200
    assert response.text == "my_challenge"


# ---------------------------------------------------------------------------
# Task 25.2 — GET /whatsapp/webhook con token incorrecto retorna 403 (req 8.4)
# ---------------------------------------------------------------------------


def test_webhook_get_token_incorrecto_retorna_403():
    """
    GET /whatsapp/webhook con token incorrecto debe retornar 403.
    Validates: Requirements 8.4
    """
    os.environ["WHATSAPP_VERIFY_TOKEN"] = "test_token"
    app, _ = _make_test_app()
    client = TestClient(app)

    response = client.get(
        "/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "xyz",
        },
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Task 25.3 — POST /whatsapp/webhook con mensaje entrante crea log ENTRANTE (req 8.3)
# ---------------------------------------------------------------------------


def test_webhook_post_mensaje_entrante_crea_log():
    """
    POST /whatsapp/webhook con un mensaje entrante debe crear un LogNotificacion
    con tipo_evento='ENTRANTE' y el teléfono del remitente.
    Validates: Requirements 8.3
    """
    app, TestSession = _make_test_app()
    client = TestClient(app)

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "573001234567",
                                    "type": "text",
                                    "text": {"body": "Hola"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    response = client.post("/whatsapp/webhook", json=payload)

    assert response.status_code == 200

    db = TestSession()
    try:
        log = db.query(LogNotificacion).filter(LogNotificacion.tipo_evento == "ENTRANTE").first()
        assert log is not None
        assert log.telefono_destino == "573001234567"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task 25.4 — GET /api/mobile/whatsapp/logs retorna estructura correcta (req 7.2)
# ---------------------------------------------------------------------------


def test_logs_retorna_estructura_correcta():
    """
    GET /api/mobile/whatsapp/logs debe retornar una lista con los campos
    id, tipo_evento, resultado y created_at en cada elemento.
    Validates: Requirements 7.2
    """
    app, TestSession = _make_test_app()

    # Insertar un log directamente en la DB
    db = TestSession()
    try:
        log = LogNotificacion(
            tipo_evento="MANUAL",
            resultado="ENVIADO",
            telefono_destino="3001234567",
            mensaje_enviado="Mensaje de prueba",
        )
        db.add(log)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    response = client.get("/api/mobile/whatsapp/logs")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    item = data[0]
    assert "id" in item
    assert "tipo_evento" in item
    assert "resultado" in item
    assert "created_at" in item
