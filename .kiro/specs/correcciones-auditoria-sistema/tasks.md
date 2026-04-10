# Plan de Implementación - Correcciones Auditoría Sistema

## Fase 1: Exploración del Bug (ANTES de implementar correcciones)

### 1. Verificar Dependencias Vulnerables

- [x] 1.1 Escribir test de exploración para dependencias vulnerables
  - **Property 1: Bug Condition** - Dependencias con CVEs Conocidos
  - **CRÍTICO**: Este test DEBE FALLAR en código sin corregir - el fallo confirma que el bug existe
  - **NO intentar corregir el test o el código cuando falle**
  - **NOTA**: Este test codifica el comportamiento esperado - validará la corrección cuando pase después de la implementación
  - **OBJETIVO**: Demostrar que las dependencias actuales tienen vulnerabilidades conocidas
  - **Enfoque PBT Acotado**: Verificar versiones específicas conocidas como vulnerables
  - Implementar test que verifica versiones de dependencias y ejecuta `safety check`
  - Test debe verificar: Werkzeug==3.1.3, Flask==3.1.2, pip==25.2, ecdsa==0.19.1
  - Test debe ejecutar `safety check` y verificar que reporta 5 CVEs críticos
  - Ejecutar test en código SIN CORREGIR
  - **RESULTADO ESPERADO**: Test FALLA (esto es correcto - prueba que el bug existe)
  - Documentar CVEs encontrados: CVE-2026-27199, CVE-2025-66221, CVE-2026-21860, CVE-2026-27205, CVE-2026-1703, CVE-2024-23342
  - Marcar tarea completa cuando test esté escrito, ejecutado, y fallo documentado
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 1.2 Escribir test de exploración para CORS mal configurado
  - **Property 1: Bug Condition** - CORS Acepta Cualquier Origen
  - **CRÍTICO**: Este test DEBE FALLAR en código sin corregir
  - **OBJETIVO**: Demostrar que CORS acepta peticiones desde orígenes no autorizados
  - Implementar test que envía petición con header `Origin: https://sitio-malicioso.com`
  - Test debe verificar que petición es aceptada (comportamiento incorrecto)
  - Test debe verificar que `app/main.py` línea 340 contiene `_origins = ["*"]`
  - Ejecutar test en código SIN CORREGIR
  - **RESULTADO ESPERADO**: Test FALLA (confirma que CORS está mal configurado)
  - Documentar contraejemplos: peticiones desde cualquier origen son aceptadas
  - _Requirements: 1.5, 1.6_

- [x] 1.3 Escribir test de exploración para base de datos sin optimizar
  - **Property 1: Bug Condition** - Consultas Lentas Sin Índices
  - **CRÍTICO**: Este test DEBE FALLAR en código sin corregir
  - **OBJETIVO**: Demostrar que consultas son lentas y no usan índices
  - Implementar test que ejecuta `EXPLAIN ANALYZE` en consultas frecuentes
  - Test debe verificar: consulta de tickets por estado+fecha muestra `Seq Scan`
  - Test debe medir latencia de `/tickets?estado=ABIERTO` y verificar >500ms
  - Test debe habilitar SQL logging y contar queries (N+1 problem)
  - Test debe verificar que `/tickets` sin parámetros retorna todos los registros
  - Ejecutar test en código SIN CORREGIR
  - **RESULTADO ESPERADO**: Test FALLA (confirma problemas de rendimiento)
  - Documentar contraejemplos: Seq Scan, latencia >500ms, N+1 queries, sin paginación
  - _Requirements: 1.7, 1.8, 1.9, 1.10_

- [x] 1.4 Escribir test de exploración para ausencia de tests frontend/móvil
  - **Property 1: Bug Condition** - Cobertura de Tests 0%
  - **CRÍTICO**: Este test DEBE FALLAR en código sin corregir
  - **OBJETIVO**: Demostrar que no existen tests en frontend/móvil
  - Implementar test que busca archivos `*.test.jsx` en `frontend/src`
  - Test debe verificar que no existe `vitest.config.js`
  - Test debe buscar archivos `*.test.js` en `mobile_app/src`
  - Test debe verificar que no existe carpeta `e2e/`
  - Ejecutar test en código SIN CORREGIR
  - **RESULTADO ESPERADO**: Test FALLA (confirma ausencia de tests)
  - Documentar contraejemplos: 0 archivos de test encontrados
  - _Requirements: 1.11, 1.12, 1.13_

- [x] 1.5 Escribir test de exploración para HTTPS no forzado
  - **Property 1: Bug Condition** - HTTP No Redirige a HTTPS
  - **CRÍTICO**: Este test DEBE FALLAR en código sin corregir
  - **OBJETIVO**: Demostrar que sistema no fuerza HTTPS en producción
  - Implementar test que accede a `http://localhost:8000/login`
  - Test debe verificar que no hay redirección a HTTPS
  - Test debe verificar que `app/main.py` no contiene `HTTPSRedirectMiddleware`
  - Test debe inspeccionar cookies y verificar que `Secure` flag es `False`
  - Test debe verificar que `SameSite` es `lax` en lugar de `strict`
  - Ejecutar test en código SIN CORREGIR
  - **RESULTADO ESPERADO**: Test FALLA (confirma falta de HTTPS forzado)
  - Documentar contraejemplos: sin redirección, cookies inseguras
  - _Requirements: 1.14, 1.15, 1.16_

- [x] 1.6 Escribir test de exploración para ausencia de protección CSRF
  - **Property 1: Bug Condition** - Sin Validación CSRF
  - **CRÍTICO**: Este test DEBE FALLAR en código sin corregir
  - **OBJETIVO**: Demostrar que endpoints no validan tokens CSRF
  - Implementar test que envía `POST /tickets` sin header `X-CSRF-Token`
  - Test debe verificar que petición es aceptada (comportamiento incorrecto)
  - Test debe verificar que `fastapi-csrf-protect` no está en requirements.txt
  - Test debe verificar que `app/main.py` no contiene configuración CSRF
  - Ejecutar test en código SIN CORREGIR
  - **RESULTADO ESPERADO**: Test FALLA (confirma falta de protección CSRF)
  - Documentar contraejemplos: peticiones sin token CSRF son aceptadas
  - _Requirements: 1.17, 1.18_

- [x] 1.7 Escribir test de exploración para ausencia de caché
  - **Property 1: Bug Condition** - Sin Caché Redis
  - **CRÍTICO**: Este test DEBE FALLAR en código sin corregir
  - **OBJETIVO**: Demostrar que no existe caché y todas las peticiones consultan BD
  - Implementar test que verifica si Redis está corriendo (`docker ps | grep redis`)
  - Test debe verificar que `fastapi-cache2` no está en requirements.txt
  - Test debe habilitar SQL logging y verificar queries repetidas
  - Test debe llamar `/economia/estadisticas` 10 veces y contar queries a BD
  - Ejecutar test en código SIN CORREGIR
  - **RESULTADO ESPERADO**: Test FALLA (confirma ausencia de caché)
  - Documentar contraejemplos: sin Redis, queries repetidas, latencia consistente
  - _Requirements: 1.19, 1.20_

## Fase 2: Tests de Preservación (ANTES de implementar correcciones)

- [x] 2. Escribir tests de preservación para funcionalidad existente
  - **Property 2: Preservation** - Funcionalidad Existente Inalterada
  - **IMPORTANTE**: Seguir metodología observation-first
  - Observar comportamiento en código SIN CORREGIR para casos no afectados por bugs
  - Escribir property-based tests que capturen patrones de comportamiento observados
  - Property-based testing genera muchos casos de prueba para garantías más fuertes
  - Ejecutar tests en código SIN CORREGIR
  - **RESULTADO ESPERADO**: Tests PASAN (confirma comportamiento base a preservar)
  - Marcar tarea completa cuando tests estén escritos, ejecutados, y pasando en código sin corregir
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16_

  - [x] 2.1 Test de preservación: Autenticación JWT
    - Observar: Login con credenciales válidas genera access + refresh tokens
    - Escribir property-based test: para todos los usuarios válidos, login genera tokens JWT válidos
    - Observar: Refresh token rotation funciona correctamente
    - Escribir test: refresh token genera nuevo access token sin cambiar funcionalidad
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.2 Test de preservación: RBAC (Control de Acceso)
    - Observar: Usuario ADMIN puede acceder a todos los endpoints
    - Escribir property-based test: para todos los endpoints, ADMIN tiene acceso completo
    - Observar: Usuario SOLO_LECTURA no puede crear/editar/eliminar
    - Escribir test: SOLO_LECTURA es rechazado en operaciones de escritura
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.3 Test de preservación: Auditoría
    - Observar: Login exitoso registra evento en audit_log con IP y user agent
    - Escribir property-based test: para todos los eventos de seguridad, se registran en audit_log
    - Observar: Detección de brute force bloquea después de 5 intentos
    - Escribir test: 5 intentos fallidos bloquean cuenta temporalmente
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.4 Test de preservación: CRUD de Tickets
    - Observar: Crear ticket con procesos y repuestos calcula total correctamente
    - Escribir property-based test: para todos los tickets, total = suma(procesos) + suma(repuestos)
    - Observar: Actualizar estado de ticket funciona correctamente
    - Escribir test: actualización de estado persiste en BD
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.5 Test de preservación: Generación de PDFs
    - Observar: PDF incluye todos los datos (vehículo, procesos, repuestos, fotos)
    - Escribir test: PDF generado contiene todas las secciones esperadas
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.6 Test de preservación: Registro de Pagos
    - Observar: Registrar pago actualiza estado de ticket y crea movimiento en economía
    - Escribir property-based test: para todos los pagos, estado se actualiza y se registra en economía
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.7 Test de preservación: Validación de Contraseñas
    - Observar: Contraseña con <8 caracteres es rechazada
    - Escribir property-based test: para todas las contraseñas débiles, validación rechaza
    - Observar: Migración SHA256 → bcrypt funciona automáticamente
    - Escribir test: login con contraseña SHA256 migra a bcrypt
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.8 Test de preservación: Rate Limiting
    - Observar: 6 peticiones a /auth/login en 1 minuto son bloqueadas
    - Escribir test: exceder rate limit retorna error 429
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.9 Test de preservación: Token Blacklist
    - Observar: Logout agrega token a blacklist y rechaza peticiones posteriores
    - Escribir test: token en blacklist no puede usarse para autenticación
    - Verificar test PASA en código SIN CORREGIR

  - [x] 2.10 Test de preservación: Frontend y Móvil
    - Observar: Navegación entre páginas funciona correctamente
    - Escribir test: rutas protegidas redirigen a login sin autenticación
    - Observar: Modo offline en móvil permite consultar datos sincronizados
    - Escribir test: datos sincronizados están disponibles offline
    - Verificar test PASA en código SIN CORREGIR

## Fase 3: Implementación de Correcciones


- [x] 3. Actualizar dependencias vulnerables

  - [x] 3.1 Actualizar versiones de dependencias en requirements.txt
    - Actualizar Werkzeug de 3.1.3 a 3.1.7 (cierra CVE-2026-27199, CVE-2025-66221, CVE-2026-21860)
    - Actualizar Flask de 3.1.2 a 3.1.3 (cierra CVE-2026-27205)
    - Actualizar pip de 25.2 a 26.0.1 (cierra CVE-2026-1703)
    - Actualizar ecdsa de 0.19.1 a 0.19.2 (cierra CVE-2024-23342)
    - Agregar `safety==3.2.11` para auditoría continua
    - Pin de versiones exactas para todas las dependencias críticas
    - _Bug_Condition: systemState.werkzeugVersion == "3.1.3" OR systemState.flaskVersion == "3.1.2" OR systemState.pipVersion == "25.2" OR systemState.ecdsaVersion == "0.19.1"_
    - _Expected_Behavior: Werkzeug ≥3.1.7, Flask ≥3.1.3, pip ≥26.0.1, ecdsa ≥0.19.2, safety check retorna 0 vulnerabilidades críticas_
    - _Preservation: Toda la funcionalidad existente debe continuar funcionando sin cambios_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.2 Crear script de actualización de dependencias
    - Crear archivo `scripts/update_dependencies.sh`
    - Script debe ejecutar: `pip install --upgrade werkzeug==3.1.7 flask==3.1.3 pip==26.0.1 ecdsa==0.19.2`
    - Script debe ejecutar: `pip install safety`
    - Script debe ejecutar: `safety check`
    - Script debe ejecutar: `pip freeze > requirements.txt`
    - Hacer script ejecutable: `chmod +x scripts/update_dependencies.sh`
    - _Requirements: 2.5_

  - [x] 3.3 Verificar test de exploración ahora pasa
    - **Property 1: Expected Behavior** - Dependencias Actualizadas Sin CVEs
    - **IMPORTANTE**: Re-ejecutar el MISMO test de la tarea 1.1 - NO escribir nuevo test
    - El test de la tarea 1.1 codifica el comportamiento esperado
    - Cuando este test pase, confirma que el comportamiento esperado se satisface
    - Ejecutar test de exploración de dependencias vulnerables
    - **RESULTADO ESPERADO**: Test PASA (confirma que bug está corregido)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.4 Verificar tests de preservación siguen pasando
    - **Property 2: Preservation** - Funcionalidad Existente Inalterada
    - **IMPORTANTE**: Re-ejecutar los MISMOS tests de la tarea 2 - NO escribir nuevos tests
    - Ejecutar tests de preservación de autenticación, RBAC, auditoría, CRUD
    - **RESULTADO ESPERADO**: Tests PASAN (confirma sin regresiones)
    - Confirmar que todos los tests siguen pasando después de actualizar dependencias

- [x] 4. Configurar CORS de forma segura

  - [x] 4.1 Modificar configuración de CORS en app/main.py
    - Reemplazar `_origins = ["*"]` en línea ~340
    - Leer orígenes desde variable de entorno `ALLOWED_ORIGINS`
    - Implementar lógica: si `ALLOWED_ORIGINS` está vacío y `ENVIRONMENT=production`, fallar al iniciar
    - En desarrollo, usar por defecto: `["http://localhost:5173", "http://localhost:3000"]`
    - Mantener `allow_credentials=True` pero solo con orígenes específicos
    - _Bug_Condition: systemState.corsOrigins == ["*"] AND systemState.environment == "production"_
    - _Expected_Behavior: CORS rechaza peticiones desde orígenes no autorizados, acepta solo orígenes en ALLOWED_ORIGINS_
    - _Preservation: Funcionalidad de API debe continuar funcionando para orígenes autorizados_
    - _Requirements: 2.6, 2.7, 2.8, 2.9_

  - [x] 4.2 Actualizar archivos de configuración de entorno
    - Agregar `ALLOWED_ORIGINS=https://taller.com,https://app.taller.com` a `.env.example`
    - Agregar `ENVIRONMENT=production` a `.env.example`
    - Agregar `ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000` a `.env`
    - Agregar `ENVIRONMENT=development` a `.env`
    - _Requirements: 2.6, 2.9_

  - [x] 4.3 Verificar test de exploración ahora pasa
    - **Property 1: Expected Behavior** - CORS Configurado Correctamente
    - Re-ejecutar test de la tarea 1.2
    - Verificar que peticiones desde orígenes no autorizados son rechazadas
    - Verificar que peticiones desde orígenes en `ALLOWED_ORIGINS` son aceptadas
    - **RESULTADO ESPERADO**: Test PASA (confirma CORS configurado correctamente)
    - _Requirements: 2.6, 2.7, 2.8, 2.9_

  - [x] 4.4 Verificar tests de preservación siguen pasando
    - **Property 2: Preservation** - Funcionalidad Existente Inalterada
    - Re-ejecutar tests de preservación
    - Confirmar que API sigue funcionando para orígenes autorizados
    - **RESULTADO ESPERADO**: Tests PASAN (confirma sin regresiones)

- [x] 5. Optimizar base de datos

  - [x] 5.1 Crear migración SQL con índices compuestos
    - Crear archivo `db/migrations/add_composite_indexes.sql`
    - Agregar índice: `CREATE INDEX idx_tickets_estado_fecha ON tickets(estado, fecha_ingreso DESC)`
    - Agregar índice: `CREATE INDEX idx_tickets_placa ON tickets(placa)`
    - Agregar índice: `CREATE INDEX idx_audit_log_user_action_date ON audit_log(user_id, action, created_at DESC)`
    - Agregar índice: `CREATE INDEX idx_token_blacklist_jti_exp ON token_blacklist(jti, expires_at)`
    - Agregar índice: `CREATE INDEX idx_vehiculos_placa ON vehiculos(placa)`
    - _Bug_Condition: NOT hasIndex(systemState.database, "idx_tickets_estado_fecha")_
    - _Expected_Behavior: Consultas usan índices y responden en <50ms_
    - _Preservation: Datos existentes y funcionalidad CRUD deben permanecer inalterados_
    - _Requirements: 2.10, 2.11, 2.14_

  - [x] 5.2 Crear script para aplicar índices
    - Crear archivo `scripts/apply_db_indexes.sh`
    - Script debe ejecutar: `psql -U $DB_USER -d $DB_NAME -f db/migrations/add_composite_indexes.sql`
    - Hacer script ejecutable: `chmod +x scripts/apply_db_indexes.sh`
    - _Requirements: 2.14_

  - [x] 5.3 Implementar eager loading en ticket_repository.py
    - Importar `from sqlalchemy.orm import joinedload`
    - Crear método `get_tickets_with_details()` que usa `joinedload(Ticket.procesos)`, `joinedload(Ticket.repuestos)`, `joinedload(Ticket.fotos)`
    - Modificar método existente para usar eager loading por defecto
    - _Bug_Condition: usesNPlusOneQueries(systemState.ticketRepository)_
    - _Expected_Behavior: Relaciones se cargan en 1 query usando JOINs_
    - _Preservation: Datos retornados deben ser idénticos a antes_
    - _Requirements: 2.12_

  - [x] 5.4 Implementar paginación obligatoria en ticket_repository.py
    - Crear método `get_tickets_paginated(page=1, per_page=50, estado=None)`
    - Método debe retornar tupla: `(tickets, total)`
    - Implementar lógica: `query.offset((page - 1) * per_page).limit(per_page)`
    - Actualizar método `get_all_tickets()` para usar paginación por defecto
    - _Bug_Condition: NOT hasPagination(systemState.ticketRepository.getAll)_
    - _Expected_Behavior: Máximo 50 registros por página_
    - _Preservation: Todos los datos deben seguir siendo accesibles mediante paginación_
    - _Requirements: 2.13_

  - [x] 5.5 Actualizar endpoint de tickets en ticket_ruta.py
    - Agregar parámetros: `page: int = Query(1, ge=1)`, `per_page: int = Query(50, ge=1, le=100)`
    - Llamar a `ticket_service.get_tickets_paginated(db, page, per_page, estado)`
    - Retornar respuesta con: `{"tickets": [...], "total": N, "page": 1, "per_page": 50, "pages": M}`
    - _Requirements: 2.13_

  - [x] 5.6 Verificar test de exploración ahora pasa
    - **Property 1: Expected Behavior** - Base de Datos Optimizada
    - Re-ejecutar test de la tarea 1.3
    - Verificar que `EXPLAIN ANALYZE` muestra `Index Scan` en lugar de `Seq Scan`
    - Verificar que latencia es <50ms
    - Verificar que eager loading carga relaciones en 1 query
    - Verificar que paginación limita resultados a 50
    - **RESULTADO ESPERADO**: Test PASA (confirma optimización exitosa)
    - _Requirements: 2.10, 2.11, 2.12, 2.13, 2.14_

  - [x] 5.7 Verificar tests de preservación siguen pasando
    - **Property 2: Preservation** - Funcionalidad Existente Inalterada
    - Re-ejecutar tests de preservación de CRUD de tickets
    - Confirmar que datos retornados son idénticos
    - Confirmar que cálculo de totales sigue funcionando
    - **RESULTADO ESPERADO**: Tests PASAN (confirma sin regresiones)

- [x] 6. Implementar tests frontend/móvil/E2E

  - [x] 6.1 Configurar Vitest en frontend
    - Agregar dependencias en `frontend/package.json`: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`
    - Agregar scripts: `"test": "vitest"`, `"test:coverage": "vitest --coverage"`
    - Crear `frontend/vite.config.js` con configuración de Vitest
    - Crear `frontend/src/test/setup.js` con configuración de Testing Library
    - _Bug_Condition: systemState.frontendTestCoverage == 0_
    - _Expected_Behavior: Tests ejecutables con >60% cobertura_
    - _Preservation: Código de frontend debe continuar funcionando sin cambios_
    - _Requirements: 2.15, 2.18_

  - [x] 6.2 Crear tests de componentes críticos del frontend
    - Crear `frontend/src/__tests__/LoginPage.test.jsx` con tests de login exitoso/fallido
    - Crear `frontend/src/__tests__/ProtectedRoute.test.jsx` con tests de redirección
    - Crear `frontend/src/__tests__/authService.test.js` con tests de servicios
    - Ejecutar `npm test` y verificar que tests pasan
    - Ejecutar `npm run test:coverage` y verificar >60% cobertura
    - _Requirements: 2.15, 2.18_

  - [x] 6.3 Configurar Jest en app móvil
    - Agregar dependencias en `mobile_app/package.json`: `@testing-library/react-native`, `jest`, `@testing-library/jest-native`
    - Agregar scripts: `"test": "jest"`, `"test:coverage": "jest --coverage"`
    - Crear `mobile_app/jest.config.js` con configuración de Jest
    - _Bug_Condition: systemState.mobileTestCoverage == 0_
    - _Expected_Behavior: Tests ejecutables con >50% cobertura_
    - _Preservation: Código de app móvil debe continuar funcionando sin cambios_
    - _Requirements: 2.16, 2.18_

  - [x] 6.4 Crear tests de pantallas críticas de la app móvil
    - Crear `mobile_app/src/__tests__/LoginScreen.test.js` con tests de login
    - Crear `mobile_app/src/__tests__/HomeScreen.test.js` con tests de navegación
    - Crear `mobile_app/src/__tests__/authService.test.js` con tests de servicios
    - Ejecutar `npm test` y verificar que tests pasan
    - Ejecutar `npm run test:coverage` y verificar >50% cobertura
    - _Requirements: 2.16, 2.18_

  - [x] 6.5 Configurar Playwright para tests E2E
    - Crear carpeta `e2e/` en raíz del proyecto
    - Crear `e2e/package.json` con dependencia `@playwright/test`
    - Crear `e2e/playwright.config.js` con configuración base
    - Agregar script: `"test:e2e": "playwright test"`
    - _Bug_Condition: systemState.e2eTestCount == 0_
    - _Expected_Behavior: Tests E2E cubren 5 flujos críticos_
    - _Preservation: Flujos de usuario deben continuar funcionando sin cambios_
    - _Requirements: 2.17, 2.18_

  - [x] 6.6 Crear tests E2E de flujos críticos
    - Crear `e2e/tests/login.spec.js` con tests de login exitoso/fallido
    - Crear `e2e/tests/tickets.spec.js` con tests de crear ticket
    - Crear `e2e/tests/payments.spec.js` con tests de cobro
    - Crear `e2e/tests/search.spec.js` con tests de búsqueda
    - Crear `e2e/tests/logout.spec.js` con tests de logout
    - Ejecutar `npm run test:e2e` y verificar que 5 flujos pasan
    - _Requirements: 2.17, 2.18_

  - [x] 6.7 Verificar test de exploración ahora pasa
    - **Property 1: Expected Behavior** - Tests Implementados
    - Re-ejecutar test de la tarea 1.4
    - Verificar que existen archivos de test en frontend/móvil
    - Verificar que cobertura es >60% frontend, >50% móvil
    - Verificar que 5 flujos E2E pasan
    - **RESULTADO ESPERADO**: Test PASA (confirma tests implementados)
    - _Requirements: 2.15, 2.16, 2.17, 2.18_

  - [x] 6.8 Verificar tests de preservación siguen pasando
    - **Property 2: Preservation** - Funcionalidad Existente Inalterada
    - Re-ejecutar tests de preservación de frontend y móvil
    - Confirmar que navegación sigue funcionando
    - Confirmar que modo offline sigue funcionando
    - **RESULTADO ESPERADO**: Tests PASAN (confirma sin regresiones)


- [x] 7. Forzar HTTPS en producción

  - [x] 7.1 Agregar middleware HTTPS en app/main.py
    - Importar: `from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware`
    - Importar: `from fastapi.middleware.trustedhost import TrustedHostMiddleware`
    - Agregar condicional: `if os.getenv("ENVIRONMENT") == "production":`
    - Dentro del condicional, agregar: `app.add_middleware(HTTPSRedirectMiddleware)`
    - Agregar middleware de hosts confiables con lista desde `ALLOWED_HOSTS`
    - _Bug_Condition: systemState.environment == "production" AND NOT hasHTTPSRedirect(systemState)_
    - _Expected_Behavior: Peticiones HTTP redirigen automáticamente a HTTPS_
    - _Preservation: Funcionalidad en desarrollo debe continuar funcionando sin cambios_
    - _Requirements: 2.19, 2.21_

  - [x] 7.2 Configurar cookies seguras en auth_ruta.py
    - Modificar método `login` en `app/rutas/auth_ruta.py`
    - Agregar lógica: `is_production = os.getenv("ENVIRONMENT") == "production"`
    - Actualizar `response.set_cookie()` con: `secure=is_production`, `samesite="strict"`
    - Mantener: `httponly=True`, `max_age=7*24*60*60`
    - _Bug_Condition: NOT hasCookieSecureFlag(systemState.cookies)_
    - _Expected_Behavior: Cookies con flags Secure=True, HttpOnly=True, SameSite=strict en producción_
    - _Preservation: Autenticación debe continuar funcionando sin cambios_
    - _Requirements: 2.20_

  - [x] 7.3 Actualizar archivos de configuración de entorno
    - Agregar `ENVIRONMENT=production` a `.env.example`
    - Agregar `ALLOWED_HOSTS=taller.com,*.taller.com` a `.env.example`
    - Verificar que `.env` tiene `ENVIRONMENT=development`
    - _Requirements: 2.19, 2.21_

  - [x] 7.4 Verificar test de exploración ahora pasa
    - **Property 1: Expected Behavior** - HTTPS Forzado en Producción
    - Re-ejecutar test de la tarea 1.5
    - Verificar que peticiones HTTP redirigen a HTTPS en producción
    - Verificar que cookies tienen flags de seguridad correctos
    - **RESULTADO ESPERADO**: Test PASA (confirma HTTPS forzado)
    - _Requirements: 2.19, 2.20, 2.21_

  - [x] 7.5 Verificar tests de preservación siguen pasando
    - **Property 2: Preservation** - Funcionalidad Existente Inalterada
    - Re-ejecutar tests de preservación de autenticación
    - Confirmar que login sigue generando tokens correctamente
    - Confirmar que refresh token sigue funcionando
    - **RESULTADO ESPERADO**: Tests PASAN (confirma sin regresiones)

- [ ] 8. Implementar protección CSRF

  - [x] 8.1 Agregar dependencia CSRF
    - Agregar `fastapi-csrf-protect==0.3.4` a `requirements.txt`
    - Ejecutar `pip install fastapi-csrf-protect==0.3.4`
    - _Bug_Condition: NOT hasCSRFProtection(systemState.postEndpoints)_
    - _Expected_Behavior: Endpoints POST/PUT/DELETE validan token CSRF_
    - _Preservation: Funcionalidad de API debe continuar funcionando con token CSRF válido_
    - _Requirements: 2.22, 2.23_

  - [x] 8.2 Configurar CSRF protection en app/main.py
    - Importar: `from fastapi_csrf_protect import CsrfProtect`
    - Importar: `from fastapi_csrf_protect.exceptions import CsrfProtectError`
    - Crear clase `CsrfSettings` con configuración desde variable de entorno
    - Agregar decorador `@CsrfProtect.load_config`
    - Agregar exception handler para `CsrfProtectError` que retorna 403
    - _Requirements: 2.22, 2.23_

  - [x] 8.3 Agregar validación CSRF en endpoints de escritura
    - Modificar `app/rutas/ticket_ruta.py`: agregar `csrf_protect: CsrfProtect = Depends()` en POST/PUT/DELETE
    - Agregar `await csrf_protect.validate_csrf(request)` al inicio de cada endpoint
    - Aplicar mismo patrón a todos los endpoints de escritura en otras rutas
    - _Requirements: 2.22, 2.23_

  - [x] 8.4 Configurar frontend para enviar token CSRF
    - Modificar `frontend/src/services/api.js`
    - Crear función `getCsrfToken()` que lee cookie `fastapi-csrf-token`
    - Agregar interceptor de Axios que incluye header `X-CSRF-Token` en POST/PUT/DELETE
    - _Bug_Condition: Frontend no envía token CSRF en headers_
    - _Expected_Behavior: Frontend incluye token CSRF en todas las peticiones de escritura_
    - _Preservation: Peticiones de API deben continuar funcionando con token CSRF_
    - _Requirements: 2.24_

  - [x] 8.5 Actualizar archivos de configuración de entorno
    - Agregar `CSRF_SECRET_KEY=your-secret-key-here-change-in-production` a `.env.example`
    - Agregar `CSRF_SECRET_KEY` con valor aleatorio a `.env`
    - _Requirements: 2.22_

  - [x] 8.6 Verificar test de exploración ahora pasa
    - **Property 1: Expected Behavior** - Protección CSRF Implementada
    - Re-ejecutar test de la tarea 1.6
    - Verificar que peticiones sin token CSRF son rechazadas con 403
    - Verificar que peticiones con token CSRF válido son aceptadas
    - **RESULTADO ESPERADO**: Test PASA (confirma CSRF implementado)
    - _Requirements: 2.22, 2.23, 2.24_

  - [x] 8.7 Verificar tests de preservación siguen pasando
    - **Property 2: Preservation** - Funcionalidad Existente Inalterada
    - Re-ejecutar tests de preservación de CRUD
    - Confirmar que operaciones de escritura siguen funcionando con token CSRF
    - **RESULTADO ESPERADO**: Tests PASAN (confirma sin regresiones)

- [x] 9. Implementar caché con Redis

  - [x] 9.1 Agregar dependencias de Redis
    - Agregar `redis==5.2.0` a `requirements.txt`
    - Agregar `fastapi-cache2[redis]==0.2.2` a `requirements.txt`
    - Ejecutar `pip install redis==5.2.0 fastapi-cache2[redis]==0.2.2`
    - _Bug_Condition: NOT hasRedisCache(systemState)_
    - _Expected_Behavior: Datos se cachean en Redis por 5 minutos_
    - _Preservation: Funcionalidad de API debe continuar retornando datos correctos_
    - _Requirements: 2.25, 2.27_

  - [x] 9.2 Crear servicio Redis con Docker Compose
    - Crear archivo `docker-compose.yml` en raíz del proyecto
    - Agregar servicio Redis con imagen `redis:7-alpine`
    - Configurar puerto 6379 y volumen persistente
    - Agregar comando: `redis-server --appendonly yes`
    - _Requirements: 2.25_

  - [x] 9.3 Crear configuración de caché
    - Crear archivo `app/configuracion/cache.py`
    - Implementar función `async def init_cache()` que inicializa FastAPICache con RedisBackend
    - Leer URL de Redis desde variable de entorno `REDIS_URL`
    - _Requirements: 2.25_

  - [x] 9.4 Inicializar caché en startup de la aplicación
    - Modificar `app/main.py`
    - Importar: `from contextlib import asynccontextmanager`
    - Importar: `from app.configuracion.cache import init_cache`
    - Crear función `lifespan` que inicializa caché en startup
    - Pasar `lifespan` a `FastAPI(lifespan=lifespan)`
    - _Requirements: 2.25_

  - [x] 9.5 Agregar caché a endpoints de lectura
    - Modificar `app/rutas/economia_ruta.py`
    - Importar: `from fastapi_cache.decorator import cache`
    - Agregar decorador `@cache(expire=300)` a endpoint `/estadisticas` (5 minutos)
    - _Bug_Condition: NOT cacheEnabled(systemState.estadisticasEndpoint)_
    - _Expected_Behavior: Estadísticas se cachean por 5 minutos_
    - _Preservation: Datos retornados deben ser idénticos_
    - _Requirements: 2.25, 2.27_

  - [x] 9.6 Implementar invalidación de caché en escritura
    - Modificar endpoints POST/PUT/DELETE en `app/rutas/economia_ruta.py`
    - Importar: `from fastapi_cache import FastAPICache`
    - Agregar `await FastAPICache.clear(namespace="estadisticas")` después de crear/actualizar datos
    - _Bug_Condition: Caché no se invalida al crear/actualizar datos_
    - _Expected_Behavior: Caché se invalida automáticamente_
    - _Preservation: Datos siempre deben estar actualizados_
    - _Requirements: 2.26_

  - [x] 9.7 Actualizar archivos de configuración de entorno
    - Agregar `REDIS_URL=redis://localhost:6379` a `.env.example`
    - Agregar `REDIS_URL=redis://localhost:6379` a `.env`
    - _Requirements: 2.25_

  - [x] 9.8 Verificar test de exploración ahora pasa
    - **Property 1: Expected Behavior** - Caché Implementado
    - Re-ejecutar test de la tarea 1.7
    - Verificar que Redis está corriendo
    - Verificar que primera petición consulta BD
    - Verificar que segunda petición responde desde Redis (sin query a BD)
    - Verificar que crear/actualizar datos invalida caché
    - **RESULTADO ESPERADO**: Test PASA (confirma caché implementado)
    - _Requirements: 2.25, 2.26, 2.27_

  - [x] 9.9 Verificar tests de preservación siguen pasando
    - **Property 2: Preservation** - Funcionalidad Existente Inalterada
    - Re-ejecutar tests de preservación de economía
    - Confirmar que estadísticas retornan datos correctos
    - Confirmar que datos se actualizan correctamente
    - **RESULTADO ESPERADO**: Tests PASAN (confirma sin regresiones)

## Fase 4: Checkpoint Final

- [x] 10. Checkpoint - Asegurar que todos los tests pasan
  - Ejecutar suite completa de tests backend: `pytest`
  - Ejecutar tests frontend: `cd frontend && npm test`
  - Ejecutar tests móvil: `cd mobile_app && npm test`
  - Ejecutar tests E2E: `cd e2e && npm run test:e2e`
  - Ejecutar `safety check` y verificar 0 vulnerabilidades críticas
  - Verificar que todos los tests de exploración ahora pasan (confirma bugs corregidos)
  - Verificar que todos los tests de preservación siguen pasando (confirma sin regresiones)
  - Si algún test falla, investigar y resolver antes de continuar
  - Preguntar al usuario si hay dudas o problemas

