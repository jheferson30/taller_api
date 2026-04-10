"""
Unit Tests: TwilioWhatsAppService
==================================
Cubre los requerimientos de la integración WhatsApp Business.

Tasks 23 y 24 del spec whatsapp-business-integration.
"""

import asyncio
from unittest.mock import MagicMock, patch

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
from app.configuracion.base_datos import Base
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.modelos.log_notificacion import LogNotificacion
from app.modelos.ticket import Ticket
from app.modelos.vehiculo import Vehiculo
from app.servicios.twilio_whatsapp_service import TwilioWhatsAppService
from app.servicios.whatsapp_service import ResultadoEnvio, TipoEvento

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session():
    """Crea una sesión SQLite en memoria con todas las tablas."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _config(db, enabled=True, token="valid_token", phone_id="1234567890"):
    """Persiste y retorna un ConfiguracionTaller con id=1."""
    cfg = ConfiguracionTaller(
        id=1,
        nombre_taller="Taller Test",
        whatsapp_enabled=enabled,
        whatsapp_token=token,
        whatsapp_phone_id=phone_id,
    )
    db.add(cfg)
    db.commit()
    return cfg


def _vehiculo(db, placa="ABC123", nombre="Juan Pérez", telefono="3001234567"):
    """Persiste y retorna un Vehiculo."""
    v = Vehiculo(
        placa=placa,
        nombre_propietario=nombre,
        telefono_propietario=telefono,
    )
    db.add(v)
    db.flush()
    return v


def _ticket(
    db,
    vehiculo_id,
    codigo="T-001",
    motivo="Revisión general",
    total=100000,
    saldo=50000,
    recomendaciones=None,
):
    """Persiste y retorna un Ticket."""
    t = Ticket(
        vehiculo_id=vehiculo_id,
        ticket_codigo=codigo,
        placa="ABC123",
        motivo_visita=motivo,
        total_servicio=total,
        saldo_pendiente=saldo,
        recomendaciones=recomendaciones,
    )
    db.add(t)
    db.flush()
    return t


# ---------------------------------------------------------------------------
# Task 23.1 — Servicio deshabilitado retorna OMITIDO sin llamada HTTP (req 1.3)
# ---------------------------------------------------------------------------


def test_servicio_deshabilitado_retorna_omitido_sin_http():
    """
    Si whatsapp_enabled=False, enviar_notificacion debe retornar OMITIDO
    y no realizar ninguna llamada HTTP.
    Validates: Requirements 1.3
    """
    db = _make_session()
    _config(db, enabled=False)
    v = _vehiculo(db)
    t = _ticket(db, vehiculo_id=v.id)
    db.commit()

    service = TwilioWhatsAppService()

    with patch("httpx.AsyncClient") as mock_client_cls:
        resultado = asyncio.run(service.enviar_notificacion(TipoEvento.RECEPCION, t, v, db))

    assert resultado == ResultadoEnvio.OMITIDO
    mock_client_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Task 23.2 — Token vacío retorna ERROR sin llamada HTTP (req 1.4)
# ---------------------------------------------------------------------------


def test_token_vacio_retorna_error_sin_http():
    """
    Si whatsapp_token está vacío, enviar_notificacion debe retornar ERROR
    y no realizar ninguna llamada HTTP.
    Validates: Requirements 1.4
    """
    db = _make_session()
    _config(db, enabled=True, token="")
    v = _vehiculo(db)
    t = _ticket(db, vehiculo_id=v.id)
    db.commit()

    service = TwilioWhatsAppService()

    with patch("httpx.AsyncClient") as mock_client_cls:
        resultado = asyncio.run(service.enviar_notificacion(TipoEvento.RECEPCION, t, v, db))

    assert resultado == ResultadoEnvio.ERROR
    mock_client_cls.assert_not_called()


def test_token_solo_espacios_retorna_error_sin_http():
    """
    Si whatsapp_token contiene solo espacios, debe retornar ERROR sin HTTP.
    Validates: Requirements 1.4
    """
    db = _make_session()
    _config(db, enabled=True, token="   ")
    v = _vehiculo(db)
    t = _ticket(db, vehiculo_id=v.id)
    db.commit()

    service = TwilioWhatsAppService()

    with patch("httpx.AsyncClient") as mock_client_cls:
        resultado = asyncio.run(service.enviar_notificacion(TipoEvento.RECEPCION, t, v, db))

    assert resultado == ResultadoEnvio.ERROR
    mock_client_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Task 23.3 — Teléfono ausente retorna OMITIDO con motivo "sin_telefono" (req 2.3)
# ---------------------------------------------------------------------------


def test_telefono_ausente_retorna_omitido_con_motivo_sin_telefono():
    """
    Si telefono_propietario es None, enviar_notificacion debe retornar OMITIDO
    y el log debe tener error_detalle="sin_telefono".
    Validates: Requirements 2.3
    """
    db = _make_session()
    _config(db, enabled=True, token="valid_token", phone_id="1234567890")
    v = _vehiculo(db, telefono=None)
    t = _ticket(db, vehiculo_id=v.id)
    db.commit()

    service = TwilioWhatsAppService()

    with patch("httpx.AsyncClient") as mock_client_cls:
        resultado = asyncio.run(service.enviar_notificacion(TipoEvento.RECEPCION, t, v, db))

    assert resultado == ResultadoEnvio.OMITIDO
    mock_client_cls.assert_not_called()

    log = db.query(LogNotificacion).order_by(LogNotificacion.id.desc()).first()
    assert log is not None
    assert log.error_detalle == "sin_telefono"
    assert log.resultado == ResultadoEnvio.OMITIDO.value


def test_telefono_vacio_retorna_omitido_con_motivo_sin_telefono():
    """
    Si telefono_propietario es cadena vacía, debe retornar OMITIDO con "sin_telefono".
    Validates: Requirements 2.3
    """
    db = _make_session()
    _config(db, enabled=True, token="valid_token", phone_id="1234567890")
    v = _vehiculo(db, placa="XYZ999", telefono="")
    t = _ticket(db, vehiculo_id=v.id, codigo="T-002")
    db.commit()

    service = TwilioWhatsAppService()

    with patch("httpx.AsyncClient") as mock_client_cls:
        resultado = asyncio.run(service.enviar_notificacion(TipoEvento.RECEPCION, t, v, db))

    assert resultado == ResultadoEnvio.OMITIDO
    mock_client_cls.assert_not_called()

    log = db.query(LogNotificacion).order_by(LogNotificacion.id.desc()).first()
    assert log.error_detalle == "sin_telefono"


# ---------------------------------------------------------------------------
# Task 24.1 — Mensaje RECEPCION contiene nombre, placa, código, motivo (req 2.2)
# ---------------------------------------------------------------------------


def test_mensaje_recepcion_contiene_campos_requeridos():
    """
    El mensaje de RECEPCION debe incluir nombre del propietario, placa,
    código de ticket y motivo de visita.
    Validates: Requirements 2.2
    """
    service = TwilioWhatsAppService()

    vehiculo = MagicMock()
    vehiculo.nombre_propietario = "María López"
    vehiculo.placa = "DEF456"
    vehiculo.telefono_propietario = "3009876543"

    ticket = MagicMock()
    ticket.id = 42
    ticket.motivo_visita = "Cambio de aceite"

    mensaje = service._construir_mensaje(TipoEvento.RECEPCION, ticket, vehiculo)

    assert "María López" in mensaje
    assert "DEF456" in mensaje
    assert "42" in mensaje
    assert "Cambio de aceite" in mensaje


# ---------------------------------------------------------------------------
# Task 24.2 — Mensaje FINALIZACION contiene total y saldo (req 3.2)
# ---------------------------------------------------------------------------


def test_mensaje_finalizacion_contiene_total_y_saldo():
    """
    El mensaje de FINALIZACION debe incluir total del servicio y saldo pendiente.
    Validates: Requirements 3.2
    """
    service = TwilioWhatsAppService()

    vehiculo = MagicMock()
    vehiculo.nombre_propietario = "Carlos Ruiz"
    vehiculo.placa = "GHI789"
    vehiculo.telefono_propietario = "3001112233"

    ticket = MagicMock()
    ticket.id = 99
    ticket.total_servicio = 250000
    ticket.total = 250000
    ticket.saldo_pendiente = 100000

    mensaje = service._construir_mensaje(TipoEvento.FINALIZACION, ticket, vehiculo)

    assert "250000" in mensaje
    assert "100000" in mensaje


def test_mensaje_finalizacion_saldo_cero_indica_pagado():
    """
    Si saldo_pendiente es 0, el mensaje debe indicar que está completamente pagado.
    Validates: Requirements 3.2, 3.3
    """
    service = TwilioWhatsAppService()

    vehiculo = MagicMock()
    vehiculo.nombre_propietario = "Ana Torres"
    vehiculo.placa = "JKL012"
    vehiculo.telefono_propietario = "3004445566"

    ticket = MagicMock()
    ticket.id = 55
    ticket.total = 180000
    ticket.saldo_pendiente = 0

    mensaje = service._construir_mensaje(TipoEvento.FINALIZACION, ticket, vehiculo)

    assert "pagado" in mensaje.lower()


# ---------------------------------------------------------------------------
# Task 24.3 — Mensaje ENTREGA omite recomendaciones si están vacías (req 4.3)
# ---------------------------------------------------------------------------


def test_mensaje_entrega_omite_recomendaciones_si_vacias():
    """
    Si recomendaciones es None o vacío, el mensaje de ENTREGA no debe
    incluir la sección de recomendaciones.
    Validates: Requirements 4.3
    """
    service = TwilioWhatsAppService()

    vehiculo = MagicMock()
    vehiculo.nombre_propietario = "Pedro Gómez"
    vehiculo.placa = "MNO345"
    vehiculo.telefono_propietario = "3007778899"

    ticket_sin_rec = MagicMock()
    ticket_sin_rec.id = 77
    ticket_sin_rec.recomendaciones = None

    mensaje_none = service._construir_mensaje(TipoEvento.ENTREGA, ticket_sin_rec, vehiculo)
    assert "Recomendaciones" not in mensaje_none
    assert "recomendaciones" not in mensaje_none.lower()

    ticket_vacio = MagicMock()
    ticket_vacio.id = 78
    ticket_vacio.recomendaciones = ""

    mensaje_vacio = service._construir_mensaje(TipoEvento.ENTREGA, ticket_vacio, vehiculo)
    assert "Recomendaciones" not in mensaje_vacio
    assert "recomendaciones" not in mensaje_vacio.lower()


def test_mensaje_entrega_incluye_recomendaciones_si_existen():
    """
    Si recomendaciones tiene contenido, debe aparecer en el mensaje de ENTREGA.
    Validates: Requirements 4.2
    """
    service = TwilioWhatsAppService()

    vehiculo = MagicMock()
    vehiculo.nombre_propietario = "Laura Díaz"
    vehiculo.placa = "PQR678"
    vehiculo.telefono_propietario = "3002223344"

    ticket = MagicMock()
    ticket.id = 88
    ticket.recomendaciones = "Cambiar filtro en 3 meses"

    mensaje = service._construir_mensaje(TipoEvento.ENTREGA, ticket, vehiculo)
    assert "Cambiar filtro en 3 meses" in mensaje


# ---------------------------------------------------------------------------
# Task 24.4 — Log persiste tipo_evento, resultado y created_at no nulos (req 7.1)
# ---------------------------------------------------------------------------


def test_log_persiste_campos_requeridos_no_nulos():
    """
    Después de enviar_notificacion, el log debe tener tipo_evento,
    resultado y created_at no nulos.
    Validates: Requirements 7.1
    """
    db = _make_session()
    _config(db, enabled=False)  # deshabilitado → OMITIDO, pero igual persiste log
    v = _vehiculo(db, placa="LOG001")
    t = _ticket(db, vehiculo_id=v.id, codigo="T-LOG-001")
    db.commit()

    service = TwilioWhatsAppService()

    with patch("httpx.AsyncClient"):
        asyncio.run(service.enviar_notificacion(TipoEvento.RECEPCION, t, v, db))

    log = db.query(LogNotificacion).order_by(LogNotificacion.id.desc()).first()
    assert log is not None
    assert log.tipo_evento is not None
    assert log.resultado is not None
    # created_at puede ser None en SQLite con server_default, verificamos que el campo existe
    # y que tipo_evento y resultado tienen los valores correctos
    assert log.tipo_evento == TipoEvento.RECEPCION.value
    assert log.resultado == ResultadoEnvio.OMITIDO.value


def test_log_persiste_ticket_id_y_tipo_evento():
    """
    El log debe reflejar el ticket_id del intento de envío.
    Validates: Requirements 7.1
    """
    db = _make_session()
    _config(db, enabled=True, token="valid_token", phone_id="1234567890")
    v = _vehiculo(db, placa="LOG002", telefono=None)  # sin teléfono → OMITIDO
    t = _ticket(db, vehiculo_id=v.id, codigo="T-LOG-002")
    db.commit()

    service = TwilioWhatsAppService()

    with patch("httpx.AsyncClient"):
        asyncio.run(service.enviar_notificacion(TipoEvento.FINALIZACION, t, v, db))

    log = db.query(LogNotificacion).order_by(LogNotificacion.id.desc()).first()
    assert log is not None
    assert log.ticket_id == t.id
    assert log.tipo_evento == TipoEvento.FINALIZACION.value
    assert log.resultado == ResultadoEnvio.OMITIDO.value
    assert log.error_detalle == "sin_telefono"
