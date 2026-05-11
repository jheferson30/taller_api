"""
Unit tests for miscellaneous RLS fixes (Phase 6).

Tests authentication requirements for:
- cambiar_password_admin (seguridad_ruta.py)
- All ticket_ruta.py endpoints
- listar_mecanicos (configuracion_ruta.py)

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.modelos.mecanico import Mecanico
from app.modelos.ticket import Ticket
from app.modelos.vehiculo import Vehiculo
from tests.conftest import create_test_user, generate_jwt_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Create test user with taller_id."""
    return create_test_user(db_session, username="testuser", taller_id=1)


@pytest.fixture
def jwt_token(test_user):
    """Generate JWT token for test user."""
    return generate_jwt_token(test_user)


@pytest.fixture
def test_vehiculo(db_session):
    """Create test vehicle."""
    vehiculo = Vehiculo(
        placa="ABC123",
        nombre_propietario="Juan Pérez",
        telefono_propietario="3001234567",
        taller_id=1,
    )
    db_session.add(vehiculo)
    db_session.commit()
    db_session.refresh(vehiculo)
    return vehiculo


@pytest.fixture
def test_ticket(db_session, test_vehiculo):
    """Create test ticket."""
    ticket = Ticket(
        ticket_codigo="TK-ABC123-20260508120000",
        placa="ABC123",
        vehiculo_id=test_vehiculo.id,
        motivo_visita="Cambio de aceite",
        estado="ABIERTO",
        kilometraje=15000,
        taller_id=1,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


@pytest.fixture
def test_mecanico(db_session):
    """Create test mechanic."""
    mecanico = Mecanico(nombre="Carlos Méndez", activo=True, taller_id=1)
    db_session.add(mecanico)
    db_session.commit()
    db_session.refresh(mecanico)
    return mecanico


# ── Tests for cambiar_password_admin (M-01) ──────────────────────────────────


def test_cambiar_password_admin_without_jwt_returns_401(client):
    """
    Test cambiar_password_admin without JWT returns 401.
    Requirement: 5.1
    """
    response = client.post(
        "/seguridad/cambiar-password-admin",
        json={
            "password_actual": "oldpassword",
            "password_nueva": "newpassword123",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_cambiar_password_admin_with_valid_jwt_processes_request(
    client, jwt_token, db_session
):
    """
    Test cambiar_password_admin with valid JWT processes request.
    Requirement: 5.1, 5.5
    """
    # Set up existing admin password in DB
    from app.modelos.configuracion_seguridad import ConfiguracionSeguridad
    import hashlib

    existing_hash = hashlib.sha256("oldpassword".encode()).hexdigest()
    config = ConfiguracionSeguridad(clave="admin_password", valor_hash=existing_hash)
    db_session.add(config)
    db_session.commit()

    response = client.post(
        "/seguridad/cambiar-password-admin",
        json={
            "password_actual": "oldpassword",
            "password_nueva": "newpassword123",
        },
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    # Should process (may return 200 or validation error, but not 401)
    assert response.status_code != status.HTTP_401_UNAUTHORIZED


# ── Tests for ticket_ruta.py endpoints (M-02) ─────────────────────────────────


def test_listar_procesos_rapidos_without_jwt_returns_401(client):
    """
    Test GET /tickets/procesos-rapidos without JWT returns 401.
    Requirement: 5.2
    """
    response = client.get("/tickets/procesos-rapidos")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_listar_procesos_rapidos_with_jwt_returns_200(client, jwt_token):
    """
    Test GET /tickets/procesos-rapidos with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.get(
        "/tickets/procesos-rapidos", headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert response.status_code == status.HTTP_200_OK


def test_listar_tickets_abiertos_without_jwt_returns_401(client):
    """
    Test GET /tickets/abiertos without JWT returns 401.
    Requirement: 5.2
    """
    response = client.get("/tickets/abiertos")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_listar_tickets_abiertos_with_jwt_returns_200(client, jwt_token):
    """
    Test GET /tickets/abiertos with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.get(
        "/tickets/abiertos", headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert response.status_code == status.HTTP_200_OK


def test_buscar_tickets_without_jwt_returns_401(client):
    """
    Test GET /tickets/buscar without JWT returns 401.
    Requirement: 5.2
    """
    response = client.get("/tickets/buscar")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_buscar_tickets_with_jwt_returns_200(client, jwt_token):
    """
    Test GET /tickets/buscar with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.get(
        "/tickets/buscar", headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert response.status_code == status.HTTP_200_OK


def test_obtener_ticket_without_jwt_returns_401(client, test_ticket):
    """
    Test GET /tickets/{id} without JWT returns 401.
    Requirement: 5.2
    """
    response = client.get(f"/tickets/{test_ticket.id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_obtener_ticket_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test GET /tickets/{id} with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.get(
        f"/tickets/{test_ticket.id}", headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert response.status_code == status.HTTP_200_OK


def test_obtener_resumen_ticket_without_jwt_returns_401(client, test_ticket):
    """
    Test GET /tickets/{id}/resumen without JWT returns 401.
    Requirement: 5.2
    """
    response = client.get(f"/tickets/{test_ticket.id}/resumen")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_obtener_resumen_ticket_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test GET /tickets/{id}/resumen with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.get(
        f"/tickets/{test_ticket.id}/resumen",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_agregar_proceso_without_jwt_returns_401(client, test_ticket):
    """
    Test POST /tickets/{id}/procesos without JWT returns 401.
    Requirement: 5.2
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/procesos",
        json={
            "nombre": "Cambio de aceite",
            "mecanico": "Carlos",
            "descripcion": "Aceite 20W50",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_proceso_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test POST /tickets/{id}/procesos with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/procesos",
        json={
            "nombre": "Cambio de aceite",
            "mecanico": "Carlos",
            "descripcion": "Aceite 20W50",
        },
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_eliminar_proceso_without_jwt_returns_401(client, test_ticket):
    """
    Test DELETE /tickets/{id}/procesos/{proceso_id} without JWT returns 401.
    Requirement: 5.2
    """
    response = client.delete(f"/tickets/{test_ticket.id}/procesos/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_repuesto_without_jwt_returns_401(client, test_ticket):
    """
    Test POST /tickets/{id}/repuestos without JWT returns 401.
    Requirement: 5.2
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/repuestos",
        json={
            "nombre": "Filtro de aceite",
            "cantidad": 1,
            "marca_referencia": "Bosch",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_repuesto_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test POST /tickets/{id}/repuestos with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/repuestos",
        json={
            "nombre": "Filtro de aceite",
            "cantidad": 1,
            "marca_referencia": "Bosch",
        },
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_eliminar_repuesto_without_jwt_returns_401(client, test_ticket):
    """
    Test DELETE /tickets/{id}/repuestos/{repuesto_id} without JWT returns 401.
    Requirement: 5.2
    """
    response = client.delete(f"/tickets/{test_ticket.id}/repuestos/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_foto_without_jwt_returns_401(client, test_ticket):
    """
    Test POST /tickets/{id}/fotos without JWT returns 401.
    Requirement: 5.2
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/fotos",
        json={"tipo": "ANTES", "archivo_url": "/uploads/foto.jpg"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_foto_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test POST /tickets/{id}/fotos with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/fotos",
        json={"tipo": "ANTES", "archivo_url": "/uploads/foto.jpg"},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_eliminar_foto_without_jwt_returns_401(client, test_ticket):
    """
    Test DELETE /tickets/{id}/fotos/{foto_id} without JWT returns 401.
    Requirement: 5.2
    """
    response = client.delete(f"/tickets/{test_ticket.id}/fotos/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_compra_without_jwt_returns_401(client, test_ticket):
    """
    Test POST /tickets/{id}/compras without JWT returns 401.
    Requirement: 5.2
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/compras",
        json={
            "descripcion": "Repuesto X",
            "valor": 50000,
            "responsable": "Carlos",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_compra_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test POST /tickets/{id}/compras with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/compras",
        json={
            "descripcion": "Repuesto X",
            "valor": 50000,
            "responsable": "Carlos",
        },
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_eliminar_compra_without_jwt_returns_401(client, test_ticket):
    """
    Test DELETE /tickets/{id}/compras/{compra_id} without JWT returns 401.
    Requirement: 5.2
    """
    response = client.delete(f"/tickets/{test_ticket.id}/compras/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_cobro_without_jwt_returns_401(client, test_ticket):
    """
    Test POST /tickets/{id}/cobros without JWT returns 401.
    Requirement: 5.2
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/cobros",
        json={"concepto": "Anticipo", "valor": 50000},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_agregar_cobro_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test POST /tickets/{id}/cobros with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/cobros",
        json={"concepto": "Anticipo", "valor": 50000},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_eliminar_cobro_without_jwt_returns_401(client, test_ticket):
    """
    Test DELETE /tickets/{id}/cobros/{cobro_id} without JWT returns 401.
    Requirement: 5.2
    """
    response = client.delete(f"/tickets/{test_ticket.id}/cobros/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_actualizar_finanzas_ticket_without_jwt_returns_401(client, test_ticket):
    """
    Test PUT /tickets/{id}/finanzas without JWT returns 401.
    Requirement: 5.2
    """
    response = client.put(
        f"/tickets/{test_ticket.id}/finanzas",
        json={"total_servicio": 150000, "metodo_pago_final": "EFECTIVO"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_actualizar_finanzas_ticket_with_jwt_returns_200(
    client, jwt_token, test_ticket
):
    """
    Test PUT /tickets/{id}/finanzas with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.put(
        f"/tickets/{test_ticket.id}/finanzas",
        json={"total_servicio": 150000, "metodo_pago_final": "EFECTIVO"},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_actualizar_observaciones_finales_without_jwt_returns_401(client, test_ticket):
    """
    Test PUT /tickets/{id}/observaciones-finales without JWT returns 401.
    Requirement: 5.2
    """
    response = client.put(
        f"/tickets/{test_ticket.id}/observaciones-finales",
        json={"observaciones_finales": "Todo OK"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_actualizar_observaciones_finales_with_jwt_returns_200(
    client, jwt_token, test_ticket
):
    """
    Test PUT /tickets/{id}/observaciones-finales with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.put(
        f"/tickets/{test_ticket.id}/observaciones-finales",
        json={"observaciones_finales": "Todo OK"},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_finalizar_ticket_without_jwt_returns_401(client, test_ticket):
    """
    Test POST /tickets/{id}/finalizar without JWT returns 401.
    Requirement: 5.2
    """
    response = client.post(f"/tickets/{test_ticket.id}/finalizar")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_finalizar_ticket_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test POST /tickets/{id}/finalizar with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/finalizar",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_generar_pdf_cliente_without_jwt_returns_401(client, test_ticket):
    """
    Test GET /tickets/{id}/pdf without JWT returns 401.
    Requirement: 5.2
    """
    response = client.get(f"/tickets/{test_ticket.id}/pdf")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_generar_pdf_cliente_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test GET /tickets/{id}/pdf with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    response = client.get(
        f"/tickets/{test_ticket.id}/pdf",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_marcar_entregado_without_jwt_returns_401(client, test_ticket):
    """
    Test POST /tickets/{id}/entregar without JWT returns 401.
    Requirement: 5.2
    """
    response = client.post(
        f"/tickets/{test_ticket.id}/entregar",
        json={"confirmado_entrega_por": "Juan Pérez"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_marcar_entregado_with_jwt_returns_200(client, jwt_token, test_ticket):
    """
    Test POST /tickets/{id}/entregar with JWT returns 200.
    Requirement: 5.2, 5.5
    """
    # First finalize the ticket
    test_ticket.estado = "FINALIZADO"
    test_ticket.total_servicio = 150000

    response = client.post(
        f"/tickets/{test_ticket.id}/entregar",
        json={"confirmado_entrega_por": "Juan Pérez"},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


# ── Tests for listar_mecanicos (M-03) ─────────────────────────────────────────


def test_listar_mecanicos_without_jwt_returns_401(client):
    """
    Test GET /configuracion/mecanicos without JWT returns 401.
    Requirement: 5.3
    """
    response = client.get("/configuracion/mecanicos")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_listar_mecanicos_with_jwt_returns_200(client, jwt_token, test_mecanico):
    """
    Test GET /configuracion/mecanicos with JWT returns 200.
    Requirement: 5.3, 5.5
    """
    response = client.get(
        "/configuracion/mecanicos", headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


# ── Tests for generic error messages (5.4) ────────────────────────────────────


def test_endpoints_return_generic_401_message(client):
    """
    Test that endpoints return generic 401 message when JWT is missing.
    Requirement: 5.4
    """
    endpoints = [
        "/seguridad/cambiar-password-admin",
        "/tickets/procesos-rapidos",
        "/tickets/abiertos",
        "/configuracion/mecanicos",
    ]

    for endpoint in endpoints:
        if endpoint == "/seguridad/cambiar-password-admin":
            response = client.post(endpoint, json={})
        else:
            response = client.get(endpoint)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Verify generic message (not revealing internal details)
        assert "Authentication required" in response.json().get("detail", "")
