#!/usr/bin/env python3
"""
Secrets Scanner — detecta credenciales hardcodeadas en el codebase.

Uso:
    python scripts/secrets_scanner.py

Salida:
    [FOUND] ruta/archivo.py:34 — password (password = "123456")
    Total: 2 secreto(s) encontrado(s). Exit code: 1

    Si no hay hallazgos:
    [SECRETS SCANNER] OK — 0 secreto(s) encontrado(s). Exit code: 0

Solo usa stdlib de Python — sin dependencias del proyecto.
Compatible con ejecución local y en CI/CD.
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Patrones de detección (compilados, case-insensitive donde aplique)
# ---------------------------------------------------------------------------
PATTERNS = [
    ("password",    re.compile(r'password\s*=\s*["\'][^"\']{4,}', re.IGNORECASE)),
    ("api_key",     re.compile(r'api[_-]?key\s*=\s*["\'][^"\']{8,}', re.IGNORECASE)),
    ("jwt_secret",  re.compile(r'jwt[_-]?secret\s*=\s*["\'][^"\']{8,}', re.IGNORECASE)),
    ("db_url",      re.compile(r'postgresql://\w+:[^@\s]+@')),
    ("private_key", re.compile(r'-----BEGIN\s+\w*\s*PRIVATE KEY-----')),
]

# Extensiones de archivo a escanear
EXTENSIONS = {".py", ".yaml", ".yml", ".json", ".sh", ".env", ".cfg", ".ini"}

# Directorios que se omiten completamente
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".hypothesis"}

# Archivos que se omiten del escaneo (contienen patrones intencionalmente)
ALLOWLIST = {
    "secrets_scanner.py",       # el propio script contiene los patrones
    ".env.example",             # archivos de ejemplo con valores placeholder
    ".env.test.example",
    ".env.production.example",
    # Scripts de migración — contienen URLs de ejemplo en docstrings/comentarios
    "migrar_mono_a_multi_tenant.py",
    # Tests — contienen contraseñas ficticias para probar hashing y autenticación
    "test_auth_ruta.py",
    "test_auth_service.py",
    "test_password_hasher.py",
    "test_password_security.py",
    "test_user_service.py",
    "test_users_ruta_simple.py",
    "test_config_validator.py",
    # Tests del scanner — contienen los patrones intencionalmente para verificarlos
    "test_secrets_scanner.py",
}


def collect_files(root: str) -> list[str]:
    """Recorre el directorio raíz recursivamente y retorna archivos a escanear."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Omitir directorios excluidos (modificar in-place para que os.walk no los recorra)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            # Omitir archivos en la allowlist
            if filename in ALLOWLIST:
                continue

            _, ext = os.path.splitext(filename)
            if ext in EXTENSIONS:
                files.append(os.path.join(dirpath, filename))

    return sorted(files)


def scan_file(filepath: str) -> list[tuple[int, str, str]]:
    """
    Escanea un archivo en busca de patrones de secretos.

    Retorna lista de (numero_linea, tipo_patron, fragmento_match).
    """
    findings = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                for pattern_name, pattern in PATTERNS:
                    match = pattern.search(line)
                    if match:
                        # Fragmento del match, máximo 60 caracteres
                        fragment = match.group(0)[:60].strip()
                        findings.append((lineno, pattern_name, fragment))
    except OSError:
        # Archivo no legible — ignorar silenciosamente
        pass
    return findings


def main() -> None:
    root = os.getcwd()
    files = collect_files(root)

    print(f"[SECRETS SCANNER] Escaneando {len(files)} archivos...")

    total_findings = 0
    for filepath in files:
        # Mostrar ruta relativa al directorio actual
        rel_path = os.path.relpath(filepath, root)
        findings = scan_file(filepath)
        for lineno, pattern_name, fragment in findings:
            print(f"[FOUND] {rel_path}:{lineno} — {pattern_name} ({fragment})")
            total_findings += 1

    if total_findings == 0:
        print(f"[SECRETS SCANNER] OK — 0 secreto(s) encontrado(s). Exit code: 0")
        sys.exit(0)
    else:
        print(f"Total: {total_findings} secreto(s) encontrado(s). Exit code: 1")
        sys.exit(1)


if __name__ == "__main__":
    main()
