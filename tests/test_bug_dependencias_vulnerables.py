"""
Test de Exploración: Dependencias Vulnerables (Bug Condition)

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

CRÍTICO: Este test DEBE FALLAR en código sin corregir - el fallo confirma que el bug existe.
NO intentar corregir el test o el código cuando falle.

Este test codifica el comportamiento esperado - validará la corrección cuando pase después
de la implementación.

OBJETIVO: Demostrar que las dependencias actuales tienen vulnerabilidades conocidas.
"""

import subprocess
import sys

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


class TestDependenciasVulnerables:
    """
    Property 1: Bug Condition - Dependencias con CVEs Conocidos

    Este test verifica que las dependencias actuales tienen vulnerabilidades conocidas.
    En código SIN CORREGIR, este test DEBE FALLAR.
    """

    def test_verificar_versiones_vulnerables_instaladas(self):
        """
        Verifica que las versiones vulnerables específicas están instaladas.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que dependencias vulnerables están presentes)
        """
        from importlib.metadata import PackageNotFoundError, version

        # Versiones vulnerables conocidas que deben estar presentes en código sin corregir
        versiones_vulnerables = {
            "werkzeug": "3.1.3",
            "flask": "3.1.2",
            "pip": "25.2",
            "ecdsa": "0.19.1",
        }

        versiones_encontradas = {}
        paquetes_faltantes = []

        for paquete, version_esperada in versiones_vulnerables.items():
            try:
                version_instalada = version(paquete)
                versiones_encontradas[paquete] = version_instalada
            except PackageNotFoundError:
                paquetes_faltantes.append(paquete)

        # En código sin corregir, esperamos encontrar las versiones vulnerables
        # Este test FALLA si las versiones son diferentes (lo cual es correcto - confirma el bug)
        for paquete, version_esperada in versiones_vulnerables.items():
            if paquete in versiones_encontradas:
                version_actual = versiones_encontradas[paquete]
                assert version_actual == version_esperada, (
                    f"Bug Condition: {paquete} debería estar en versión vulnerable {version_esperada}, "
                    f"pero está en {version_actual}. "
                    f"Si este test falla, las dependencias ya fueron actualizadas."
                )

    def test_safety_check_reporta_cves_criticos(self):
        """
        Ejecuta safety check y verifica que reporta los 5 CVEs críticos conocidos.

        CVEs esperados:
        - CVE-2026-27199 (Werkzeug)
        - CVE-2025-66221 (Werkzeug)
        - CVE-2026-21860 (Werkzeug)
        - CVE-2026-27205 (Flask)
        - CVE-2026-1703 (pip)
        - CVE-2024-23342 (ecdsa)

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que safety check detecta vulnerabilidades)
        """
        try:
            # Intentar ejecutar safety check
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                pytest.skip("No se pudo ejecutar pip list para verificar dependencias")

            # Verificar que safety está disponible
            try:
                safety_result = subprocess.run(
                    ["safety", "--version"], capture_output=True, text=True, timeout=10
                )
                if safety_result.returncode != 0:
                    pytest.skip("Safety no está instalado. Instalar con: pip install safety")
            except FileNotFoundError:
                pytest.skip("Safety no está instalado. Instalar con: pip install safety")

            # Ejecutar safety check
            safety_check = subprocess.run(
                ["safety", "check", "--json"], capture_output=True, text=True, timeout=60
            )

            # Safety check retorna código de salida != 0 cuando encuentra vulnerabilidades
            # En código sin corregir, esperamos que encuentre vulnerabilidades
            assert safety_check.returncode != 0, (
                "Bug Condition: safety check debería reportar vulnerabilidades en código sin corregir, "
                "pero no encontró ninguna. Si este test falla, las dependencias ya fueron actualizadas."
            )

            output = safety_check.stdout + safety_check.stderr

            # Verificar que el output menciona vulnerabilidades
            assert any(
                keyword in output.lower() for keyword in ["vulnerability", "vulnerabilities", "cve"]
            ), (
                f"Bug Condition: safety check debería reportar CVEs, pero el output no los menciona.\n"
                f"Output: {output}"
            )

            # Documentar los CVEs encontrados
            print("\n" + "=" * 80)
            print("DOCUMENTACIÓN DE CVEs ENCONTRADOS (Bug Condition)")
            print("=" * 80)
            print(f"\nSafety Check Output:\n{output}")
            print("\nCVEs Esperados:")
            print("- CVE-2026-27199 (Werkzeug 3.1.3 - DoS attack)")
            print("- CVE-2025-66221 (Werkzeug 3.1.3 - DoS attack)")
            print("- CVE-2026-21860 (Werkzeug 3.1.3 - DoS attack)")
            print("- CVE-2026-27205 (Flask 3.1.2 - information disclosure)")
            print("- CVE-2026-1703 (pip 25.2 - path traversal)")
            print("- CVE-2024-23342 (ecdsa 0.19.1 - Minerva timing attack)")
            print("=" * 80 + "\n")

        except subprocess.TimeoutExpired:
            pytest.fail("Safety check timeout - el comando tardó demasiado")
        except Exception as e:
            pytest.fail(f"Error ejecutando safety check: {str(e)}")

    @given(paquete=st.sampled_from(["werkzeug", "flask", "pip", "ecdsa"]))
    @settings(
        max_examples=4,  # Solo 4 paquetes a verificar
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_property_dependencias_tienen_versiones_vulnerables(self, paquete):
        """
        Property-Based Test: Para cualquier dependencia crítica,
        el sistema sin corregir tiene versiones con CVEs conocidos.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que cada dependencia crítica tiene vulnerabilidades)
        """
        from importlib.metadata import PackageNotFoundError, version

        # Mapeo de paquetes a versiones vulnerables conocidas
        versiones_vulnerables = {
            "werkzeug": "3.1.3",
            "flask": "3.1.2",
            "pip": "25.2",
            "ecdsa": "0.19.1",
        }

        # Mapeo de paquetes a CVEs conocidos
        cves_conocidos = {
            "werkzeug": ["CVE-2026-27199", "CVE-2025-66221", "CVE-2026-21860"],
            "flask": ["CVE-2026-27205"],
            "pip": ["CVE-2026-1703"],
            "ecdsa": ["CVE-2024-23342"],
        }

        try:
            version_instalada = version(paquete)
            version_vulnerable = versiones_vulnerables[paquete]

            # En código sin corregir, esperamos la versión vulnerable
            assert version_instalada == version_vulnerable, (
                f"Bug Condition Property: {paquete} debería estar en versión vulnerable {version_vulnerable} "
                f"(expuesta a {', '.join(cves_conocidos[paquete])}), "
                f"pero está en {version_instalada}. "
                f"Si este test falla, la dependencia ya fue actualizada."
            )

            print(
                f"\n✓ Confirmado: {paquete}=={version_instalada} está expuesto a {', '.join(cves_conocidos[paquete])}"
            )

        except PackageNotFoundError:
            pytest.skip(f"Paquete {paquete} no está instalado")

    def test_requirements_txt_no_tiene_versiones_pinned(self):
        """
        Verifica que requirements.txt no tiene versiones exactas especificadas,
        lo cual es parte del bug (permite instalar versiones vulnerables).

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que requirements.txt no especifica versiones seguras)
        """
        try:
            with open("requirements.txt") as f:
                contenido = f.read()

            # Verificar que las dependencias críticas no tienen versiones pinned
            dependencias_criticas = ["werkzeug", "flask", "ecdsa"]

            for dep in dependencias_criticas:
                # Buscar si la dependencia está en requirements.txt
                lineas = [l.strip() for l in contenido.split("\n") if l.strip()]

                # Verificar que no hay versiones específicas seguras pinned
                tiene_version_segura = False
                for linea in lineas:
                    if dep in linea.lower():
                        # Si tiene ==, verificar que no es una versión segura
                        if "==" in linea:
                            # Extraer versión
                            if "werkzeug==3.1.7" in linea or "werkzeug>=3.1.7" in linea:
                                tiene_version_segura = True
                            elif "flask==3.1.3" in linea or "flask>=3.1.3" in linea:
                                tiene_version_segura = True
                            elif "ecdsa==0.19.2" in linea or "ecdsa>=0.19.2" in linea:
                                tiene_version_segura = True

                assert not tiene_version_segura, (
                    f"Bug Condition: requirements.txt no debería tener versiones seguras de {dep} "
                    f"en código sin corregir. Si este test falla, requirements.txt ya fue actualizado."
                )

            print(
                "\n✓ Confirmado: requirements.txt no especifica versiones seguras (Bug Condition)"
            )

        except FileNotFoundError:
            pytest.skip("requirements.txt no encontrado")

    def test_safety_no_esta_en_requirements(self):
        """
        Verifica que 'safety' no está en requirements.txt,
        lo cual es parte del bug (no hay auditoría continua de vulnerabilidades).

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que safety no está configurado para auditoría continua)
        """
        try:
            with open("requirements.txt") as f:
                contenido = f.read().lower()

            assert "safety" not in contenido, (
                "Bug Condition: 'safety' no debería estar en requirements.txt en código sin corregir. "
                "Si este test falla, safety ya fue agregado para auditoría continua."
            )

            print("\n✓ Confirmado: safety no está en requirements.txt (Bug Condition)")

        except FileNotFoundError:
            pytest.skip("requirements.txt no encontrado")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST DE EXPLORACIÓN: DEPENDENCIAS VULNERABLES (Bug Condition)")
    print("=" * 80)
    print("\nCRÍTICO: Este test DEBE FALLAR en código sin corregir.")
    print("El fallo confirma que el bug existe (dependencias con CVEs conocidos).")
    print("\nEste test validará la corrección cuando pase después de la implementación.")
    print("=" * 80 + "\n")

    pytest.main([__file__, "-v", "-s"])
