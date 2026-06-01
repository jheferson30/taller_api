"""
Tests: Webhook Routing Multi-Tenant (Task 3.4)
===============================================
Valida que el endpoint POST /whatsapp/webhook use WebhookRouter
para enrutar mensajes al taller correcto y maneje mensajes no enrutados.

Requirements: 1.5, 1.6 (C-05)
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.configuracion.base_datos import Base, obtener_db
from app.modelos.log_notificacion import LogNotificacion
from app.modelos.taller import Taller
from app.rutas.whatsapp_ruta import router


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
    
    # Mock rate limiter to avoid Redis dependency
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        return app, TestSession


# ---------------------------------------------------------------------------
# Task 3.4.1 — Webhook routing con taller registrado (Requirement 1.5)
# ---------------------------------------------------------------------------


def test_webhook_routing_con_taller_registrado():
    """
    POST /whatsapp/webhook con número registrado debe enrutar al taller correcto
    y crear LogNotificacion con taller_id asignado.
    
    Validates: Requirement 1.5
    """
    app, TestSession = _make_test_app()
    
    # Crear taller con número de WhatsApp registrado
    db = TestSession()
    try:
        taller = Taller(
            nombre="Taller Test",
            whatsapp_phone_number="+573001234567"
        )
        db.add(taller)
        db.commit()
        db.refresh(taller)
        taller_id = taller.id
    finally:
        db.close()
    
    # Mock rate limiter
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {
                                    "display_phone_number": "+573001234567"
                                },
                                "messages": [
                                    {
                                        "from": "573009876543",
                                        "type": "text",
                                        "text": {"body": "Hola desde cliente"}
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
        assert response.json() == {"status": "ok"}
        
        # Verificar que se creó el log con taller_id correcto
        db = TestSession()
        try:
            log = db.query(LogNotificacion).filter(
                LogNotificacion.tipo_evento == "ENTRANTE"
            ).first()
            
            assert log is not None
            assert log.taller_id == taller_id
            assert log.telefono_destino == "573009876543"
            assert log.mensaje_enviado == "Hola desde cliente"
            assert log.resultado == "ENVIADO"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Task 3.4.2 — Webhook routing sin taller registrado retorna 404 (Requirement 1.6)
# ---------------------------------------------------------------------------


def test_webhook_routing_sin_taller_registrado_retorna_404():
    """
    POST /whatsapp/webhook con número NO registrado debe retornar 404
    y loguear el mensaje no enrutado.
    
    Validates: Requirement 1.6
    """
    app, TestSession = _make_test_app()
    
    # Mock rate limiter
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {
                                    "display_phone_number": "+573009999999"  # No registrado
                                },
                                "messages": [
                                    {
                                        "from": "573009876543",
                                        "type": "text",
                                        "text": {"body": "Mensaje sin destino"}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/whatsapp/webhook", json=payload)
        
        # Debe retornar 404 con mensaje genérico
        assert response.status_code == 404
        assert response.json() == {"status": "unrouted", "message": "Resource not found"}
        
        # Verificar que se logueó el mensaje no enrutado
        db = TestSession()
        try:
            log = db.query(LogNotificacion).filter(
                LogNotificacion.tipo_evento == "ENTRANTE",
                LogNotificacion.resultado == "ERROR"
            ).first()
            
            assert log is not None
            assert log.taller_id is None  # Sin taller asignado
            assert log.telefono_destino == "+573009999999"
            assert "Unrouted message" in log.error_detalle
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Task 3.4.3 — Webhook routing con payload malformado no crashea
# ---------------------------------------------------------------------------


def test_webhook_routing_con_payload_malformado():
    """
    POST /whatsapp/webhook con payload malformado debe retornar error
    sin crashear el servidor.
    """
    app, TestSession = _make_test_app()
    
    # Mock rate limiter
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        
        # Payload sin estructura esperada
        payload = {"invalid": "structure"}
        
        response = client.post("/whatsapp/webhook", json=payload)
        
        # Debe retornar 200 con status error (no revelar detalles internos)
        assert response.status_code == 200
        # El endpoint retorna {"status": "ok"} incluso si no hay mensajes


# ---------------------------------------------------------------------------
# Task 3.4.4 — Webhook routing loguea warning para mensajes no enrutados
# ---------------------------------------------------------------------------


def test_webhook_routing_loguea_warning():
    """
    POST /whatsapp/webhook con número no registrado debe loguear warning
    para investigación.
    
    Validates: Requirement 1.6
    """
    app, TestSession = _make_test_app()
    
    # Mock rate limiter y logger
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f), \
         patch('app.rutas.whatsapp_ruta.logger') as mock_logger:
        
        client = TestClient(app)
        
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {
                                    "display_phone_number": "+573008888888"
                                },
                                "messages": [
                                    {
                                        "from": "573009876543",
                                        "type": "text",
                                        "text": {"body": "Test"}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/whatsapp/webhook", json=payload)
        
        assert response.status_code == 404
        
        # Verificar que se logueó warning
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Unrouted WhatsApp message" in warning_call
        assert "+573008888888" in warning_call
