#!/usr/bin/env python3
"""Script para remover todas las referencias a CSRF de los archivos de rutas"""

import re
from pathlib import Path

# Archivos a procesar
files = [
    "app/rutas/citas_ruta.py",
    "app/rutas/configuracion_ruta.py",
    "app/rutas/seguridad_ruta.py",
    "app/rutas/ticket_ruta.py",
    "app/rutas/upload_ruta.py",
    "app/rutas/users_ruta.py",
    "app/rutas/vehiculo_ruta.py",
    "app/rutas/whatsapp_ruta.py",
]

for filepath in files:
    path = Path(filepath)
    if not path.exists():
        print(f"❌ No existe: {filepath}")
        continue

    content = path.read_text(encoding="utf-8")
    original = content

    # Remover import
    content = re.sub(r"from fastapi_csrf_protect import CsrfProtect\n?", "", content)

    # Remover parámetro csrf_protect de funciones
    content = re.sub(r",\s*csrf_protect:\s*CsrfProtect\s*=\s*Depends\(\)", "", content)
    content = re.sub(r"csrf_protect:\s*CsrfProtect\s*=\s*Depends\(\),?\s*", "", content)

    # Remover llamadas a validate_csrf
    content = re.sub(r"\s*await csrf_protect\.validate_csrf\(request\)\n?", "", content)

    if content != original:
        path.write_text(content, encoding="utf-8")
        print(f"✅ Actualizado: {filepath}")
    else:
        print(f"⚠️  Sin cambios: {filepath}")

print("\n✅ Proceso completado")
