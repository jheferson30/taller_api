# 🔄 Instrucciones para Limpiar Caché del Navegador

El frontend está mostrando la versión vieja porque el navegador tiene caché. Sigue estos pasos:

## Opción 1: Recarga Forzada (Más Rápido)

1. Abre el navegador en http://localhost:8000
2. Presiona **Ctrl + Shift + R** (Windows/Linux) o **Cmd + Shift + R** (Mac)
3. Esto forzará una recarga sin caché

## Opción 2: Limpiar Caché Completo

### Google Chrome / Edge
1. Presiona **Ctrl + Shift + Delete**
2. Selecciona "Imágenes y archivos en caché"
3. Selecciona "Desde siempre" en el rango de tiempo
4. Haz clic en "Borrar datos"
5. Recarga la página con **F5**

### Firefox
1. Presiona **Ctrl + Shift + Delete**
2. Selecciona "Caché"
3. Selecciona "Todo" en el rango de tiempo
4. Haz clic en "Limpiar ahora"
5. Recarga la página con **F5**

## Opción 3: Modo Incógnito

1. Abre una ventana de incógnito/privada:
   - Chrome/Edge: **Ctrl + Shift + N**
   - Firefox: **Ctrl + Shift + P**
2. Navega a http://localhost:8000
3. Deberías ver la página de login

## Opción 4: DevTools (Para Desarrolladores)

1. Abre DevTools: **F12**
2. Haz clic derecho en el botón de recarga
3. Selecciona "Vaciar caché y volver a cargar de manera forzada"

## ✅ ¿Cómo Saber si Funcionó?

Después de limpiar el caché, deberías ver:
- Una página de **LOGIN** con campos de usuario y contraseña
- NO deberías ver directamente el dashboard de recepción

Si ves la página de login, ¡funcionó! Usa estas credenciales:
- **Usuario**: admin
- **Contraseña**: Admin123

## 🐛 Si Aún No Funciona

Si después de limpiar el caché sigues viendo el frontend viejo, ejecuta:

```bash
# Detener el servidor
# (Presiona Ctrl+C en la terminal donde corre uvicorn)

# Limpiar y reconstruir
cd frontend
npm run build

# Reiniciar el servidor
cd ..
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Luego abre el navegador en modo incógnito.
