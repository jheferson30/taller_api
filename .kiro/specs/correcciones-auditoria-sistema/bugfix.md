# Documento de Requisitos de Bugfix

## Introducción

Este bugfix aborda múltiples vulnerabilidades críticas y problemas de seguridad, rendimiento y calidad identificados en la auditoría completa del sistema de gestión de taller mecánico (6 de Abril de 2026). El sistema actualmente presenta 5 CVEs críticos en dependencias, configuración CORS insegura, falta de optimización en base de datos, ausencia de tests en frontend/móvil, y falta de protección HTTPS/CSRF.

El impacto de estos problemas incluye:
- **Seguridad**: Exposición a ataques DoS, CSRF, XSS, y divulgación de información
- **Rendimiento**: Consultas lentas (>500ms) por falta de índices compuestos
- **Calidad**: 0% cobertura de tests en frontend y app móvil, riesgo de regresiones
- **Producción**: Sistema no apto para producción sin correcciones críticas

Este bugfix se enfoca en corregir los problemas CRÍTICOS y de ALTA prioridad identificados en la auditoría, elevando la calificación del sistema de 7.8/10 a 9.0/10.

---

## Análisis del Bug

### Comportamiento Actual (Defecto)

#### 1. Dependencias Vulnerables

1.1 CUANDO el sistema usa Werkzeug 3.1.3 ENTONCES está expuesto a CVE-2026-27199, CVE-2025-66221, CVE-2026-21860 (ataques DoS)

1.2 CUANDO el sistema usa Flask 3.1.2 ENTONCES está expuesto a CVE-2026-27205 (divulgación de información)

1.3 CUANDO el sistema usa pip 25.2 ENTONCES está expuesto a CVE-2026-1703 (path traversal)

1.4 CUANDO el sistema usa ecdsa 0.19.1 ENTONCES está expuesto a CVE-2024-23342 (timing attack Minerva)

#### 2. CORS Mal Configurado

1.5 CUANDO el sistema configura CORS con `allow_origins=["*"]` ENTONCES permite peticiones desde cualquier origen, exponiendo el sistema a ataques CSRF y XSS desde dominios maliciosos

1.6 CUANDO el sistema permite todos los orígenes ENTONCES no valida la procedencia de las peticiones, permitiendo robo de tokens y datos sensibles

#### 3. Base de Datos Sin Optimizar

1.7 CUANDO se consultan tickets filtrados por estado y fecha ENTONCES la query no usa índices compuestos y tarda >500ms en responder

1.8 CUANDO se consultan registros de audit_log por user_id y action ENTONCES la query hace full table scan sin índices, causando lentitud

1.9 CUANDO se cargan tickets con sus relaciones (procesos, repuestos, fotos) ENTONCES se ejecutan consultas N+1, generando múltiples queries innecesarias

1.10 CUANDO se solicitan todos los tickets sin paginación ENTONCES el sistema puede retornar miles de registros, causando timeout y consumo excesivo de memoria

#### 4. Sin Tests Frontend/Móvil

1.11 CUANDO se modifica código del frontend ENTONCES no hay tests que validen que la funcionalidad sigue funcionando (0% cobertura)

1.12 CUANDO se modifica código de la app móvil ENTONCES no hay tests que prevengan regresiones (0% cobertura)

1.13 CUANDO se despliega a producción ENTONCES no hay tests E2E que validen flujos críticos completos

#### 5. Sin HTTPS Forzado

1.14 CUANDO un usuario accede por HTTP en producción ENTONCES el sistema no redirige automáticamente a HTTPS, permitiendo interceptación de tráfico

1.15 CUANDO el sistema configura cookies ENTONCES no incluye el flag `Secure`, permitiendo que sean enviadas por HTTP sin cifrar

1.16 CUANDO se transmiten tokens JWT por HTTP ENTONCES pueden ser interceptados en ataques man-in-the-middle

#### 6. Sin Protección CSRF

1.17 CUANDO se envían peticiones POST/PUT/DELETE desde un sitio malicioso ENTONCES el sistema las procesa sin validar token CSRF, permitiendo acciones no autorizadas

1.18 CUANDO un usuario autenticado visita un sitio malicioso ENTONCES ese sitio puede ejecutar acciones en nombre del usuario sin su consentimiento

#### 7. Sin Caché

1.19 CUANDO se solicitan estadísticas de economía repetidamente ENTONCES el sistema ejecuta la misma query costosa en cada petición, sobrecargando la base de datos

1.20 CUANDO múltiples usuarios consultan los mismos datos ENTONCES no se reutilizan resultados previos, causando carga innecesaria

---

### Comportamiento Esperado (Correcto)

#### 1. Dependencias Actualizadas y Seguras

2.1 CUANDO el sistema usa Werkzeug 3.1.7 o superior ENTONCES NO estará expuesto a CVE-2026-27199, CVE-2025-66221, CVE-2026-21860

2.2 CUANDO el sistema usa Flask 3.1.3 o superior ENTONCES NO estará expuesto a CVE-2026-27205

2.3 CUANDO el sistema usa pip 26.0.1 o superior ENTONCES NO estará expuesto a CVE-2026-1703

2.4 CUANDO el sistema usa ecdsa 0.19.2 o superior ENTONCES NO estará expuesto a CVE-2024-23342

2.5 CUANDO se ejecuta `safety check` ENTONCES NO reportará vulnerabilidades críticas

#### 2. CORS Configurado Correctamente

2.6 CUANDO el sistema está en producción ENTONCES DEBERÁ configurar CORS solo con orígenes específicos desde variable de entorno `ALLOWED_ORIGINS`

2.7 CUANDO el sistema recibe una petición desde un origen no autorizado ENTONCES DEBERÁ rechazarla con error CORS

2.8 CUANDO `ALLOWED_ORIGINS` no está configurado en producción ENTONCES el sistema DEBERÁ fallar al iniciar con error claro

2.9 CUANDO el sistema está en desarrollo ENTONCES DEBERÁ permitir solo `http://localhost:5173` y `http://localhost:3000`

#### 3. Base de Datos Optimizada

2.10 CUANDO se consultan tickets filtrados por estado y fecha ENTONCES DEBERÁ usar índice compuesto `idx_tickets_estado_fecha` y responder en <50ms

2.11 CUANDO se consultan registros de audit_log por user_id y action ENTONCES DEBERÁ usar índice compuesto `idx_audit_log_user_action_date` y responder en <50ms

2.12 CUANDO se cargan tickets con sus relaciones ENTONCES DEBERÁ usar eager loading (joinedload) para cargar todo en una sola query

2.13 CUANDO se solicitan tickets ENTONCES DEBERÁ implementar paginación obligatoria con límite máximo de 50 registros por página

2.14 CUANDO se crean índices en base de datos ENTONCES DEBERÁN incluir: `idx_tickets_estado_fecha`, `idx_tickets_placa`, `idx_audit_log_user_action_date`, `idx_token_blacklist_jti_exp`, `idx_vehiculos_placa`

#### 4. Tests Implementados

2.15 CUANDO se ejecutan tests del frontend ENTONCES DEBERÁ tener al menos 60% de cobertura en componentes críticos (LoginPage, ProtectedRoute, servicios)

2.16 CUANDO se ejecutan tests de la app móvil ENTONCES DEBERÁ tener al menos 50% de cobertura en pantallas críticas (LoginScreen, HomeScreen, servicios)

2.17 CUANDO se ejecutan tests E2E ENTONCES DEBERÁN cubrir al menos 5 flujos críticos (login, crear ticket, cobro, búsqueda, logout)

2.18 CUANDO se modifica código del frontend/móvil ENTONCES los tests DEBERÁN ejecutarse automáticamente y fallar si hay regresiones

#### 5. HTTPS Forzado en Producción

2.19 CUANDO un usuario accede por HTTP en producción ENTONCES el sistema DEBERÁ redirigir automáticamente a HTTPS

2.20 CUANDO el sistema configura cookies ENTONCES DEBERÁ incluir flags `Secure=True`, `HttpOnly=True`, `SameSite=strict`

2.21 CUANDO el sistema está en producción ENTONCES DEBERÁ validar que el host está en la lista de hosts confiables

#### 6. Protección CSRF Implementada

2.22 CUANDO se envían peticiones POST/PUT/DELETE ENTONCES el sistema DEBERÁ validar token CSRF antes de procesarlas

2.23 CUANDO una petición no incluye token CSRF válido ENTONCES el sistema DEBERÁ rechazarla con error 403

2.24 CUANDO el frontend/móvil envía peticiones de escritura ENTONCES DEBERÁ incluir el token CSRF en headers

#### 7. Caché Implementado

2.25 CUANDO se solicitan estadísticas de economía ENTONCES el sistema DEBERÁ cachear el resultado por 5 minutos en Redis

2.26 CUANDO se crean/actualizan datos ENTONCES el sistema DEBERÁ invalidar automáticamente el caché relacionado

2.27 CUANDO se consultan datos cacheados ENTONCES el sistema DEBERÁ responder desde Redis sin consultar la base de datos

---

### Comportamiento Sin Cambios (Prevención de Regresiones)

#### Autenticación y Autorización

3.1 CUANDO un usuario se autentica con credenciales válidas ENTONCES el sistema DEBERÁ CONTINUAR generando tokens JWT (access + refresh) correctamente

3.2 CUANDO un usuario intenta acceder a un endpoint protegido ENTONCES el sistema DEBERÁ CONTINUAR validando el token JWT y los roles requeridos

3.3 CUANDO se detectan 5 intentos fallidos de login ENTONCES el sistema DEBERÁ CONTINUAR bloqueando la cuenta temporalmente

3.4 CUANDO un usuario hace logout ENTONCES el sistema DEBERÁ CONTINUAR agregando el token a la blacklist

#### Funcionalidad de Negocio

3.5 CUANDO se crea un ticket ENTONCES el sistema DEBERÁ CONTINUAR validando datos, guardando en BD y retornando el ticket creado

3.6 CUANDO se agregan procesos/repuestos a un ticket ENTONCES el sistema DEBERÁ CONTINUAR calculando el total correctamente

3.7 CUANDO se genera un PDF de ticket ENTONCES el sistema DEBERÁ CONTINUAR incluyendo todos los datos (vehículo, procesos, repuestos, fotos)

3.8 CUANDO se registra un pago ENTONCES el sistema DEBERÁ CONTINUAR actualizando el estado del ticket y registrando en economía

#### Auditoría

3.9 CUANDO ocurre un evento de seguridad (login, logout, cambio de contraseña) ENTONCES el sistema DEBERÁ CONTINUAR registrándolo en audit_log con IP y user agent

3.10 CUANDO se consultan logs de auditoría ENTONCES el sistema DEBERÁ CONTINUAR filtrando por usuario, acción y rango de fechas

#### API y Endpoints

3.11 CUANDO se consultan endpoints existentes ENTONCES el sistema DEBERÁ CONTINUAR retornando las mismas estructuras de respuesta JSON

3.12 CUANDO se envían datos inválidos ENTONCES el sistema DEBERÁ CONTINUAR retornando errores de validación con códigos HTTP apropiados

3.13 CUANDO se excede el rate limit ENTONCES el sistema DEBERÁ CONTINUAR retornando error 429 con mensaje descriptivo

#### Frontend y Móvil

3.14 CUANDO un usuario navega en el frontend ENTONCES la interfaz DEBERÁ CONTINUAR mostrando los mismos componentes y funcionalidad

3.15 CUANDO la app móvil está offline ENTONCES DEBERÁ CONTINUAR permitiendo consultar datos sincronizados previamente

3.16 CUANDO se suben fotos de tickets ENTONCES el sistema DEBERÁ CONTINUAR guardándolas y mostrándolas correctamente
