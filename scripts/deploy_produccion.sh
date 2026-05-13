#!/bin/bash
# =============================================================================
# SCRIPT DE DESPLIEGUE — Taller API v3
# VM Azure: 68.155.145.217
#
# Uso desde la VM:
#   chmod +x scripts/deploy_produccion.sh
#   ./scripts/deploy_produccion.sh
# =============================================================================

set -e

VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
ROJO='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${VERDE}✅  $1${NC}"; }
info() { echo -e "${AMARILLO}➡️   $1${NC}"; }
err()  { echo -e "${ROJO}❌  $1${NC}"; exit 1; }

echo ""
echo "================================================"
echo "   DESPLIEGUE PRODUCCIÓN — Taller API v3"
echo "================================================"
echo ""

# ── 0. Verificaciones previas ─────────────────────────────────────────────────
info "Verificando requisitos..."
[ -f ".env.production" ]                 || err ".env.production no encontrado"
[ -f "docker-compose.production.yml" ]   || err "docker-compose.production.yml no encontrado"
[ -f "mono/taller_backup_20260512.sql" ] || err "mono/taller_backup_20260512.sql no encontrado"
[ -f "mono/migrar_pulga_taller25.sql" ]  || err "mono/migrar_pulga_taller25.sql no encontrado"
[ -f "scripts/crear_super_admin.sql" ]   || err "scripts/crear_super_admin.sql no encontrado"
[ -f "scripts/cifrar_pii_migracion.py" ] || err "scripts/cifrar_pii_migracion.py no encontrado"
command -v docker >/dev/null 2>&1        || err "Docker no está instalado"
ok "Requisitos verificados"

# ── 1. Crear directorios de uploads ──────────────────────────────────────────
info "Creando directorios de uploads..."
mkdir -p uploads/talleres/25/fotos
mkdir -p uploads/talleres/25/compras
mkdir -p uploads/talleres/25/logos
mkdir -p uploads/pdfs
mkdir -p uploads/firmas
ok "Directorios creados"

# ── 2. Construir imágenes ─────────────────────────────────────────────────────
info "Construyendo imágenes Docker (puede tardar unos minutos)..."
docker compose -f docker-compose.production.yml build --no-cache
ok "Imágenes construidas"

# ── 3. Levantar BD y Redis ────────────────────────────────────────────────────
info "Levantando base de datos y Redis..."
docker compose -f docker-compose.production.yml up -d db redis

echo "   Esperando que PostgreSQL esté listo..."
for i in $(seq 1 30); do
    if docker compose -f docker-compose.production.yml exec -T db \
        pg_isready -U postgres -d taller_db >/dev/null 2>&1; then
        ok "PostgreSQL listo"
        break
    fi
    [ $i -eq 30 ] && err "PostgreSQL no respondió después de 90 segundos"
    sleep 3
done

# ── 4. Ejecutar migraciones Alembic ──────────────────────────────────────────
info "Ejecutando migraciones de base de datos..."
docker compose -f docker-compose.production.yml run --rm \
    --env-file .env.production \
    api alembic upgrade head
ok "Migraciones completadas"

# ── 5. Crear SUPER_ADMIN ──────────────────────────────────────────────────────
info "Creando usuario SUPER_ADMIN..."
docker compose -f docker-compose.production.yml exec -T db \
    psql -U postgres -d taller_db < scripts/crear_super_admin.sql
ok "SUPER_ADMIN creado (usuario: superadmin)"

# ── 6. Importar datos del taller 25 ──────────────────────────────────────────
info "Importando datos de Pulga Mecánica FI (taller 25)..."
docker compose -f docker-compose.production.yml exec -T db \
    psql -U postgres -d taller_db < mono/migrar_pulga_taller25.sql
ok "Datos del taller 25 importados"

# ── 7. Cifrar campos PII ──────────────────────────────────────────────────────
info "Cifrando campos PII (nombres y teléfonos de clientes)..."
docker compose -f docker-compose.production.yml run --rm \
    --env-file .env.production \
    api python /app/scripts/cifrar_pii_migracion.py
ok "Campos PII cifrados"

# ── 8. Levantar todos los servicios ───────────────────────────────────────────
info "Levantando todos los servicios..."
docker compose -f docker-compose.production.yml up -d
ok "Todos los servicios levantados"

# ── 9. Verificar que la API responde ─────────────────────────────────────────
info "Verificando que la API responde..."
for i in $(seq 1 20); do
    if curl -sf http://localhost:8000/info >/dev/null 2>&1; then
        ok "API respondiendo correctamente"
        break
    fi
    [ $i -eq 20 ] && err "La API no respondió. Revisa los logs: docker compose -f docker-compose.production.yml logs api"
    echo "   Esperando API... intento $i/20"
    sleep 5
done

# ── 10. Resumen ───────────────────────────────────────────────────────────────
IP=$(curl -s ifconfig.me 2>/dev/null || echo "68.155.145.217")
echo ""
echo "================================================"
echo -e "${VERDE}   DESPLIEGUE COMPLETADO EXITOSAMENTE${NC}"
echo "================================================"
echo ""
echo "  API:        http://${IP}:8000"
echo "  Docs:       http://${IP}:8000/docs"
echo "  Frontend:   http://${IP}:8000"
echo ""
echo "  SuperAdmin: usuario=superadmin"
echo ""
echo "  Contenedores:"
docker compose -f docker-compose.production.yml ps --format "table {{.Name}}\t{{.Status}}"
echo ""
echo "  Logs en tiempo real:"
echo "  docker compose -f docker-compose.production.yml logs -f api"
echo ""
