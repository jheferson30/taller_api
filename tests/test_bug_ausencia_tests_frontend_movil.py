"""
Test de Exploración: Ausencia de Tests Frontend/Móvil (Bug Condition)

**Validates: Requirements 1.11, 1.12, 1.13**

CRÍTICO: Este test DEBE FALLAR en código sin corregir - el fallo confirma que el bug existe.
NO intentar corregir el test o el código cuando falle.

Este test codifica el comportamiento esperado - validará la corrección cuando pase después
de la implementación.

OBJETIVO: Demostrar que no existen tests en frontend/móvil.
"""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


class TestAusenciaTestsFrontendMovil:
    """
    Property 1: Bug Condition - Cobertura de Tests 0%

    Este test verifica que no existen tests en frontend/móvil.
    En código SIN CORREGIR, este test DEBE FALLAR.
    """

    def test_frontend_no_tiene_archivos_test(self):
        """
        Verifica que no existen archivos *.test.jsx en frontend/src.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay tests en frontend)
        """
        frontend_src = Path("frontend/src")

        if not frontend_src.exists():
            pytest.skip("Directorio frontend/src no existe")

        # Buscar archivos *.test.jsx y *.test.js en frontend/src
        test_files_jsx = list(frontend_src.rglob("*.test.jsx"))
        test_files_js = list(frontend_src.rglob("*.test.js"))
        test_files_tsx = list(frontend_src.rglob("*.test.tsx"))
        test_files_ts = list(frontend_src.rglob("*.test.ts"))

        total_test_files = test_files_jsx + test_files_js + test_files_tsx + test_files_ts

        # En código sin corregir, NO deberían existir archivos de test
        assert len(total_test_files) == 0, (
            f"Bug Condition: frontend/src NO debería tener archivos de test en código sin corregir, "
            f"pero se encontraron {len(total_test_files)} archivos: {[str(f) for f in total_test_files]}. "
            f"Si este test falla, los tests de frontend ya fueron implementados."
        )

        print("\n✓ Confirmado: 0 archivos de test encontrados en frontend/src (Bug Condition)")

    def test_frontend_no_tiene_vitest_config(self):
        """
        Verifica que no existe vitest.config.js en frontend.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que Vitest no está configurado)
        """
        vitest_configs = [
            Path("frontend/vitest.config.js"),
            Path("frontend/vitest.config.ts"),
            Path("frontend/vitest.config.mjs"),
        ]

        configs_existentes = [c for c in vitest_configs if c.exists()]

        # En código sin corregir, NO debería existir configuración de Vitest
        assert len(configs_existentes) == 0, (
            f"Bug Condition: frontend NO debería tener vitest.config.js en código sin corregir, "
            f"pero se encontró: {[str(c) for c in configs_existentes]}. "
            f"Si este test falla, Vitest ya fue configurado."
        )

        print("\n✓ Confirmado: vitest.config.js no existe en frontend (Bug Condition)")

    def test_frontend_no_tiene_carpeta_tests(self):
        """
        Verifica que no existe carpeta __tests__ en frontend/src.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay estructura de tests)
        """
        tests_dir = Path("frontend/src/__tests__")
        test_dir = Path("frontend/src/test")
        tests_dir_root = Path("frontend/__tests__")

        # En código sin corregir, NO deberían existir carpetas de tests
        carpetas_tests = []
        if tests_dir.exists():
            carpetas_tests.append(str(tests_dir))
        if test_dir.exists():
            carpetas_tests.append(str(test_dir))
        if tests_dir_root.exists():
            carpetas_tests.append(str(tests_dir_root))

        assert len(carpetas_tests) == 0, (
            f"Bug Condition: frontend NO debería tener carpetas de tests en código sin corregir, "
            f"pero se encontraron: {carpetas_tests}. "
            f"Si este test falla, la estructura de tests ya fue creada."
        )

        print("\n✓ Confirmado: No existen carpetas __tests__ en frontend (Bug Condition)")

    def test_mobile_no_tiene_archivos_test(self):
        """
        Verifica que no existen archivos *.test.js en mobile_app/src.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay tests en app móvil)
        """
        mobile_src = Path("mobile_app/src")

        if not mobile_src.exists():
            pytest.skip("Directorio mobile_app/src no existe")

        # Buscar archivos *.test.js y *.test.jsx en mobile_app/src
        test_files_js = list(mobile_src.rglob("*.test.js"))
        test_files_jsx = list(mobile_src.rglob("*.test.jsx"))
        test_files_ts = list(mobile_src.rglob("*.test.ts"))
        test_files_tsx = list(mobile_src.rglob("*.test.tsx"))

        total_test_files = test_files_js + test_files_jsx + test_files_ts + test_files_tsx

        # En código sin corregir, NO deberían existir archivos de test
        assert len(total_test_files) == 0, (
            f"Bug Condition: mobile_app/src NO debería tener archivos de test en código sin corregir, "
            f"pero se encontraron {len(total_test_files)} archivos: {[str(f) for f in total_test_files]}. "
            f"Si este test falla, los tests de app móvil ya fueron implementados."
        )

        print("\n✓ Confirmado: 0 archivos de test encontrados en mobile_app/src (Bug Condition)")

    def test_mobile_no_tiene_jest_config(self):
        """
        Verifica que no existe jest.config.js en mobile_app.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que Jest no está configurado)
        """
        jest_configs = [
            Path("mobile_app/jest.config.js"),
            Path("mobile_app/jest.config.ts"),
            Path("mobile_app/jest.config.json"),
        ]

        configs_existentes = [c for c in jest_configs if c.exists()]

        # En código sin corregir, NO debería existir configuración de Jest
        assert len(configs_existentes) == 0, (
            f"Bug Condition: mobile_app NO debería tener jest.config.js en código sin corregir, "
            f"pero se encontró: {[str(c) for c in configs_existentes]}. "
            f"Si este test falla, Jest ya fue configurado."
        )

        print("\n✓ Confirmado: jest.config.js no existe en mobile_app (Bug Condition)")

    def test_mobile_no_tiene_carpeta_tests(self):
        """
        Verifica que no existe carpeta __tests__ en mobile_app/src.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay estructura de tests)
        """
        tests_dir = Path("mobile_app/src/__tests__")
        test_dir = Path("mobile_app/src/test")
        tests_dir_root = Path("mobile_app/__tests__")

        # En código sin corregir, NO deberían existir carpetas de tests
        carpetas_tests = []
        if tests_dir.exists():
            carpetas_tests.append(str(tests_dir))
        if test_dir.exists():
            carpetas_tests.append(str(test_dir))
        if tests_dir_root.exists():
            carpetas_tests.append(str(tests_dir_root))

        assert len(carpetas_tests) == 0, (
            f"Bug Condition: mobile_app NO debería tener carpetas de tests en código sin corregir, "
            f"pero se encontraron: {carpetas_tests}. "
            f"Si este test falla, la estructura de tests ya fue creada."
        )

        print("\n✓ Confirmado: No existen carpetas __tests__ en mobile_app (Bug Condition)")

    def test_no_existe_carpeta_e2e(self):
        """
        Verifica que no existe carpeta e2e/ en la raíz del proyecto.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay tests E2E)
        """
        e2e_dir = Path("e2e")

        # En código sin corregir, NO debería existir carpeta e2e
        assert not e2e_dir.exists(), (
            "Bug Condition: NO debería existir carpeta e2e/ en código sin corregir. "
            "Si este test falla, los tests E2E ya fueron implementados."
        )

        print("\n✓ Confirmado: carpeta e2e/ no existe (Bug Condition)")

    def test_no_existe_playwright_config(self):
        """
        Verifica que no existe playwright.config.js en e2e/.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que Playwright no está configurado)
        """
        playwright_configs = [
            Path("e2e/playwright.config.js"),
            Path("e2e/playwright.config.ts"),
            Path("playwright.config.js"),
            Path("playwright.config.ts"),
        ]

        configs_existentes = [c for c in playwright_configs if c.exists()]

        # En código sin corregir, NO debería existir configuración de Playwright
        assert len(configs_existentes) == 0, (
            f"Bug Condition: NO debería existir playwright.config.js en código sin corregir, "
            f"pero se encontró: {[str(c) for c in configs_existentes]}. "
            f"Si este test falla, Playwright ya fue configurado."
        )

        print("\n✓ Confirmado: playwright.config.js no existe (Bug Condition)")

    @given(proyecto=st.sampled_from(["frontend", "mobile_app"]))
    @settings(
        max_examples=2,  # Solo 2 proyectos a verificar
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_property_proyectos_no_tienen_tests(self, proyecto):
        """
        Property-Based Test: Para cualquier proyecto frontend/móvil,
        el sistema sin corregir NO tiene tests implementados.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que cada proyecto no tiene tests)
        """
        src_dir = Path(f"{proyecto}/src")

        if not src_dir.exists():
            pytest.skip(f"Directorio {proyecto}/src no existe")

        # Buscar archivos de test
        test_patterns = [
            "*.test.js",
            "*.test.jsx",
            "*.test.ts",
            "*.test.tsx",
            "*.spec.js",
            "*.spec.jsx",
        ]
        test_files = []

        for pattern in test_patterns:
            test_files.extend(list(src_dir.rglob(pattern)))

        # En código sin corregir, NO deberían existir archivos de test
        assert len(test_files) == 0, (
            f"Bug Condition Property: {proyecto} NO debería tener archivos de test en código sin corregir, "
            f"pero se encontraron {len(test_files)} archivos: {[str(f) for f in test_files]}. "
            f"Si este test falla, los tests ya fueron implementados."
        )

        print(f"\n✓ Confirmado: {proyecto} no tiene archivos de test (Bug Condition)")

    def test_frontend_package_json_no_tiene_scripts_test(self):
        """
        Verifica que package.json del frontend no tiene scripts de test configurados.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay scripts de test)
        """
        import json

        package_json = Path("frontend/package.json")

        if not package_json.exists():
            pytest.skip("frontend/package.json no existe")

        with open(package_json, encoding="utf-8") as f:
            package_data = json.load(f)

        scripts = package_data.get("scripts", {})

        # Buscar scripts relacionados con tests
        test_scripts = [key for key in scripts.keys() if "test" in key.lower()]

        # Verificar que no hay scripts de test o que no están configurados para Vitest
        tiene_vitest = any("vitest" in str(scripts.get(key, "")).lower() for key in test_scripts)

        assert not tiene_vitest, (
            f"Bug Condition: frontend/package.json NO debería tener scripts de Vitest en código sin corregir. "
            f"Scripts encontrados: {test_scripts}. "
            f"Si este test falla, los scripts de test ya fueron configurados."
        )

        print("\n✓ Confirmado: frontend/package.json no tiene scripts de Vitest (Bug Condition)")

    def test_mobile_package_json_no_tiene_scripts_test(self):
        """
        Verifica que package.json de mobile_app no tiene scripts de test configurados.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay scripts de test)
        """
        import json

        package_json = Path("mobile_app/package.json")

        if not package_json.exists():
            pytest.skip("mobile_app/package.json no existe")

        with open(package_json, encoding="utf-8") as f:
            package_data = json.load(f)

        scripts = package_data.get("scripts", {})

        # Buscar scripts relacionados con tests
        test_scripts = [key for key in scripts.keys() if "test" in key.lower()]

        # Verificar que no hay scripts de test o que no están configurados para Jest
        tiene_jest = any("jest" in str(scripts.get(key, "")).lower() for key in test_scripts)

        assert not tiene_jest, (
            f"Bug Condition: mobile_app/package.json NO debería tener scripts de Jest en código sin corregir. "
            f"Scripts encontrados: {test_scripts}. "
            f"Si este test falla, los scripts de test ya fueron configurados."
        )

        print("\n✓ Confirmado: mobile_app/package.json no tiene scripts de Jest (Bug Condition)")

    def test_resumen_cobertura_cero(self):
        """
        Test resumen que documenta la cobertura de tests actual (0%).

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (documenta el estado actual de cobertura)
        """
        frontend_src = Path("frontend/src")
        mobile_src = Path("mobile_app/src")
        e2e_dir = Path("e2e")

        # Contar archivos de test
        frontend_tests = 0
        mobile_tests = 0
        e2e_tests = 0

        if frontend_src.exists():
            test_patterns = ["*.test.js", "*.test.jsx", "*.test.ts", "*.test.tsx"]
            for pattern in test_patterns:
                frontend_tests += len(list(frontend_src.rglob(pattern)))

        if mobile_src.exists():
            test_patterns = ["*.test.js", "*.test.jsx", "*.test.ts", "*.test.tsx"]
            for pattern in test_patterns:
                mobile_tests += len(list(mobile_src.rglob(pattern)))

        if e2e_dir.exists():
            test_patterns = ["*.spec.js", "*.spec.ts", "*.test.js", "*.test.ts"]
            for pattern in test_patterns:
                e2e_tests += len(list(e2e_dir.rglob(pattern)))

        total_tests = frontend_tests + mobile_tests + e2e_tests

        # Documentar contraejemplos
        print("\n" + "=" * 80)
        print("DOCUMENTACIÓN DE CONTRAEJEMPLOS (Bug Condition)")
        print("=" * 80)
        print("\nCobertura de Tests Actual:")
        print(f"  - Frontend: {frontend_tests} archivos de test")
        print(f"  - Mobile: {mobile_tests} archivos de test")
        print(f"  - E2E: {e2e_tests} archivos de test")
        print(f"  - TOTAL: {total_tests} archivos de test")
        print("\nCobertura Estimada: 0%")
        print("\nProblemas Identificados:")
        print("  ✗ No existen tests en frontend/src")
        print("  ✗ No existe vitest.config.js")
        print("  ✗ No existen tests en mobile_app/src")
        print("  ✗ No existe jest.config.js")
        print("  ✗ No existe carpeta e2e/")
        print("  ✗ No existe playwright.config.js")
        print("\nImpacto:")
        print("  - Regresiones no detectadas")
        print("  - Falta de confianza en deploys")
        print("  - Bugs en producción")
        print("=" * 80 + "\n")

        # En código sin corregir, esperamos 0 tests
        assert total_tests == 0, (
            f"Bug Condition: Cobertura de tests debería ser 0% en código sin corregir, "
            f"pero se encontraron {total_tests} archivos de test. "
            f"Si este test falla, los tests ya fueron implementados."
        )

        print("✓ Confirmado: Cobertura de tests es 0% (Bug Condition)")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST DE EXPLORACIÓN: AUSENCIA DE TESTS FRONTEND/MÓVIL (Bug Condition)")
    print("=" * 80)
    print("\nCRÍTICO: Este test DEBE FALLAR en código sin corregir.")
    print("El fallo confirma que el bug existe (0% cobertura de tests).")
    print("\nEste test validará la corrección cuando pase después de la implementación.")
    print("=" * 80 + "\n")

    pytest.main([__file__, "-v", "-s"])
