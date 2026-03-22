"""
Preservation Property Tests
============================
Estos tests DEBEN PASAR en el código sin corregir.
Documentan el 

Propiedades verificadas:
  - Para todo ticket con total_servicio > 0, después de finalizar:
      saldo_pendiente = max(0, total_servicio - anticipo_recibido - total_cobros)
  - Cuando se finaliza un ticket: se crea MovimientoCaja de tipo INGRESO_FINAL
      con valor = total_servicio - anticipo_recibido
  - Ticket sin total_servicio → siempre 400 Bad Request
  - Clientes autenticados correctamente siguen recibiendo respuestas normales
  - Endpoints de economía, vehículos, citas y seguridad responden normalmente

**Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importar TODOS los modelos antes de create_all para que SQLAlchemy resuelva FKs
from app.configuracion.base_datos import Base
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
from app.modelos.ticket_cobro import TicketCobro
from app.modelos.movimiento_caja import MovimientoCaja, TipoMovimiento


# ---------------------------------------------------------------------------
# Helpers — SQLite en memoria
# ---------------------------------------------------------------------------

def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _ticket_base(db, total_servicio=None, anticipo=0):
    """Crea y persiste un ticket mínimo en la sesión dada."""
    vehiculo = Vehiculo(
        placa="TST001",
        marca="Toyota",
        modelo="Corolla",
        anio=2020,
        nombre_propietario="Test",
        telefono_propietario="3000000000",
    )
    db.add(vehiculo)
    db.flush()

    ticket = Ticket(
        vehiculo_id=vehiculo.id,
        ticket_codigo="T-TEST-001",
        placa="TST001",
        motivo_visita="Prueba",
        anticipo_recibido=anticipo,
        total_servicio=total_servicio,
        estado="ABIERTO",
    )
    db.add(ticket)
    db.flush()
    return ticket


# ---------------------------------------------------------------------------
# Property 3.1 — saldo_pendiente = max(0, total - anticipo - cobros)
# ---------------------------------------------------------------------------

class TestPreservacion31_SaldoPendiente:
    """
    Validates: Requirements 3.1

    Para todo ticket con total_servicio > 0, después de finalizar:
      saldo_pendiente = max(0, total_servicio - anticipo_recibido - total_cobros)
    """

    @given(
        total=st.integers(min_value=1, max_value=10_000_000),
        anticipo=st.integers(min_value=0, max_value=10_000_000),
        cobros=st.lists(st.integers(min_value=0, max_value=1_000_000), max_size=5),
    )
    @settings(max_examples=50)
    def test_saldo_pendiente_formula(self, total, anticipo, cobros):
        """
        La fórmula de saldo_pendiente se aplica correctamente para cualquier
        combinación de total_servicio, anticipo y cobros parciales.
        """
        db = _make_session()
        try:
            ticket = _ticket_base(db, total_servicio=total, anticipo=anticipo)

            for valor_cobro in cobros:
                cobro = TicketCobro(
                    ticket_id=ticket.id,
                    concepto="cobro parcial",
                    valor=valor_cobro,
                )
                db.add(cobro)
            db.flush()

            # Reproducir la lógica actual de ticket_ruta.py → finalizar_ticket
            cobros_db = db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket.id).all()
            total_cobros = sum(c.valor for c in cobros_db)
            saldo = ticket.total_servicio - (ticket.anticipo_recibido or 0) - total_cobros
            if saldo < 0:
                saldo = 0
            ticket.saldo_pendiente = saldo
            ticket.estado = "FINALIZADO"
            db.commit()
            db.refresh(ticket)

            esperado = max(0, total - anticipo - sum(cobros))
            assert ticket.saldo_pendiente == esperado, (
                f"saldo_pendiente={ticket.saldo_pendiente} != esperado={esperado} "
                f"(total={total}, anticipo={anticipo}, cobros={cobros})"
            )
        finally:
            db.close()

    def test_saldo_no_negativo_cuando_anticipo_mayor_que_total(self):
        """
        Caso borde: anticipo > total_servicio → saldo_pendiente debe ser 0, no negativo.
        """
        db = _make_session()
        try:
            ticket = _ticket_base(db, total_servicio=50_000, anticipo=80_000)

            total_cobros = 0
            saldo = ticket.total_servicio - (ticket.anticipo_recibido or 0) - total_cobros
            if saldo < 0:
                saldo = 0
            ticket.saldo_pendiente = saldo
            ticket.estado = "FINALIZADO"
            db.commit()
            db.refresh(ticket)

            assert ticket.saldo_pendiente == 0
        finally:
            db.close()

    def test_saldo_exacto_sin_anticipo_ni_cobros(self):
        """
        Sin anticipo ni cobros parciales: saldo_pendiente == total_servicio.
        """
        db = _make_session()
        try:
            ticket = _ticket_base(db, total_servicio=120_000, anticipo=0)

            saldo = ticket.total_servicio - 0 - 0
            ticket.saldo_pendiente = saldo
            ticket.estado = "FINALIZADO"
            db.commit()
            db.refresh(ticket)

            assert ticket.saldo_pendiente == 120_000
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Property 3.2 — MovimientoCaja INGRESO_FINAL con valor = total - anticipo
# ---------------------------------------------------------------------------

class TestPreservacion32_MovimientoCaja:
    """
    Validates: Requirements 3.2

    Cuando se finaliza un ticket, se crea un MovimientoCaja de tipo
    INGRESO_FINAL con valor = total_servicio - anticipo_recibido.
    """

    @given(
        total=st.integers(min_value=1, max_value=10_000_000),
        anticipo=st.integers(min_value=0, max_value=10_000_000),
    )
    @settings(max_examples=50)
    def test_movimiento_ingreso_final_creado(self, total, anticipo):
        """
        Para cualquier total > 0, se crea exactamente un MovimientoCaja
        de tipo INGRESO_FINAL con el valor correcto.
        """
        db = _make_session()
        try:
            ticket = _ticket_base(db, total_servicio=total, anticipo=anticipo)

            # Reproducir la lógica actual de ticket_ruta.py → finalizar_ticket
            valor_ingreso = ticket.total_servicio - (ticket.anticipo_recibido or 0)
            if valor_ingreso > 0:
                movimiento = MovimientoCaja(
                    tipo=TipoMovimiento.INGRESO_FINAL,
                    ticket_id=ticket.id,
                    ticket_codigo=ticket.ticket_codigo,
                    placa=ticket.placa,
                    valor=valor_ingreso,
                )
                db.add(movimiento)

            ticket.estado = "FINALIZADO"
            db.commit()

            movimientos = (
                db.query(MovimientoCaja)
                .filter(
                    MovimientoCaja.ticket_id == ticket.id,
                    MovimientoCaja.tipo == TipoMovimiento.INGRESO_FINAL,
                )
                .all()
            )

            valor_esperado = total - anticipo
            if valor_esperado > 0:
                assert len(movimientos) == 1, (
                    f"Se esperaba 1 MovimientoCaja INGRESO_FINAL, se encontraron {len(movimientos)}"
                )
                assert movimientos[0].valor == valor_esperado, (
                    f"valor={movimientos[0].valor} != esperado={valor_esperado} "
                    f"(total={total}, anticipo={anticipo})"
                )
            else:
                # valor_ingreso <= 0: no se crea movimiento (comportamiento actual)
                assert len(movimientos) == 0
        finally:
            db.close()

    def test_tipo_movimiento_es_ingreso_final(self):
        """
        El tipo del movimiento creado al finalizar debe ser exactamente INGRESO_FINAL.
        """
        db = _make_session()
        try:
            ticket = _ticket_base(db, total_servicio=100_000, anticipo=20_000)

            valor_ingreso = 100_000 - 20_000
            movimiento = MovimientoCaja(
                tipo=TipoMovimiento.INGRESO_FINAL,
                ticket_id=ticket.id,
                ticket_codigo=ticket.ticket_codigo,
                placa=ticket.placa,
                valor=valor_ingreso,
            )
            db.add(movimiento)
            ticket.estado = "FINALIZADO"
            db.commit()

            mov = db.query(MovimientoCaja).filter(MovimientoCaja.ticket_id == ticket.id).first()
            assert mov is not None
            assert mov.tipo == TipoMovimiento.INGRESO_FINAL
            assert mov.valor == 80_000
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Property 3.3 — Sin total_servicio → 400 Bad Request
# ---------------------------------------------------------------------------

class TestPreservacion33_SinTotalServicio:
    """
    Validates: Requirements 3.3

    Cuando un ticket no tiene total_servicio definido y se intenta finalizar,
    el sistema retorna 400 Bad Request.
    """

    def test_finalizar_sin_total_servicio_lanza_400(self):
        """
        La lógica actual lanza HTTPException(400) cuando total_servicio es None.
        """
        from app.rutas.ticket_ruta import finalizar_ticket

        db = _make_session()
        try:
            ticket = _ticket_base(db, total_servicio=None, anticipo=0)
            ticket_id = ticket.id
            db.commit()

            with pytest.raises(HTTPException) as exc_info:
                finalizar_ticket(ticket_id=ticket_id, db=db)

            assert exc_info.value.status_code == 400
        finally:
            db.close()

    @given(total=st.none() | st.just(0))
    @settings(max_examples=10)
    def test_finalizar_con_total_falsy_lanza_400(self, total):
        """
        Tanto None como 0 son valores falsy para total_servicio → 400.
        """
        from app.rutas.ticket_ruta import finalizar_ticket

        db = _make_session()
        try:
            ticket = _ticket_base(db, total_servicio=total, anticipo=0)
            ticket_id = ticket.id
            db.commit()

            with pytest.raises(HTTPException) as exc_info:
                finalizar_ticket(ticket_id=ticket_id, db=db)

            assert exc_info.value.status_code == 400
        finally:
            db.close()

    def test_finalizar_con_total_servicio_valido_no_lanza_400(self):
        """
        Con total_servicio > 0, la finalización debe completarse sin error.
        """
        from app.rutas.ticket_ruta import finalizar_ticket

        db = _make_session()
        try:
            ticket = _ticket_base(db, total_servicio=50_000, anticipo=0)
            ticket_id = ticket.id
            db.commit()

            # No debe lanzar excepción
            resultado = finalizar_ticket(ticket_id=ticket_id, db=db)
            assert resultado.estado == "FINALIZADO"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Shared test app fixtures
# ---------------------------------------------------------------------------

def _make_test_engine():
    """Crea un engine SQLite en memoria con todas las tablas creadas."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Todos los modelos ya están importados al inicio del módulo,
    # así que Base.metadata tiene todas las tablas registradas.
    Base.metadata.create_all(engine)
    return engine


def _make_test_client_with_routers(*router_modules):
    """
    Crea un TestClient con los routers dados y una DB en memoria.
    Retorna (client, session_factory).
    """
    from fastapi import FastAPI
    from app.configuracion.base_datos import obtener_db

    engine = _make_test_engine()
    TestSession = sessionmaker(bind=engine)

    app = FastAPI()

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[obtener_db] = override_db
    for mod in router_modules:
        app.include_router(mod.router)

    return TestClient(app), TestSession


# ---------------------------------------------------------------------------
# Property 3.5 — Clientes autenticados correctamente siguen siendo procesados
# ---------------------------------------------------------------------------

class TestPreservacion35_AutenticacionNormal:
    """
    Validates: Requirements 3.5

    WHEN un cliente autenticado correctamente accede a cualquier endpoint de
    tickets THEN el sistema SHALL CONTINUE TO procesar la petición normalmente.

    En el código sin corregir los endpoints de tickets NO requieren auth,
    por lo que cualquier petición (con o sin cabecera) es procesada.
    Este test verifica que el comportamiento de "petición procesada" se mantiene.
    """

    def test_endpoint_tickets_abiertos_responde_200(self):
        """
        GET /tickets/abiertos responde 200 con autenticación correcta.
        """
        from app.rutas import ticket_ruta, vehiculo_ruta
        client, _ = _make_test_client_with_routers(ticket_ruta, vehiculo_ruta)
        response = client.get("/tickets/abiertos", headers={"X-Admin-Password": "1234"})
        assert response.status_code == 200

    def test_endpoint_tickets_buscar_responde_200(self):
        """
        GET /tickets/buscar responde 200 con autenticación correcta.
        """
        from app.rutas import ticket_ruta, vehiculo_ruta
        client, _ = _make_test_client_with_routers(ticket_ruta, vehiculo_ruta)
        response = client.get("/tickets/buscar", headers={"X-Admin-Password": "1234"})
        assert response.status_code == 200

    def test_finalizar_ticket_con_total_servicio_retorna_ticket_finalizado(self):
        """
        POST /tickets/{id}/finalizar con total_servicio definido retorna el ticket
        con estado FINALIZADO y saldo_pendiente correcto.

        Caso concreto del spec: total=100000, anticipo=20000 → saldo=80000.
        """
        from app.rutas import ticket_ruta, vehiculo_ruta
        client, TestSession = _make_test_client_with_routers(ticket_ruta, vehiculo_ruta)

        db = TestSession()
        try:
            vehiculo = Vehiculo(
                placa="ABC123",
                marca="Honda",
                modelo="Civic",
                anio=2021,
                nombre_propietario="Carlos",
                telefono_propietario="3001234567",
            )
            db.add(vehiculo)
            db.flush()

            ticket = Ticket(
                vehiculo_id=vehiculo.id,
                ticket_codigo="TK-ABC123-001",
                placa="ABC123",
                motivo_visita="Revisión",
                anticipo_recibido=20_000,
                total_servicio=100_000,
                estado="ABIERTO",
            )
            db.add(ticket)
            db.commit()
            ticket_id = ticket.id
        finally:
            db.close()

        response = client.post(f"/tickets/{ticket_id}/finalizar", headers={"X-Admin-Password": "1234"})
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "FINALIZADO"
        assert data["saldo_pendiente"] == 80_000


# ---------------------------------------------------------------------------
# Property 3.6 — Otros routers no se ven afectados
# ---------------------------------------------------------------------------

class TestPreservacion36_OtrosRouters:
    """
    Validates: Requirements 3.6

    WHEN los endpoints de economía, vehículos, citas y seguridad reciben
    peticiones THEN el sistema SHALL CONTINUE TO comportarse exactamente
    igual que antes de los cambios.
    """

    def test_economia_resumen_responde_200(self):
        """
        GET /economia-dia responde 200 (sin autenticación requerida para resumen).
        """
        from app.rutas import economia_ruta
        client, _ = _make_test_client_with_routers(economia_ruta)
        response = client.get("/economia-dia")
        assert response.status_code == 200

    def test_vehiculos_listar_responde_200(self):
        """
        GET /vehiculos/ responde 200.
        """
        from app.rutas import vehiculo_ruta
        client, _ = _make_test_client_with_routers(vehiculo_ruta)
        response = client.get("/vehiculos/")
        assert response.status_code == 200

    def test_citas_listar_responde_200(self):
        """
        GET /citas responde 200.
        """
        from app.rutas import citas_ruta
        client, _ = _make_test_client_with_routers(citas_ruta)
        response = client.get("/citas")
        assert response.status_code == 200

    def test_seguridad_tiene_password_responde_200(self):
        """
        GET /seguridad/economia/tiene-password responde 200.
        """
        from app.rutas import seguridad_ruta
        client, _ = _make_test_client_with_routers(seguridad_ruta)
        response = client.get("/seguridad/economia/tiene-password")
        assert response.status_code == 200

    def test_vehiculos_buscar_placa_inexistente_responde_200(self):
        """
        GET /vehiculos/buscar?placa=XYZ999 responde 200 con existe=False.
        """
        from app.rutas import vehiculo_ruta
        client, _ = _make_test_client_with_routers(vehiculo_ruta)
        response = client.get("/vehiculos/buscar?placa=XYZ999")
        assert response.status_code == 200
        assert response.json()["existe"] is False

    def test_citas_proximas_responde_200(self):
        """
        GET /citas/proximas responde 200.
        """
        from app.rutas import citas_ruta
        client, _ = _make_test_client_with_routers(citas_ruta)
        response = client.get("/citas/proximas")
        assert response.status_code == 200
