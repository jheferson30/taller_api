#!/bin/bash
# ============================================================
# Script de despliegue para Azure VM (Ubuntu 24.04)
# Uso: bash deploy.sh
# ============================================================
set -e

echo "======================================"
echo "  MecaApp - Despliegue en Azure VM"
echo "======================================"

# ── 1. Instalar Docker si no está instalado ──────────────────
if ! command -v docker &> /dev/null; then
    echo "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✅ Docker instalado"
else
    echo "✅ Docker ya instalado: $(docker --version)"
fi

# ── 2. Instalar Docker Compose si no está ───────────────────
if ! command -v docker compose &> /dev/null; then
    echo "📦 Instalando Docker Compose..."
    sudo apt-get update -qq
    sudo apt-get install -y docker-compose-plugin
    echo "✅ Docker Compose instalado"
else
    echo "✅ Docker Compose ya instalado"
fi

# ── 3. Verificar .env.production ────────────────────────────
if [ ! -f ".env.production" ]; then
    echo ""
    echo "❌ ERROR: No existe .env.production"
    echo "   Copia .env.production.example como .env.production y llena los valores"
    echo "   cp .env.production.example .env.production"
    exit 1
fi
echo "✅ .env.production encontrado"

# ── 4. Crear directorios de uploads ─────────────────────────
mkdir -p uploads/fotos uploads/compras uploads/firmas uploads/logo
echo "✅ Directorios de uploads creados"

# ── 5. Construir y levantar contenedores ────────────────────
echo ""
echo "🔨 Construyendo imagen Docker (puede tardar unos minutos)..."
docker compose -f docker-compose.prod.yml --env-file .env.production build --no-cache

echo ""
echo "🚀 Levantando servicios..."
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

echo ""
echo "⏳ Esperando que los servicios estén listos..."
sleep 15

# ── 6. Verificar estado ──────────────────────────────────────
echo ""
echo "📊 Estado de los contenedores:"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "📋 Logs de la API (últimas 20 líneas):"
docker compose -f docker-compose.prod.yml logs api --tail=20

echo ""
echo "======================================"
echo "✅ Despliegue completado"
echo "   URL: http://$(curl -s ifconfig.me 2>/dev/null || echo 'TU_IP_PUBLICA')"
echo "   Usuario admin: admin"
echo "   Contraseña:    ver ADMIN_PASSWORD en .env.production"
echo "======================================"
