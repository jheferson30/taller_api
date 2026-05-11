"""
Tests unitarios para verificar RLS en el endpoint de logs de WhatsApp.

Tarea 3.2 del spec seguridad-rls: Add authentication and RLS filter to WhatsApp logs endpoint (C-04)

Requirements: 1.3, 1.4
"""

import os
from datetime import datetime
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.configuracion.base_datos import Base, obtener_db
from app.modelos.log_notificacion import LogNotificacion
from app.rutas.whatsapp_ruta import router
from app.seguridad.token_manager import TokenManager


@pytest.fixture
def test_app():
    """Crea una app FastAPI con SQLite en memoria."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Crear tablas simples sin foreign keys para tests
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE talleres (
                id INTEGER PRIMARY KEY,
                nombre VARCHAR(200) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY,
                vehiculo_id INTEGER
            )
        """))
        conn.execute(text("""
            CREATE TABLE log_notificacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                taller_id INTEGER,
                ticket_id INTEGER,
                telefono_destino VARCHAR(30),
                tipo_evento VARCHAR(20) NOT NULL,
                mensaje_enviado TEXT,
                resultado VARCHAR(10) NOT NULL,
                error_detalle TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
    
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


@pytest.fixture
def token_manager():
    """Crea un TokenManager para generar tokens de prueba."""
    os.environ["JWT_SECRET_KEY"] = "test_secret_key_with_at_least_32_characters_for_security"
    os.environ["JWT_ALGORITHM"] = "HS256"
    return TokenManager()


def test_whatsapp_logs_requires_authentication(test_app):
    """
    Test: GET /api/mobile/whatsapp/logs sin JWT debe retornar 401.
    
    Validates: Requirement 1.3 - El endpoint requiere autenticación
    """
    app, _ = test_app
    client = TestClient(app)
    
    # Act: Request sin token JWT
    response = client.get("/api/mobile/whatsapp/logs")
    
    # Assert: Debe retornar 401 Unauthorized
    assert response.status_code == 401


def test_whatsapp_logs_filters_by_taller_id(test_app, token_manager):
    """
    Test: GET /api/mobile/whatsapp/logs debe filtrar logs por taller_id del JWT.
    
    Validates: Requirement 1.4 - El endpoint filtra por taller_id del JWT
    """
    app, TestSession = test_app
    
    # Arrange: Crear logs para dos talleres diferentes
    db = TestSession()
    try:
        log_taller_1 = LogNotificacion(
            taller_id=1,
            tipo_evento="MANUAL",
            resultado="ENVIADO",
            telefono_destino="3001111111",
            mensaje_enviado="Mensaje taller 1",
            created_at=datetime.now()
        )
        log_taller_2 = LogNotificacion(
            taller_id=2,
            tipo_evento="MANUAL",
            resultado="ENVIADO",
            telefono_destino="3002222222",
            mensaje_enviado="Mensaje taller 2",
            created_at=datetime.now()
        )
        db.add(log_taller_1)
        db.add(log_taller_2)
        db.commit()
        log_id_1 = log_taller_1.id
        log_id_2 = log_taller_2.id
    finally:
        db.close()
    
    # Act: Request con JWT de taller_id=1
    token = token_manager.create_access_token(
        data={"sub": "user1", "taller_id": 1, "roles": ["ADMIN"]}
    )
    
    # Mock del middleware de autenticación
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            # Simular que el middleware ya validó el token
            scope["state"] = {"user": {"sub": "user1"}, "taller_id": 1}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    
    client = TestClient(app)
    response = client.get(
        "/api/mobile/whatsapp/logs",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert: Debe retornar solo logs de taller_id=1
    assert response.status_code == 200
    logs = response.json()
    
    # Verificar que solo hay logs del taller 1
    assert len(logs) == 1
    assert logs[0]["id"] == log_id_1
    assert logs[0]["telefono_destino"] == "3001111111"
    
    # Verificar que NO hay logs del taller 2
    log_ids = [log["id"] for log in logs]
    assert log_id_2 not in log_ids


def test_whatsapp_logs_returns_only_own_taller_data(test_app, token_manager):
    """
    Test: GET /api/mobile/whatsapp/logs nunca retorna logs de otro taller.
    
    Validates: Requirement 1.4 - Cross-tenant isolation
    """
    app, TestSession = test_app
    
    # Arrange: Crear múltiples logs para taller 1 y taller 2
    db = TestSession()
    try:
        for i in range(3):
            db.add(LogNotificacion(
                taller_id=1,
                tipo_evento="MANUAL",
                resultado="ENVIADO",
                telefono_destino=f"30011111{i}",
                mensaje_enviado=f"Mensaje taller 1 - {i}",
                created_at=datetime.now()
            ))
        
        for i in range(3):
            db.add(LogNotificacion(
                taller_id=2,
                tipo_evento="MANUAL",
                resultado="ENVIADO",
                telefono_destino=f"30022222{i}",
                mensaje_enviado=f"Mensaje taller 2 - {i}",
                created_at=datetime.now()
            ))
        
        db.commit()
    finally:
        db.close()
    
    # Act: Request con JWT de taller_id=2
    token = token_manager.create_access_token(
        data={"sub": "user2", "taller_id": 2, "roles": ["ADMIN"]}
    )
    
    # Mock del middleware de autenticación
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            scope["state"] = {"user": {"sub": "user2"}, "taller_id": 2}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    
    client = TestClient(app)
    response = client.get(
        "/api/mobile/whatsapp/logs",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert: Debe retornar solo logs de taller_id=2
    assert response.status_code == 200
    logs = response.json()
    
    # Verificar que hay exactamente 3 logs
    assert len(logs) == 3
    
    # Verificar que todos los logs son del taller 2
    for log in logs:
        # El teléfono debe empezar con 30022222
        assert log["telefono_destino"].startswith("30022222")
        # El mensaje debe contener "taller 2"
        assert "taller 2" in log["mensaje_enviado"]


def test_whatsapp_logs_with_ticket_id_filter(test_app, token_manager):
    """
    Test: GET /api/mobile/whatsapp/logs?ticket_id=X debe filtrar por ticket_id y taller_id.
    
    Validates: Requirement 1.4 - Filtrado combinado por taller_id y ticket_id
    """
    app, TestSession = test_app
    
    # Arrange: Crear logs con diferentes ticket_ids
    db = TestSession()
    try:
        db.add(LogNotificacion(
            taller_id=1,
            ticket_id=100,
            tipo_evento="MANUAL",
            resultado="ENVIADO",
            telefono_destino="3001111111",
            mensaje_enviado="Mensaje ticket 100",
            created_at=datetime.now()
        ))
        db.add(LogNotificacion(
            taller_id=1,
            ticket_id=200,
            tipo_evento="MANUAL",
            resultado="ENVIADO",
            telefono_destino="3001111111",
            mensaje_enviado="Mensaje ticket 200",
            created_at=datetime.now()
        ))
        db.commit()
    finally:
        db.close()
    
    # Act: Request con JWT de taller_id=1 y filtro ticket_id=100
    token = token_manager.create_access_token(
        data={"sub": "user1", "taller_id": 1, "roles": ["ADMIN"]}
    )
    
    # Mock del middleware de autenticación
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            scope["state"] = {"user": {"sub": "user1"}, "taller_id": 1}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    
    client = TestClient(app)
    response = client.get(
        "/api/mobile/whatsapp/logs?ticket_id=100",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert: Debe retornar solo el log del ticket 100
    assert response.status_code == 200
    logs = response.json()
    
    assert len(logs) == 1
    assert logs[0]["ticket_id"] == 100
    assert "ticket 100" in logs[0]["mensaje_enviado"]
