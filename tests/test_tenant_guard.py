"""
Tests unitarios para el módulo tenant_guard.

Verifica que las funciones de validación de pertenencia al taller funcionen correctamente
y mantengan el aislamiento multi-tenant del sistema.

Cubre:
- Acceso correcto al propio taller
- Intento cross-tenant sin request (sin logging)
- Intento cross-tenant con request (con logging y contador Redis)
- 4to intento → alerta HIGH via SecurityAlertService
- Objeto sin taller_id (recursos globales)

Requirements: 1, 5, 11, 12, 20
"""

import os
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.configuracion.base_datos import Base

# ---------------------------------------------------------------------------
# Modelo de prueba simple (sin EncryptedString para evitar dependencia PII_MASTER_KEY)
# ---------------------------------------------------------------------------


class RecursoTest(Base):
    """Modelo SQLAlchemy mínimo para tests de tenant_guard."""

    __tablename__ = "recursos_test"

    id = Column(Integer, primary_key=True, index=True)
    taller_id = Column(Integer, nullable=False, index=True)
    nombre = Column(String(100), nullable=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db_session():
    """Crea una sesión de base de datos SQLite en memoria para tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def recurso_taller_1(db_session):
    """Crea un recurso de prueba para el taller 1."""
    recurso = RecursoTest(taller_id=1, nombre="Recurso del taller 1")
    db_session.add(recurso)
    db_session.commit()
    db_session.refresh(recurso)
    return recurso


@pytest.fixture
def recurso_taller_2(db_session):
    """Crea un recurso de prueba para el taller 2."""
    recurso = RecursoTest(taller_id=2, nombre="Recurso del taller 2")
    db_session.add(recurso)
    db_session.commit()
    db_session.refresh(recurso)
    return recurso


def _make_mock_request(user_id: int | None = 42, taller_id: int = 1, ip: str = "10.0.0.1"):
    """
    Construye un mock de FastAPI Request con los atributos mínimos necesarios.

    Args:
        user_id:   ID del usuario autenticado (None para usuario anónimo).
        taller_id: taller_id del JWT del usuario.
        ip:        IP del cliente.

    Returns:
        MagicMock que simula un Request de FastAPI.
    """
    request = MagicMock()
    request.state.user = {"user_id": user_id, "taller_id": taller_id}
    request.state.taller_id = taller_id
    request.client.host = ip
    request.headers.get.return_value = "TestAgent/1.0"
    request.url.path = "/api/v1/recursos/1"
    return request


# ---------------------------------------------------------------------------
# Tests de verificar_pertenencia
# ---------------------------------------------------------------------------


class TestVerificarPertenencia:
    """Tests para la función verificar_pertenencia."""

    def test_objeto_none_lanza_404(self):
        """Verifica que se lance 404 cuando el objeto es None."""
        from app.utils.tenant_guard import verificar_pertenencia

        with pytest.raises(HTTPException) as exc_info:
            verificar_pertenencia(None, taller_id=1, nombre_recurso="Ticket")

        assert exc_info.value.status_code == 404
        assert "Ticket no encontrado" in exc_info.value.detail

    def test_objeto_sin_taller_id_no_lanza_excepcion(self):
        """Verifica que objetos sin taller_id (recursos globales) no lancen excepción."""
        from app.utils.tenant_guard import verificar_pertenencia

        class ObjetoGlobal:
            id = 1
            nombre = "Global"

        # No debe lanzar excepción — recursos globales no tienen aislamiento por taller
        verificar_pertenencia(ObjetoGlobal(), taller_id=1, nombre_recurso="Recurso Global")

    def test_objeto_con_taller_id_correcto_no_lanza_excepcion(self):
        """Verifica que objetos con taller_id correcto no lancen excepción."""
        from app.utils.tenant_guard import verificar_pertenencia

        class ObjetoConTaller:
            id = 1
            taller_id = 5

        verificar_pertenencia(ObjetoConTaller(), taller_id=5, nombre_recurso="Recurso")

    def test_objeto_con_taller_id_incorrecto_lanza_404(self):
        """Verifica que se lance 404 cuando el taller_id no coincide (sin request)."""
        from app.utils.tenant_guard import verificar_pertenencia

        class ObjetoConTaller:
            id = 1
            taller_id = 5

        with pytest.raises(HTTPException) as exc_info:
            verificar_pertenencia(ObjetoConTaller(), taller_id=3, nombre_recurso="Recurso")

        assert exc_info.value.status_code == 404
        assert "Recurso no encontrado" in exc_info.value.detail

    def test_cross_tenant_sin_request_no_llama_log(self):
        """
        Cuando no se proporciona request, el intento cross-tenant lanza 404
        pero NO registra en audit log ni incrementa contador Redis.
        """
        from app.utils.tenant_guard import verificar_pertenencia

        class ObjetoConTaller:
            id = 1
            taller_id = 5

        with patch("app.utils.tenant_guard._log_cross_tenant_attempt") as mock_log:
            with pytest.raises(HTTPException) as exc_info:
                verificar_pertenencia(ObjetoConTaller(), taller_id=3, nombre_recurso="Recurso")

            mock_log.assert_not_called()

        assert exc_info.value.status_code == 404

    def test_cross_tenant_con_request_llama_log(self):
        """
        Cuando se proporciona request, el intento cross-tenant registra en audit log.
        """
        from app.utils.tenant_guard import verificar_pertenencia

        class ObjetoConTaller:
            id = 1
            taller_id = 5

        request = _make_mock_request(user_id=42, taller_id=3)

        with patch("app.utils.tenant_guard._log_cross_tenant_attempt") as mock_log:
            with pytest.raises(HTTPException) as exc_info:
                verificar_pertenencia(
                    ObjetoConTaller(), taller_id=3, nombre_recurso="Recurso", request=request
                )

            mock_log.assert_called_once_with(
                request=request,
                taller_id_real=5,
                taller_id_solicitado=3,
            )

        assert exc_info.value.status_code == 404

    def test_usa_404_no_403_para_seguridad(self):
        """
        Verifica que se use 404 en lugar de 403 para no revelar existencia de recursos.

        Security: Usar 404 en lugar de 403 evita revelar que el recurso existe
        en otro taller (seguridad por oscuridad).
        """
        from app.utils.tenant_guard import verificar_pertenencia

        class ObjetoConTaller:
            id = 1
            taller_id = 5

        with pytest.raises(HTTPException) as exc_info:
            verificar_pertenencia(ObjetoConTaller(), taller_id=3, nombre_recurso="Recurso")

        assert exc_info.value.status_code == 404
        assert exc_info.value.status_code != 403

    def test_mensaje_personalizado_en_excepcion(self):
        """Verifica que el mensaje de error use el nombre del recurso proporcionado."""
        from app.utils.tenant_guard import verificar_pertenencia

        with pytest.raises(HTTPException) as exc_info:
            verificar_pertenencia(None, taller_id=1, nombre_recurso="Vehículo")

        assert "Vehículo no encontrado" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Tests de obtener_recurso_del_taller
# ---------------------------------------------------------------------------


class TestObtenerRecursoDelTaller:
    """Tests para la función obtener_recurso_del_taller."""

    def test_recurso_no_existe_lanza_404(self, db_session: Session):
        """Verifica que se lance 404 cuando el recurso no existe."""
        from app.utils.tenant_guard import obtener_recurso_del_taller

        with pytest.raises(HTTPException) as exc_info:
            obtener_recurso_del_taller(
                db_session, RecursoTest, recurso_id=99999, taller_id=1, nombre_recurso="Recurso"
            )

        assert exc_info.value.status_code == 404
        assert "Recurso no encontrado" in exc_info.value.detail

    def test_recurso_del_taller_correcto_retorna_objeto(self, db_session: Session, recurso_taller_1):
        """Verifica que se retorne el objeto cuando pertenece al taller correcto."""
        from app.utils.tenant_guard import obtener_recurso_del_taller

        recurso = obtener_recurso_del_taller(
            db_session, RecursoTest, recurso_id=recurso_taller_1.id, taller_id=1, nombre_recurso="Recurso"
        )

        assert recurso is not None
        assert recurso.id == recurso_taller_1.id
        assert recurso.taller_id == 1

    def test_recurso_de_otro_taller_sin_request_lanza_404(
        self, db_session: Session, recurso_taller_1
    ):
        """
        Verifica que se lance 404 cuando el recurso pertenece a otro taller (sin request).
        No debe llamar a _log_cross_tenant_attempt.
        """
        from app.utils.tenant_guard import obtener_recurso_del_taller

        with patch("app.utils.tenant_guard._log_cross_tenant_attempt") as mock_log:
            with pytest.raises(HTTPException) as exc_info:
                obtener_recurso_del_taller(
                    db_session,
                    RecursoTest,
                    recurso_id=recurso_taller_1.id,
                    taller_id=2,
                    nombre_recurso="Recurso",
                )

            mock_log.assert_not_called()

        assert exc_info.value.status_code == 404

    def test_recurso_de_otro_taller_con_request_registra_intento(
        self, db_session: Session, recurso_taller_1
    ):
        """
        Cuando el recurso existe pero pertenece a otro taller y se proporciona request,
        debe registrar el intento cross-tenant antes de lanzar 404.
        """
        from app.utils.tenant_guard import obtener_recurso_del_taller

        request = _make_mock_request(user_id=42, taller_id=2)

        with patch("app.utils.tenant_guard._log_cross_tenant_attempt") as mock_log:
            with pytest.raises(HTTPException) as exc_info:
                obtener_recurso_del_taller(
                    db_session,
                    RecursoTest,
                    recurso_id=recurso_taller_1.id,
                    taller_id=2,
                    nombre_recurso="Recurso",
                    request=request,
                )

            mock_log.assert_called_once_with(
                request=request,
                taller_id_real=1,   # taller al que pertenece el recurso
                taller_id_solicitado=2,  # taller del JWT del usuario
            )

        assert exc_info.value.status_code == 404

    def test_recurso_inexistente_con_request_no_registra_intento(
        self, db_session: Session
    ):
        """
        Cuando el recurso no existe en absoluto (ni en otro taller), no debe
        registrar intento cross-tenant — no hay evidencia de acceso a datos ajenos.
        """
        from app.utils.tenant_guard import obtener_recurso_del_taller

        request = _make_mock_request(user_id=42, taller_id=1)

        with patch("app.utils.tenant_guard._log_cross_tenant_attempt") as mock_log:
            with pytest.raises(HTTPException) as exc_info:
                obtener_recurso_del_taller(
                    db_session,
                    RecursoTest,
                    recurso_id=99999,
                    taller_id=1,
                    nombre_recurso="Recurso",
                    request=request,
                )

            mock_log.assert_not_called()

        assert exc_info.value.status_code == 404

    def test_mensaje_personalizado_en_excepcion(self, db_session: Session):
        """Verifica que el mensaje de error use el nombre del recurso proporcionado."""
        from app.utils.tenant_guard import obtener_recurso_del_taller

        with pytest.raises(HTTPException) as exc_info:
            obtener_recurso_del_taller(
                db_session, RecursoTest, recurso_id=99999, taller_id=1, nombre_recurso="Vehículo"
            )

        assert "Vehículo no encontrado" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Tests de _log_cross_tenant_attempt (integración interna)
# ---------------------------------------------------------------------------


class TestLogCrossTenantAttempt:
    """Tests para la función interna _log_cross_tenant_attempt."""

    def test_registra_en_audit_log(self):
        """Verifica que se crea un registro en audit_log con los datos correctos."""
        from app.utils.tenant_guard import _log_cross_tenant_attempt

        request = _make_mock_request(user_id=42, taller_id=1)

        mock_db = MagicMock()
        mock_session_local = MagicMock(return_value=mock_db)

        with patch("app.utils.tenant_guard._get_redis_client", return_value=None):
            with patch("app.configuracion.base_datos.SessionLocal", mock_session_local):
                with patch("app.utils.tenant_guard._write_audit_log") as mock_audit:
                    _log_cross_tenant_attempt(
                        request=request,
                        taller_id_real=2,
                        taller_id_solicitado=1,
                    )

                    mock_audit.assert_called_once()
                    call_kwargs = mock_audit.call_args[1]
                    assert call_kwargs["user_id"] == 42
                    assert call_kwargs["taller_id_real"] == 2
                    assert call_kwargs["taller_id_solicitado"] == 1
                    assert call_kwargs["ip_address"] == "10.0.0.1"

    def test_incrementa_contador_redis(self):
        """Verifica que se incrementa el contador Redis con TTL correcto."""
        from app.utils.tenant_guard import _log_cross_tenant_attempt

        request = _make_mock_request(user_id=42, taller_id=1)

        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1  # Primer intento

        with patch("app.utils.tenant_guard._write_audit_log"):
            with patch("app.utils.tenant_guard._get_redis_client", return_value=mock_redis):
                _log_cross_tenant_attempt(
                    request=request,
                    taller_id_real=2,
                    taller_id_solicitado=1,
                )

                mock_redis.incr.assert_called_once_with("CROSS_TENANT:42")
                # TTL debe establecerse en el primer incremento
                mock_redis.expire.assert_called_once_with("CROSS_TENANT:42", 3600)

    def test_no_establece_ttl_en_incrementos_posteriores(self):
        """
        El TTL solo se establece en el primer incremento (count == 1).
        En incrementos posteriores no se reinicia la ventana de tiempo.
        """
        from app.utils.tenant_guard import _log_cross_tenant_attempt

        request = _make_mock_request(user_id=42, taller_id=1)

        mock_redis = MagicMock()
        mock_redis.incr.return_value = 2  # Segundo intento — TTL ya establecido

        with patch("app.utils.tenant_guard._write_audit_log"):
            with patch("app.utils.tenant_guard._get_redis_client", return_value=mock_redis):
                _log_cross_tenant_attempt(
                    request=request,
                    taller_id_real=2,
                    taller_id_solicitado=1,
                )

                mock_redis.incr.assert_called_once()
                mock_redis.expire.assert_not_called()  # No reiniciar TTL

    def test_cuarto_intento_dispara_alerta_high(self):
        """
        Cuando el contador supera el umbral (> 3), debe dispararse una alerta HIGH.
        El 4to intento (count=4) debe activar la alerta.
        """
        from app.utils.tenant_guard import _log_cross_tenant_attempt

        request = _make_mock_request(user_id=42, taller_id=1)

        mock_redis = MagicMock()
        mock_redis.incr.return_value = 4  # 4to intento — supera umbral de 3

        with patch("app.utils.tenant_guard._write_audit_log"):
            with patch("app.utils.tenant_guard._get_redis_client", return_value=mock_redis):
                with patch("app.utils.tenant_guard._dispatch_high_severity_alert") as mock_alert:
                    _log_cross_tenant_attempt(
                        request=request,
                        taller_id_real=2,
                        taller_id_solicitado=1,
                    )

                    mock_alert.assert_called_once()
                    call_kwargs = mock_alert.call_args[1]
                    assert call_kwargs["user_id"] == 42
                    assert call_kwargs["attempt_count"] == 4

    def test_tercer_intento_no_dispara_alerta(self):
        """
        El 3er intento (count=3) NO debe disparar alerta — el umbral es > 3.
        """
        from app.utils.tenant_guard import _log_cross_tenant_attempt

        request = _make_mock_request(user_id=42, taller_id=1)

        mock_redis = MagicMock()
        mock_redis.incr.return_value = 3  # Exactamente en el umbral — no supera

        with patch("app.utils.tenant_guard._write_audit_log"):
            with patch("app.utils.tenant_guard._get_redis_client", return_value=mock_redis):
                with patch("app.utils.tenant_guard._dispatch_high_severity_alert") as mock_alert:
                    _log_cross_tenant_attempt(
                        request=request,
                        taller_id_real=2,
                        taller_id_solicitado=1,
                    )

                    mock_alert.assert_not_called()

    def test_sin_redis_no_lanza_excepcion(self):
        """
        Si Redis no está disponible, el flujo continúa sin error.
        El 404 al cliente siempre se lanza independientemente de Redis.
        """
        from app.utils.tenant_guard import _log_cross_tenant_attempt

        request = _make_mock_request(user_id=42, taller_id=1)

        with patch("app.utils.tenant_guard._write_audit_log"):
            with patch("app.utils.tenant_guard._get_redis_client", return_value=None):
                # No debe lanzar excepción aunque Redis no esté disponible
                _log_cross_tenant_attempt(
                    request=request,
                    taller_id_real=2,
                    taller_id_solicitado=1,
                )

    def test_usuario_anonimo_no_incrementa_contador(self):
        """
        Si el usuario no tiene user_id (anónimo), no se incrementa el contador Redis.
        """
        from app.utils.tenant_guard import _log_cross_tenant_attempt

        request = _make_mock_request(user_id=None, taller_id=1)

        mock_redis = MagicMock()

        with patch("app.utils.tenant_guard._write_audit_log"):
            with patch("app.utils.tenant_guard._get_redis_client", return_value=mock_redis):
                _log_cross_tenant_attempt(
                    request=request,
                    taller_id_real=2,
                    taller_id_solicitado=1,
                )

                mock_redis.incr.assert_not_called()


# ---------------------------------------------------------------------------
# Tests de _dispatch_high_severity_alert
# ---------------------------------------------------------------------------


class TestDispatchHighSeverityAlert:
    """Tests para la función _dispatch_high_severity_alert."""

    def test_llama_security_alert_service_cuando_disponible(self):
        """Verifica que se llama a SecurityAlertService.dispatch_high_severity cuando existe."""
        from app.utils.tenant_guard import _dispatch_high_severity_alert

        mock_service_instance = MagicMock()
        mock_service_class = MagicMock(return_value=mock_service_instance)

        with patch.dict("sys.modules", {"app.servicios.security_alert_service": MagicMock(
            SecurityAlertService=mock_service_class
        )}):
            _dispatch_high_severity_alert(
                user_id=42,
                ip_address="10.0.0.1",
                attempt_count=4,
                taller_id_solicitado=1,
                taller_id_real=2,
                endpoint="/api/v1/recursos/1",
            )

            mock_service_instance.dispatch_high_severity.assert_called_once()

    def test_loguea_critical_cuando_service_no_disponible(self):
        """
        Si SecurityAlertService no está implementado (ImportError),
        debe loguear CRITICAL en lugar de fallar silenciosamente.
        """
        from app.utils.tenant_guard import _dispatch_high_severity_alert

        with patch("app.utils.tenant_guard.logger") as mock_logger:
            # Simular que el módulo no existe
            with patch.dict("sys.modules", {"app.servicios.security_alert_service": None}):
                _dispatch_high_severity_alert(
                    user_id=42,
                    ip_address="10.0.0.1",
                    attempt_count=4,
                    taller_id_solicitado=1,
                    taller_id_real=2,
                    endpoint="/api/v1/recursos/1",
                )

                # Debe loguear como CRITICAL para no perder el evento
                mock_logger.critical.assert_called_once()


# ---------------------------------------------------------------------------
# Tests de aislamiento multi-tenant (integración)
# ---------------------------------------------------------------------------


class TestAislamientoMultiTenant:
    """Tests de seguridad para verificar aislamiento multi-tenant."""

    def test_no_puede_acceder_recurso_de_otro_taller(
        self, db_session: Session, recurso_taller_2
    ):
        """
        Verifica que un usuario del taller 1 no pueda acceder a recursos del taller 2.

        Security: Invariante crítica del sistema multi-tenant.
        """
        from app.utils.tenant_guard import obtener_recurso_del_taller

        with pytest.raises(HTTPException) as exc_info:
            obtener_recurso_del_taller(
                db_session, RecursoTest, recurso_id=recurso_taller_2.id, taller_id=1, nombre_recurso="Recurso"
            )

        assert exc_info.value.status_code == 404

    def test_puede_acceder_recurso_de_su_taller(
        self, db_session: Session, recurso_taller_1
    ):
        """Verifica que un usuario del taller 1 pueda acceder a recursos de su propio taller."""
        from app.utils.tenant_guard import obtener_recurso_del_taller

        recurso = obtener_recurso_del_taller(
            db_session, RecursoTest, recurso_id=recurso_taller_1.id, taller_id=1, nombre_recurso="Recurso"
        )

        assert recurso is not None
        assert recurso.taller_id == 1

    def test_usa_404_no_403_para_no_revelar_existencia(
        self, db_session: Session, recurso_taller_2
    ):
        """
        Verifica que se use 404 en lugar de 403 para no revelar que el recurso existe.

        Security: Usar 404 en lugar de 403 evita que un atacante pueda enumerar
        recursos de otros talleres.
        """
        from app.utils.tenant_guard import obtener_recurso_del_taller

        with pytest.raises(HTTPException) as exc_info:
            obtener_recurso_del_taller(
                db_session, RecursoTest, recurso_id=recurso_taller_2.id, taller_id=1, nombre_recurso="Recurso"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.status_code != 403

    def test_multiples_intentos_cross_tenant_acumulan_contador(self):
        """
        Verifica que múltiples intentos cross-tenant del mismo usuario acumulan
        el contador Redis correctamente.
        """
        from app.utils.tenant_guard import _increment_cross_tenant_counter

        mock_redis = MagicMock()
        # Simular incrementos sucesivos
        mock_redis.incr.side_effect = [1, 2, 3, 4]

        with patch("app.utils.tenant_guard._get_redis_client", return_value=mock_redis):
            counts = [_increment_cross_tenant_counter(user_id=99) for _ in range(4)]

        assert counts == [1, 2, 3, 4]
        assert mock_redis.incr.call_count == 4
        # TTL solo se establece en el primer incremento
        assert mock_redis.expire.call_count == 1
