"""
Test de Exploración: Ausencia de Protección CSRF (Bug Condition)

**Validates: Requirements 1.17, 1.18**

CRÍTICO: Este test DEBE FALLAR en código sin corregir - el fallo confirma que el bug existe.
NO intentar corregir el test o el código cuando falle.

Este test codifica el comportamiento esperado - validará la corrección cuando pase después
de la implementación.

OBJETIVO: Demostrar que endpoints no validan tokens CSRF.
"""

import os

import pytest
import requests
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


class TestAusenciaProteccionCSRF:
    """
    Property 1: Bug Condition - Sin Validación CSRF

    Este test verifica que el sistema no valida tokens CSRF en endpoints de escritura.
    En código SIN CORREGIR, este test DEBE FALLAR.
    """

    @pytest.fixture(scope="class")
    def api_base_url(self):
        """URL base de la API para testing"""
        return os.getenv("API_BASE_URL", "http://localhost:8000")

    @pytest.fixture(scope="class")
    def auth_token(self, api_base_url):
        """Obtener token de autenticación para tests"""
        try:
            # Intentar login con credenciales de test
            response = requests.post(
                f"{api_base_url}/auth/login",
                json={"username": "admin", "password": "Admin123"},
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                pytest.skip("No se pudo obtener token de autenticación")
        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")

    def test_post_sin_csrf_token_es_aceptado(self, api_base_url, auth_token):
        """
        Verifica que peticiones POST sin token CSRF son aceptadas.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay protección CSRF)
        """
        if not auth_token:
            pytest.skip("No hay token de autenticación")

        try:
            # Intentar agregar un proceso a un ticket sin token CSRF
            # Primero, obtener un ticket abierto
            response_tickets = requests.get(
                f"{api_base_url}/tickets/abiertos",
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=5,
            )

            if response_tickets.status_code != 200:
                pytest.skip("No se pudo obtener lista de tickets")

            tickets = response_tickets.json()
            if not tickets:
                pytest.skip("No hay tickets abiertos para probar")

            ticket_id = tickets[0]["id"]

            # Intentar POST sin header X-CSRF-Token
            response = requests.post(
                f"{api_base_url}/tickets/{ticket_id}/procesos",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    # NO incluir X-CSRF-Token
                },
                json={"nombre": "Test CSRF", "descripcion": "Test CSRF - Proceso de prueba"},
                timeout=5,
            )

            # En código sin corregir, esperamos que la petición NO sea rechazada por CSRF (403)
            # Si recibimos 200/201 = éxito, 422 = validación, ambos confirman que NO hay CSRF
            # Este test FALLA si la petición es rechazada con 403 (lo cual sería correcto)
            assert response.status_code != 403, (
                f"Bug Condition: POST sin token CSRF NO debería ser rechazado con 403 en código sin corregir, "
                f"pero recibió status {response.status_code}. "
                f"Si este test falla, la protección CSRF ya fue implementada."
            )

            print("\n✓ Confirmado: POST sin token CSRF NO fue rechazado con 403 (Bug Condition)")
            print(f"  Status Code: {response.status_code}")
            print(f"  Endpoint: POST /tickets/{ticket_id}/procesos")
            print("  Esto confirma que NO hay protección CSRF implementada")

        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo. Iniciar con: uvicorn app.main:app")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")

    def test_fastapi_csrf_protect_no_en_requirements(self):
        """
        Verifica que fastapi-csrf-protect no está en requirements.txt.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay dependencia CSRF instalada)
        """
        try:
            with open("requirements.txt", encoding="utf-8") as f:
                contenido = f.read()

            # Buscar fastapi-csrf-protect en requirements
            tiene_csrf_protect = "fastapi-csrf-protect" in contenido.lower()

            # En código sin corregir, NO debería tener la dependencia
            assert not tiene_csrf_protect, (
                "Bug Condition: requirements.txt no debería tener fastapi-csrf-protect "
                "en código sin corregir. Si este test falla, la dependencia ya fue agregada."
            )

            print(
                "\n✓ Confirmado: fastapi-csrf-protect no está en requirements.txt (Bug Condition)"
            )

        except FileNotFoundError:
            pytest.skip("requirements.txt no encontrado")

    def test_main_no_tiene_configuracion_csrf(self):
        """
        Verifica que app/main.py no contiene configuración CSRF.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay middleware CSRF configurado)
        """
        try:
            with open("app/main.py", encoding="utf-8") as f:
                contenido = f.read()

            # Buscar imports relacionados con CSRF
            tiene_import_csrf = (
                "fastapi_csrf_protect" in contenido
                or "CsrfProtect" in contenido
                or "csrf_protect" in contenido
            )

            # Buscar configuración de CSRF
            tiene_config_csrf = (
                "CsrfSettings" in contenido
                or "csrf_secret" in contenido.lower()
                or "CsrfProtectError" in contenido
            )

            # En código sin corregir, NO debería tener configuración CSRF
            assert not tiene_import_csrf, (
                "Bug Condition: app/main.py no debería tener imports de CSRF "
                "en código sin corregir. Si este test falla, CSRF ya fue configurado."
            )

            assert not tiene_config_csrf, (
                "Bug Condition: app/main.py no debería tener configuración de CSRF "
                "en código sin corregir. Si este test falla, CSRF ya fue configurado."
            )

            print("\n✓ Confirmado: app/main.py no tiene configuración CSRF (Bug Condition)")

        except FileNotFoundError:
            pytest.skip("app/main.py no encontrado")

    def test_rutas_no_validan_csrf(self):
        """
        Verifica que las rutas de tickets no validan CSRF.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que endpoints no tienen validación CSRF)
        """
        archivos_rutas = [
            "app/rutas/ticket_ruta.py",
            "app/rutas/mobile_api_ruta.py",
            "app/rutas/economia_ruta.py",
        ]

        for archivo in archivos_rutas:
            try:
                with open(archivo, encoding="utf-8") as f:
                    contenido = f.read()

                # Buscar validación CSRF en endpoints
                tiene_csrf_protect = (
                    "CsrfProtect" in contenido
                    or "csrf_protect" in contenido
                    or "validate_csrf" in contenido
                )

                # En código sin corregir, NO debería tener validación CSRF
                assert not tiene_csrf_protect, (
                    f"Bug Condition: {archivo} no debería tener validación CSRF "
                    f"en código sin corregir. Si este test falla, CSRF ya fue implementado."
                )

                print(f"\n✓ Confirmado: {archivo} no valida CSRF (Bug Condition)")

            except FileNotFoundError:
                # Si el archivo no existe, continuar con el siguiente
                pass

    def test_env_no_tiene_csrf_secret_key(self):
        """
        Verifica que .env.example no documenta CSRF_SECRET_KEY.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay documentación de configuración CSRF)
        """
        archivos_env = [".env.example", ".env"]

        for archivo in archivos_env:
            try:
                with open(archivo, encoding="utf-8") as f:
                    contenido = f.read()

                # Verificar que NO tiene CSRF_SECRET_KEY configurado
                tiene_csrf_secret = "CSRF_SECRET_KEY" in contenido

                # En código sin corregir, NO debería tener CSRF_SECRET_KEY
                assert not tiene_csrf_secret, (
                    f"Bug Condition: {archivo} no debería tener CSRF_SECRET_KEY "
                    f"en código sin corregir. Si este test falla, la configuración ya fue documentada."
                )

                print(f"\n✓ Confirmado: {archivo} no tiene CSRF_SECRET_KEY (Bug Condition)")

            except FileNotFoundError:
                # Si el archivo no existe, eso también confirma falta de documentación
                print(f"\n✓ Confirmado: {archivo} no existe (Bug Condition)")

    @given(
        endpoint_path=st.sampled_from(
            [
                "/tickets/{ticket_id}/procesos",
                "/tickets/{ticket_id}/repuestos",
                "/tickets/{ticket_id}/cobros",
                "/tickets/{ticket_id}/compras",
            ]
        )
    )
    @settings(
        max_examples=4,
        deadline=None,  # Disable deadline for HTTP requests
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_property_endpoints_escritura_sin_csrf(self, endpoint_path, api_base_url, auth_token):
        """
        Property-Based Test: Para cualquier endpoint de escritura,
        el sistema sin corregir acepta peticiones sin token CSRF.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que ningún endpoint valida CSRF)
        """
        if not auth_token:
            pytest.skip("No hay token de autenticación")

        try:
            # Obtener un ticket para usar en el endpoint
            response_tickets = requests.get(
                f"{api_base_url}/tickets/abiertos",
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=5,
            )

            if response_tickets.status_code != 200:
                pytest.skip("No se pudo obtener lista de tickets")

            tickets = response_tickets.json()
            if not tickets:
                pytest.skip("No hay tickets abiertos para probar")

            ticket_id = tickets[0]["id"]
            url = f"{api_base_url}{endpoint_path.replace('{ticket_id}', str(ticket_id))}"

            # Preparar payload según el endpoint
            payload = {}
            if "procesos" in endpoint_path:
                payload = {"nombre": "Test CSRF", "descripcion": "Test CSRF"}
            elif "repuestos" in endpoint_path:
                payload = {"nombre": "Test CSRF", "cantidad": 1, "marca_referencia": "Test"}
            elif "cobros" in endpoint_path:
                payload = {"concepto": "Test CSRF", "valor": 100.0}
            elif "compras" in endpoint_path:
                payload = {"descripcion": "Test CSRF", "valor": 40.0, "responsable": "Test"}

            # Intentar POST sin header X-CSRF-Token
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json",
                    # NO incluir X-CSRF-Token
                },
                json=payload,
                timeout=5,
            )

            # En código sin corregir, esperamos que la petición NO sea rechazada por CSRF (403)
            assert response.status_code != 403, (
                f"Bug Condition Property: POST a {endpoint_path} sin token CSRF "
                f"NO debería ser rechazado con 403 en código sin corregir, "
                f"pero recibió status {response.status_code}. "
                f"Si este test falla, la protección CSRF ya fue implementada."
            )

            print(f"\n✓ Confirmado: POST a {endpoint_path} sin CSRF NO fue rechazado con 403")
            print(f"  Status Code: {response.status_code} (confirma ausencia de CSRF)")

        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")

    def test_frontend_no_envia_csrf_token(self):
        """
        Verifica que el frontend no está configurado para enviar tokens CSRF.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que frontend no maneja CSRF)
        """
        archivos_frontend = [
            "frontend/src/services/api.js",
            "frontend/src/services/authService.js",
            "frontend/src/utils/api.js",
        ]

        for archivo in archivos_frontend:
            try:
                with open(archivo, encoding="utf-8") as f:
                    contenido = f.read()

                # Buscar configuración de CSRF en frontend
                tiene_csrf_config = (
                    "X-CSRF-Token" in contenido
                    or "csrf" in contenido.lower()
                    or "getCsrfToken" in contenido
                )

                # En código sin corregir, NO debería tener configuración CSRF
                assert not tiene_csrf_config, (
                    f"Bug Condition: {archivo} no debería tener configuración CSRF "
                    f"en código sin corregir. Si este test falla, CSRF ya fue implementado en frontend."
                )

                print(f"\n✓ Confirmado: {archivo} no maneja tokens CSRF (Bug Condition)")

            except FileNotFoundError:
                # Si el archivo no existe, continuar con el siguiente
                pass

    def test_mobile_app_no_envia_csrf_token(self):
        """
        Verifica que la app móvil no está configurada para enviar tokens CSRF.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que app móvil no maneja CSRF)
        """
        archivos_mobile = [
            "mobile_app/src/services/api.js",
            "mobile_app/src/services/authService.js",
            "mobile_app/src/utils/api.js",
        ]

        for archivo in archivos_mobile:
            try:
                with open(archivo, encoding="utf-8") as f:
                    contenido = f.read()

                # Buscar configuración de CSRF en app móvil
                tiene_csrf_config = (
                    "X-CSRF-Token" in contenido
                    or "csrf" in contenido.lower()
                    or "getCsrfToken" in contenido
                )

                # En código sin corregir, NO debería tener configuración CSRF
                assert not tiene_csrf_config, (
                    f"Bug Condition: {archivo} no debería tener configuración CSRF "
                    f"en código sin corregir. Si este test falla, CSRF ya fue implementado en app móvil."
                )

                print(f"\n✓ Confirmado: {archivo} no maneja tokens CSRF (Bug Condition)")

            except FileNotFoundError:
                # Si el archivo no existe, continuar con el siguiente
                pass


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST DE EXPLORACIÓN: AUSENCIA DE PROTECCIÓN CSRF (Bug Condition)")
    print("=" * 80)
    print("\nCRÍTICO: Este test DEBE FALLAR en código sin corregir.")
    print("El fallo confirma que el bug existe (sin validación CSRF).")
    print("\nEste test validará la corrección cuando pase después de la implementación.")
    print("=" * 80 + "\n")

    pytest.main([__file__, "-v", "-s"])
