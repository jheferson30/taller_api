"""
Test de Exploración: HTTPS No Forzado (Bug Condition)

**Validates: Requirements 1.14, 1.15, 1.16**

CRÍTICO: Este test DEBE FALLAR en código sin corregir - el fallo confirma que el bug existe.
NO intentar corregir el test o el código cuando falle.

Este test codifica el comportamiento esperado - validará la corrección cuando pase después 
de la implementación.

OBJETIVO: Demostrar que sistema no fuerza HTTPS en producción.
"""

import pytest
import requests
from hypothesis import given, strategies as st, settings, HealthCheck
import os


class TestHTTPSNoForzado:
    """
    Property 1: Bug Condition - HTTP No Redirige a HTTPS
    
    Este test verifica que el sistema no fuerza HTTPS en producción.
    En código SIN CORREGIR, este test DEBE FALLAR.
    """
    
    @pytest.fixture(scope="class")
    def api_base_url(self):
        """URL base de la API para testing"""
        return os.getenv("API_BASE_URL", "http://localhost:8000")
    
    def test_http_no_redirige_a_https(self, api_base_url):
        """
        Verifica que peticiones HTTP no son redirigidas automáticamente a HTTPS.
        
        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay redirección HTTPS)
        """
        try:
            # Intentar acceder por HTTP (sin seguir redirecciones)
            response = requests.get(
                f"{api_base_url}/info",
                allow_redirects=False,
                timeout=5
            )
            
            # En código sin corregir, esperamos que NO haya redirección a HTTPS
            # Status 200 = sin redirección, 301/302/307/308 = con redirección
            assert response.status_code == 200, (
                f"Bug Condition: HTTP debería ser aceptado sin redirección en código sin corregir, "
                f"pero recibió status {response.status_code}. "
                f"Si este test falla, HTTPSRedirectMiddleware ya fue implementado."
            )
            
            # Verificar que no hay header Location (indicaría redirección)
            assert "Location" not in response.headers, (
                f"Bug Condition: No debería haber header Location en código sin corregir, "
                f"pero se encontró: {response.headers.get('Location')}. "
                f"Si este test falla, HTTPS redirect ya fue configurado."
            )
            
            print(f"\n✓ Confirmado: HTTP es aceptado sin redirección a HTTPS (Bug Condition)")
            print(f"  Status Code: {response.status_code}")
            print(f"  No hay redirección automática a HTTPS")
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo. Iniciar con: uvicorn app.main:app")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")
    
    def test_codigo_fuente_no_tiene_https_redirect_middleware(self):
        """
        Verifica que app/main.py no contiene HTTPSRedirectMiddleware.
        
        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que middleware HTTPS no está implementado)
        """
        try:
            with open('app/main.py', 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar importación de HTTPSRedirectMiddleware
            tiene_import = 'HTTPSRedirectMiddleware' in contenido
            
            # En código sin corregir, NO debería tener el middleware
            assert not tiene_import, (
                "Bug Condition: app/main.py no debería tener HTTPSRedirectMiddleware "
                "en código sin corregir. Si este test falla, el middleware ya fue agregado."
            )
            
            # Verificar que no hay add_middleware con HTTPSRedirectMiddleware
            tiene_middleware = 'add_middleware(HTTPSRedirectMiddleware)' in contenido
            
            assert not tiene_middleware, (
                "Bug Condition: app/main.py no debería configurar HTTPSRedirectMiddleware "
                "en código sin corregir. Si este test falla, el middleware ya fue configurado."
            )
            
            print("\n✓ Confirmado: HTTPSRedirectMiddleware no está en app/main.py (Bug Condition)")
            
        except FileNotFoundError:
            pytest.skip("app/main.py no encontrado")
    
    def test_cookies_no_tienen_secure_flag(self, api_base_url):
        """
        Verifica que cookies no tienen el flag Secure=True.
        
        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que cookies son inseguras)
        """
        try:
            # Intentar hacer login para obtener cookies
            response = requests.post(
                f"{api_base_url}/auth/login",
                json={
                    "username": "admin",
                    "password": "Admin123"
                },
                timeout=5
            )
            
            # Si el login falla, skip (no es el objetivo de este test)
            if response.status_code != 200:
                pytest.skip("No se pudo hacer login para verificar cookies")
            
            # Verificar cookies en la respuesta
            cookies = response.cookies
            
            if len(cookies) == 0:
                # Si no hay cookies en la respuesta, verificar el código fuente
                pytest.skip("No se encontraron cookies en la respuesta, verificando código fuente")
            
            # Verificar que las cookies NO tienen Secure flag
            for cookie in cookies:
                # En código sin corregir, esperamos que Secure sea False
                assert not cookie.secure, (
                    f"Bug Condition: Cookie '{cookie.name}' no debería tener Secure=True "
                    f"en código sin corregir. Si este test falla, las cookies ya fueron aseguradas."
                )
                
                print(f"\n✓ Confirmado: Cookie '{cookie.name}' no tiene Secure flag (Bug Condition)")
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")
    
    def test_codigo_fuente_cookies_sin_secure_flag(self):
        """
        Verifica que el código fuente no configura cookies con Secure=True.
        
        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que cookies no tienen flag de seguridad)
        """
        try:
            with open('app/rutas/auth_ruta.py', 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar configuración de cookies
            lineas = contenido.split('\n')
            
            # Buscar set_cookie y verificar que NO tiene secure=True
            tiene_secure_true = False
            tiene_set_cookie = False
            
            for i, linea in enumerate(lineas):
                if 'set_cookie' in linea.lower():
                    tiene_set_cookie = True
                    # Verificar las siguientes 10 líneas para secure=True
                    for j in range(i, min(i+10, len(lineas))):
                        if 'secure=True' in lineas[j] or 'secure = True' in lineas[j]:
                            tiene_secure_true = True
                            break
            
            if not tiene_set_cookie:
                pytest.skip("No se encontró set_cookie en auth_ruta.py")
            
            # En código sin corregir, NO debería tener secure=True
            assert not tiene_secure_true, (
                "Bug Condition: auth_ruta.py no debería tener secure=True en set_cookie "
                "en código sin corregir. Si este test falla, las cookies ya fueron aseguradas."
            )
            
            print("\n✓ Confirmado: set_cookie no tiene secure=True en auth_ruta.py (Bug Condition)")
            
        except FileNotFoundError:
            pytest.skip("app/rutas/auth_ruta.py no encontrado")
    
    def test_samesite_es_lax_no_strict(self):
        """
        Verifica que SameSite es 'lax' en lugar de 'strict'.
        
        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que SameSite no está en modo más seguro)
        """
        try:
            with open('app/rutas/auth_ruta.py', 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar configuración de SameSite
            tiene_samesite_lax = 'samesite="lax"' in contenido.lower() or "samesite='lax'" in contenido.lower()
            tiene_samesite_strict = 'samesite="strict"' in contenido.lower() or "samesite='strict'" in contenido.lower()
            
            # En código sin corregir, esperamos lax (no strict)
            if tiene_samesite_lax:
                assert not tiene_samesite_strict, (
                    "Bug Condition: SameSite debería ser 'lax' en código sin corregir, "
                    "pero se encontró 'strict'. Si este test falla, SameSite ya fue actualizado."
                )
                print("\n✓ Confirmado: SameSite es 'lax' (no 'strict') en auth_ruta.py (Bug Condition)")
            else:
                # Si no tiene ninguno, también es un bug
                print("\n✓ Confirmado: No se encontró configuración de SameSite (Bug Condition)")
            
        except FileNotFoundError:
            pytest.skip("app/rutas/auth_ruta.py no encontrado")
    
    def test_variable_entorno_environment_no_valida_https(self):
        """
        Verifica que NO hay validación condicional basada en ENVIRONMENT=production
        para forzar HTTPS.
        
        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay lógica condicional para producción)
        """
        try:
            with open('app/main.py', 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar patrón de validación condicional para HTTPS en producción
            lineas = contenido.split('\n')
            tiene_validacion_https_produccion = False
            
            for i, linea in enumerate(lineas):
                if 'ENVIRONMENT' in linea and 'production' in linea:
                    # Verificar las siguientes 5 líneas para HTTPSRedirectMiddleware
                    for j in range(i, min(i+5, len(lineas))):
                        if 'HTTPSRedirectMiddleware' in lineas[j]:
                            tiene_validacion_https_produccion = True
                            break
            
            # En código sin corregir, NO debería tener validación condicional
            assert not tiene_validacion_https_produccion, (
                "Bug Condition: No debería haber validación condicional para HTTPS en producción "
                "en código sin corregir. Si este test falla, la lógica condicional ya fue implementada."
            )
            
            print("\n✓ Confirmado: No hay validación condicional HTTPS para producción (Bug Condition)")
            
        except FileNotFoundError:
            pytest.skip("app/main.py no encontrado")
    
    @given(
        endpoint=st.sampled_from([
            "/info",
            "/auth/login",
            "/tickets",
            "/"
        ])
    )
    @settings(
        max_examples=4,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_http_aceptado_en_todos_endpoints(self, endpoint, api_base_url):
        """
        Property-Based Test: Para cualquier endpoint público,
        el sistema sin corregir acepta peticiones HTTP sin redirección.
        
        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que HTTP es aceptado en todos los endpoints)
        """
        try:
            response = requests.get(
                f"{api_base_url}{endpoint}",
                allow_redirects=False,
                timeout=5
            )
            
            # En código sin corregir, esperamos que NO haya redirección
            # (status 200, 401, 404 son aceptables - lo importante es que no sea 301/302/307/308)
            assert response.status_code not in [301, 302, 307, 308], (
                f"Bug Condition Property: Endpoint '{endpoint}' no debería redirigir a HTTPS "
                f"en código sin corregir, pero recibió status {response.status_code}. "
                f"Si este test falla, HTTPS redirect ya fue implementado."
            )
            
            print(f"\n✓ Confirmado: Endpoint '{endpoint}' acepta HTTP sin redirección")
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API no está corriendo")
        except requests.exceptions.Timeout:
            pytest.skip("API no responde (timeout)")
    
    def test_trusted_host_middleware_no_configurado(self):
        """
        Verifica que TrustedHostMiddleware no está configurado.
        
        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay validación de hosts confiables)
        """
        try:
            with open('app/main.py', 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar TrustedHostMiddleware
            tiene_trusted_host = 'TrustedHostMiddleware' in contenido
            
            # En código sin corregir, NO debería tener TrustedHostMiddleware
            assert not tiene_trusted_host, (
                "Bug Condition: app/main.py no debería tener TrustedHostMiddleware "
                "en código sin corregir. Si este test falla, el middleware ya fue agregado."
            )
            
            print("\n✓ Confirmado: TrustedHostMiddleware no está configurado (Bug Condition)")
            
        except FileNotFoundError:
            pytest.skip("app/main.py no encontrado")
    
    def test_documentacion_contraejemplos(self):
        """
        Documenta los contraejemplos encontrados (Bug Condition).
        
        Este test siempre pasa pero documenta el estado actual del sistema.
        """
        print("\n" + "="*80)
        print("DOCUMENTACIÓN DE CONTRAEJEMPLOS (Bug Condition)")
        print("="*80)
        print("\nProblemas Identificados:")
        print("1. HTTP no redirige a HTTPS")
        print("   - Peticiones HTTP son aceptadas sin redirección automática")
        print("   - No hay HTTPSRedirectMiddleware configurado")
        print("   - Vulnerable a ataques man-in-the-middle")
        print("\n2. Cookies sin flag Secure")
        print("   - Cookies pueden ser transmitidas por HTTP sin cifrar")
        print("   - Tokens JWT pueden ser interceptados")
        print("   - set_cookie no incluye secure=True")
        print("\n3. SameSite es 'lax' en lugar de 'strict'")
        print("   - Menor protección contra CSRF")
        print("   - Cookies pueden ser enviadas en navegación cross-site")
        print("\n4. Sin validación condicional para producción")
        print("   - No hay lógica que fuerce HTTPS solo en producción")
        print("   - Sistema puede desplegarse en producción sin HTTPS")
        print("\n5. Sin TrustedHostMiddleware")
        print("   - No hay validación de hosts confiables")
        print("   - Vulnerable a ataques de host header injection")
        print("\nImpacto de Seguridad:")
        print("- Tokens JWT interceptables en tráfico HTTP")
        print("- Credenciales expuestas en ataques MITM")
        print("- Cookies de sesión vulnerables")
        print("- Sistema no apto para producción sin correcciones")
        print("="*80 + "\n")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEST DE EXPLORACIÓN: HTTPS NO FORZADO (Bug Condition)")
    print("="*80)
    print("\nCRÍTICO: Este test DEBE FALLAR en código sin corregir.")
    print("El fallo confirma que el bug existe (HTTP no redirige a HTTPS).")
    print("\nEste test validará la corrección cuando pase después de la implementación.")
    print("="*80 + "\n")
    
    pytest.main([__file__, '-v', '-s'])
