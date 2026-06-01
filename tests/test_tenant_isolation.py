"""
Property-based tests para aislamiento multi-tenant (taller_id).

Valida las 6 propiedades de corrección definidas en el diseño:

P1 — Aislamiento de lectura:
     get_all() retorna SOLO registros del taller del usuario autenticado.

P2 — Aislamiento de escritura:
     create() asigna taller_id del contexto, ignorando cualquier valor en el objeto.

P3 — Opacidad cross-tenant:
     get_by_id() con ID de otro taller retorna None (HTTP 404, nunca 403).

P4 — Integridad referencial:
     Crear Ticket con vehiculo_id de otro taller lanza error.

P5 — Contexto inmutable:
     taller_id efectivo siempre viene del JWT, nunca del body/query/headers.

P6 — Taller inactivo bloquea acceso:
     Usuario de taller inactivo recibe HTTP 403 en cualquier endpoint protegido.
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.mecanico import Mecanico
from app.modelos.taller import Taller
from app.modelos.ticket import Ticket
from app.modelos.user import User
from app.modelos.vehiculo import Vehiculo
from app.repositorios.tenant_repository import TenantRepository
from app.repositorios.vehiculo_repository import VehiculoRepository
from app.seguridad.auth_middleware import AuthMiddleware, require_auth
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.token_manager import TokenManager
from app.utils.exceptions import MissingTenantContextError


# ── Estrategias Hypothesis ────────────────────────────────────────────────────

@st.composite
def taller_id_pair(draw):
    """Genera dos taller_ids distintos."""
    t1 = draw(st.integers(min_value=1, max_value=500))
    t2 = draw(st.integers(min_value=501, max_value=1000))
    return t1, t2


@st.composite
def placa_valida(draw):
    """Genera placas de vehículo válidas."""
    letras = draw(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=3, max_size=3))
    numeros = draw(st.text(alphabet="0123456789", min_size=3, max_size=3))
    return f"{letras}{numeros}"


@st.composite
def nombre_valido(draw):
    """Genera nombres válidos."""
    return draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        min_size=3, max_size=30
    ))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Base de datos SQLite en memoria para tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def token_manager():
    return TokenManager(
        secret_key="test_secret_key_with_at_least_32_characters_for_security"
    )


@pytest.fixture
def password_hasher():
    return PasswordHasher(cost_factor=4)


def crear_taller(db, nombre: str, activo: bool = True) -> Taller:
    """Helper: crea un taller en la BD."""
    taller = Taller(nombre=nombre, activo=activo)
    db.add(taller)
    db.flush()
    return taller


def crear_usuario(db, taller_id: int, username: str, password_hasher) -> User:
    """Helper: crea un usuario asociado a un taller."""
    user = User(
        taller_id=taller_id,
        username=username,
        email=f"{username}@test.com",
        password_hash=password_hasher.hash_password("Test1234!"),
        is_active=True,
        is_migrated=True,
    )
    db.add(user)
    db.flush()
    return user


def crear_vehiculo(db, taller_id: int, placa: str) -> Vehiculo:
    """Helper: crea un vehículo asociado a un taller."""
    v = Vehiculo(taller_id=taller_id, placa=placa, marca="Test", modelo="Test")
    db.add(v)
    db.flush()
    return v


# ── P1: Aislamiento de lectura ────────────────────────────────────────────────

class TestP1_AislamientoLectura:
    """
    P1 — Para cualquier usuario con taller_id=T,
         get_all() retorna SOLO registros con taller_id==T.
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        n_propios=st.integers(min_value=1, max_value=5),
        n_ajenos=st.integers(min_value=1, max_value=5),
        nombre_base=nombre_valido(),
    )
    def test_get_all_solo_retorna_registros_del_taller(
        self, db_session, n_propios, n_ajenos, nombre_base
    ):
        """
        P1: get_all() con taller_id=T nunca retorna registros de taller_id≠T.
        """
        taller_a = crear_taller(db_session, f"TallerA_{nombre_base[:10]}")
        taller_b = crear_taller(db_session, f"TallerB_{nombre_base[:10]}")

        # Crear mecánicos en taller A
        for i in range(n_propios):
            db_session.add(Mecanico(
                taller_id=taller_a.id,
                nombre=f"Mec_A_{i}_{nombre_base[:5]}",
                activo=True
            ))

        # Crear mecánicos en taller B
        for i in range(n_ajenos):
            db_session.add(Mecanico(
                taller_id=taller_b.id,
                nombre=f"Mec_B_{i}_{nombre_base[:5]}",
                activo=True
            ))

        db_session.flush()

        # Consultar desde perspectiva del taller A
        repo_a = VehiculoRepository.__new__(VehiculoRepository)
        # Usar TenantRepository directamente con Mecanico
        class MecanicoRepo(TenantRepository):
            model = Mecanico

        repo = MecanicoRepo(db_session, taller_a.id)
        resultados = repo.get_all(limit=100)

        # Todos los resultados deben pertenecer al taller A
        for r in resultados:
            assert r.taller_id == taller_a.id, (
                f"P1 violada: get_all() retornó registro de taller_id={r.taller_id} "
                f"cuando se consultó con taller_id={taller_a.id}"
            )

        # Debe retornar exactamente n_propios registros
        assert len(resultados) == n_propios, (
            f"P1: se esperaban {n_propios} registros del taller A, "
            f"se obtuvieron {len(resultados)}"
        )


# ── P2: Aislamiento de escritura ──────────────────────────────────────────────

class TestP2_AislamientoEscritura:
    """
    P2 — create() asigna taller_id del contexto,
         ignorando cualquier valor en el objeto.
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        taller_id_contexto=st.integers(min_value=1, max_value=500),
        taller_id_objeto=st.integers(min_value=501, max_value=1000),
        nombre_base=nombre_valido(),
    )
    def test_create_asigna_taller_id_del_contexto(
        self, db_session, taller_id_contexto, taller_id_objeto, nombre_base
    ):
        """
        P2: create() siempre asigna el taller_id del repositorio,
            sin importar el valor que traiga el objeto.
        """
        # Crear los talleres en BD para satisfacer FK
        taller_ctx = Taller(id=taller_id_contexto, nombre=f"Ctx_{nombre_base[:10]}", activo=True)
        taller_obj = Taller(id=taller_id_objeto, nombre=f"Obj_{nombre_base[:10]}", activo=True)
        db_session.add(taller_ctx)
        db_session.add(taller_obj)
        db_session.flush()

        class MecanicoRepo(TenantRepository):
            model = Mecanico

        repo = MecanicoRepo(db_session, taller_id_contexto)

        # Crear objeto con taller_id diferente al contexto
        mecanico = Mecanico(
            taller_id=taller_id_objeto,  # intento de inyectar taller ajeno
            nombre=f"Test_{nombre_base[:10]}",
            activo=True,
        )

        resultado = repo.create(mecanico)

        # El taller_id debe ser el del contexto, no el del objeto
        assert resultado.taller_id == taller_id_contexto, (
            f"P2 violada: create() asignó taller_id={resultado.taller_id} "
            f"en lugar del contexto taller_id={taller_id_contexto}"
        )


# ── P3: Opacidad cross-tenant ─────────────────────────────────────────────────

class TestP3_OpacidadCrossTenant:
    """
    P3 — get_by_id() con ID de otro taller retorna None.
         El sistema no revela la existencia del recurso.
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_get_by_id_retorna_none_para_recurso_de_otro_taller(
        self, db_session, nombre_base
    ):
        """
        P3: get_by_id() con ID que existe pero pertenece a otro taller retorna None.
        """
        taller_a = crear_taller(db_session, f"A_{nombre_base[:10]}")
        taller_b = crear_taller(db_session, f"B_{nombre_base[:10]}")

        # Crear mecánico en taller B
        mecanico_b = Mecanico(
            taller_id=taller_b.id,
            nombre=f"Mec_B_{nombre_base[:10]}",
            activo=True
        )
        db_session.add(mecanico_b)
        db_session.flush()

        # Consultar desde taller A con el ID del mecánico de taller B
        class MecanicoRepo(TenantRepository):
            model = Mecanico

        repo_a = MecanicoRepo(db_session, taller_a.id)
        resultado = repo_a.get_by_id(mecanico_b.id)

        assert resultado is None, (
            f"P3 violada: get_by_id({mecanico_b.id}) desde taller_id={taller_a.id} "
            f"retornó un registro que pertenece a taller_id={taller_b.id}"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_get_by_id_retorna_registro_del_propio_taller(
        self, db_session, nombre_base
    ):
        """
        P3 (positivo): get_by_id() retorna el registro si pertenece al taller correcto.
        """
        taller = crear_taller(db_session, f"T_{nombre_base[:10]}")

        mecanico = Mecanico(
            taller_id=taller.id,
            nombre=f"Mec_{nombre_base[:10]}",
            activo=True
        )
        db_session.add(mecanico)
        db_session.flush()

        class MecanicoRepo(TenantRepository):
            model = Mecanico

        repo = MecanicoRepo(db_session, taller.id)
        resultado = repo.get_by_id(mecanico.id)

        assert resultado is not None, (
            f"P3: get_by_id({mecanico.id}) debería retornar el registro "
            f"del propio taller_id={taller.id}"
        )
        assert resultado.taller_id == taller.id


# ── P4: Integridad referencial ────────────────────────────────────────────────

class TestP4_IntegridadReferencial:
    """
    P4 — Crear Ticket con vehiculo_id de otro taller debe ser bloqueado.
         El servicio verifica que las referencias sean del mismo taller.
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        placa_a=placa_valida(),
        placa_b=placa_valida(),
        nombre_base=nombre_valido(),
    )
    def test_vehiculo_de_otro_taller_no_puede_usarse_en_ticket(
        self, db_session, placa_a, placa_b, nombre_base
    ):
        """
        P4: VehiculoRepository.get_by_id() desde taller A no puede ver
            vehículos de taller B, previniendo referencias cross-tenant.
        """
        from hypothesis import assume
        assume(placa_a != placa_b)

        taller_a = crear_taller(db_session, f"A_{nombre_base[:8]}")
        taller_b = crear_taller(db_session, f"B_{nombre_base[:8]}")

        # Vehículo en taller B
        vehiculo_b = crear_vehiculo(db_session, taller_b.id, placa_b)

        # Intentar obtener el vehículo de taller B desde el repositorio de taller A
        repo_a = VehiculoRepository(db_session, taller_a.id)
        resultado = repo_a.get_by_id(vehiculo_b.id)

        # El repositorio de taller A no debe ver el vehículo de taller B
        assert resultado is None, (
            f"P4 violada: VehiculoRepository(taller_id={taller_a.id}).get_by_id({vehiculo_b.id}) "
            f"retornó un vehículo de taller_id={taller_b.id}. "
            "Esto permitiría crear tickets con vehículos de otro taller."
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(placa=placa_valida(), nombre_base=nombre_valido())
    def test_vehiculo_del_propio_taller_es_accesible(
        self, db_session, placa, nombre_base
    ):
        """
        P4 (positivo): VehiculoRepository puede acceder a vehículos del propio taller.
        """
        taller = crear_taller(db_session, f"T_{nombre_base[:10]}")
        vehiculo = crear_vehiculo(db_session, taller.id, placa)

        repo = VehiculoRepository(db_session, taller.id)
        resultado = repo.get_by_id(vehiculo.id)

        assert resultado is not None, (
            f"P4: VehiculoRepository(taller_id={taller.id}).get_by_id({vehiculo.id}) "
            "debería retornar el vehículo del propio taller"
        )
        assert resultado.taller_id == taller.id


# ── P5: Contexto inmutable ────────────────────────────────────────────────────

class TestP5_ContextoInmutable:
    """
    P5 — El taller_id efectivo siempre viene del JWT,
         nunca del body, query params o headers del cliente.
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_taller_id_viene_del_jwt_no_del_body(
        self, db_session, token_manager, password_hasher, nombre_base
    ):
        """
        P5: request.state.taller_id es inyectado por AuthMiddleware desde el JWT.
            El cliente no puede sobreescribirlo con un valor en el body.
        """
        taller = crear_taller(db_session, f"T_{nombre_base[:10]}")
        user = crear_usuario(db_session, taller.id, f"u_{nombre_base[:8]}", password_hasher)
        db_session.commit()
        db_session.refresh(user)
        # Cargar roles para el token
        user.roles = []

        token = token_manager.generate_access_token(user)

        # Crear app que expone el taller_id del request.state
        app = FastAPI()

        def test_db_factory():
            return db_session

        app.add_middleware(
            AuthMiddleware,
            token_manager=token_manager,
            db_session_factory=test_db_factory,
        )

        @app.post("/test-taller-id")
        @require_auth
        async def endpoint(request: Request, body: dict = None):
            # El taller_id debe venir del JWT, no del body
            return {"taller_id_efectivo": request.state.taller_id}

        client = TestClient(app)

        # Intentar enviar un taller_id diferente en el body
        taller_id_falso = taller.id + 9999
        response = client.post(
            "/test-taller-id",
            json={"taller_id": taller_id_falso},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        taller_id_efectivo = response.json()["taller_id_efectivo"]

        assert taller_id_efectivo == taller.id, (
            f"P5 violada: taller_id efectivo={taller_id_efectivo} "
            f"debería ser {taller.id} (del JWT), no {taller_id_falso} (del body)"
        )
        assert taller_id_efectivo != taller_id_falso, (
            "P5: el taller_id del body no debe sobreescribir el del JWT"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_taller_id_no_puede_sobreescribirse_via_query_param(
        self, db_session, token_manager, password_hasher, nombre_base
    ):
        """
        P5: El taller_id en query params no afecta el contexto de seguridad.
        """
        taller = crear_taller(db_session, f"T2_{nombre_base[:8]}")
        user = crear_usuario(db_session, taller.id, f"u2_{nombre_base[:7]}", password_hasher)
        db_session.commit()
        db_session.refresh(user)
        user.roles = []

        token = token_manager.generate_access_token(user)

        app = FastAPI()

        def test_db_factory():
            return db_session

        app.add_middleware(
            AuthMiddleware,
            token_manager=token_manager,
            db_session_factory=test_db_factory,
        )

        @app.get("/test-query-taller")
        @require_auth
        async def endpoint(request: Request, taller_id: int = None):
            return {"taller_id_efectivo": request.state.taller_id}

        client = TestClient(app)

        taller_id_falso = taller.id + 9999
        response = client.get(
            f"/test-query-taller?taller_id={taller_id_falso}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        taller_id_efectivo = response.json()["taller_id_efectivo"]

        assert taller_id_efectivo == taller.id, (
            f"P5 violada: query param taller_id={taller_id_falso} "
            f"sobreescribió el contexto JWT taller_id={taller.id}"
        )


# ── P6: Taller inactivo bloquea acceso ───────────────────────────────────────

class TestP6_TallerInactivoBloquea:
    """
    P6 — Si taller.activo == False, ningún usuario de ese taller
         puede autenticarse ni acceder a endpoints protegidos.
    """

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_usuario_de_taller_inactivo_recibe_403(
        self, db_session, token_manager, password_hasher, nombre_base
    ):
        """
        P6: AuthMiddleware retorna HTTP 403 si el taller del usuario está inactivo.
        """
        # Crear taller INACTIVO
        taller = crear_taller(db_session, f"Inactivo_{nombre_base[:8]}", activo=False)
        user = crear_usuario(db_session, taller.id, f"u3_{nombre_base[:7]}", password_hasher)
        db_session.commit()
        db_session.refresh(user)
        user.roles = []

        token = token_manager.generate_access_token(user)

        app = FastAPI()

        def test_db_factory():
            return db_session

        app.add_middleware(
            AuthMiddleware,
            token_manager=token_manager,
            db_session_factory=test_db_factory,
        )

        @app.get("/protected")
        @require_auth
        async def endpoint(request: Request):
            return {"ok": True}

        client = TestClient(app)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403, (
            f"P6 violada: usuario de taller inactivo recibió HTTP {response.status_code} "
            "en lugar de HTTP 403"
        )
        assert "inactivo" in response.json().get("detail", "").lower(), (
            "P6: el mensaje de error debe indicar que el taller está inactivo"
        )

    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(nombre_base=nombre_valido())
    def test_usuario_de_taller_activo_puede_acceder(
        self, db_session, token_manager, password_hasher, nombre_base
    ):
        """
        P6 (positivo): Usuario de taller activo puede acceder normalmente.
        """
        taller = crear_taller(db_session, f"Activo_{nombre_base[:8]}", activo=True)
        user = crear_usuario(db_session, taller.id, f"u4_{nombre_base[:7]}", password_hasher)
        db_session.commit()
        db_session.refresh(user)
        user.roles = []

        token = token_manager.generate_access_token(user)

        app = FastAPI()

        def test_db_factory():
            return db_session

        app.add_middleware(
            AuthMiddleware,
            token_manager=token_manager,
            db_session_factory=test_db_factory,
        )

        @app.get("/protected")
        @require_auth
        async def endpoint(request: Request):
            return {"ok": True}

        client = TestClient(app)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, (
            f"P6: usuario de taller activo recibió HTTP {response.status_code} "
            "en lugar de HTTP 200"
        )


# ── P_Extra: MissingTenantContextError ───────────────────────────────────────

class TestMissingTenantContext:
    """
    Propiedad extra: TenantRepository lanza MissingTenantContextError
    si se instancia sin taller_id.
    """

    def test_tenant_repository_sin_taller_id_lanza_excepcion(self, db_session):
        """
        TenantRepository no puede instanciarse sin taller_id.
        """
        class MecanicoRepo(TenantRepository):
            model = Mecanico

        with pytest.raises(MissingTenantContextError):
            MecanicoRepo(db_session, taller_id=None)

    def test_tenant_repository_con_taller_id_cero_lanza_excepcion(self, db_session):
        """
        taller_id=0 es falsy y debe lanzar MissingTenantContextError.
        """
        class MecanicoRepo(TenantRepository):
            model = Mecanico

        with pytest.raises(MissingTenantContextError):
            MecanicoRepo(db_session, taller_id=0)

    def test_tenant_repository_con_taller_id_valido_funciona(self, db_session):
        """
        TenantRepository con taller_id válido se instancia correctamente.
        """
        class MecanicoRepo(TenantRepository):
            model = Mecanico

        repo = MecanicoRepo(db_session, taller_id=1)
        assert repo.taller_id == 1
