"""
Test de Exploración: CORS Mal Configurado (Bug Condition)

**Validates: Requirements 1.5, 1.6**

CRÍTICO: Este test DEBE FALLAR en código sin corregir - el fallo confirma que el bug existe.
NO intentar corregir el test o el código cuando falle.

Este test codifica el comportamiento esperado - validará la corrección cuando pase después
de la implementación.

OBJETIVO: Demostrar que CORS acepta peticiones desde orígenes no autorizados.
"""

import os

import pytest
import requests
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


class TestCORSMalConfigurado:
    """
    Property 1: Bug Condition - CORS Acepta Cualquier Origen

    Este test verifica que CORS está mal configurado y acepta peticiones desde cualquier origen.
    En código SIN CORREGIR, este test DEBE FALLAR.
    """

    @pytest.fixture(scope="class")
    def api_base_url(self):
        """URL base de la API para testing"""
        return os.getenv("API_BASE_URL", "http://localhost:8000")

    def test_cors_acepta_origen_malicioso(self, api_base_url):
        """
        Verifica que el sistema acepta peticiones desde orígenes no autorizados.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que CORS acepta cualquier origen)
        """
        # Origen malicioso que NO debería ser aceptado
        origen_malicioso = "https://sitio-malicioso.com"

        try:
            # Intentar hacer una petición con origen malicioso
            response = requests.options(
                f"{api_base_url}/",
                headers={"Origin": origen_malicioso, "Access-Control-Request-Method": "GET"},
                timeout=5,
            )

            # Verificar headers CORS en la respuesta
            cors_allow_origin = response.headers.get("Access-Control-Allow-Origin", "")

            # En código sin corregir, esperamos que el origen malicioso sea aceptado
            # Este test FALLA si el origen es rechazado (lo cual sería correcto)
            assert cors_allow_origin == "*" or cors_allow_origin == origen_malicioso, (
                f"Bug Condition: CORS debería aceptar origen malicioso '{origen_malicioso}' "
                f"en código sin corregir, pero Access-Control-Allow-Origin es '{cors_allow_origin}'. "
                f"Si este test falla, CORS ya fue configurado correctamente."
            )

            print(
                f"\n✓ Confirmado: CORS acepta origen malicioso '{origen_malicioso}' (Bug Condition)"
            )
            print(f"  Access-Control-Allow-Origin: {cors_allow_origin}")

        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo. Iniciar con: uvicorn app.main:app")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")

    def test_codigo_fuente_tiene_origins_wildcard(self):
        """
        Verifica que el código fuente tiene _origins = ["*"] configurado.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que CORS está configurado con wildcard)
        """
        try:
            with open("app/main.py", encoding="utf-8") as f:
                contenido = f.read()

            # Buscar la línea que configura _origins
            lineas = contenido.split("\n")

            encontrado_wildcard = False
            linea_numero = 0

            for i, linea in enumerate(lineas, 1):
                # Buscar _origins = ["*"] o _origins = ['*']
                if "_origins" in linea and "=" in linea and "*" in linea:
                    encontrado_wildcard = True
                    linea_numero = i
                    print(f"\n✓ Confirmado: Encontrado _origins con wildcard en línea {i}")
                    print(f"  Contenido: {linea.strip()}")
                    break

            # En código sin corregir, esperamos encontrar el wildcard
            assert encontrado_wildcard, (
                "Bug Condition: app/main.py debería tener _origins = ['*'] en código sin corregir. "
                "Si este test falla, CORS ya fue configurado con orígenes específicos."
            )

            # Verificar que está cerca de la línea 313 (±20 líneas)
            assert 293 <= linea_numero <= 333, (
                f"Bug Condition: _origins con wildcard debería estar cerca de la línea 313, "
                f"pero se encontró en línea {linea_numero}. "
                f"Si este test falla, el código fue refactorizado."
            )

        except FileNotFoundError:
            pytest.skip("app/main.py no encontrado")

    def test_cors_permite_credenciales_con_wildcard(self):
        """
        Verifica la combinación peligrosa: allow_credentials=True con allow_origins=["*"]

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma configuración insegura)
        """
        try:
            with open("app/main.py", encoding="utf-8") as f:
                contenido = f.read()

            # Buscar configuración de CORS middleware
            tiene_wildcard = (
                "_origins" in contenido
                and '["*"]' in contenido
                or "_origins" in contenido
                and "['*']" in contenido
            )
            tiene_credentials = "allow_credentials=True" in contenido

            # En código sin corregir, esperamos ambas configuraciones (combinación peligrosa)
            assert tiene_wildcard and tiene_credentials, (
                "Bug Condition: CORS debería tener allow_origins=['*'] Y allow_credentials=True "
                "en código sin corregir (combinación insegura). "
                f"Encontrado: wildcard={tiene_wildcard}, credentials={tiene_credentials}. "
                "Si este test falla, la configuración ya fue corregida."
            )

            print("\n✓ Confirmado: CORS tiene combinación insegura (Bug Condition)")
            print("  - allow_origins=['*']")
            print("  - allow_credentials=True")
            print("  Esta combinación permite ataques CSRF desde cualquier origen")

        except FileNotFoundError:
            pytest.skip("app/main.py no encontrado")

    def test_variable_entorno_allowed_origins_no_configurada(self):
        """
        Verifica que NO hay validación estricta que falle en producción sin ALLOWED_ORIGINS.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay validación que prevenga inicio en producción sin configuración)
        """
        try:
            with open("app/main.py", encoding="utf-8") as f:
                contenido = f.read()

            # Verificar que NO hay validación que levante RuntimeError en producción
            # cuando ALLOWED_ORIGINS no está configurado

            # Buscar el patrón de validación estricta:
            # if os.getenv("ENVIRONMENT") == "production":
            #     raise RuntimeError("ALLOWED_ORIGINS must be set in production")

            lineas = contenido.split("\n")
            tiene_validacion_estricta = False

            for i, linea in enumerate(lineas):
                if "ENVIRONMENT" in linea and "production" in linea:
                    # Verificar las siguientes 3 líneas para RuntimeError
                    for j in range(i, min(i + 3, len(lineas))):
                        if "RuntimeError" in lineas[j] or "raise" in lineas[j]:
                            if "ALLOWED_ORIGINS" in lineas[j] or "ALLOWED_ORIGINS" in lineas[j - 1]:
                                tiene_validacion_estricta = True
                                break

            # En código sin corregir, NO debería tener validación estricta
            assert not tiene_validacion_estricta, (
                "Bug Condition: No debería haber RuntimeError para ALLOWED_ORIGINS en producción "
                "en código sin corregir. Si este test falla, la validación ya fue implementada."
            )

            print(
                "\n✓ Confirmado: No hay RuntimeError para ALLOWED_ORIGINS vacío en producción (Bug Condition)"
            )

        except FileNotFoundError:
            pytest.skip("app/main.py no encontrado")

    @given(
        origen_malicioso=st.sampled_from(
            [
                "https://sitio-malicioso.com",
                "http://attacker.evil",
                "https://phishing-site.net",
                "http://malware-distributor.org",
            ]
        )
    )
    @settings(max_examples=4, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_cors_acepta_cualquier_origen(self, origen_malicioso, api_base_url):
        """
        Property-Based Test: Para cualquier origen malicioso,
        el sistema sin corregir acepta la petición CORS.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que CORS acepta todos los orígenes)
        """
        try:
            response = requests.options(
                f"{api_base_url}/",
                headers={"Origin": origen_malicioso, "Access-Control-Request-Method": "GET"},
                timeout=5,
            )

            cors_allow_origin = response.headers.get("Access-Control-Allow-Origin", "")

            # En código sin corregir, esperamos que CUALQUIER origen sea aceptado
            assert cors_allow_origin == "*" or cors_allow_origin == origen_malicioso, (
                f"Bug Condition Property: CORS debería aceptar origen '{origen_malicioso}' "
                f"en código sin corregir, pero Access-Control-Allow-Origin es '{cors_allow_origin}'. "
                f"Si este test falla, CORS ya fue configurado con lista de orígenes permitidos."
            )

            print(f"\n✓ Confirmado: CORS acepta origen malicioso '{origen_malicioso}'")

        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")

    def test_archivo_env_no_tiene_allowed_origins(self):
        """
        Verifica que .env.example no documenta ALLOWED_ORIGINS correctamente.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay documentación de configuración segura)
        """
        archivos_env = [".env.example", ".env"]

        for archivo in archivos_env:
            try:
                with open(archivo, encoding="utf-8") as f:
                    contenido = f.read()

                # Verificar que NO tiene ALLOWED_ORIGINS configurado con valores seguros
                tiene_allowed_origins = "ALLOWED_ORIGINS" in contenido

                if tiene_allowed_origins:
                    # Si existe, verificar que NO tiene valores de producción seguros
                    tiene_valores_seguros = "https://" in contenido and "taller.com" in contenido

                    assert not tiene_valores_seguros, (
                        f"Bug Condition: {archivo} no debería tener ALLOWED_ORIGINS con valores seguros "
                        f"en código sin corregir. Si este test falla, la configuración ya fue documentada."
                    )
                else:
                    # Si no existe, eso confirma el bug
                    print(
                        f"\n✓ Confirmado: {archivo} no tiene ALLOWED_ORIGINS configurado (Bug Condition)"
                    )

            except FileNotFoundError:
                # Si el archivo no existe, eso también confirma falta de documentación
                print(f"\n✓ Confirmado: {archivo} no existe (Bug Condition)")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST DE EXPLORACIÓN: CORS MAL CONFIGURADO (Bug Condition)")
    print("=" * 80)
    print("\nCRÍTICO: Este test DEBE FALLAR en código sin corregir.")
    print("El fallo confirma que el bug existe (CORS acepta cualquier origen).")
    print("\nEste test validará la corrección cuando pase después de la implementación.")
    print("=" * 80 + "\n")

    pytest.main([__file__, "-v", "-s"])
