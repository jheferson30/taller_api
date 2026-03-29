"""
conftest.py — configuración global de pytest para el proyecto.

Establece las variables de entorno requeridas antes de que se importen
los módulos de la aplicación, de modo que las dependencias de seguridad
funcionen correctamente durante los tests.
"""
import os
from dotenv import load_dotenv

# Cargar variables desde .env.test si existe (excluido de git)
load_dotenv(".env.test", override=False)

# Fallback vacío para entornos CI donde .env.test no existe —
# en CI las variables deben inyectarse como variables de entorno del sistema
os.environ.setdefault("PDF_PASSWORD", "")
os.environ.setdefault("ADMIN_PASSWORD", "")
