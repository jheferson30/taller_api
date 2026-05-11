"""
Tests unitarios para WebhookRouter.

Valida el routing multi-tenant de webhooks de WhatsApp según el número
de teléfono de WhatsApp Business que recibió el mensaje.

Resolves: C-05 (Webhook routing incorrecto para multi-taller)
Requirements: 1.5, 1.6
"""
import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Base local para tests sin dependencias de relaciones
TestBase = declarative_base()


class TallerTest(TestBase):
    """Modelo simplificado de Taller solo para tests."""
    __tablename__ = "talleres"
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), unique=True, nullable=False)
    whatsapp_phone_number = Column(String(50), nullable=True, unique=True)


# Configuración de base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Fixture que provee una sesión de base de datos limpia para cada test."""
    TestBase.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        TestBase.metadata.drop_all(bind=engine)


# Importar WebhookRouter después de definir el modelo de test
from app.servicios.whatsapp_service import WebhookRouter  # noqa: E402


@pytest.fixture
def taller_con_whatsapp(db: Session) -> TallerTest:
    """Crea un taller con número de WhatsApp registrado."""
    taller = TallerTest(
        nombre="Taller Test WhatsApp",
        whatsapp_phone_number="+573001234567"
    )
    db.add(taller)
    db.commit()
    db.refresh(taller)
    return taller


@pytest.fixture
def taller_sin_whatsapp(db: Session) -> TallerTest:
    """Crea un taller sin número de WhatsApp."""
    taller = TallerTest(
        nombre="Taller Sin WhatsApp",
        whatsapp_phone_number=None
    )
    db.add(taller)
    db.commit()
    db.refresh(taller)
    return taller


def test_route_whatsapp_message_encuentra_taller(db: Session, taller_con_whatsapp: TallerTest):
    """
    WHEN un webhook llega con un número registrado
    THEN el router debe retornar el taller_id correcto
    
    Validates: Requirement 1.5
    """
    router = WebhookRouter(db)
    
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "phone_number_id": "123456789",
                        "display_phone_number": "+573001234567"
                    },
                    "messages": [{
                        "from": "+573009876543",
                        "text": {"body": "Hola"}
                    }]
                }
            }]
        }]
    }
    
    taller_id, phone_number = router.route_whatsapp_message(payload)
    
    assert taller_id == taller_con_whatsapp.id
    assert phone_number == "+573001234567"


def test_route_whatsapp_message_no_encuentra_taller(db: Session):
    """
    WHEN un webhook llega con un número NO registrado
    THEN el router debe retornar (None, phone_number)
    
    Validates: Requirement 1.6
    """
    router = WebhookRouter(db)
    
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "phone_number_id": "123456789",
                        "display_phone_number": "+573009999999"
                    },
                    "messages": [{
                        "from": "+573009876543",
                        "text": {"body": "Hola"}
                    }]
                }
            }]
        }]
    }
    
    taller_id, phone_number = router.route_whatsapp_message(payload)
    
    assert taller_id is None
    assert phone_number == "+573009999999"


def test_route_whatsapp_message_payload_vacio(db: Session):
    """
    WHEN el payload está vacío o malformado
    THEN el router debe retornar (None, "")
    """
    router = WebhookRouter(db)
    
    # Payload vacío
    taller_id, phone_number = router.route_whatsapp_message({})
    assert taller_id is None
    assert phone_number == ""
    
    # Payload sin entry
    taller_id, phone_number = router.route_whatsapp_message({"entry": []})
    assert taller_id is None
    assert phone_number == ""
    
    # Payload sin changes
    taller_id, phone_number = router.route_whatsapp_message({
        "entry": [{"changes": []}]
    })
    assert taller_id is None
    assert phone_number == ""
    
    # Payload sin metadata
    taller_id, phone_number = router.route_whatsapp_message({
        "entry": [{
            "changes": [{
                "value": {}
            }]
        }]
    })
    assert taller_id is None
    assert phone_number == ""


def test_route_whatsapp_message_multiples_talleres(db: Session):
    """
    WHEN existen múltiples talleres con diferentes números
    THEN el router debe enrutar al taller correcto según el número
    """
    # Crear múltiples talleres
    taller1 = TallerTest(nombre="Taller 1", whatsapp_phone_number="+573001111111")
    taller2 = TallerTest(nombre="Taller 2", whatsapp_phone_number="+573002222222")
    taller3 = TallerTest(nombre="Taller 3", whatsapp_phone_number="+573003333333")
    
    db.add_all([taller1, taller2, taller3])
    db.commit()
    
    router = WebhookRouter(db)
    
    # Probar routing al taller 2
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "display_phone_number": "+573002222222"
                    }
                }
            }]
        }]
    }
    
    taller_id, phone_number = router.route_whatsapp_message(payload)
    
    assert taller_id == taller2.id
    assert phone_number == "+573002222222"


def test_extract_to_field_payload_valido(db: Session):
    """
    WHEN el payload tiene la estructura correcta de Twilio/Meta
    THEN _extract_to_field debe extraer el número correctamente
    """
    router = WebhookRouter(db)
    
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "phone_number_id": "123456789",
                        "display_phone_number": "+573001234567"
                    }
                }
            }]
        }]
    }
    
    phone_number = router._extract_to_field(payload)
    
    assert phone_number == "+573001234567"


def test_extract_to_field_payload_malformado(db: Session):
    """
    WHEN el payload está malformado
    THEN _extract_to_field debe retornar None sin lanzar excepción
    """
    router = WebhookRouter(db)
    
    # Payload sin estructura
    assert router._extract_to_field({}) is None
    assert router._extract_to_field({"entry": []}) is None
    assert router._extract_to_field({"entry": [{}]}) is None
    assert router._extract_to_field({"entry": [{"changes": []}]}) is None
    assert router._extract_to_field({"entry": [{"changes": [{}]}]}) is None
    assert router._extract_to_field({
        "entry": [{
            "changes": [{
                "value": {}
            }]
        }]
    }) is None
    assert router._extract_to_field({
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {}
                }
            }]
        }]
    }) is None


def test_whatsapp_phone_number_unique_constraint(db: Session):
    """
    WHEN se intenta crear dos talleres con el mismo whatsapp_phone_number
    THEN debe lanzar una excepción de constraint único
    """
    taller1 = TallerTest(nombre="Taller 1", whatsapp_phone_number="+573001234567")
    taller2 = TallerTest(nombre="Taller 2", whatsapp_phone_number="+573001234567")
    
    db.add(taller1)
    db.commit()
    
    db.add(taller2)
    
    with pytest.raises(Exception):  # IntegrityError
        db.commit()
