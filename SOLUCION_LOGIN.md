# 🔐 Solución: Forzar Página de Login

## El Problema
El navegador está usando:
1. **Caché del build anterior** (versión vieja del código)
2. **Token guardado en localStorage** (de una sesión anterior)

Por eso te deja entrar directamente sin login.

## ✅ Solución Rápida (3 pasos)

### Paso 1: Abrir DevTools
1. Presiona **F12** en el navegador
2. Ve a la pestaña **Application** (o **Aplicación**)

### Paso 2: Limpiar localStorage
1. En el panel izquierdo, expande **Local Storage**
2. Haz clic en `http://localhost:8000`
3. Verás 3 items:
   - `access_token`
   - `refresh_token`
   - `user`
4. **Haz clic derecho** en el área y selecciona **"Clear"** o **"Borrar todo"**

### Paso 3: Limpiar Caché y Recargar
1. Mantén presionado **Ctrl + Shift + R** (Windows) o **Cmd + Shift + R** (Mac)
2. Esto forzará una recarga sin caché

## ✅ Alternativa: Modo Incógnito

Si los pasos anteriores no funcionan:

1. Abre una ventana de incógnito:
   - Chrome/Edge: **Ctrl + Shift + N**
   - Firefox: **Ctrl + Shift + P**
2. Navega a http://localhost:8000
3. Deberías ver la página de login

## ✅ ¿Qué Deberías Ver?

Después de limpiar localStorage y caché:
- ✅ Página de **LOGIN** (sin sidebar)
- ✅ Campos de "Usuario" y "Contraseña"
- ✅ Botón "Iniciar Sesión"

**NO** deberías ver:
- ❌ El sidebar con opciones (Recepción, Tickets, etc.)
- ❌ El dashboard directamente

## 🔑 Credenciales de Prueba

```
Usuario: admin
Contraseña: Admin123
```

## 🐛 Si Aún No Funciona

Si después de limpiar localStorage y caché sigues viendo el dashboard directamente:

1. **Cierra TODAS las pestañas** de localhost:8000
2. **Cierra el navegador completamente**
3. **Abre el navegador de nuevo**
4. **Abre DevTools (F12)**
5. **Ve a Application > Local Storage > http://localhost:8000**
6. **Verifica que esté vacío** (no debe haber access_token, refresh_token, ni user)
7. **Recarga con Ctrl + Shift + R**

## 📸 Captura de Pantalla de lo que Deberías Ver

Después de limpiar todo, deberías ver una página de login limpia, sin el sidebar.

## 🔧 Comando para Verificar el Build

Si quieres verificar que el build está actualizado:

```bash
# Ver el contenido del index.html
cat frontend/dist/index.html
```

Deberías ver: `index-CSzeiWsf.js` (el nuevo build)

Si ves: `index-BuMrkCr0.js` (el build viejo), ejecuta:

```bash
cd frontend
npm run build
```

## ✅ Confirmación de que Funcionó

Sabrás que funcionó cuando:
1. Abres http://localhost:8000
2. Ves SOLO la página de login (sin sidebar)
3. Al hacer login con admin/Admin123
4. Te redirige al dashboard CON sidebar

---

**¿Necesitas ayuda?** Comparte una captura de pantalla de lo que ves al abrir http://localhost:8000
