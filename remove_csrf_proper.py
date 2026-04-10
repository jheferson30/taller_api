#!/usr/bin/env python3
"""Script robusto para remover CSRF manteniendo la estructura correcta"""

from pathlib import Path

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
        continue

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    new_lines = []

    for line in lines:
        # Skip import line
        if "from fastapi_csrf_protect import CsrfProtect" in line:
            continue

        # Skip validate_csrf line
        if "await csrf_protect.validate_csrf(request)" in line:
            continue

        # Remove csrf_protect parameter from function signatures
        if "csrf_protect: CsrfProtect = Depends()" in line:
            # Check if it's the last parameter (has closing paren)
            if "):" in line:
                # Remove the parameter and keep the closing
                line = line.replace(", csrf_protect: CsrfProtect = Depends()", "")
                line = line.replace("csrf_protect: CsrfProtect = Depends(),", "")
            else:
                # It's on its own line, skip it
                continue

        new_lines.append(line)

    new_content = "\n".join(new_lines)
    path.write_text(new_content, encoding="utf-8")
    print(f"✅ Procesado: {filepath}")

print("\n✅ CSRF removido correctamente")
