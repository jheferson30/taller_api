#!/usr/bin/env python3
"""Script para arreglar indentación después de remover CSRF"""

import re
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
    fixed_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Si encontramos una línea que termina con "):    " (sin newline después del paréntesis)
        # significa que el script anterior juntó dos líneas
        if re.match(r"^.*\):\s+\w", line):
            # Separar en dos líneas
            match = re.match(r"^(.*\):)\s+(.+)$", line)
            if match:
                fixed_lines.append(match.group(1))
                # La siguiente línea debe tener indentación de 4 espacios
                fixed_lines.append("    " + match.group(2))
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

        i += 1

    fixed_content = "\n".join(fixed_lines)
    path.write_text(fixed_content, encoding="utf-8")
    print(f"✅ Arreglado: {filepath}")

print("\n✅ Indentación corregida")
