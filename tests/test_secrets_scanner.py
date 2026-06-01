"""
Tests para Property 3: No Hardcoded Secrets in Codebase.

Verifica que ningún archivo del repositorio con extensiones objetivo contiene
strings que coincidan con los patrones de secretos definidos en Secrets_Scanner.

Usa los mismos patrones, extensiones y allowlist que ``scripts/secrets_scanner.py``
para garantizar consistencia entre el test y el scanner de CI/CD.

**Validates: Requirements 1.5, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7 — Property 3**
"""

import os
import re

import pytest

# ---------------------------------------------------------------------------
# Importar patrones, extensiones y allowlist directamente del scanner
# para garantizar que el test y el CI usan exactamente la misma lógica.
# ---------------------------------------------------------------------------
from scripts.secrets_scanner import (
    ALLOWLIST,
    EXTENSIONS,
    PATTERNS,
    SKIP_DIRS,
    collect_files,
    scan_file,
)


# ---------------------------------------------------------------------------
# Recolección de archivos objetivo
# ---------------------------------------------------------------------------

def _get_target_files() -> list[str]:
    """
    Retorna todos los archivos del repositorio que deben ser escaneados.

    Usa la misma función ``collect_files`` del scanner para garantizar
    que el test y el CI/CD escanean exactamente el mismo conjunto de archivos.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return collect_files(root)


# Recolectar archivos una sola vez al cargar el módulo (evita re-escaneo por cada test)
_TARGET_FILES = _get_target_files()

# Calcular rutas relativas para los IDs de pytest (más legibles en la salida)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TARGET_FILES_REL = [os.path.relpath(f, _ROOT) for f in _TARGET_FILES]


# ---------------------------------------------------------------------------
# Property 3: No Hardcoded Secrets
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filepath", _TARGET_FILES, ids=_TARGET_FILES_REL)
def test_no_hardcoded_secrets(filepath: str) -> None:
    """
    Property 3: No Hardcoded Secrets in Codebase.

    FOR ALL files in the repository with extensions .py, .yaml, .yml, .json,
    .sh, .cfg, .ini, the file content SHALL NOT contain strings matching the
    secret patterns defined in Secrets_Scanner.

    Falla con ruta relativa y número de línea en el primer match encontrado,
    igual que el scanner de CI/CD.

    **Validates: Requirements 1.5, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7 — Property 3**
    """
    findings = scan_file(filepath)

    if findings:
        rel_path = os.path.relpath(filepath, _ROOT)
        # Reportar el primer hallazgo con ruta y línea (igual que el scanner)
        lineno, pattern_name, fragment = findings[0]
        pytest.fail(
            f"Secreto hardcodeado detectado en {rel_path}:{lineno} "
            f"— patrón '{pattern_name}' coincide con: {fragment!r}\n"
            f"Total de coincidencias en este archivo: {len(findings)}"
        )


# ---------------------------------------------------------------------------
# Tests unitarios del scanner (verifican que los patrones funcionan)
# ---------------------------------------------------------------------------

class TestPatrones:
    """
    Verifica que cada patrón del scanner detecta correctamente los casos
    que debe detectar y no genera falsos positivos en casos legítimos.
    """

    def _matches(self, pattern_name: str, text: str) -> bool:
        """Retorna True si el patrón con ese nombre coincide en el texto."""
        for name, pattern in PATTERNS:
            if name == pattern_name:
                return bool(pattern.search(text))
        raise ValueError(f"Patrón desconocido: {pattern_name!r}")

    # --- password ---

    def test_password_detecta_asignacion_con_comillas_dobles(self):
        assert self._matches("password", 'password = "secreto123"')

    def test_password_detecta_asignacion_con_comillas_simples(self):
        assert self._matches("password", "password = 'secreto123'")

    def test_password_detecta_case_insensitive(self):
        assert self._matches("password", 'PASSWORD = "secreto123"')

    def test_password_no_detecta_valor_demasiado_corto(self):
        # Menos de 4 caracteres entre comillas → no debe detectar
        assert not self._matches("password", 'password = "ab"')

    def test_password_no_detecta_sin_valor(self):
        assert not self._matches("password", "password = ''")

    # --- api_key ---

    def test_api_key_detecta_con_guion_bajo(self):
        assert self._matches("api_key", 'api_key = "abcdefghij"')

    def test_api_key_detecta_con_guion(self):
        assert self._matches("api_key", 'api-key = "abcdefghij"')

    def test_api_key_detecta_sin_separador(self):
        assert self._matches("api_key", 'apikey = "abcdefghij"')

    def test_api_key_no_detecta_valor_corto(self):
        # Menos de 8 caracteres → no debe detectar
        assert not self._matches("api_key", 'api_key = "abc"')

    # --- jwt_secret ---

    def test_jwt_secret_detecta_con_guion_bajo(self):
        assert self._matches("jwt_secret", 'jwt_secret = "supersecretkey123"')

    def test_jwt_secret_detecta_con_guion(self):
        assert self._matches("jwt_secret", 'jwt-secret = "supersecretkey123"')

    def test_jwt_secret_no_detecta_valor_corto(self):
        assert not self._matches("jwt_secret", 'jwt_secret = "abc"')

    # --- db_url ---

    def test_db_url_detecta_postgresql_con_credenciales(self):
        assert self._matches("db_url", "postgresql://usuario:contraseña@localhost/db")

    def test_db_url_detecta_con_puerto(self):
        assert self._matches("db_url", "postgresql://admin:pass123@db.host:5432/mydb")

    def test_db_url_no_detecta_sin_credenciales(self):
        # Sin contraseña (solo usuario sin @) → no debe detectar
        assert not self._matches("db_url", "postgresql://localhost/db")

    # --- private_key ---

    def test_private_key_detecta_bloque_rsa(self):
        assert self._matches("private_key", "-----BEGIN RSA PRIVATE KEY-----")

    def test_private_key_detecta_bloque_generico(self):
        assert self._matches("private_key", "-----BEGIN PRIVATE KEY-----")

    def test_private_key_detecta_bloque_ec(self):
        assert self._matches("private_key", "-----BEGIN EC PRIVATE KEY-----")


class TestAllowlist:
    """Verifica que la allowlist incluye los archivos correctos."""

    def test_secrets_scanner_en_allowlist(self):
        """El propio script del scanner debe estar en la allowlist."""
        assert "secrets_scanner.py" in ALLOWLIST

    def test_env_example_en_allowlist(self):
        """Los archivos .env.example deben estar en la allowlist."""
        assert ".env.example" in ALLOWLIST

    def test_env_test_example_en_allowlist(self):
        assert ".env.test.example" in ALLOWLIST

    def test_env_production_example_en_allowlist(self):
        assert ".env.production.example" in ALLOWLIST


class TestExtensiones:
    """Verifica que el conjunto de extensiones objetivo es correcto."""

    def test_extensiones_objetivo_incluyen_python(self):
        assert ".py" in EXTENSIONS

    def test_extensiones_objetivo_incluyen_yaml(self):
        assert ".yaml" in EXTENSIONS

    def test_extensiones_objetivo_incluyen_yml(self):
        assert ".yml" in EXTENSIONS

    def test_extensiones_objetivo_incluyen_json(self):
        assert ".json" in EXTENSIONS

    def test_extensiones_objetivo_incluyen_sh(self):
        assert ".sh" in EXTENSIONS

    def test_extensiones_objetivo_incluyen_cfg(self):
        assert ".cfg" in EXTENSIONS

    def test_extensiones_objetivo_incluyen_ini(self):
        assert ".ini" in EXTENSIONS


class TestCollectFiles:
    """Verifica que collect_files omite los directorios y archivos correctos."""

    def test_collect_files_omite_git(self):
        """El directorio .git no debe aparecer en los archivos recolectados."""
        files = collect_files(_ROOT)
        assert not any(".git" + os.sep in f for f in files)

    def test_collect_files_omite_venv(self):
        """El directorio .venv no debe aparecer en los archivos recolectados."""
        files = collect_files(_ROOT)
        assert not any(os.sep + ".venv" + os.sep in f for f in files)

    def test_collect_files_omite_hypothesis(self):
        """El directorio .hypothesis no debe aparecer en los archivos recolectados."""
        files = collect_files(_ROOT)
        assert not any(".hypothesis" in f for f in files)

    def test_collect_files_omite_archivos_en_allowlist(self):
        """Los archivos en la allowlist no deben aparecer en los resultados."""
        files = collect_files(_ROOT)
        filenames = {os.path.basename(f) for f in files}
        for allowlisted in ALLOWLIST:
            assert allowlisted not in filenames, (
                f"El archivo '{allowlisted}' está en la allowlist pero fue recolectado"
            )

    def test_collect_files_incluye_archivos_python(self):
        """Debe haber archivos .py en los resultados."""
        files = collect_files(_ROOT)
        assert any(f.endswith(".py") for f in files)
