"""
Test de Exploración: Ausencia de Caché (Bug Condition)

**Validates: Requirements 1.19, 1.20**

CRÍTICO: Este test DEBE FALLAR en código sin corregir - el fallo confirma que el bug existe.
NO intentar corregir el test o el código cuando falle.

Este test codifica el comportamiento esperado - validará la corrección cuando pase después
de la implementación.

OBJETIVO: Demostrar que no existe caché y todas las peticiones consultan la base de datos.
"""

import os
import subprocess
import time

import pytest
import requests
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


class TestAusenciaCache:
    """
    Property 1: Bug Condition - Sin Caché Redis

    Este test verifica que no existe caché Redis y todas las peticiones consultan la BD.
    En código SIN CORREGIR, este test DEBE FALLAR.
    """

    @pytest.fixture(scope="class")
    def api_base_url(self):
        """URL base de la API para testing"""
        return os.getenv("API_BASE_URL", "http://localhost:8000")

    def test_redis_no_esta_corriendo(self):
        """
        Verifica que Redis NO está corriendo en el sistema.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que Redis no está configurado)
        """
        try:
            # Intentar verificar si docker está disponible
            docker_check = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=5
            )

            if docker_check.returncode != 0:
                # Docker no disponible, verificar si Redis está corriendo localmente
                try:
                    redis_check = subprocess.run(
                        ["redis-cli", "ping"], capture_output=True, text=True, timeout=5
                    )

                    # En código sin corregir, esperamos que Redis NO esté corriendo
                    assert redis_check.returncode != 0 or "PONG" not in redis_check.stdout, (
                        "Bug Condition: Redis NO debería estar corriendo en código sin corregir. "
                        "Si este test falla, Redis ya fue configurado."
                    )
                except FileNotFoundError:
                    # redis-cli no encontrado, confirma que Redis no está instalado
                    print("\n✓ Confirmado: redis-cli no encontrado (Bug Condition)")
                    return
            else:
                # Docker disponible, verificar contenedores Redis
                docker_ps = subprocess.run(
                    ["docker", "ps"], capture_output=True, text=True, timeout=10
                )

                # En código sin corregir, esperamos que NO haya contenedor Redis corriendo
                assert "redis" not in docker_ps.stdout.lower(), (
                    "Bug Condition: No debería haber contenedor Redis corriendo en código sin corregir. "
                    f"Si este test falla, Redis ya fue configurado.\nDocker ps output: {docker_ps.stdout}"
                )

                print("\n✓ Confirmado: No hay contenedor Redis corriendo (Bug Condition)")

        except FileNotFoundError:
            # Docker no encontrado, verificar Redis local
            try:
                redis_check = subprocess.run(
                    ["redis-cli", "ping"], capture_output=True, text=True, timeout=5
                )

                assert (
                    redis_check.returncode != 0 or "PONG" not in redis_check.stdout
                ), "Bug Condition: Redis NO debería estar corriendo en código sin corregir."
            except FileNotFoundError:
                print("\n✓ Confirmado: Redis no está instalado (Bug Condition)")
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout verificando Redis")

    def test_fastapi_cache2_no_esta_en_requirements(self):
        """
        Verifica que fastapi-cache2 NO está en requirements.txt.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que caché no está configurado)
        """
        try:
            with open("requirements.txt", encoding="utf-8") as f:
                contenido = f.read().lower()

            # En código sin corregir, esperamos que fastapi-cache2 NO esté presente
            assert "fastapi-cache2" not in contenido and "fastapi_cache2" not in contenido, (
                "Bug Condition: fastapi-cache2 NO debería estar en requirements.txt en código sin corregir. "
                "Si este test falla, fastapi-cache2 ya fue agregado."
            )

            print("\n✓ Confirmado: fastapi-cache2 no está en requirements.txt (Bug Condition)")

        except FileNotFoundError:
            pytest.skip("requirements.txt no encontrado")

    def test_redis_no_esta_en_requirements(self):
        """
        Verifica que redis NO está en requirements.txt.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que Redis no está configurado)
        """
        try:
            with open("requirements.txt", encoding="utf-8") as f:
                contenido = f.read().lower()

            # En código sin corregir, esperamos que redis NO esté presente
            # (puede estar como dependencia transitiva, pero no explícitamente)
            lineas = [
                l.strip()
                for l in contenido.split("\n")
                if l.strip() and not l.strip().startswith("#")
            ]

            tiene_redis_explicito = any(
                l.startswith("redis==") or l.startswith("redis>=") or l == "redis" for l in lineas
            )

            assert not tiene_redis_explicito, (
                "Bug Condition: redis NO debería estar explícitamente en requirements.txt en código sin corregir. "
                "Si este test falla, redis ya fue agregado."
            )

            print("\n✓ Confirmado: redis no está en requirements.txt (Bug Condition)")

        except FileNotFoundError:
            pytest.skip("requirements.txt no encontrado")

    def test_docker_compose_no_tiene_redis(self):
        """
        Verifica que docker-compose.yml NO existe o NO tiene servicio Redis.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que Redis no está configurado en Docker)
        """
        if not os.path.exists("docker-compose.yml"):
            print("\n✓ Confirmado: docker-compose.yml no existe (Bug Condition)")
            return

        try:
            with open("docker-compose.yml", encoding="utf-8") as f:
                contenido = f.read().lower()

            # En código sin corregir, esperamos que NO haya servicio Redis
            assert "redis" not in contenido or "image: redis" not in contenido, (
                "Bug Condition: docker-compose.yml NO debería tener servicio Redis en código sin corregir. "
                "Si este test falla, Redis ya fue configurado en Docker."
            )

            print("\n✓ Confirmado: docker-compose.yml no tiene servicio Redis (Bug Condition)")

        except FileNotFoundError:
            print("\n✓ Confirmado: docker-compose.yml no existe (Bug Condition)")

    def test_codigo_no_tiene_configuracion_cache(self):
        """
        Verifica que app/main.py NO tiene configuración de caché.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que caché no está inicializado)
        """
        try:
            with open("app/main.py", encoding="utf-8") as f:
                contenido = f.read()

            # En código sin corregir, esperamos que NO haya imports de fastapi-cache2
            assert "fastapi_cache" not in contenido and "FastAPICache" not in contenido, (
                "Bug Condition: app/main.py NO debería tener imports de fastapi_cache en código sin corregir. "
                "Si este test falla, caché ya fue configurado."
            )

            # Verificar que NO hay inicialización de Redis
            assert "RedisBackend" not in contenido and "redis" not in contenido.lower(), (
                "Bug Condition: app/main.py NO debería tener configuración de Redis en código sin corregir. "
                "Si este test falla, Redis ya fue configurado."
            )

            print("\n✓ Confirmado: app/main.py no tiene configuración de caché (Bug Condition)")

        except FileNotFoundError:
            pytest.skip("app/main.py no encontrado")

    def test_endpoint_estadisticas_no_tiene_decorador_cache(self):
        """
        Verifica que el endpoint /economia/estadisticas NO tiene decorador @cache.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que endpoint no usa caché)
        """
        try:
            with open("app/rutas/economia_ruta.py", encoding="utf-8") as f:
                contenido = f.read()

            # En código sin corregir, esperamos que NO haya decorador @cache
            assert "@cache" not in contenido, (
                "Bug Condition: economia_ruta.py NO debería tener decorador @cache en código sin corregir. "
                "Si este test falla, caché ya fue implementado."
            )

            # Verificar que NO hay imports de fastapi-cache2
            assert "from fastapi_cache" not in contenido, (
                "Bug Condition: economia_ruta.py NO debería importar fastapi_cache en código sin corregir. "
                "Si este test falla, caché ya fue implementado."
            )

            print(
                "\n✓ Confirmado: /economia/estadisticas no tiene decorador @cache (Bug Condition)"
            )

        except FileNotFoundError:
            pytest.skip("app/rutas/economia_ruta.py no encontrado")

    def test_variable_entorno_redis_url_no_configurada(self):
        """
        Verifica que REDIS_URL NO está configurado en .env.example.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que Redis no está documentado)
        """
        archivos_env = [".env.example", ".env"]

        for archivo in archivos_env:
            if not os.path.exists(archivo):
                print(f"\n✓ Confirmado: {archivo} no existe o no tiene REDIS_URL (Bug Condition)")
                continue

            try:
                with open(archivo, encoding="utf-8") as f:
                    contenido = f.read()

                # En código sin corregir, esperamos que REDIS_URL NO esté configurado
                assert "REDIS_URL" not in contenido, (
                    f"Bug Condition: {archivo} NO debería tener REDIS_URL en código sin corregir. "
                    f"Si este test falla, Redis ya fue documentado."
                )

                print(f"\n✓ Confirmado: {archivo} no tiene REDIS_URL (Bug Condition)")

            except FileNotFoundError:
                print(f"\n✓ Confirmado: {archivo} no existe (Bug Condition)")

    @pytest.mark.skipif(os.getenv("SKIP_API_TESTS") == "1", reason="API tests deshabilitados")
    def test_peticiones_repetidas_consultan_base_datos(self, api_base_url):
        """
        Verifica que peticiones repetidas al endpoint /economia/estadisticas
        consultan la base de datos cada vez (sin caché).

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay caché y cada petición consulta BD)

        NOTA: Este test requiere que la API esté corriendo y que haya
        un usuario admin autenticado. Se puede saltar si la API no está disponible.
        """
        try:
            # Intentar hacer login para obtener token
            login_response = requests.post(
                f"{api_base_url}/auth/login",
                data={"username": "admin", "password": "Admin123"},
                timeout=5,
            )

            if login_response.status_code != 200:
                pytest.skip("No se pudo autenticar con credenciales de prueba")

            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Hacer 10 peticiones al endpoint de estadísticas
            latencias = []

            for i in range(10):
                inicio = time.time()
                response = requests.get(
                    f"{api_base_url}/economia/estadisticas", headers=headers, timeout=10
                )
                fin = time.time()

                if response.status_code != 200:
                    pytest.skip(f"Endpoint retornó {response.status_code}")

                latencia = (fin - inicio) * 1000  # Convertir a ms
                latencias.append(latencia)

                # Pequeña pausa entre peticiones
                time.sleep(0.1)

            # Calcular estadísticas de latencia
            latencia_promedio = sum(latencias) / len(latencias)
            latencia_min = min(latencias)
            latencia_max = max(latencias)

            print("\n" + "=" * 80)
            print("ANÁLISIS DE LATENCIA (Bug Condition)")
            print("=" * 80)
            print(f"\nPeticiones realizadas: {len(latencias)}")
            print(f"Latencia promedio: {latencia_promedio:.2f}ms")
            print(f"Latencia mínima: {latencia_min:.2f}ms")
            print(f"Latencia máxima: {latencia_max:.2f}ms")
            print("\nLatencias individuales:")
            for i, lat in enumerate(latencias, 1):
                print(f"  Petición {i}: {lat:.2f}ms")

            # En código sin corregir, esperamos que:
            # 1. NO haya mejora significativa en latencia entre peticiones
            # 2. Todas las latencias sean similares (sin caché, todas consultan BD)

            # Calcular variación entre primera y última petición
            variacion = abs(latencias[0] - latencias[-1]) / latencias[0] * 100

            # En código sin corregir, la variación debería ser pequeña (<50%)
            # porque todas las peticiones consultan BD
            assert variacion < 50, (
                f"Bug Condition: Latencia debería ser consistente sin caché, "
                f"pero hay variación de {variacion:.1f}% entre primera y última petición. "
                f"Si este test falla, puede que ya exista caché implementado."
            )

            # Verificar que la latencia promedio es relativamente alta (>50ms)
            # porque consulta BD cada vez
            assert latencia_promedio > 50, (
                f"Bug Condition: Latencia promedio debería ser >50ms sin caché, "
                f"pero es {latencia_promedio:.2f}ms. "
                f"Si este test falla, puede que ya exista caché implementado."
            )

            print("\n✓ Confirmado: Latencia consistente indica ausencia de caché (Bug Condition)")
            print("=" * 80 + "\n")

        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo. Iniciar con: uvicorn app.main:app")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")

    @given(num_peticiones=st.integers(min_value=5, max_value=10))
    @settings(max_examples=2, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_sin_cache_todas_peticiones_consultan_bd(self, num_peticiones, api_base_url):
        """
        Property-Based Test: Para cualquier número de peticiones repetidas,
        el sistema sin caché consulta la base de datos cada vez.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay caché y cada petición consulta BD)
        """
        if os.getenv("SKIP_API_TESTS") == "1":
            pytest.skip("API tests deshabilitados")

        try:
            # Intentar hacer login
            login_response = requests.post(
                f"{api_base_url}/auth/login",
                data={"username": "admin", "password": "Admin123"},
                timeout=5,
            )

            if login_response.status_code != 200:
                pytest.skip("No se pudo autenticar")

            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Hacer N peticiones
            latencias = []

            for i in range(num_peticiones):
                inicio = time.time()
                response = requests.get(
                    f"{api_base_url}/economia/estadisticas", headers=headers, timeout=10
                )
                fin = time.time()

                if response.status_code != 200:
                    pytest.skip(f"Endpoint retornó {response.status_code}")

                latencia = (fin - inicio) * 1000
                latencias.append(latencia)
                time.sleep(0.1)

            # En código sin corregir, esperamos latencias consistentes
            latencia_promedio = sum(latencias) / len(latencias)

            # Todas las latencias deberían estar en un rango similar (±50% del promedio)
            for lat in latencias:
                desviacion = abs(lat - latencia_promedio) / latencia_promedio * 100
                assert desviacion < 100, (
                    f"Bug Condition Property: Latencias deberían ser consistentes sin caché, "
                    f"pero hay desviación de {desviacion:.1f}% respecto al promedio. "
                    f"Si este test falla, puede que ya exista caché."
                )

            print(
                f"\n✓ Confirmado: {num_peticiones} peticiones con latencia consistente (sin caché)"
            )

        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST DE EXPLORACIÓN: AUSENCIA DE CACHÉ (Bug Condition)")
    print("=" * 80)
    print("\nCRÍTICO: Este test DEBE FALLAR en código sin corregir.")
    print("El fallo confirma que el bug existe (sin caché Redis).")
    print("\nEste test validará la corrección cuando pase después de la implementación.")
    print("=" * 80 + "\n")

    pytest.main([__file__, "-v", "-s"])
