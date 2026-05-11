# Hallazgos de Auditoría — Frontend
_Generado en Fase 1, Tarea 5_

---

## 5.1 Rutas del Router (App.jsx)

Todas las páginas existentes en `frontend/src/pages/` tienen ruta registrada en el router. **No hay páginas huérfanas.**

| Página | Ruta | Roles |
|--------|------|-------|
| `LoginPage.jsx` | `/login` | Público |
| `RecepcionPage.jsx` | `/` | Todos |
| `TicketPage.jsx` | `/tickets` | Todos |
| `CitasPage.jsx` | `/citas` | Todos |
| `InfoPage.jsx` | `/info` | Todos |
| `EntregadosPage.jsx` | `/entregados` | ADMIN, RECEPCIONISTA |
| `EconomiaPage.jsx` | `/economia` | ADMIN |
| `ConfiguracionPage.jsx` | `/configuracion` | ADMIN (vía ConfiguracionRouter) |
| `ConfiguracionMecanicoPage.jsx` | `/configuracion` | MECANICO, RECEPCIONISTA (vía ConfiguracionRouter) |
| `SuperAdminPage.jsx` | `/super-admin` | SUPER_ADMIN |

**Conclusión:** 0 páginas sin ruta. Nada que eliminar aquí.

---

## 5.2 Componentes React — Uso en el Proyecto

| Componente | ¿Importado? | Dónde |
|------------|-------------|-------|
| `EconomiaAuth.jsx` | ❌ **NO** | No tiene ningún `import EconomiaAuth` en todo el proyecto |
| `EstadisticasDashboard.jsx` | ✅ Sí | `EconomiaPage.jsx` |
| `PageHero.jsx` | ✅ Sí | `TicketPage.jsx`, `RecepcionPage.jsx`, `InfoPage.jsx`, `EntregadosPage.jsx`, `EconomiaPage.jsx`, `ConfiguracionPage.jsx`, `CitasPage.jsx` |
| `Starfield.jsx` | ✅ Sí | `App.jsx` (renderizado globalmente como fondo animado) |
| `InputDinero.jsx` | ✅ Sí | `TicketPage.jsx` |
| `NotificationBadge.jsx` | ✅ Sí | `App.jsx` |
| `NotificationBanner.jsx` | ✅ Sí | `App.jsx` |
| `ProtectedRoute.jsx` | ✅ Sí | Tests (`ProtectedRoute.test.jsx`) — verificar si se usa en producción |
| `SelectMecanico.jsx` | ✅ Sí | `TicketPage.jsx`, `RecepcionPage.jsx` |

### Hallazgo crítico: EconomiaAuth.jsx — COMPONENTE NO USADO
- **Archivo:** `frontend/src/components/EconomiaAuth.jsx`
- **Severidad:** Medio
- **Descripción:** Componente de autenticación de economía que no es importado en ninguna página ni componente del proyecto. Probablemente fue reemplazado por el sistema de roles (`RoleGuard` en `App.jsx`).
- **Acción:** ELIMINAR en Fase 3B

### Hallazgo: ProtectedRoute.jsx — Solo en tests
- **Archivo:** `frontend/src/components/ProtectedRoute.jsx`
- **Severidad:** Bajo
- **Descripción:** Solo aparece en archivos de test. No se usa en producción (App.jsx usa `AppLayout` + `RoleGuard` en su lugar).
- **Acción:** Revisar si se puede eliminar junto con sus tests, o mantener si los tests son válidos.

---

## 5.3 Duplicación de Lógica de Autenticación: api.js vs authService.js

### Responsabilidades actuales (bien separadas):

**`authService.js`** — Gestión de sesión y tokens:
- Login (`POST /auth/login`) — almacena tokens en localStorage
- Logout (`POST /auth/logout`) — invalida refresh token en backend
- Refresh de access token (`POST /auth/refresh`)
- Interceptores de axios (request: agrega Bearer token; response: maneja 401 y refresca)
- Helpers: `getAccessToken()`, `getRefreshToken()`, `getUser()`, `isAuthenticated()`, `clearTokens()`

**`api.js`** — Cliente HTTP de dominio:
- Todos los endpoints de negocio (vehículos, tickets, citas, economía, configuración, etc.)
- Función `request()` genérica que usa axios (ya configurado por authService)
- Exporta `api` (operaciones de taller) y `apiSuperAdmin` (operaciones de plataforma)

### Duplicación detectada:

| Elemento | api.js | authService.js | Veredicto |
|----------|--------|----------------|-----------|
| `API_BASE` (cálculo de URL base) | ✅ Líneas 4-6 | ✅ Líneas 4-6 | **DUPLICADO** — código idéntico |
| Configuración de axios (`baseURL`, `timeout`, `withCredentials`) | ✅ Líneas 10-12 | ❌ No | Solo en api.js |
| Interceptores de axios | ❌ No (comentario dice "ya configurados en authService") | ✅ Sí | Correcto — solo en authService |
| Lógica de login/logout/refresh | ❌ No | ✅ Sí | Correcto |

### Hallazgo: API_BASE duplicado
- **Severidad:** Bajo
- **Descripción:** La lógica de cálculo de `API_BASE` está copiada literalmente en ambos archivos (3 líneas idénticas). Si cambia la lógica, hay que actualizarla en dos lugares.
- **Acción (Fase 3B):** Extraer a una constante compartida en `frontend/src/config.js` o `frontend/src/utils/apiBase.js` e importarla en ambos archivos.

### Conclusión general:
La separación de responsabilidades entre `api.js` y `authService.js` es **correcta y bien diseñada**. No hay duplicación de lógica de autenticación real — solo la constante `API_BASE` está duplicada.

---

## 5.4 Dependencias No Usadas (depcheck)

### Dependencias de producción — TODAS USADAS ✅
depcheck no reportó ninguna dependencia de producción sin usar.

### Dependencias de desarrollo no usadas:
| Dependencia | Estado |
|-------------|--------|
| `@testing-library/user-event` | ❌ No referenciada en ningún test |
| `@vitest/coverage-v8` | ❌ No referenciada en ningún archivo (solo útil via CLI `vitest --coverage`) |

**Nota sobre `@vitest/coverage-v8`:** Aunque no aparece en imports, es necesaria para ejecutar `vitest --coverage`. No eliminar.

**Acción:** Eliminar `@testing-library/user-event` de `devDependencies` si no se planea usar en tests futuros.

---

## 5.5 Uso de qrcode.react

**`qrcode.react` SÍ se usa** — en dos páginas:

| Archivo | Uso |
|---------|-----|
| `frontend/src/pages/ConfiguracionPage.jsx` | `import { QRCodeSVG } from "qrcode.react"` — renderiza QR de conexión WiFi/IP |
| `frontend/src/pages/ConfiguracionMecanicoPage.jsx` | `import { QRCodeSVG } from "qrcode.react"` — mismo uso |

**Conclusión:** `qrcode.react` **NO debe eliminarse**. La suposición del diseño de que podría ser no usada era incorrecta.

---

## Resumen de Hallazgos Frontend

| # | Hallazgo | Severidad | Fase | Acción |
|---|----------|-----------|------|--------|
| F-01 | `EconomiaAuth.jsx` no importado en ningún lugar | Medio | 3B | Eliminar |
| F-02 | `ProtectedRoute.jsx` solo en tests, no en producción | Bajo | 3B | Revisar y posiblemente eliminar |
| F-03 | `API_BASE` duplicado en `api.js` y `authService.js` | Bajo | 3B | Extraer a constante compartida |
| F-04 | `@testing-library/user-event` no usada en tests | Bajo | 3B | Eliminar de devDependencies |
| F-05 | `@vitest/coverage-v8` no en imports pero necesaria para CLI | Info | — | Mantener |
| F-06 | `qrcode.react` SÍ se usa (ConfiguracionPage, ConfiguracionMecanicoPage) | Info | — | Mantener (no eliminar) |
