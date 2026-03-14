"""
conftest.py — configuración global de pytest para el proyecto.

Establece las variables de entorno requeridas antes de que se importen
los módulos de la aplicación, de modo que las dependencias de seguridad
funcionen correctamente durante los tests.
"""
import os

# Establecer variables de entorno requeridas antes de cualquier import de la app
os.environ.setdefault("PDF_PASSWORD", "1234")
os.environ.setdefault("ADMIN_PASSWORD", "1234")
