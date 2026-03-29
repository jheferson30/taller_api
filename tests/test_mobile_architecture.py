import hashlib
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.configuracion.base_datos import Base, obtener_db
import app.modelos.cita  # noqa: F401
import app.modelos.configuracion_seguridad  # noqa: F401
import app.modelos.configuracion_taller  # noqa: F401
import app.modelos.movimiento_caja  # noqa: F401
import app.modelos.ticket  # noqa: F401
import app.modelos.ticket_cobro  # noqa: F401
import app.modelos.ticket_compra  # noqa: F401
import app.modelos.ticket_foto  # noqa: F401
import app.modelos.ticket_proceso  # noqa: F401
import app.modelos.ticket_repuesto  # noqa: F401
import app.modelos.vehiculo  # noqa: F401
from app.modelos.configuracion_seguridad import ConfiguracionSeguridad
from app.modelos.ticket import Ticket
from app.modelos.ticket_cobro import TicketCobro
from app.modelos.ticket_compra import TicketCompra
from app.modelos.ticket_foto import TicketFoto
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.ticket_repuesto import TicketRepuesto
from app.modelos.vehiculo import Vehiculo


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _make_test_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _make_mobile_client():
    __import__("slowapi")
    from app.rutas import mobile_api_ruta

    app = FastAPI()
    session_factory = _make_test_session()

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[obtener_db] = override_db
    app.include_router(mobile_api_ruta.router)
    return TestClient(app), session_factory


def _make_vehicle_and_ticket(db):
    vehiculo = Vehiculo(
        placa="MOB001",
        marca="Mazda",
        modelo="3",
        anio=2022,
        nombre_propietario="Laura",
        telefono_propietario="3001112233",
    )
    db.add(vehiculo)
    db.flush()

    ticket = Ticket(
        vehiculo_id=vehiculo.id,
        ticket_codigo="TK-MOB-001",
        placa=vehiculo.placa,
        motivo_visita="Diagnostico",
        estado="EN_PROCESO",
        anticipo_recibido=25_000,
        total_servicio=180_000,
        saldo_pendiente=95_000,
    )
    db.add(ticket)
    db.flush()
    return ticket


def test_rate_limiting_en_seguridad_retorna_429_al_exceder_limite():
    pytest = __import__("pytest")
    pytest.importorskip("slowapi", reason="slowapi no esta instalado en este entorno")

    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    from app.configuracion.limiter import limiter
    from app.rutas import seguridad_ruta

    app = FastAPI()
    session_factory = _make_test_session()

    storage = getattr(limiter, "_storage", None)
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.dependency_overrides[obtener_db] = override_db
    app.include_router(seguridad_ruta.router)
    client = TestClient(app)

    db = session_factory()
    try:
        db.add(
            ConfiguracionSeguridad(
                clave="economia_password",
                valor_hash=_hash_password("secreto-ok"),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/seguridad/economia/validar-password",
        json={"password": "secreto-ok"},
    )
    assert response.status_code == 200

    ultima_respuesta = None
    for _ in range(10):
        ultima_respuesta = client.post(
            "/seguridad/economia/validar-password",
            json={"password": "secreto-ok"},
        )

    assert ultima_respuesta is not None
    assert ultima_respuesta.status_code == 429


def test_resumen_mobile_retorna_los_mismos_contadores_y_totales():
    pytest = __import__("pytest")
    pytest.importorskip("slowapi", reason="slowapi no esta instalado en este entorno")

    client, session_factory = _make_mobile_client()

    db = session_factory()
    try:
        ticket = _make_vehicle_and_ticket(db)

        db.add_all(
            [
                TicketProceso(ticket_id=ticket.id, nombre="Diagnostico"),
                TicketProceso(ticket_id=ticket.id, nombre="Cambio de aceite"),
                TicketRepuesto(ticket_id=ticket.id, nombre="Filtro", cantidad=1),
                TicketRepuesto(ticket_id=ticket.id, nombre="Aceite", cantidad=4),
                TicketFoto(ticket_id=ticket.id, tipo="ANTES", archivo_url="/foto-1.jpg"),
                TicketFoto(ticket_id=ticket.id, tipo="DESPUES", archivo_url="/foto-2.jpg"),
                TicketFoto(ticket_id=ticket.id, tipo="PROCESO", archivo_url="/foto-3.jpg"),
                TicketCompra(ticket_id=ticket.id, descripcion="Aceite", valor=40_000),
                TicketCompra(ticket_id=ticket.id, descripcion="Filtro", valor=15_000),
                TicketCobro(ticket_id=ticket.id, concepto="Abono 1", valor=20_000),
                TicketCobro(ticket_id=ticket.id, concepto="Abono 2", valor=40_000),
            ]
        )
        db.commit()
        ticket_id = ticket.id
    finally:
        db.close()

    password = os.getenv("ADMIN_PASSWORD") or os.getenv("PDF_PASSWORD", "")
    response = client.get(
        f"/api/mobile/tickets/{ticket_id}/resumen",
        headers={"X-Admin-Password": password},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["contadores"]["procesos"] == 2
    assert data["contadores"]["repuestos"] == 2
    assert data["contadores"]["fotos"] == 2
    assert data["contadores"]["compras"] == 2
    assert data["finanzas"]["total_egresos"] == 55_000
    assert data["finanzas"]["total_cobros"] == 60_000
    assert data["finanzas"]["anticipo"] == 25_000
    assert data["finanzas"]["total_servicio"] == 180_000
    assert data["finanzas"]["saldo_pendiente"] == 95_000


def test_mobile_schema_se_puede_importar_sin_router():
    from app.esquemas.mobile_schema import TicketListResponse

    schema = TicketListResponse(
        id=1,
        ticket_codigo="TK-1",
        placa="ABC123",
        motivo_visita="Revision",
        estado="ABIERTO",
        fecha_ingreso="2026-03-29T10:00:00",
    )

    assert schema.ticket_codigo == "TK-1"
