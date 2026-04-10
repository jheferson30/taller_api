#!/bin/bash
# Script de actualización de dependencias vulnerables
# Actualiza dependencias a versiones seguras que cierran CVEs conocidos

echo "=========================================="
echo "Actualizando dependencias vulnerables..."
echo "=========================================="
echo ""

# Actualizar dependencias específicas
echo "1. Actualizando Werkzeug a 3.1.7 (cierra CVE-2026-27199, CVE-2025-66221, CVE-2026-21860)..."
pip install --upgrade werkzeug==3.1.7

echo ""
echo "2. Actualizando Flask a 3.1.3 (cierra CVE-2026-27205)..."
pip install --upgrade flask==3.1.3

echo ""
echo "3. Actualizando ecdsa a 0.19.2 (cierra CVE-2024-23342)..."
pip install --upgrade ecdsa==0.19.2

echo ""
echo "4. Instalando safety para auditoría continua..."
pip install safety==3.7.0

echo ""
echo "=========================================="
echo "Ejecutando auditoría de seguridad..."
echo "=========================================="
safety check

echo ""
echo "=========================================="
echo "Actualizando requirements.txt..."
echo "=========================================="
pip freeze > requirements_frozen.txt
echo "Dependencias congeladas guardadas en requirements_frozen.txt"

echo ""
echo "=========================================="
echo "Actualización completada"
echo "=========================================="
echo ""
echo "Resumen de versiones actualizadas:"
pip list | grep -E "werkzeug|flask|ecdsa|safety"
