#!/bin/bash
# Script para reemplazar URLs hardcodeadas en el frontend compilado

echo "🔧 Fixing hardcoded URLs in frontend build..."

# Directorio donde están los archivos JS compilados
DIST_DIR="/app/frontend/dist/assets"

if [ -d "$DIST_DIR" ]; then
    # Reemplazar todas las URLs hardcodeadas con URLs relativas
    find "$DIST_DIR" -name "*.js" -type f -exec sed -i 's|http://localhost:8000||g' {} \;
    find "$DIST_DIR" -name "*.js" -type f -exec sed -i 's|http://127\.0\.0\.1:8000||g' {} \;
    find "$DIST_DIR" -name "*.js" -type f -exec sed -i 's|http://localhost||g' {} \;
    find "$DIST_DIR" -name "*.js" -type f -exec sed -i 's|http://127\.0\.0\.1||g' {} \;
    
    echo "✅ URLs fixed in frontend build"
    
    # Verificar que no queden URLs hardcodeadas
    echo "🔍 Checking for remaining hardcoded URLs..."
    if grep -r "http://localhost\|http://127\.0\.0\.1" "$DIST_DIR" 2>/dev/null; then
        echo "⚠️  Some hardcoded URLs may still remain"
    else
        echo "✅ No hardcoded URLs found"
    fi
else
    echo "❌ Frontend dist directory not found: $DIST_DIR"
fi