# Correcciones Auditoría Sistema - Bugfix Design

## Overview

Este bugfix aborda 7 problemas críticos identificados en la auditoría del sistema de gestión de taller mecánico. Los problemas incluyen vulnerabilidades de seguridad (5 CVEs en dependencias, CORS mal configurado, falta de HTTPS/CSRF), problemas de rendimiento (consultas lentas sin índices, ausencia de caché), y falta de cobertura de tests en frontend/móvil.

La estrategia de corrección se divide en 7 categorías independientes que pueden implementarse en paralelo:
1. Actualización de dependencias vulnerables
2. Configuración segura de CORS
3. Optimización de base de datos con índices compuestos
4. Implementación de tests frontend/móvil
5. Forzado de HTTPS en producción
6. Protección CSRF
7. Implementación de caché con Redis

Cada corrección está diseñada para ser mínimamente invasiva, preservando toda la funcionalidad existente mientras elimina las vulnerabilidades y mejora el rendimiento.

## Glossary

- **Bug_Condition (C)**: Conjunto de 7 condiciones que representan los problemas del sistema: dependencias vulnerables, CORS abierto, consultas sin índices, ausencia de tests, falta de HTTPS, sin CSRF, sin caché
- **Property (P)**: El comportamiento correcto esperado después de las correcciones: dependencias actualizadas sin CVEs, CORS configurado con orígenes específicos, consultas optimizadas <50ms, tests con cobertura >60%, HTTPS forzado, CSRF implementado, caché funcional
- **Preservation**: Toda la funcionalidad existente debe continuar funcionando exactamente igual: autenticación JWT, RBAC, auditoría, CRUD de tickets, generación de PDFs, API endpoints
- **CVE (Common Vulnerabilities and Exposures)**: Identificadores únicos de vulnerabilidades de seguridad conocidas públicamente
- **CORS (Cross-Origin Resource Sharing)**: Mecanismo de seguridad que controla qué orígenes pueden acceder a recursos del servidor
- **CSRF (Cross-Site Request Forgery)**: Ataque que fuerza a usuarios autenticados a ejecutar acciones no deseadas
- **Índice Compuesto**: Índice de base de datos que incluye múltiples columnas para optimizar consultas con filtros combinados
- **N+1 Query**: Anti-patrón donde se ejecuta una query adicional por cada elemento de una lista
- **Eager Loading**: Técnica para cargar relaciones en una sola query usando JOINs
- **Rate Limiting**: Limitación de número de peticiones por tiempo para prevenir abuso
- **JWT (JSON Web Token)**: Token de autenticación usado en el sistema (access + refresh tokens)


## Bug Details

### Bug Condition

Este bugfix aborda múltiples problemas independientes que afectan la seguridad, rendimiento y calidad del sistema. Cada problema representa una condición de bug separada:

**Formal Specification:**
```
FUNCTION isBugCondition(systemState)
  INPUT: systemState of type SystemConfiguration
  OUTPUT: boolean
  
  RETURN (
    // 1. Dependencias vulnerables
    systemState.werkzeugVersion == "3.1.3" AND hasCVEs(["CVE-2026-27199", "CVE-2025-66221", "CVE-2026-21860"])
    OR systemState.flaskVersion == "3.1.2" AND hasCVEs(["CVE-2026-27205"])
    OR systemState.pipVersion == "25.2" AND hasCVEs(["CVE-2026-1703"])
    OR systemState.ecdsaVersion == "0.19.1" AND hasCVEs(["CVE-2024-23342"])
    
    // 2. CORS mal configurado
    OR systemState.corsOrigins == ["*"] AND systemState.environment == "production"
    
    // 3. Base de datos sin optimizar
    OR NOT hasIndex(systemState.database, "idx_tickets_estado_fecha")
    OR NOT hasIndex(systemState.database, "idx_audit_log_user_action_date")
    OR usesNPlusOneQueries(systemState.ticketRepository)
    OR NOT hasPagination(systemState.ticketRepository.getAll)
    
    // 4. Sin tests frontend/móvil
    OR systemState.frontendTestCoverage == 0
    OR systemState.mobileTestCoverage == 0
    OR systemState.e2eTestCount == 0
    
    // 5. Sin HTTPS forzado
    OR (systemState.environment == "production" AND NOT hasHTTPSRedirect(systemState))
    OR NOT hasCookieSecureFlag(systemState.cookies)
    
    // 6. Sin protección CSRF
    OR NOT hasCSRFProtection(systemState.postEndpoints)
    OR NOT hasCSRFProtection(systemState.putEndpoints)
    OR NOT hasCSRFProtection(systemState.deleteEndpoints)
    
    // 7. Sin caché
    OR NOT hasRedisCache(systemState)
    OR NOT cacheEnabled(systemState.estadisticasEndpoint)
  )
END FUNCTION
```

### Examples

**Ejemplo 1: Dependencias Vulnerables**
- **Input**: Sistema con Werkzeug 3.1.3
- **Comportamiento Actual**: Expuesto a CVE-2026-27199 (DoS attack)
- **Comportamiento Esperado**: Werkzeug 3.1.7+ sin vulnerabilidades conocidas

**Ejemplo 2: CORS Abierto**
- **Input**: Petición desde `https://sitio-malicioso.com` con credenciales
- **Comportamiento Actual**: Sistema acepta la petición y retorna datos sensibles
- **Comportamiento Esperado**: Sistema rechaza la petición con error CORS

**Ejemplo 3: Consulta Lenta sin Índice**
- **Input**: `SELECT * FROM tickets WHERE estado='ABIERTO' AND fecha_ingreso > '2026-01-01' ORDER BY fecha_ingreso DESC`
- **Comportamiento Actual**: Full table scan, 500ms de latencia
- **Comportamiento Esperado**: Usa índice compuesto, <50ms de latencia

**Ejemplo 4: N+1 Query**
- **Input**: Cargar 100 tickets con sus procesos y repuestos
- **Comportamiento Actual**: 1 query para tickets + 100 queries para procesos + 100 queries para repuestos = 201 queries
- **Comportamiento Esperado**: 1 query con JOINs carga todo = 1 query

**Ejemplo 5: Sin Tests Frontend**
- **Input**: Modificar componente LoginPage
- **Comportamiento Actual**: No hay tests que detecten regresiones
- **Comportamiento Esperado**: Tests automáticos fallan si se rompe funcionalidad

**Ejemplo 6: HTTP sin Redirigir**
- **Input**: Usuario accede a `http://taller.com/login` en producción
- **Comportamiento Actual**: Sistema sirve contenido por HTTP (interceptable)
- **Comportamiento Esperado**: Sistema redirige automáticamente a `https://taller.com/login`

**Ejemplo 7: Sin CSRF**
- **Input**: Sitio malicioso envía POST a `/tickets` con cookies del usuario
- **Comportamiento Actual**: Sistema procesa la petición y crea ticket no autorizado
- **Comportamiento Esperado**: Sistema rechaza petición sin token CSRF válido

**Ejemplo 8: Sin Caché**
- **Input**: 100 usuarios consultan `/economia/estadisticas` simultáneamente
- **Comportamiento Actual**: 100 queries costosas a la base de datos
- **Comportamiento Esperado**: 1 query inicial, 99 respuestas desde caché Redis


## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Autenticación JWT con access tokens (15 min) y refresh tokens (7 días) debe continuar funcionando exactamente igual
- Control de acceso basado en roles (ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA) debe continuar validando permisos correctamente
- Auditoría completa en tabla `audit_log` debe continuar registrando todos los eventos de seguridad
- Rate limiting (5 req/min en login, 30 req/min en creación, 100 req/min en lectura) debe continuar funcionando
- CRUD de tickets, vehículos, usuarios, citas debe continuar funcionando sin cambios en la API
- Generación de PDFs de tickets debe continuar incluyendo todos los datos (vehículo, procesos, repuestos, fotos)
- Registro de pagos y actualización de estado de tickets debe continuar funcionando
- Migración automática de contraseñas SHA256 a bcrypt debe continuar funcionando
- Detección de brute force (5 intentos en 10 min) debe continuar bloqueando cuentas
- Token blacklist para logout efectivo debe continuar funcionando
- Validación de contraseñas (mínimo 8 caracteres, mayúscula, minúscula, dígito) debe continuar funcionando
- Frontend React y app móvil React Native deben continuar mostrando la misma interfaz y funcionalidad
- Modo offline en app móvil debe continuar permitiendo consultar datos sincronizados
- Subida de fotos de tickets debe continuar guardándolas y mostrándolas correctamente

**Scope:**
Todas las funcionalidades existentes del sistema deben permanecer completamente inalteradas. Las correcciones son ADITIVAS (agregan seguridad, optimización, tests) y NO modifican la lógica de negocio existente. Los únicos cambios visibles para los usuarios serán:
- Mejora en velocidad de respuesta (consultas más rápidas)
- Posible redirección HTTP → HTTPS en producción (transparente)
- Posible inclusión de token CSRF en formularios (manejado automáticamente por el frontend)


## Hypothesized Root Cause

Basado en el análisis de la auditoría, los problemas tienen las siguientes causas raíz:

### 1. Dependencias Vulnerables

**Causa Raíz**: El archivo `requirements.txt` no especifica versiones exactas de las dependencias, usando solo nombres de paquetes sin pins de versión. Esto causa que `pip install` instale versiones desactualizadas o con vulnerabilidades conocidas.

**Evidencia**:
- `requirements.txt` contiene `fastapi` en lugar de `fastapi==0.115.0`
- No hay proceso de actualización periódica de dependencias
- No se ejecuta `safety check` en CI/CD

**Impacto**: 5 CVEs críticos exponen el sistema a ataques DoS, divulgación de información, path traversal y timing attacks.

### 2. CORS Mal Configurado

**Causa Raíz**: En `app/main.py` línea 340, la configuración de CORS usa `_origins = ["*"]` hardcodeado, permitiendo peticiones desde cualquier origen sin validación.

**Evidencia**:
```python
# app/main.py línea 340
_origins = ["*"]  # ❌ PELIGROSO
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,  # ❌ Combinación peligrosa con "*"
    ...
)
```

**Impacto**: Vulnerable a ataques CSRF y XSS desde cualquier dominio malicioso.

### 3. Base de Datos Sin Optimizar

**Causa Raíz Múltiple**:

a) **Falta de Índices Compuestos**: Las migraciones SQL en `/db/` no incluyen índices para consultas frecuentes con filtros combinados (estado + fecha, user_id + action).

b) **Consultas N+1**: En `app/repositorios/ticket_repository.py`, el método `get_all()` no usa eager loading, causando queries adicionales por cada relación (procesos, repuestos, fotos).

c) **Sin Paginación Obligatoria**: Los métodos de repositorio retornan `.all()` sin límite, permitiendo cargar miles de registros en memoria.

**Evidencia**:
```python
# app/repositorios/ticket_repository.py
def get_all_tickets(self):
    return self.db.query(Ticket).all()  # ❌ Sin paginación
    # No usa .options(joinedload(...))  # ❌ Sin eager loading
```

**Impacto**: Consultas lentas (>500ms), alto consumo de memoria, posibles timeouts.

### 4. Sin Tests Frontend/Móvil

**Causa Raíz**: Los proyectos frontend (`/frontend`) y móvil (`/mobile_app`) no tienen configurado ningún framework de testing (Vitest, Jest, Playwright).

**Evidencia**:
- No existe carpeta `__tests__` o `*.test.jsx` en frontend
- No existe `vitest.config.js` o `jest.config.js`
- No hay scripts de test en `package.json`

**Impacto**: Regresiones no detectadas, falta de confianza en deploys, bugs en producción.

### 5. Sin HTTPS Forzado

**Causa Raíz**: `app/main.py` no incluye middleware `HTTPSRedirectMiddleware` ni configuración de cookies seguras.

**Evidencia**:
```python
# app/main.py - Falta middleware
# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
# app.add_middleware(HTTPSRedirectMiddleware)  # ❌ No existe

# app/rutas/auth_ruta.py - Cookies sin flag Secure
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    # secure=True,  # ❌ Falta
    samesite="lax",  # ❌ Debería ser "strict"
)
```

**Impacto**: Tokens interceptables en ataques man-in-the-middle.

### 6. Sin Protección CSRF

**Causa Raíz**: El sistema no tiene instalado ni configurado `fastapi-csrf-protect` o similar. Los endpoints POST/PUT/DELETE no validan tokens CSRF.

**Evidencia**:
- `requirements.txt` no incluye `fastapi-csrf-protect`
- No existe middleware CSRF en `app/main.py`
- Frontend no envía tokens CSRF en headers

**Impacto**: Sitios maliciosos pueden ejecutar acciones en nombre de usuarios autenticados.

### 7. Sin Caché

**Causa Raíz**: El sistema no tiene Redis configurado ni usa `fastapi-cache2`. Todas las peticiones consultan directamente la base de datos.

**Evidencia**:
- `requirements.txt` no incluye `redis` ni `fastapi-cache2`
- No existe configuración de Redis en `docker-compose.yml` o `.env`
- Endpoints de lectura no usan decorador `@cache()`

**Impacto**: Carga innecesaria en base de datos, latencia alta en consultas repetidas.


## Correctness Properties

Property 1: Bug Condition - Dependencias Actualizadas Sin CVEs

_For any_ sistema donde las dependencias están actualizadas a versiones seguras (Werkzeug ≥3.1.7, Flask ≥3.1.3, pip ≥26.0.1, ecdsa ≥0.19.2), el sistema fijo SHALL NO estar expuesto a las vulnerabilidades CVE-2026-27199, CVE-2025-66221, CVE-2026-21860, CVE-2026-27205, CVE-2026-1703, CVE-2024-23342, y `safety check` SHALL retornar 0 vulnerabilidades críticas.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

Property 2: Bug Condition - CORS Configurado Correctamente

_For any_ petición desde un origen no autorizado cuando el sistema está en producción, el sistema fijo SHALL rechazar la petición con error CORS, y SHALL aceptar solo peticiones desde orígenes especificados en la variable de entorno `ALLOWED_ORIGINS`.

**Validates: Requirements 2.6, 2.7, 2.8, 2.9**

Property 3: Bug Condition - Base de Datos Optimizada

_For any_ consulta de tickets filtrada por estado y fecha, el sistema fijo SHALL usar el índice compuesto `idx_tickets_estado_fecha` y responder en menos de 50ms, y SHALL usar eager loading para cargar relaciones en una sola query, y SHALL implementar paginación obligatoria con máximo 50 registros por página.

**Validates: Requirements 2.10, 2.11, 2.12, 2.13, 2.14**

Property 4: Bug Condition - Tests Implementados

_For any_ modificación en el código del frontend o app móvil, el sistema fijo SHALL ejecutar tests automáticos que detecten regresiones, con cobertura mínima de 60% en frontend y 50% en móvil, y SHALL incluir tests E2E que cubran al menos 5 flujos críticos.

**Validates: Requirements 2.15, 2.16, 2.17, 2.18**

Property 5: Bug Condition - HTTPS Forzado en Producción

_For any_ petición HTTP en producción, el sistema fijo SHALL redirigir automáticamente a HTTPS, y SHALL configurar cookies con flags `Secure=True`, `HttpOnly=True`, `SameSite=strict`, y SHALL validar que el host está en la lista de hosts confiables.

**Validates: Requirements 2.19, 2.20, 2.21**

Property 6: Bug Condition - Protección CSRF Implementada

_For any_ petición POST/PUT/DELETE, el sistema fijo SHALL validar el token CSRF antes de procesarla, y SHALL rechazar peticiones sin token CSRF válido con error 403, y el frontend/móvil SHALL incluir el token CSRF en headers de peticiones de escritura.

**Validates: Requirements 2.22, 2.23, 2.24**

Property 7: Bug Condition - Caché Implementado

_For any_ consulta de estadísticas de economía, el sistema fijo SHALL cachear el resultado en Redis por 5 minutos, y SHALL invalidar automáticamente el caché cuando se crean/actualizan datos relacionados, y SHALL responder desde Redis sin consultar la base de datos cuando los datos están cacheados.

**Validates: Requirements 2.25, 2.26, 2.27**

Property 8: Preservation - Funcionalidad Existente Inalterada

_For any_ funcionalidad existente del sistema (autenticación JWT, RBAC, auditoría, CRUD de tickets, generación de PDFs, registro de pagos, validación de contraseñas, detección de brute force, token blacklist, frontend/móvil), el sistema fijo SHALL producir exactamente el mismo comportamiento que el sistema original, preservando toda la lógica de negocio sin cambios.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16**


## Fix Implementation

### Changes Required

Asumiendo que nuestro análisis de causa raíz es correcto, las correcciones se implementarán en 7 categorías independientes:

---

### 1. Actualización de Dependencias Vulnerables

**File**: `requirements.txt`

**Specific Changes**:
1. **Pin de Versiones Exactas**: Especificar versiones exactas de todas las dependencias para garantizar reproducibilidad
   ```
   # Antes
   fastapi
   werkzeug
   flask
   
   # Después
   fastapi==0.115.0
   werkzeug==3.1.7
   flask==3.1.3
   ```

2. **Actualizar Dependencias Críticas**: Actualizar a versiones sin CVEs conocidos
   - Werkzeug: 3.1.3 → 3.1.7 (cierra CVE-2026-27199, CVE-2025-66221, CVE-2026-21860)
   - Flask: 3.1.2 → 3.1.3 (cierra CVE-2026-27205)
   - pip: 25.2 → 26.0.1 (cierra CVE-2026-1703)
   - ecdsa: 0.19.1 → 0.19.2 (cierra CVE-2024-23342)

3. **Agregar Safety para Auditoría**: Incluir `safety` en requirements para verificación continua de vulnerabilidades

4. **Documentar Proceso de Actualización**: Crear script `scripts/update_dependencies.sh` para automatizar actualizaciones futuras

**Comando de Actualización**:
```bash
pip install --upgrade werkzeug==3.1.7 flask==3.1.3 pip==26.0.1 ecdsa==0.19.2
pip install safety
safety check
pip freeze > requirements.txt
```

---

### 2. Configuración Segura de CORS

**File**: `app/main.py`

**Function**: Configuración de middleware CORS (línea ~340)

**Specific Changes**:
1. **Leer Orígenes desde Variable de Entorno**: Reemplazar `_origins = ["*"]` con lectura de `ALLOWED_ORIGINS`
   ```python
   # Antes (línea 340)
   _origins = ["*"]
   
   # Después
   _raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
   if _raw_origins and _raw_origins != "*":
       _origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
   else:
       if os.getenv("ENVIRONMENT") == "production":
           raise RuntimeError("ALLOWED_ORIGINS must be set in production")
       _origins = ["http://localhost:5173", "http://localhost:3000"]
   ```

2. **Validar Configuración en Producción**: Fallar al iniciar si `ALLOWED_ORIGINS` no está configurado en producción

3. **Mantener allow_credentials**: Mantener `allow_credentials=True` pero solo con orígenes específicos

**File**: `.env.example`

**Specific Changes**:
1. **Agregar Variable ALLOWED_ORIGINS**: Documentar variable de entorno requerida
   ```env
   # CORS Configuration
   ALLOWED_ORIGINS=https://taller.com,https://app.taller.com
   ENVIRONMENT=production
   ```

**File**: `.env` (desarrollo)

**Specific Changes**:
1. **Configurar Orígenes de Desarrollo**:
   ```env
   ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
   ENVIRONMENT=development
   ```

---

### 3. Optimización de Base de Datos

**File**: `db/migrations/add_composite_indexes.sql` (nuevo)

**Specific Changes**:
1. **Crear Índices Compuestos**: Agregar índices para consultas frecuentes
   ```sql
   -- Índice para consultas de tickets por estado y fecha
   CREATE INDEX IF NOT EXISTS idx_tickets_estado_fecha 
   ON tickets(estado, fecha_ingreso DESC);
   
   -- Índice para búsqueda por placa
   CREATE INDEX IF NOT EXISTS idx_tickets_placa 
   ON tickets(placa);
   
   -- Índice para audit_log
   CREATE INDEX IF NOT EXISTS idx_audit_log_user_action_date 
   ON audit_log(user_id, action, created_at DESC);
   
   -- Índice para token blacklist
   CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti_exp 
   ON token_blacklist(jti, expires_at);
   
   -- Índice para vehículos
   CREATE INDEX IF NOT EXISTS idx_vehiculos_placa 
   ON vehiculos(placa);
   ```

**File**: `app/repositorios/ticket_repository.py`

**Specific Changes**:
1. **Implementar Eager Loading**: Agregar método con `joinedload` para cargar relaciones
   ```python
   from sqlalchemy.orm import joinedload
   
   def get_tickets_with_details(self, filters=None):
       query = self.db.query(Ticket)\
           .options(joinedload(Ticket.procesos))\
           .options(joinedload(Ticket.repuestos))\
           .options(joinedload(Ticket.fotos))
       
       if filters:
           # Aplicar filtros
           pass
       
       return query.all()
   ```

2. **Implementar Paginación Obligatoria**: Agregar método paginado
   ```python
   from typing import Tuple, List
   
   def get_tickets_paginated(
       self, 
       page: int = 1, 
       per_page: int = 50,
       estado: str = None
   ) -> Tuple[List[Ticket], int]:
       query = self.db.query(Ticket)
       
       if estado:
           query = query.filter(Ticket.estado == estado)
       
       total = query.count()
       tickets = query\
           .offset((page - 1) * per_page)\
           .limit(per_page)\
           .all()
       
       return tickets, total
   ```

3. **Actualizar Métodos Existentes**: Modificar `get_all_tickets()` para usar paginación por defecto

**File**: `app/rutas/ticket_ruta.py`

**Specific Changes**:
1. **Agregar Parámetros de Paginación**: Actualizar endpoints para aceptar `page` y `per_page`
   ```python
   @router.get("/tickets")
   async def get_tickets(
       page: int = Query(1, ge=1),
       per_page: int = Query(50, ge=1, le=100),
       estado: str = None,
       db: Session = Depends(get_db)
   ):
       tickets, total = ticket_service.get_tickets_paginated(db, page, per_page, estado)
       return {
           "tickets": tickets,
           "total": total,
           "page": page,
           "per_page": per_page,
           "pages": (total + per_page - 1) // per_page
       }
   ```

**Script de Migración**: `scripts/apply_db_indexes.sh`
```bash
#!/bin/bash
psql -U $DB_USER -d $DB_NAME -f db/migrations/add_composite_indexes.sql
```

---

### 4. Implementación de Tests Frontend/Móvil

**A. Tests Frontend**

**File**: `frontend/package.json`

**Specific Changes**:
1. **Agregar Dependencias de Testing**:
   ```json
   {
     "devDependencies": {
       "vitest": "^2.0.0",
       "@testing-library/react": "^16.0.0",
       "@testing-library/jest-dom": "^6.0.0",
       "@testing-library/user-event": "^14.0.0"
     },
     "scripts": {
       "test": "vitest",
       "test:ui": "vitest --ui",
       "test:coverage": "vitest --coverage"
     }
   }
   ```

**File**: `frontend/vite.config.js`

**Specific Changes**:
1. **Configurar Vitest**:
   ```javascript
   import { defineConfig } from 'vite'
   import react from '@vitejs/plugin-react'
   
   export default defineConfig({
     plugins: [react()],
     test: {
       globals: true,
       environment: 'jsdom',
       setupFiles: './src/test/setup.js',
       coverage: {
         provider: 'v8',
         reporter: ['text', 'json', 'html'],
         exclude: ['node_modules/', 'src/test/']
       }
     },
   })
   ```

**File**: `frontend/src/test/setup.js` (nuevo)

**Specific Changes**:
1. **Configurar Testing Library**:
   ```javascript
   import '@testing-library/jest-dom'
   import { cleanup } from '@testing-library/react'
   import { afterEach } from 'vitest'
   
   afterEach(() => {
     cleanup()
   })
   ```

**File**: `frontend/src/__tests__/LoginPage.test.jsx` (nuevo)

**Specific Changes**:
1. **Crear Tests de LoginPage**:
   ```javascript
   import { render, screen, fireEvent, waitFor } from '@testing-library/react'
   import { BrowserRouter } from 'react-router-dom'
   import { vi } from 'vitest'
   import LoginPage from '../pages/LoginPage'
   import authService from '../services/authService'
   
   vi.mock('../services/authService')
   
   describe('LoginPage', () => {
     test('muestra error con credenciales inválidas', async () => {
       authService.login.mockRejectedValue(new Error('Credenciales inválidas'))
       
       render(
         <BrowserRouter>
           <LoginPage />
         </BrowserRouter>
       )
       
       fireEvent.change(screen.getByPlaceholderText('Usuario'), {
         target: { value: 'admin' }
       })
       fireEvent.change(screen.getByPlaceholderText('Contraseña'), {
         target: { value: 'wrong' }
       })
       fireEvent.click(screen.getByText('Iniciar Sesión'))
       
       await waitFor(() => {
         expect(screen.getByText(/credenciales inválidas/i)).toBeInTheDocument()
       })
     })
     
     test('redirige al dashboard con credenciales válidas', async () => {
       authService.login.mockResolvedValue({
         access_token: 'token123',
         user: { username: 'admin', roles: ['ADMIN'] }
       })
       
       render(
         <BrowserRouter>
           <LoginPage />
         </BrowserRouter>
       )
       
       fireEvent.change(screen.getByPlaceholderText('Usuario'), {
         target: { value: 'admin' }
       })
       fireEvent.change(screen.getByPlaceholderText('Contraseña'), {
         target: { value: 'Admin123' }
       })
       fireEvent.click(screen.getByText('Iniciar Sesión'))
       
       await waitFor(() => {
         expect(window.location.pathname).toBe('/')
       })
     })
   })
   ```

**Files**: `frontend/src/__tests__/ProtectedRoute.test.jsx`, `frontend/src/__tests__/authService.test.js` (nuevos)

**Specific Changes**:
1. **Crear Tests Adicionales**: Tests para ProtectedRoute, servicios, componentes críticos

**B. Tests E2E**

**File**: `e2e/package.json` (nuevo)

**Specific Changes**:
1. **Configurar Playwright**:
   ```json
   {
     "name": "e2e-tests",
     "devDependencies": {
       "@playwright/test": "^1.47.0"
     },
     "scripts": {
       "test:e2e": "playwright test",
       "test:e2e:ui": "playwright test --ui"
     }
   }
   ```

**File**: `e2e/playwright.config.js` (nuevo)

**Specific Changes**:
1. **Configurar Playwright**:
   ```javascript
   import { defineConfig } from '@playwright/test'
   
   export default defineConfig({
     testDir: './tests',
     use: {
       baseURL: 'http://localhost:8000',
       screenshot: 'only-on-failure',
       video: 'retain-on-failure',
     },
     webServer: {
       command: 'cd .. && npm run dev',
       port: 8000,
       reuseExistingServer: true,
     },
   })
   ```

**File**: `e2e/tests/login.spec.js` (nuevo)

**Specific Changes**:
1. **Crear Tests E2E de Login**:
   ```javascript
   import { test, expect } from '@playwright/test'
   
   test.describe('Login Flow', () => {
     test('login exitoso redirige al dashboard', async ({ page }) => {
       await page.goto('/login')
       
       await page.fill('input[name="username"]', 'admin')
       await page.fill('input[name="password"]', 'Admin123')
       await page.click('button[type="submit"]')
       
       await expect(page).toHaveURL('/')
       await expect(page.locator('text=Recepcion')).toBeVisible()
     })
     
     test('login fallido muestra error', async ({ page }) => {
       await page.goto('/login')
       
       await page.fill('input[name="username"]', 'admin')
       await page.fill('input[name="password"]', 'wrong')
       await page.click('button[type="submit"]')
       
       await expect(page.locator('text=/error|inválid/i')).toBeVisible()
     })
   })
   ```

**Files**: `e2e/tests/tickets.spec.js`, `e2e/tests/payments.spec.js` (nuevos)

**Specific Changes**:
1. **Crear Tests E2E Adicionales**: Tests para crear ticket, cobro, búsqueda, logout

**C. Tests App Móvil**

**File**: `mobile_app/package.json`

**Specific Changes**:
1. **Agregar Dependencias de Testing**:
   ```json
   {
     "devDependencies": {
       "@testing-library/react-native": "^12.0.0",
       "jest": "^29.0.0",
       "@testing-library/jest-native": "^5.0.0"
     },
     "scripts": {
       "test": "jest",
       "test:coverage": "jest --coverage"
     }
   }
   ```

**File**: `mobile_app/jest.config.js` (nuevo)

**Specific Changes**:
1. **Configurar Jest**:
   ```javascript
   module.exports = {
     preset: 'react-native',
     setupFilesAfterEnv: ['@testing-library/jest-native/extend-expect'],
     transformIgnorePatterns: [
       'node_modules/(?!(react-native|@react-native|expo|@expo)/)',
     ],
     collectCoverageFrom: [
       'src/**/*.{js,jsx}',
       '!src/**/*.test.{js,jsx}',
     ],
   }
   ```

**File**: `mobile_app/src/__tests__/LoginScreen.test.js` (nuevo)

**Specific Changes**:
1. **Crear Tests de LoginScreen**:
   ```javascript
   import { render, fireEvent, waitFor } from '@testing-library/react-native'
   import LoginScreen from '../screens/LoginScreen'
   import authService from '../services/authService'
   
   jest.mock('../services/authService')
   
   describe('LoginScreen', () => {
     test('muestra error con credenciales inválidas', async () => {
       authService.login.mockRejectedValue(new Error('Credenciales inválidas'))
       
       const { getByPlaceholderText, getByText, findByText } = render(
         <LoginScreen navigation={{}} />
       )
       
       fireEvent.changeText(getByPlaceholderText('Usuario'), 'admin')
       fireEvent.changeText(getByPlaceholderText('Contraseña'), 'wrong')
       fireEvent.press(getByText('Iniciar Sesión'))
       
       expect(await findByText(/credenciales inválidas/i)).toBeTruthy()
     })
   })
   ```

**Files**: `mobile_app/src/__tests__/HomeScreen.test.js`, `mobile_app/src/__tests__/authService.test.js` (nuevos)

**Specific Changes**:
1. **Crear Tests Adicionales**: Tests para HomeScreen, TicketListScreen, servicios

---

### 5. Forzado de HTTPS en Producción

**File**: `app/main.py`

**Specific Changes**:
1. **Agregar Middleware HTTPS**: Importar y configurar `HTTPSRedirectMiddleware`
   ```python
   from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
   from fastapi.middleware.trustedhost import TrustedHostMiddleware
   import os
   
   # Después de crear app
   if os.getenv("ENVIRONMENT") == "production":
       # Redirigir HTTP → HTTPS
       app.add_middleware(HTTPSRedirectMiddleware)
       
       # Validar host
       allowed_hosts = os.getenv("ALLOWED_HOSTS", "").split(",")
       if allowed_hosts:
           app.add_middleware(
               TrustedHostMiddleware,
               allowed_hosts=[h.strip() for h in allowed_hosts if h.strip()]
           )
   ```

**File**: `app/rutas/auth_ruta.py`

**Function**: `login` (configuración de cookies)

**Specific Changes**:
1. **Configurar Cookies Seguras**: Agregar flags de seguridad
   ```python
   # Antes
   response.set_cookie(
       key="refresh_token",
       value=refresh_token,
       httponly=True,
       samesite="lax",
       max_age=7*24*60*60
   )
   
   # Después
   is_production = os.getenv("ENVIRONMENT") == "production"
   response.set_cookie(
       key="refresh_token",
       value=refresh_token,
       httponly=True,
       secure=is_production,  # ✅ Solo HTTPS en producción
       samesite="strict",     # ✅ Protección CSRF
       max_age=7*24*60*60
   )
   ```

**File**: `.env.example`

**Specific Changes**:
1. **Documentar Variables de Entorno**:
   ```env
   # HTTPS Configuration
   ENVIRONMENT=production
   ALLOWED_HOSTS=taller.com,*.taller.com
   ```

---

### 6. Protección CSRF

**File**: `requirements.txt`

**Specific Changes**:
1. **Agregar Dependencia CSRF**:
   ```
   fastapi-csrf-protect==0.3.4
   ```

**File**: `app/main.py`

**Specific Changes**:
1. **Configurar CSRF Protection**:
   ```python
   from fastapi_csrf_protect import CsrfProtect
   from fastapi_csrf_protect.exceptions import CsrfProtectError
   from pydantic import BaseModel
   
   class CsrfSettings(BaseModel):
       secret_key: str = os.getenv("CSRF_SECRET_KEY", "your-secret-key-here")
       cookie_samesite: str = "strict"
       cookie_secure: bool = os.getenv("ENVIRONMENT") == "production"
   
   @CsrfProtect.load_config
   def get_csrf_config():
       return CsrfSettings()
   
   @app.exception_handler(CsrfProtectError)
   def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
       return JSONResponse(
           status_code=403,
           content={"detail": "CSRF token validation failed"}
       )
   ```

**File**: `app/rutas/ticket_ruta.py`

**Specific Changes**:
1. **Agregar Validación CSRF en Endpoints de Escritura**:
   ```python
   from fastapi_csrf_protect import CsrfProtect
   
   @router.post("/tickets")
   async def create_ticket(
       ticket_data: TicketCreate,
       csrf_protect: CsrfProtect = Depends(),
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       await csrf_protect.validate_csrf(request)
       # ... resto del código
   ```

2. **Aplicar a Todos los Endpoints POST/PUT/DELETE**: Agregar validación CSRF en todos los endpoints de escritura

**File**: `frontend/src/services/api.js`

**Specific Changes**:
1. **Incluir Token CSRF en Peticiones**:
   ```javascript
   // Obtener token CSRF del cookie
   const getCsrfToken = () => {
     const match = document.cookie.match(/fastapi-csrf-token=([^;]+)/)
     return match ? match[1] : null
   }
   
   // Agregar a headers
   const api = axios.create({
     baseURL: import.meta.env.VITE_API_URL,
     headers: {
       'Content-Type': 'application/json',
     },
   })
   
   api.interceptors.request.use((config) => {
     const csrfToken = getCsrfToken()
     if (csrfToken && ['post', 'put', 'delete', 'patch'].includes(config.method)) {
       config.headers['X-CSRF-Token'] = csrfToken
     }
     return config
   })
   ```

**File**: `.env.example`

**Specific Changes**:
1. **Documentar Variable CSRF**:
   ```env
   # CSRF Protection
   CSRF_SECRET_KEY=your-secret-key-here-change-in-production
   ```

---

### 7. Implementación de Caché con Redis

**File**: `requirements.txt`

**Specific Changes**:
1. **Agregar Dependencias de Redis**:
   ```
   redis==5.2.0
   fastapi-cache2[redis]==0.2.2
   ```

**File**: `docker-compose.yml` (nuevo)

**Specific Changes**:
1. **Agregar Servicio Redis**:
   ```yaml
   version: '3.8'
   services:
     redis:
       image: redis:7-alpine
       ports:
         - "6379:6379"
       volumes:
         - redis_data:/data
       command: redis-server --appendonly yes
   
   volumes:
     redis_data:
   ```

**File**: `app/configuracion/cache.py` (nuevo)

**Specific Changes**:
1. **Configurar FastAPI Cache**:
   ```python
   from fastapi_cache import FastAPICache
   from fastapi_cache.backends.redis import RedisBackend
   from redis import asyncio as aioredis
   import os
   
   async def init_cache():
       redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
       redis = aioredis.from_url(
           redis_url, 
           encoding="utf8", 
           decode_responses=True
       )
       FastAPICache.init(RedisBackend(redis), prefix="taller-cache:")
   ```

**File**: `app/main.py`

**Specific Changes**:
1. **Inicializar Caché en Startup**:
   ```python
   from contextlib import asynccontextmanager
   from app.configuracion.cache import init_cache
   
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Inicializar cache
       await init_cache()
       yield
       # Cleanup si es necesario
   
   app = FastAPI(lifespan=lifespan)
   ```

**File**: `app/rutas/economia_ruta.py`

**Specific Changes**:
1. **Agregar Caché a Endpoints de Lectura**:
   ```python
   from fastapi_cache.decorator import cache
   
   @router.get("/estadisticas")
   @cache(expire=300)  # 5 minutos
   async def get_estadisticas(
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       return await economia_service.get_estadisticas(db)
   ```

2. **Invalidar Caché en Escritura**:
   ```python
   from fastapi_cache import FastAPICache
   
   @router.post("/movimientos")
   async def create_movimiento(...):
       movimiento = await movimiento_service.create(...)
       
       # Invalidar cache de estadísticas
       await FastAPICache.clear(namespace="estadisticas")
       
       return movimiento
   ```

**File**: `.env.example`

**Specific Changes**:
1. **Documentar Variable Redis**:
   ```env
   # Redis Cache
   REDIS_URL=redis://localhost:6379
   ```


## Testing Strategy

### Validation Approach

La estrategia de testing sigue un enfoque de tres fases para cada categoría de corrección:

1. **Exploratory Bug Condition Checking**: Verificar que los problemas existen en el código sin corregir
2. **Fix Checking**: Verificar que las correcciones resuelven los problemas identificados
3. **Preservation Checking**: Verificar que la funcionalidad existente no se ha roto

Dado que este bugfix aborda 7 problemas independientes, la estrategia se divide en 7 secciones correspondientes.

---

### 1. Exploratory Bug Condition Checking - Dependencias Vulnerables

**Goal**: Confirmar que las dependencias actuales tienen CVEs conocidos ANTES de actualizar.

**Test Plan**: Ejecutar `safety check` en el código sin corregir para observar las vulnerabilidades reportadas.

**Test Cases**:
1. **Verificar CVEs en Werkzeug**: Ejecutar `pip show werkzeug` y verificar versión 3.1.3 (fallará con CVEs)
2. **Verificar CVEs en Flask**: Ejecutar `pip show flask` y verificar versión 3.1.2 (fallará con CVEs)
3. **Verificar CVEs en pip**: Ejecutar `pip --version` y verificar versión 25.2 (fallará con CVEs)
4. **Verificar CVEs en ecdsa**: Ejecutar `pip show ecdsa` y verificar versión 0.19.1 (fallará con CVEs)
5. **Safety Check**: Ejecutar `safety check` y observar 5 vulnerabilidades críticas

**Expected Counterexamples**:
- `safety check` reportará CVE-2026-27199, CVE-2025-66221, CVE-2026-21860 en Werkzeug
- `safety check` reportará CVE-2026-27205 en Flask
- `safety check` reportará CVE-2026-1703 en pip
- `safety check` reportará CVE-2024-23342 en ecdsa

---

### 2. Exploratory Bug Condition Checking - CORS Mal Configurado

**Goal**: Confirmar que CORS acepta peticiones desde cualquier origen ANTES de corregir.

**Test Plan**: Enviar peticiones desde orígenes no autorizados y observar que son aceptadas.

**Test Cases**:
1. **Petición desde Origen Malicioso**: Enviar petición con header `Origin: https://sitio-malicioso.com` (será aceptada en código sin corregir)
2. **Verificar Configuración**: Inspeccionar `app/main.py` línea 340 y confirmar `_origins = ["*"]`
3. **Verificar Headers de Respuesta**: Confirmar que `Access-Control-Allow-Origin: *` está presente

**Expected Counterexamples**:
- Peticiones desde cualquier origen son aceptadas
- Header `Access-Control-Allow-Origin: *` está presente en respuestas
- No hay validación de origen en el código

---

### 3. Exploratory Bug Condition Checking - Base de Datos Sin Optimizar

**Goal**: Confirmar que las consultas son lentas y no usan índices ANTES de optimizar.

**Test Plan**: Ejecutar `EXPLAIN ANALYZE` en consultas frecuentes y medir tiempo de respuesta.

**Test Cases**:
1. **Consulta de Tickets sin Índice**: Ejecutar `EXPLAIN ANALYZE SELECT * FROM tickets WHERE estado='ABIERTO' AND fecha_ingreso > '2026-01-01' ORDER BY fecha_ingreso DESC` (mostrará Seq Scan)
2. **Medir Latencia**: Usar `ab` o `wrk` para medir latencia de `/tickets?estado=ABIERTO` (>500ms esperado)
3. **Verificar N+1 Queries**: Habilitar logging de SQL y observar múltiples queries al cargar tickets con relaciones
4. **Verificar Sin Paginación**: Llamar `/tickets` sin parámetros y observar que retorna todos los registros

**Expected Counterexamples**:
- `EXPLAIN ANALYZE` muestra `Seq Scan` en lugar de `Index Scan`
- Latencia >500ms en consultas con filtros
- Logs muestran N+1 queries (1 + N queries por cada relación)
- Endpoint retorna miles de registros sin límite

---

### 4. Exploratory Bug Condition Checking - Sin Tests Frontend/Móvil

**Goal**: Confirmar que no existen tests en frontend/móvil ANTES de implementarlos.

**Test Plan**: Buscar archivos de test y ejecutar comandos de test.

**Test Cases**:
1. **Buscar Tests Frontend**: Ejecutar `find frontend/src -name "*.test.jsx"` (no encontrará archivos)
2. **Ejecutar Tests Frontend**: Ejecutar `cd frontend && npm test` (fallará con "no test script")
3. **Verificar Cobertura**: Ejecutar `cd frontend && npm run test:coverage` (fallará)
4. **Buscar Tests Móvil**: Ejecutar `find mobile_app/src -name "*.test.js"` (no encontrará archivos)
5. **Buscar Tests E2E**: Buscar carpeta `e2e/` (no existirá)

**Expected Counterexamples**:
- No existen archivos `*.test.jsx` o `*.test.js`
- No existe configuración de Vitest o Jest
- No existe carpeta `e2e/` con tests de Playwright
- Cobertura de tests es 0%

---

### 5. Exploratory Bug Condition Checking - Sin HTTPS Forzado

**Goal**: Confirmar que el sistema no redirige HTTP a HTTPS ANTES de implementar.

**Test Plan**: Acceder por HTTP y verificar que no hay redirección.

**Test Cases**:
1. **Acceso HTTP**: Acceder a `http://localhost:8000/login` (no redirigirá a HTTPS)
2. **Verificar Middleware**: Inspeccionar `app/main.py` y confirmar que no existe `HTTPSRedirectMiddleware`
3. **Verificar Cookies**: Inspeccionar cookies en DevTools y confirmar que `Secure` flag es `false`
4. **Verificar SameSite**: Confirmar que `SameSite` es `lax` en lugar de `strict`

**Expected Counterexamples**:
- Acceso HTTP no redirige a HTTPS
- Cookies no tienen flag `Secure=True`
- Cookies tienen `SameSite=lax` en lugar de `strict`
- No existe middleware de redirección HTTPS

---

### 6. Exploratory Bug Condition Checking - Sin Protección CSRF

**Goal**: Confirmar que endpoints POST/PUT/DELETE no validan tokens CSRF ANTES de implementar.

**Test Plan**: Enviar peticiones sin token CSRF y observar que son aceptadas.

**Test Cases**:
1. **POST sin Token CSRF**: Enviar `POST /tickets` sin header `X-CSRF-Token` (será aceptado)
2. **Verificar Dependencias**: Ejecutar `pip show fastapi-csrf-protect` (no estará instalado)
3. **Verificar Middleware**: Inspeccionar `app/main.py` y confirmar que no existe configuración CSRF
4. **Verificar Frontend**: Inspeccionar `frontend/src/services/api.js` y confirmar que no envía token CSRF

**Expected Counterexamples**:
- Peticiones POST/PUT/DELETE sin token CSRF son aceptadas
- No existe `fastapi-csrf-protect` en requirements.txt
- No existe middleware CSRF en app/main.py
- Frontend no envía header `X-CSRF-Token`

---

### 7. Exploratory Bug Condition Checking - Sin Caché

**Goal**: Confirmar que no existe caché y todas las peticiones consultan la base de datos ANTES de implementar.

**Test Plan**: Habilitar logging de SQL y observar queries repetidas.

**Test Cases**:
1. **Verificar Redis**: Ejecutar `docker ps | grep redis` (no habrá contenedor Redis)
2. **Verificar Dependencias**: Ejecutar `pip show fastapi-cache2` (no estará instalado)
3. **Habilitar SQL Logging**: Configurar SQLAlchemy con `echo=True` y observar queries repetidas
4. **Medir Latencia**: Llamar `/economia/estadisticas` 10 veces y observar que todas consultan la BD

**Expected Counterexamples**:
- No existe servicio Redis corriendo
- No existe `fastapi-cache2` en requirements.txt
- Logs muestran queries repetidas para las mismas peticiones
- Latencia es consistentemente alta (no hay mejora en peticiones repetidas)

---

### Fix Checking

**Goal**: Verificar que para todos los problemas identificados, las correcciones producen el comportamiento esperado.

**Pseudocode:**
```
FOR EACH problema IN [dependencias, cors, bd, tests, https, csrf, cache] DO
  APPLY corrección(problema)
  
  FOR ALL input WHERE isBugCondition(input, problema) DO
    result := sistema_corregido(input)
    ASSERT expectedBehavior(result, problema)
  END FOR
END FOR
```

**Test Plan por Categoría**:

**1. Dependencias Actualizadas**:
- Ejecutar `safety check` y verificar 0 vulnerabilidades críticas
- Verificar versiones: Werkzeug ≥3.1.7, Flask ≥3.1.3, pip ≥26.0.1, ecdsa ≥0.19.2
- Ejecutar suite de tests backend y verificar que todo pasa

**2. CORS Configurado**:
- Enviar petición desde origen no autorizado y verificar error CORS
- Enviar petición desde origen autorizado (en `ALLOWED_ORIGINS`) y verificar éxito
- Verificar que en producción sin `ALLOWED_ORIGINS` el sistema falla al iniciar

**3. Base de Datos Optimizada**:
- Ejecutar `EXPLAIN ANALYZE` y verificar uso de índices (`Index Scan`)
- Medir latencia de consultas y verificar <50ms
- Verificar que eager loading carga relaciones en 1 query
- Verificar que paginación limita resultados a 50 por defecto

**4. Tests Implementados**:
- Ejecutar `cd frontend && npm test` y verificar >60% cobertura
- Ejecutar `cd mobile_app && npm test` y verificar >50% cobertura
- Ejecutar `cd e2e && npm run test:e2e` y verificar 5 flujos pasan
- Modificar código y verificar que tests detectan regresiones

**5. HTTPS Forzado**:
- Acceder por HTTP en producción y verificar redirección a HTTPS
- Verificar cookies con flags `Secure=True`, `HttpOnly=True`, `SameSite=strict`
- Verificar que hosts no autorizados son rechazados

**6. CSRF Implementado**:
- Enviar POST/PUT/DELETE sin token CSRF y verificar error 403
- Enviar con token CSRF válido y verificar éxito
- Verificar que frontend incluye token en headers

**7. Caché Implementado**:
- Llamar `/economia/estadisticas` y verificar query a BD
- Llamar nuevamente y verificar respuesta desde Redis (sin query a BD)
- Crear movimiento y verificar que caché se invalida
- Verificar latencia reducida en peticiones cacheadas

---

### Preservation Checking

**Goal**: Verificar que para todas las funcionalidades existentes, el sistema corregido produce el mismo resultado que el sistema original.

**Pseudocode:**
```
FOR ALL funcionalidad IN [auth, rbac, audit, crud, pdf, payments, ...] DO
  FOR ALL input WHERE NOT isBugCondition(input) DO
    result_original := sistema_original(input)
    result_corregido := sistema_corregido(input)
    ASSERT result_original == result_corregido
  END FOR
END FOR
```

**Testing Approach**: Property-based testing es recomendado para preservation checking porque:
- Genera muchos casos de prueba automáticamente
- Cubre edge cases que tests manuales podrían omitir
- Proporciona garantías fuertes de que el comportamiento no ha cambiado

**Test Plan**: Observar comportamiento en código SIN CORREGIR primero, luego escribir tests que capturen ese comportamiento y verificar que continúa después de las correcciones.

**Test Cases**:

**1. Autenticación JWT**:
- Observar: Login con credenciales válidas genera access + refresh tokens
- Test: Verificar que después de correcciones, login sigue generando tokens idénticos
- Observar: Refresh token rotation funciona correctamente
- Test: Verificar que refresh sigue funcionando igual

**2. RBAC (Control de Acceso)**:
- Observar: Usuario ADMIN puede acceder a todos los endpoints
- Test: Verificar que ADMIN sigue teniendo acceso completo
- Observar: Usuario SOLO_LECTURA no puede crear/editar/eliminar
- Test: Verificar que SOLO_LECTURA sigue siendo rechazado en escritura

**3. Auditoría**:
- Observar: Login exitoso registra evento en audit_log con IP y user agent
- Test: Verificar que auditoría sigue registrando eventos idénticos
- Observar: Detección de brute force bloquea después de 5 intentos
- Test: Verificar que brute force sigue funcionando igual

**4. CRUD de Tickets**:
- Observar: Crear ticket con procesos y repuestos calcula total correctamente
- Test: Verificar que cálculo de total sigue siendo idéntico
- Observar: Actualizar estado de ticket funciona correctamente
- Test: Verificar que actualización sigue funcionando igual

**5. Generación de PDFs**:
- Observar: PDF incluye todos los datos (vehículo, procesos, repuestos, fotos)
- Test: Verificar que PDF generado es idéntico (mismo contenido)

**6. Registro de Pagos**:
- Observar: Registrar pago actualiza estado de ticket y crea movimiento en economía
- Test: Verificar que pago sigue actualizando estado y economía igual

**7. Validación de Contraseñas**:
- Observar: Contraseña con <8 caracteres es rechazada
- Test: Verificar que validación sigue rechazando contraseñas débiles
- Observar: Migración SHA256 → bcrypt funciona automáticamente
- Test: Verificar que migración sigue funcionando igual

**8. Rate Limiting**:
- Observar: 6 peticiones a /auth/login en 1 minuto son bloqueadas
- Test: Verificar que rate limiting sigue bloqueando igual

**9. Token Blacklist**:
- Observar: Logout agrega token a blacklist y rechaza peticiones posteriores
- Test: Verificar que blacklist sigue funcionando igual

**10. Frontend y Móvil**:
- Observar: Navegación entre páginas funciona correctamente
- Test: Verificar que navegación sigue funcionando igual
- Observar: Modo offline en móvil permite consultar datos sincronizados
- Test: Verificar que modo offline sigue funcionando igual

---

### Unit Tests

**Backend (Python)**:
- Test de actualización de dependencias: Verificar versiones correctas instaladas
- Test de configuración CORS: Verificar que orígenes se leen de variable de entorno
- Test de índices BD: Verificar que índices existen en base de datos
- Test de paginación: Verificar que repositorios retornan máximo 50 registros
- Test de eager loading: Verificar que relaciones se cargan en 1 query
- Test de HTTPS middleware: Verificar que redirección funciona en producción
- Test de cookies seguras: Verificar flags Secure, HttpOnly, SameSite
- Test de CSRF: Verificar que endpoints validan token
- Test de caché: Verificar que datos se cachean y se invalidan correctamente

**Frontend (JavaScript)**:
- Test de LoginPage: Verificar login exitoso y fallido
- Test de ProtectedRoute: Verificar redirección sin autenticación
- Test de authService: Verificar llamadas a API correctas
- Test de token CSRF: Verificar que se incluye en headers

**Móvil (JavaScript)**:
- Test de LoginScreen: Verificar login exitoso y fallido
- Test de HomeScreen: Verificar carga de datos
- Test de authService: Verificar llamadas a API correctas
- Test de modo offline: Verificar acceso a datos sincronizados

---

### Property-Based Tests

**Backend (Hypothesis)**:
- Generar usuarios aleatorios y verificar que autenticación funciona correctamente
- Generar tickets aleatorios y verificar que CRUD funciona correctamente
- Generar peticiones con orígenes aleatorios y verificar que CORS valida correctamente
- Generar peticiones con/sin token CSRF y verificar que validación funciona
- Generar consultas con filtros aleatorios y verificar que paginación funciona

**Frontend (fast-check)**:
- Generar credenciales aleatorias y verificar que validación funciona
- Generar datos de formularios aleatorios y verificar que validación funciona

---

### Integration Tests

**Flujos Completos**:
- Test de flujo completo de login → crear ticket → agregar procesos → cobrar → logout
- Test de flujo de búsqueda de tickets con filtros y paginación
- Test de flujo de generación de PDF con todos los datos
- Test de flujo de auditoría: login → acción → verificar registro en audit_log
- Test de flujo de caché: consulta → verificar BD → consulta repetida → verificar Redis
- Test de flujo CSRF: obtener token → enviar petición → verificar éxito
- Test de flujo HTTPS: acceso HTTP → verificar redirección → verificar cookies seguras

**Tests E2E (Playwright)**:
- Test de login completo con redirección al dashboard
- Test de crear ticket con procesos y repuestos
- Test de cobro de ticket con actualización de estado
- Test de búsqueda de tickets con filtros
- Test de logout con invalidación de sesión

**Tests de Carga**:
- Test de 100 peticiones concurrentes a `/tickets` con paginación
- Test de 100 peticiones concurrentes a `/economia/estadisticas` con caché
- Test de rate limiting con 10 peticiones simultáneas a `/auth/login`

---

### Métricas de Éxito

**Seguridad**:
- ✅ 0 vulnerabilidades críticas en `safety check`
- ✅ CORS rechaza orígenes no autorizados
- ✅ HTTPS forzado en producción
- ✅ CSRF protege todos los endpoints de escritura

**Rendimiento**:
- ✅ Consultas con índices <50ms (mejora 10x)
- ✅ Caché reduce latencia 80% en peticiones repetidas
- ✅ Paginación previene timeouts

**Calidad**:
- ✅ Frontend: >60% cobertura de tests
- ✅ Móvil: >50% cobertura de tests
- ✅ E2E: 5 flujos críticos cubiertos
- ✅ Backend: Mantener >50% cobertura

**Preservación**:
- ✅ Todos los tests existentes siguen pasando
- ✅ API retorna mismas estructuras de respuesta
- ✅ Frontend y móvil funcionan sin cambios visibles
- ✅ Auditoría registra eventos idénticos

