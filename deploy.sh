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
    echo ""
    echo "⚠️  IMPORTANTE: Cierra sesión y vuelve a entrar para que Docker funcione"
    echo "   Luego ejecuta este script de nuevo: bash deploy.sh"
    exit 0
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
    echo ""
    echo "   Pasos:"
    echo "   1. cp .env.production.example .env.production"
    echo "   2. nano .env.production"
    echo "   3. Configura: DB_PASSWORD, ADMIN_PASSWORD, JWT_SECRET_KEY, CSRF_SECRET_KEY, PUBLIC_IP"
    echo ""
    echo "   Generar claves secretas:"
    echo "   python3 -c \"import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))\""
    echo "   python3 -c \"import secrets; print('CSRF_SECRET_KEY=' + secrets.token_urlsafe(32))\""
    exit 1
fi
echo "✅ .env.production encontrado"

# ── 4. Validar variables críticas ───────────────────────────
echo "🔍 Validando configuración..."
source .env.production

MISSING_VARS=()
[ -z "$DB_PASSWORD" ] && MISSING_VARS+=("DB_PASSWORD")
[ -z "$ADMIN_PASSWORD" ] && MISSING_VARS+=("ADMIN_PASSWORD")
[ -z "$JWT_SECRET_KEY" ] && MISSING_VARS+=("JWT_SECRET_KEY")
[ -z "$CSRF_SECRET_KEY" ] && MISSING_VARS+=("CSRF_SECRET_KEY")

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo ""
    echo "❌ ERROR: Faltan variables críticas en .env.production:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "   Edita .env.production y configura estas variables"
    exit 1
fi
echo "✅ Configuración validada"

# ── 5. Crear directorios de uploads ─────────────────────────
mkdir -p uploads/fotos uploads/compras uploads/firmas uploads/logo
echo "✅ Directorios de uploads creados"

# ── 6. Detener servicios anteriores si existen ──────────────
if docker compose -f docker-compose.prod.yml ps -q 2>/dev/null | grep -q .; then
    echo "🛑 Deteniendo servicios anteriores..."
    docker compose -f docker-compose.prod.yml down
fi

# ── 7. Construir y levantar contenedores ────────────────────
echo ""
echo "🔨 Construyendo imagen Docker (puede tardar 5-10 minutos)..."
docker compose -f docker-compose.prod.yml build --no-cache

echo ""
echo "🚀 Levantando servicios..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "⏳ Esperando que los servicios estén listos (30 segundos)..."
sleep 30

# ── 8. Verificar estado ──────────────────────────────────────
echo ""
echo "📊 Estado de los contenedores:"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "📋 Logs de la API (últimas 30 líneas):"
docker compose -f docker-compose.prod.yml logs api --tail=30

# ── 9. Verificar salud de la API ────────────────────────────
echo ""
echo "🏥 Verificando salud de la API..."
sleep 5

if docker compose -f docker-compose.prod.yml ps api | grep -q "Up"; then
    echo "✅ API está corriendo"
    
    # Intentar hacer una petición de prueba
    if command -v curl &> /dev/null; then
        if curl -f http://localhost:8000/info &> /dev/null; then
            echo "✅ API responde correctamente"
        else
            echo "⚠️  API está corriendo pero no responde aún (puede tardar unos segundos más)"
        fi
    fi
else
    echo "❌ API no está corriendo correctamente"
    echo ""
    echo "Ver logs completos con:"
    echo "   docker compose -f docker-compose.prod.yml logs api"
    exit 1
fi

# ── 10. Resumen final ───────────────────────────────────────
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "${PUBLIC_IP:-TU_IP_PUBLICA}")

echo ""
echo "======================================"
echo "✅ Despliegue completado exitosamente"
echo "======================================"
echo ""
echo "📍 Acceso a la aplicación:"
echo "   URL:        http://$PUBLIC_IP"
echo "   API Docs:   http://$PUBLIC_IP/docs"
echo ""
echo "🔐 Credenciales:"
echo "   Usuario:    admin"
echo "   Contraseña: (ver ADMIN_PASSWORD en .env.production)"
echo ""
echo "📚 Comandos útiles:"
echo "   Ver logs:       docker compose -f docker-compose.prod.yml logs -f"
echo "   Reiniciar:      docker compose -f docker-compose.prod.yml restart"
echo "   Detener:        docker compose -f docker-compose.prod.yml down"
echo "   Estado:         docker compose -f docker-compose.prod.yml ps"
echo ""
echo "⚠️  IMPORTANTE: Cambia la contraseña del admin después del primer login"
echo "======================================"
