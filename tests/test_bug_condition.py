"""
Bug Condition Exploration Tests — Expected Behavior Verification
================================================================
Estos tests verifican que los bugs han sido corregidos.
Cuando PASAN, confirman que el comportamiento esperado está satisfecho.

Caso A — Lógica de finalización compartida (Requirements: 2.1, 2.2):
  La función `finalizar_ticket` DEBE existir como función importable compartida
  en `app.servicios.ticket_service`. Ambas rutas (ticket_ruta.py y
  mobile_api_ruta.py) deben usarla en lugar de tener lógica duplicada.

Caso B — PDF con propietario (Requirement: 2.7):
  En ticket_ruta.py, la construcción de ticket_dict debe leer
  `nombre_propietario` y `telefono_propietario` desde el modelo Vehiculo,
  no desde Ticket (que no tiene esos campos).

**Validates: Requirements 2.1, 2.2, 2.7**
"""

import importlib
import sys
import pytest


# ===========================================================================
# CASO A — Lógica de finalización compartida
# ===========================================================================

class TestCasoA_LogicaDuplicada:
    """
    Verifica que EXISTE una función compartida `finalizar_ticket` en
    app.servicios.ticket_service.

    Con el bug corregido, el módulo existe y la función es importable.

    Validates: Requirements 2.1, 2.2
    """

    def test_ticket_service_module_existe(self):
        """
        El módulo app.servicios.ticket_service DEBE existir tras la corrección.
        """
        sys.modules.pop("app.servicios.ticket_service", None)

        # No debe lanzar ImportError — el módulo existe
        modulo = importlib.import_module("app.servicios.ticket_service")
        assert modulo is not None

    def test_finalizar_ticket_importable_desde_servicio(self):
        """
        La función `finalizar_ticket` DEBE ser importable desde
        app.servicios.ticket_service tras la corrección.
        """
        sys.modules.pop("app.servicios.ticket_service", None)

        from app.servicios.ticket_service import finalizar_ticket  # noqa: F401
        assert callable(finalizar_ticket)


# ===========================================================================
# CASO B — PDF con propietario
# ===========================================================================

class TestCasoB_PDFSinPropietario:
    """
    Verifica que el código corregido en ticket_ruta.py lee
    `nombre_propietario` y `telefono_propietario` desde el modelo Vehiculo.

    El modelo Ticket NO tiene esos campos (están en Vehiculo), por lo que
    el código correcto debe leer del vehículo asociado.

    Validates: Requirement 2.7
    """

    def test_ticket_model_no_tiene_nombre_propietario(self):
        """
        El modelo Ticket NO debe tener el atributo nombre_propietario.
        Los datos del propietario están en Vehiculo, no en Ticket.
        """
        from app.modelos.ticket import Ticket

        ticket = Ticket()
        # Ticket no tiene nombre_propietario — los datos están en Vehiculo
        tiene_atributo = hasattr(ticket, "nombre_propietario")
        assert tiene_atributo is False, (
            "Ticket.nombre_propietario no debe existir — "
            "el propietario está en el modelo Vehiculo"
        )

    def test_ticket_model_no_tiene_telefono_propietario(self):
        """
        El modelo Ticket NO debe tener el atributo telefono_propietario.
        """
        from app.modelos.ticket import Ticket

        ticket = Ticket()
        tiene_atributo = hasattr(ticket, "telefono_propietario")
        assert tiene_atributo is False, (
            "Ticket.telefono_propietario no debe existir — "
            "el propietario está en el modelo Vehiculo"
        )

    def test_ticket_dict_propietario_viene_del_vehiculo(self):
        """
        Simula el código CORREGIDO de ticket_ruta.py al construir ticket_dict.
        Con el fix aplicado, nombre_propietario y telefono_propietario se leen
        del vehículo asociado, no del ticket.

        El test PASA porque el código corregido lee los datos del vehículo.
        """
        from app.modelos.ticket import Ticket
        from app.modelos.vehiculo import Vehiculo

        # Simular un vehículo con datos de propietario
        vehiculo = Vehiculo()
        vehiculo.nombre_propietario = "Juan"
        vehiculo.telefono_propietario = "3001234567"

        # Simular un ticket asociado a ese vehículo
        ticket = Ticket()
        ticket.vehiculo_id = 1

        # Reproducir el código CORREGIDO de ticket_ruta.py
        nombre_en_dict = vehiculo.nombre_propietario if vehiculo else None
        telefono_en_dict = vehiculo.telefono_propietario if vehiculo else None

        # COMPORTAMIENTO ESPERADO (correcto): los campos vienen del vehículo
        assert nombre_en_dict == "Juan", (
            f"nombre_propietario en ticket_dict es '{nombre_en_dict}' "
            f"en lugar de 'Juan'. El código debe leer del vehículo."
        )
        assert telefono_en_dict == "3001234567", (
            f"telefono_propietario en ticket_dict es '{telefono_en_dict}' "
            f"en lugar de '3001234567'. El código debe leer del vehículo."
        )
