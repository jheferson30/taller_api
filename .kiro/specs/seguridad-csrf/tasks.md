# Implementation Plan: Seguridad CSRF y Headers HTTP

## Overview

Este plan implementa protección CSRF completa y headers de seguridad HTTP en el sistema SaaS multi-tenant. La implementación se divide en tres fases: backend (CSRF + headers), frontend (interceptores axios), y testing (unitarios + property-based tests).

**Lenguaje de implementación:** Python (FastAPI) para backend, JavaScript para frontend

**Archivos principales a crear/modificar:**
- Backend: `csrf_middleware.py`, `security_headers_middleware.py`, `main.py`, `requirements.txt`
- Frontend: `api.js`
- Tests: `test_csrf_middleware.py`, `test_security_headers.py`, `test_csrf_properties.py`

## Tasks

- [x] 1. Configurar dependencias y validación de secretos
  - [x] 1.1 Agregar fastapi-csrf-protect a requirements.txt
    - Agregar `fastapi-csrf-protect==0.5.0` como dependencia pinned
    - _Requirements: 1.1_
  
  - [x] 1.2 Agregar validación de CSRF_SECRET_KEY en main.py
    - Modificar función `_validate_required_secrets()` para incluir `("csrf-secret-key", "CSRF_SECRET_KEY")`
    - Garantizar que la aplicación no arranca si falta la variable de entorno
    - _Requirements: 1.7_

- [x] 2. Implementar Security Headers Middleware
  - [x] 2.1 Crear app/seguridad/security_headers_middleware.py
    - Implementar middleware ASGI puro (no BaseHTTPMiddleware) para máximo rendimiento
    - Definir `SECURITY_HEADERS_ALWAYS` con X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Content-Security-Policy
    - Definir `SECURITY_HEADERS_PRODUCTION` con Strict-Transport-Security
    - Detectar entorno de producción con `os.getenv("ENVIRONMENT") == "production"`
    - Agregar headers usando `MutableHeaders` en el mensaje `http.response.start`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [ ]* 2.2 Escribir tests unitarios para security headers
    - Crear `tests/test_security_headers.py`
    - Verificar presencia de todos los headers en respuestas GET y POST
    - Verificar que HSTS solo aparece en producción
    - Verificar valores exactos de cada header
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 3. Implementar CSRF Middleware
  - [x] 3.1 Crear app/seguridad/csrf_middleware.py
    - Implementar `CSRFMiddleware` usando `BaseHTTPMiddleware`
    - Definir `CSRF_EXEMPT_PATHS` con rutas exentas: /auth/login, /auth/refresh, /auth/forgot-password, /auth/forgot-password-by-username, /auth/reset-password, /health, /info, /info/conexion-qr, /docs, /redoc, /openapi.json, /whatsapp/webhook
    - Definir `CSRF_WRITE_METHODS` = {POST, PUT, PATCH, DELETE}
    - Validar token CSRF solo en métodos de escritura no exentos
    - Leer token del header `X-CSRF-Token`
    - Retornar HTTP 403 con mensaje "CSRF token missing or invalid" si falta o es inválido
    - Saltar validación para OPTIONS (preflight CORS)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  
  - [ ]* 3.2 Escribir tests unitarios para CSRF middleware
    - Crear `tests/test_csrf_middleware.py`
    - Verificar que métodos GET/HEAD pasan sin token
    - Verificar que POST/PUT/PATCH/DELETE sin token retornan 403
    - Verificar que rutas exentas pasan sin token
    - Verificar que token válido permite el request
    - Verificar que token inválido retorna 403
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

- [x] 4. Configurar CsrfProtect en main.py
  - [x] 4.1 Agregar configuración de CsrfProtect
    - Importar `CsrfProtect` y `CsrfProtectError` de fastapi-csrf-protect
    - Crear función `get_csrf_config()` decorada con `@CsrfProtect.load_config`
    - Configurar: secret_key (desde env), cookie_samesite=strict, cookie_secure (solo en producción), cookie_httponly=True, token_location=headers, header_name=X-CSRF-Token, header_type="" (sin prefijo)
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6_
  
  - [x] 4.2 Registrar middlewares en orden correcto
    - Agregar `SecurityHeadersMiddleware` PRIMERO (ejecuta último)
    - Agregar `CSRFMiddleware` DESPUÉS (ejecuta antes que SecurityHeaders)
    - Documentar que add_middleware se ejecuta en orden inverso
    - _Requirements: 4.7_
  
  - [x] 4.3 Agregar handler de excepción CsrfProtectError
    - Crear `@app.exception_handler(CsrfProtectError)`
    - Retornar JSONResponse con status 403 y mensaje "CSRF token missing or invalid"
    - _Requirements: 2.5, 2.6_

- [x] 5. Checkpoint - Verificar backend funciona sin romper nada
  - Ejecutar `pytest tests/ -x` para verificar que todos los tests pasan
  - Verificar que el servidor arranca sin errores con `docker-compose up`
  - Agregar `CSRF_SECRET_KEY` a `.env` local para desarrollo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Integrar CSRF en frontend (api.js)
  - [x] 6.1 Agregar función getCookie() a frontend/src/api.js
    - Implementar función helper que lee cookies por nombre
    - Retornar null si la cookie no existe
    - _Requirements: 3.1_
  
  - [x] 6.2 Agregar interceptor de request para CSRF
    - Definir constante `WRITE_METHODS` = {post, put, patch, delete}
    - Crear interceptor de axios que lee cookie `csrftoken` con `getCookie()`
    - Agregar header `X-CSRF-Token` en todos los métodos de escritura
    - _Requirements: 3.2, 3.3, 3.4, 3.5_
  
  - [x] 6.3 Agregar interceptor de response para retry automático
    - Detectar error 403 con `error.response?.data?.error === 'csrf_error'`
    - Refrescar token leyendo cookie actualizada
    - Reintentar request original exactamente una vez con flag `_csrfRetry`
    - Propagar error si el retry también falla
    - _Requirements: 3.6, 3.7_

- [x] 7. Checkpoint - Verificar integración frontend-backend
  - Abrir la app en el browser y hacer login
  - Crear un ticket nuevo (POST)
  - Actualizar un ticket existente (PUT/PATCH)
  - Eliminar un proceso (DELETE)
  - Verificar que no hay errores de consola relacionados con CSRF
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implementar property-based tests
  - [x] 8.1 Escribir property test para CSRF enforcement
    - **Property 1: CSRF Enforcement en Endpoints de Escritura**
    - **Valida: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
    - Crear `tests/test_csrf_properties.py`
    - Definir lista de endpoints de escritura representativos: POST /tickets/{id}/procesos, PUT /tickets/{id}/finanzas, PATCH /tickets/{id}/asignar-mecanico, DELETE /tickets/{id}/procesos/{id}, POST /vehiculos/, PUT /configuracion/taller, POST /upload/foto
    - Usar `@given(endpoint=st.sampled_from(WRITE_ENDPOINTS))`
    - Verificar que request sin X-CSRF-Token retorna 403 con error "csrf_error"
    - Usar JWT válido pero sin token CSRF
  
  - [x] 8.2 Escribir property test para security headers
    - **Property 2: Presencia de Headers de Seguridad**
    - **Valida: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
    - Agregar a `tests/test_csrf_properties.py`
    - Usar `@given(endpoint=st.sampled_from(["/", "/health", "/tickets/abiertos", "/auth/login"]), method=st.sampled_from(["GET", "POST"]))`
    - Verificar presencia de X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Content-Security-Policy
    - Verificar valores exactos de cada header

- [x] 9. Final checkpoint - Verificación completa
  - Ejecutar suite completa de tests: `pytest tests/ -v`
  - Verificar que todos los tests unitarios y property tests pasan
  - Verificar que el sistema funciona correctamente en desarrollo y producción
  - Verificar que los endpoints exentos funcionan sin CSRF
  - Verificar que la app móvil sigue funcionando (si aplica)
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- El orden de registro de middlewares en FastAPI es crítico: se ejecutan en orden inverso
- La implementación no requiere cambios en ningún route handler existente
- Los interceptores de axios garantizan cobertura total sin modificar las ~50 funciones del objeto `api`
- La lista de rutas exentas incluye endpoints públicos, de autenticación y webhooks externos
- El CSP incluye `'unsafe-inline'` para estilos porque Vite lo requiere en desarrollo
- En producción, HSTS se agrega automáticamente detectando `ENVIRONMENT=production`
