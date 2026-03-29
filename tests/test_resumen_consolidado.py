"""
Tests de Resumen Consolidado
=============================
Verifica que el endpoint GET /api/mobile/tickets/{id}/resumen
retorna una respuesta idéntica a la implementación original,
usando contadores y sumas calculados con func.count() y func.coalesce(func.sum(...)).

**Validates: Requirements 3.10**
"""

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.configuracion.base_datos import Base, obtener_db
import app.modelos.vehiculo  # noqa: F401
import app.modelos.ticket  # noqa: F401
import app.modelos.ticket_cobro  # noqa: F401
import app.modelos.ticket_proceso  # noqa: F401
import app.modelos.ticket_repuesto  # noqa: F401
import app.modelos.ticket_foto  # noqa: F401
import app.modelos.ticket_compra  # noqa: F401
import app.modelos.movimiento_caja  # noqa: F401
import app.modelos.cita  # noqa: F401
import app.modelos.configuracion_seguridad  # noqa: F401

from app.modelos.ticket import Ticket
from app.modelos.vehiculo import Vehiculo
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.ticket_repuesto import TicketRepuesto
from app.modelos.ticket_foto import TicketFoto
from app.modelos.ticket_compra import TicketCompra
from app.modelos.ticket_cobro import TicketCobro


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_and_db():
    """Crea un TestClient con DB SQLite en memoria y el router mobile_api."""
    pytest.importorskip("slowapi", reason="slowapi no está instalado en este entorno")
    __import__("slowapi")
    from app.rutas import mobile_api_ruta

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    app = FastAPI()

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[obtener_db] = override_db
    app.include_router(mobile_api_ruta.router)

    client = TestClient(app)
    db = TestSession()
    yield client, db
    db.close()


def _crear_ticket(db, codigo="TK-001", placa="ABC123", anticipo=0, total_servicio=None):
    """Crea un vehículo y ticket mínimos en la sesión dada."""
    vehiculo = Vehiculo(
        placa=placa,
        marca="Toyota",
        modelo="Corolla",
        anio=2022,
        nombre_propietario="Propietario Test",
        telefono_propietario="3001234567",
    )
    db.add(vehiculo)
    db.flush()

    ticket = Ticket(
        vehiculo_id=vehiculo.id,
        ticket_codigo=codigo,
        placa=placa,
        motivo_visita="Revisión general",
        anticipo_recibido=anticipo,
        total_servicio=total_servicio,
        estado="ABIERTO",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def _admin_headers():
    password = os.getenv("ADMIN_PASSWORD") or os.getenv("PDF_PASSWORD", "")
    return {"X-Admin-Password": password}


# ---------------------------------------------------------------------------
# Tests principales
# ---------------------------------------------------------------------------

class TestResumenConContadores:
    """
    Validates: Requirements 3.10

    Verifica que contadores.procesos, contadores.repuestos, contadores.fotos,
    contadores.compras y finanzas.total_egresos, finanzas.total_cobros
    coinciden con los datos insertados.
    """

    def test_contadores_con_datos_conocidos(self, client_and_db):
        """
        Crea un ticket con 2 procesos, 3 repuestos, 2 fotos (no PROCESO),
        1 compra y 1 cobro. Verifica que el resumen refleja exactamente esos valores.
        """
        client, db = client_and_db
        ticket = _crear_ticket(db, codigo="TK-CONT-001", placa="TST001")

        # 2 procesos
        for i in range(2):
            db.add(TicketProceso(ticket_id=ticket.id, nombre=f"Proceso {i+1}"))

        # 3 repuestos
        for i in range(3):
            db.add(TicketRepuesto(ticket_id=ticket.id, nombre=f"Repuesto {i+1}", cantidad=1))

        # 2 fotos tipo ANTES (no PROCESO → deben contarse)
        for i in range(2):
            db.add(TicketFoto(ticket_id=ticket.id, tipo="ANTES", archivo_url=f"/fotos/foto{i}.jpg"))

        # 1 foto tipo PROCESO (NO debe contarse en fotos)
        db.add(TicketFoto(ticket_id=ticket.id, tipo="PROCESO", archivo_url="/fotos/proceso.jpg"))

        # 1 compra con valor 50000
        db.add(TicketCompra(ticket_id=ticket.id, descripcion="Repuesto X", valor=50_000))

        # 1 cobro con valor 30000
        db.add(TicketCobro(ticket_id=ticket.id, concepto="Pago parcial", valor=30_000))

        db.commit()

        response = client.get(f"/api/mobile/tickets/{ticket.id}/resumen", headers=_admin_headers())
        assert response.status_code == 200

        data = response.json()
        contadores = data["contadores"]
        finanzas = data["finanzas"]

        assert contadores["procesos"] == 2
        assert contadores["repuestos"] == 3
        assert contadores["fotos"] == 2  # la foto tipo PROCESO no cuenta
        assert contadores["compras"] == 1
        assert finanzas["total_egresos"] == 50_000
        assert finanzas["total_cobros"] == 30_000

    def test_multiples_compras_y_cobros_suma_correcta(self, client_and_db):
        """
        Verifica que total_egresos y total_cobros son la suma de todos los registros.
        """
        client, db = client_and_db
        ticket = _crear_ticket(db, codigo="TK-SUMA-001", placa="TST002")

        # 3 compras: 10000 + 20000 + 30000 = 60000
        for valor in [10_000, 20_000, 30_000]:
            db.add(TicketCompra(ticket_id=ticket.id, descripcion="Compra", valor=valor))

        # 2 cobros: 15000 + 25000 = 40000
        for valor in [15_000, 25_000]:
            db.add(TicketCobro(ticket_id=ticket.id, concepto="Cobro", valor=valor))

        db.commit()

        response = client.get(f"/api/mobile/tickets/{ticket.id}/resumen", headers=_admin_headers())
        assert response.status_code == 200

        data = response.json()
        assert data["finanzas"]["total_egresos"] == 60_000
        assert data["finanzas"]["total_cobros"] == 40_000

    def test_estructura_respuesta_completa(self, client_and_db):
        """
        Verifica que la respuesta contiene todos los campos esperados:
        ticket_id, ticket_codigo, placa, estado, contadores y finanzas.
        """
        client, db = client_and_db
        ticket = _crear_ticket(db, codigo="TK-STRUCT-001", placa="TST003", anticipo=5_000, total_servicio=100_000)
        db.commit()

        response = client.get(f"/api/mobile/tickets/{ticket.id}/resumen", headers=_admin_headers())
        assert response.status_code == 200

        data = response.json()

        # Campos de identificación
        assert data["ticket_id"] == ticket.id
        assert data["ticket_codigo"] == "TK-STRUCT-001"
        assert data["placa"] == "TST003"
        assert data["estado"] == "ABIERTO"

        # Estructura de contadores
        assert "contadores" in data
        assert "procesos" in data["contadores"]
        assert "repuestos" in data["contadores"]
        assert "fotos" in data["contadores"]
        assert "compras" in data["contadores"]

        # Estructura de finanzas
        assert "finanzas" in data
        assert "total_egresos" in data["finanzas"]
        assert "total_cobros" in data["finanzas"]
        assert "anticipo" in data["finanzas"]
        assert "total_servicio" in data["finanzas"]
        assert "saldo_pendiente" in data["finanzas"]


# ---------------------------------------------------------------------------
# Edge case: ticket sin registros relacionados
# ---------------------------------------------------------------------------

class TestResumenTicketVacio:
    """
    Validates: Requirements 3.10

    Ticket sin procesos, repuestos, fotos, compras ni cobros → todos los
    contadores deben ser 0 y los totales financieros también 0.
    """

    def test_ticket_sin_registros_retorna_ceros(self, client_and_db):
        """
        Un ticket recién creado sin ningún registro relacionado debe retornar
        todos los contadores y totales en 0.
        """
        client, db = client_and_db
        ticket = _crear_ticket(db, codigo="TK-EMPTY-001", placa="TST004")

        response = client.get(f"/api/mobile/tickets/{ticket.id}/resumen", headers=_admin_headers())
        assert response.status_code == 200

        data = response.json()
        contadores = data["contadores"]
        finanzas = data["finanzas"]

        assert contadores["procesos"] == 0
        assert contadores["repuestos"] == 0
        assert contadores["fotos"] == 0
        assert contadores["compras"] == 0
        assert finanzas["total_egresos"] == 0
        assert finanzas["total_cobros"] == 0

    def test_ticket_inexistente_retorna_404(self, client_and_db):
        """
        Un ticket_id que no existe debe retornar 404.
        """
        client, _ = client_and_db
        response = client.get("/api/mobile/tickets/99999/resumen", headers=_admin_headers())
        assert response.status_code == 404

    def test_sin_autenticacion_retorna_401_o_403(self, client_and_db):
        """
        Sin cabecera X-Admin-Password el endpoint debe rechazar la petición.
        """
        client, db = client_and_db
        ticket = _crear_ticket(db, codigo="TK-AUTH-001", placa="TST005")

        response = client.get(f"/api/mobile/tickets/{ticket.id}/resumen")
        assert response.status_code in (401, 403)
