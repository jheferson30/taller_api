# Requirements Document

## Introduction

Este documento especifica los requerimientos para implementar todas las mejoras identificadas en la auditoría de seguridad de la API del taller mecánico (docs/auditoria_api_v1.md) y migrar el sistema de autenticación actual basado en SHA256 sin salt a un sistema robusto basado en JWT (JSON Web Tokens) con bcrypt/argon2.

El sistema actual tiene múltiples vulnerabilidades de seguridad críticas, duplicación de código, inconsistencias REST y problemas de arquitectura que deben resolverse antes de considerar el producto apto para despliegue en internet o como SaaS.

## Glossary

- **Authentication_System**: Sistema de autenticación y autorización basado en JWT
- **Password_Hasher**: Componente que hashea contraseñas usando bcrypt o argon2
- **Token_Manager**: Componente que genera, valida y refresca tokens JWT
- **Auth_Middleware**: Middleware de FastAPI que valida tokens JWT en requests
- **Service_Layer**: Capa de lógica de negocio extraída de las rutas
- **Repository_Layer**: Capa de acceso a datos que abstrae queries de SQLAlchemy
- **Mobile_App**: Aplicación móvil del taller mecánico
- **Web_Frontend**: Frontend web del taller mecánico
- **API**: API REST de FastAPI del taller mecánico
- **Audit_Trail**: Registro de cambios y acciones de usuarios
- **Rate_Limiter**: Sistema de limitación de requests por IP/usuario

## Requirements

### Requirement 1: Migrar Sistema de Autenticación a JWT

**User Story:** Como administrador del sistema, quiero que las contraseñas se almacenen de forma segura con bcrypt/argon2 y que la autenticación use JWT, para proteger las credenciales de usuarios contra ataques de rainbow tables y brindar una experiencia de autenticación moderna y segura.

#### Acceptance Criteria

1. THE Password_Hasher SHALL usar bcrypt con cost factor mínimo de 12 o argon2id para hashear contraseñas
2. THE Password_Hasher SHALL generar un salt único y aleatorio para cada contraseña
3. WHEN un usuario se autentica exitosamente, THE Token_Manager SHALL generar un access token JWT con expiración de 15 minutos
4. WHEN un usuario se autentica exitosamente, THE Token_Manager SHALL generar un refresh token JWT con expiración de 7 días
5. THE Token_Manager SHALL firmar los tokens JWT con una clave secreta de al menos 256 bits almacenada en variable de entorno
6. THE Token_Manager SHALL incluir en el payload del JWT: user_id, username, roles, exp, iat, jti
7. WHEN se valida un token JWT, THE Auth_Middleware SHALL verificar la firma, expiración y que no esté en lista negra
8. THE API SHALL proveer endpoint POST /auth/login que retorne access_token y refresh_token
9. THE API SHALL proveer endpoint POST /auth/refresh que acepte refresh_token y retorne nuevo access_token
10. THE API SHALL proveer endpoint POST /auth/logout que invalide el refresh_token agregándolo a lista negra

### Requirement 2: Migrar Contraseñas Existentes

**User Story:** Como usuario existente del sistema, quiero que mi contraseña actual se migre automáticamente al nuevo sistema de hashing, para no tener que reconfigurar mi acceso.

#### Acceptance Criteria

1. THE API SHALL proveer un script de migración que rehashee todas las contraseñas SHA256 existentes a bcrypt/argon2
2. WHEN se ejecuta la migración, THE API SHALL leer cada valor_hash de configuracion_seguridad
3. THE API SHALL marcar las contraseñas migradas con un flag temporal para permitir login híbrido durante transición
4. WHEN un usuario con contraseña SHA256 hace login exitoso, THE Authentication_System SHALL rehashear automáticamente su contraseña a bcrypt/argon2
5. THE API SHALL registrar en logs cada migración de contraseña exitosa

### Requirement 3: Proteger Endpoints sin Autenticación

**User Story:** Como administrador del sistema, quiero que todos los endpoints sensibles requieran autenticación JWT, para prevenir acceso no autorizado a funcionalidades críticas.

#### Acceptance Criteria

1. THE API SHALL requerir autenticación JWT válida en todos los endpoints de /citas
2. THE API SHALL requerir autenticación JWT válida en todos los endpoints de /upload
3. THE API SHALL requerir autenticación JWT válida en POST /movimiento-caja/crear-movimiento-caja
4. THE API SHALL requerir autenticación JWT válida en POST /movimiento-caja/cobro-rapido
5. THE API SHALL requerir autenticación JWT válida en GET /info
6. WHEN un request sin token JWT válido intenta acceder a endpoint protegido, THE API SHALL retornar HTTP 401 Unauthorized
7. THE API SHALL mantener endpoints públicos: POST /auth/login, GET /health, GET /docs
8. THE API SHALL documentar en OpenAPI qué endpoints requieren autenticación

### Requirement 4: Eliminar Exposición de Información Sensible

**User Story:** Como desarrollador del sistema, quiero que mis datos personales no estén expuestos públicamente, para proteger mi privacidad.

#### Acceptance Criteria

1. THE API SHALL remover el endpoint GET /info o requerir autenticación para accederlo
2. IF GET /info se mantiene, THE API SHALL retornar solo información no sensible del sistema (versión, estado)
3. THE API SHALL no incluir en responses públicas: nombres personales, teléfonos, correos del desarrollador
4. THE API SHALL no exponer stack traces completos en responses de producción
5. THE API SHALL configurar variable de entorno ENVIRONMENT para distinguir dev/production

### Requirement 5: Mejorar Seguridad de Contraseña PDF

**User Story:** Como usuario que genera PDFs, quiero que la contraseña no se envíe por query parameter, para evitar que quede expuesta en logs y historial del navegador.

#### Acceptance Criteria

1. THE API SHALL aceptar la contraseña PDF únicamente por header X-PDF-Password
2. THE API SHALL rechazar requests con contraseña PDF en query parameter ?token=
3. THE API SHALL retornar HTTP 400 Bad Request si se intenta usar query parameter para contraseña
4. THE Web_Frontend SHALL enviar la contraseña PDF por header en lugar de query parameter
5. THE API SHALL documentar en OpenAPI el uso correcto del header X-PDF-Password

### Requirement 6: Mejorar Mensajes de Error de Autenticación

**User Story:** Como administrador de seguridad, quiero que los mensajes de error de autenticación no filtren información sobre la existencia de usuarios, para prevenir enumeración de cuentas.

#### Acceptance Criteria

1. WHEN un login falla, THE API SHALL retornar mensaje genérico "Credenciales inválidas" sin distinguir si usuario existe o contraseña es incorrecta
2. WHEN se intenta recuperar contraseña con palabra clave incorrecta, THE API SHALL retornar mensaje genérico sin confirmar existencia de configuración
3. THE API SHALL usar timing constante en validación de credenciales para prevenir timing attacks
4. THE API SHALL registrar intentos fallidos de login en audit trail sin exponer información en response
5. THE API SHALL implementar rate limiting de 5 intentos por minuto en endpoints de autenticación

### Requirement 7: Unificar Lógica Duplicada entre ticket_ruta y mobile_api_ruta

**User Story:** Como desarrollador, quiero que la lógica de negocio de tickets esté en un solo lugar, para evitar inconsistencias y facilitar mantenimiento.

#### Acceptance Criteria

1. THE Service_Layer SHALL contener toda la lógica de creación, actualización y finalización de tickets
2. THE Service_Layer SHALL contener toda la lógica de cálculo de saldo_pendiente
3. THE Service_Layer SHALL contener toda la lógica de transiciones de estado de tickets
4. THE ticket_ruta SHALL delegar toda lógica de negocio al Service_Layer
5. THE mobile_api_ruta SHALL delegar toda lógica de negocio al Service_Layer
6. THE Service_Layer SHALL tener tests unitarios que cubran al menos 80% de la lógica
7. WHEN se modifica una regla de negocio, THE Service_Layer SHALL ser el único lugar que requiere cambios

### Requirement 8: Extraer Lógica de Negocio a Capa de Servicios

**User Story:** Como desarrollador, quiero que las rutas solo manejen HTTP y deleguen lógica de negocio a servicios, para mejorar testabilidad y separación de responsabilidades.

#### Acceptance Criteria

1. THE API SHALL crear servicios: TicketService, CitaService, MovimientoCajaService, VehiculoService
2. THE Service_Layer SHALL contener toda lógica de validaciones de negocio
3. THE Service_Layer SHALL contener toda lógica de cálculos financieros
4. THE Service_Layer SHALL contener toda lógica de creación de MovimientoCaja
5. THE rutas SHALL solo manejar: parsing de requests, validación de schemas, llamadas a servicios, formateo de responses
6. THE Service_Layer SHALL recibir Session de SQLAlchemy como dependencia inyectada
7. THE Service_Layer SHALL lanzar excepciones de dominio que las rutas conviertan a HTTPException

### Requirement 9: Implementar Capa de Repositorio

**User Story:** Como desarrollador, quiero una capa de repositorio que abstraiga el acceso a datos, para facilitar testing con mocks y reutilización de queries.

#### Acceptance Criteria

1. THE Repository_Layer SHALL proveer repositorios: TicketRepository, CitaRepository, VehiculoRepository, MovimientoCajaRepository
2. THE Repository_Layer SHALL encapsular todas las queries de SQLAlchemy
3. THE Repository_Layer SHALL proveer métodos: get_by_id, get_all, create, update, delete, find_by_criteria
4. THE Service_Layer SHALL usar repositorios en lugar de queries directas a db.query()
5. THE Repository_Layer SHALL ser fácilmente mockeable para tests unitarios
6. THE Repository_Layer SHALL manejar paginación de forma consistente

### Requirement 10: Mejorar Consistencia REST

**User Story:** Como consumidor de la API, quiero que los endpoints sigan convenciones REST consistentes, para tener una experiencia predecible.

#### Acceptance Criteria

1. THE API SHALL cambiar DELETE /citas/{id} a PATCH /citas/{id} con body {"estado": "CANCELADA"}
2. THE API SHALL cambiar PUT /mecanicos/{id} a PATCH /mecanicos/{id} con body {"activo": false}
3. THE API SHALL usar snake_case consistentemente en todas las URLs (cambiar /cobro-rapido a /cobro_rapido)
4. WHEN un DELETE es exitoso, THE API SHALL retornar HTTP 204 No Content sin body
5. WHEN un POST/PUT/PATCH es exitoso, THE API SHALL retornar el objeto completo creado/actualizado
6. THE API SHALL usar HTTP status codes correctos: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 422 Unprocessable Entity
7. THE API SHALL documentar en OpenAPI los status codes posibles para cada endpoint

### Requirement 11: Corregir Uso de datetime Deprecado

**User Story:** Como desarrollador, quiero usar APIs de datetime no deprecadas, para asegurar compatibilidad con Python 3.12+.

#### Acceptance Criteria

1. THE API SHALL reemplazar todas las llamadas a datetime.utcnow() con datetime.now(timezone.utc)
2. THE API SHALL usar timezone-aware datetimes en todos los modelos
3. THE API SHALL configurar SQLAlchemy para usar DateTime(timezone=True)
4. THE API SHALL validar en tests que todos los datetimes sean timezone-aware
5. THE API SHALL documentar en guía de desarrollo el uso correcto de datetimes

### Requirement 12: Optimizar Query de Histórico Económico

**User Story:** Como usuario que consulta histórico económico, quiero que la consulta sea rápida, para no esperar cuando hay muchos días de datos.

#### Acceptance Criteria

1. THE API SHALL reemplazar el loop while con una sola query usando GROUP BY DATE(fecha)
2. THE API SHALL usar agregaciones SQL (SUM, COUNT) en lugar de iterar en Python
3. WHEN se consulta histórico de 30 días, THE API SHALL ejecutar máximo 1 query a la base de datos
4. THE API SHALL retornar resultados en menos de 500ms para rangos de hasta 90 días
5. THE API SHALL agregar índice en columna fecha de movimiento_caja si no existe

### Requirement 13: Mejorar Manejo de multipart/form-data

**User Story:** Como desarrollador, quiero usar mecanismos nativos de FastAPI para manejar multipart/form-data, para simplificar el código y reducir errores.

#### Acceptance Criteria

1. THE API SHALL usar parámetros Form() y File() de FastAPI en lugar de parsear manualmente request.form()
2. THE API SHALL eliminar condicionales if "multipart/form-data" in content_type
3. THE API SHALL definir endpoints separados si JSON y multipart tienen schemas diferentes
4. THE API SHALL validar automáticamente tipos de datos con Pydantic en Form()
5. THE API SHALL documentar automáticamente en OpenAPI los parámetros de form-data

### Requirement 14: Implementar Sistema de Roles y Permisos

**User Story:** Como administrador del sistema, quiero definir roles con permisos específicos, para controlar qué usuarios pueden realizar qué acciones.

#### Acceptance Criteria

1. THE API SHALL definir roles: ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA
2. THE API SHALL almacenar roles de usuario en tabla users con relación many-to-many a tabla roles
3. THE Token_Manager SHALL incluir lista de roles en el payload del JWT
4. THE Auth_Middleware SHALL proveer decorador @require_role("ADMIN") para proteger endpoints
5. WHEN un usuario sin rol requerido intenta acceder a endpoint, THE API SHALL retornar HTTP 403 Forbidden
6. THE API SHALL permitir a ADMIN gestionar roles de otros usuarios
7. THE API SHALL registrar en Audit_Trail todos los cambios de roles

### Requirement 15: Implementar Audit Trail Completo

**User Story:** Como auditor del sistema, quiero un registro completo de todas las acciones de usuarios, para rastrear cambios y detectar actividad sospechosa.

#### Acceptance Criteria

1. THE API SHALL registrar en audit_log: user_id, action, resource_type, resource_id, timestamp, ip_address, user_agent
2. THE API SHALL registrar eventos: LOGIN, LOGOUT, CREATE, UPDATE, DELETE, ESTADO_CHANGE
3. THE API SHALL registrar cambios en datos sensibles: contraseñas, configuración de seguridad, roles
4. THE API SHALL registrar intentos fallidos de autenticación con IP y timestamp
5. THE Audit_Trail SHALL ser inmutable (solo INSERT, no UPDATE/DELETE)
6. THE API SHALL proveer endpoint GET /audit-log con filtros por usuario, fecha, acción (solo para ADMIN)
7. THE API SHALL retener logs de auditoría por al menos 1 año

### Requirement 16: Implementar Rate Limiting Granular

**User Story:** Como administrador del sistema, quiero rate limiting configurable por endpoint y usuario, para prevenir abuso y ataques de fuerza bruta.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL limitar endpoints de autenticación a 5 requests/minuto por IP
2. THE Rate_Limiter SHALL limitar endpoints de creación a 30 requests/minuto por usuario autenticado
3. THE Rate_Limiter SHALL limitar endpoints de lectura a 100 requests/minuto por usuario autenticado
4. WHEN se excede el límite, THE API SHALL retornar HTTP 429 Too Many Requests con header Retry-After
5. THE Rate_Limiter SHALL usar Redis o memoria para almacenar contadores
6. THE Rate_Limiter SHALL permitir configurar límites por variable de entorno
7. THE API SHALL excluir de rate limiting a IPs en whitelist configurable

### Requirement 17: Migrar Clientes a JWT

**User Story:** Como usuario de la app móvil y web, quiero que mi sesión se mantenga activa de forma segura, para no tener que autenticarme constantemente.

#### Acceptance Criteria

1. THE Mobile_App SHALL almacenar access_token y refresh_token en almacenamiento seguro (Keychain/Keystore)
2. THE Mobile_App SHALL incluir access_token en header Authorization: Bearer {token} en cada request
3. WHEN access_token expira, THE Mobile_App SHALL usar refresh_token para obtener nuevo access_token automáticamente
4. THE Web_Frontend SHALL almacenar tokens en httpOnly cookies o localStorage según configuración
5. THE Web_Frontend SHALL implementar interceptor que refresque token automáticamente antes de expiración
6. THE Mobile_App y Web_Frontend SHALL redirigir a login cuando refresh_token expira
7. THE Mobile_App y Web_Frontend SHALL limpiar tokens al hacer logout

### Requirement 18: Implementar Gestión de Usuarios

**User Story:** Como administrador, quiero gestionar usuarios del sistema (crear, editar, desactivar), para controlar quién tiene acceso.

#### Acceptance Criteria

1. THE API SHALL proveer endpoint POST /users para crear usuarios con username, password, email, roles
2. THE API SHALL proveer endpoint GET /users para listar usuarios (solo ADMIN)
3. THE API SHALL proveer endpoint GET /users/{id} para obtener detalles de usuario
4. THE API SHALL proveer endpoint PATCH /users/{id} para actualizar usuario
5. THE API SHALL proveer endpoint DELETE /users/{id} para desactivar usuario (soft delete)
6. THE API SHALL validar que username sea único
7. THE API SHALL validar que email tenga formato válido
8. THE API SHALL requerir contraseña de al menos 8 caracteres con al menos 1 mayúscula, 1 minúscula, 1 número
9. THE API SHALL permitir a usuarios cambiar su propia contraseña con POST /users/me/change-password
10. THE API SHALL requerir contraseña actual para cambiar a nueva contraseña

### Requirement 19: Implementar Recuperación de Contraseña Segura

**User Story:** Como usuario que olvidó su contraseña, quiero recuperarla de forma segura, para recuperar acceso a mi cuenta.

#### Acceptance Criteria

1. THE API SHALL proveer endpoint POST /auth/forgot-password que acepte email
2. WHEN se solicita recuperación, THE API SHALL generar token de recuperación único con expiración de 1 hora
3. THE API SHALL enviar email con link de recuperación conteniendo el token
4. THE API SHALL proveer endpoint POST /auth/reset-password que acepte token y nueva contraseña
5. WHEN se usa token de recuperación, THE API SHALL invalidarlo inmediatamente
6. THE API SHALL limitar solicitudes de recuperación a 3 por hora por email
7. THE API SHALL no revelar si el email existe en el sistema en la response

### Requirement 20: Implementar Validación de Tokens en Lista Negra

**User Story:** Como administrador de seguridad, quiero que los tokens de usuarios que hicieron logout o fueron desactivados no funcionen, para prevenir uso de tokens robados.

#### Acceptance Criteria

1. THE API SHALL mantener lista negra de tokens JWT invalidados en Redis o base de datos
2. WHEN un usuario hace logout, THE API SHALL agregar su refresh_token a lista negra
3. WHEN un usuario es desactivado, THE API SHALL agregar todos sus tokens activos a lista negra
4. THE Auth_Middleware SHALL verificar que el token no esté en lista negra antes de aceptarlo
5. THE API SHALL limpiar automáticamente tokens expirados de la lista negra cada 24 horas
6. THE API SHALL usar jti (JWT ID) único para identificar tokens en lista negra
7. THE API SHALL proveer endpoint POST /auth/revoke-token para que ADMIN invalide tokens de otros usuarios

### Requirement 21: Implementar Tests de Seguridad

**User Story:** Como desarrollador, quiero tests automatizados que validen la seguridad del sistema, para detectar regresiones.

#### Acceptance Criteria

1. THE API SHALL tener tests que validen que endpoints protegidos rechazan requests sin token
2. THE API SHALL tener tests que validen que tokens expirados son rechazados
3. THE API SHALL tener tests que validen que tokens con firma inválida son rechazados
4. THE API SHALL tener tests que validen que tokens en lista negra son rechazados
5. THE API SHALL tener tests que validen rate limiting funciona correctamente
6. THE API SHALL tener tests que validen que roles y permisos funcionan correctamente
7. THE API SHALL tener tests que validen que contraseñas son hasheadas correctamente
8. THE API SHALL tener tests que validen que mensajes de error no filtran información

### Requirement 22: Documentar Cambios de API para Clientes

**User Story:** Como desarrollador de clientes (móvil/web), quiero documentación clara de los cambios en la API, para migrar correctamente a JWT.

#### Acceptance Criteria

1. THE API SHALL proveer documento de migración con ejemplos de código para móvil y web
2. THE API SHALL documentar en OpenAPI todos los endpoints nuevos de autenticación
3. THE API SHALL documentar formato del header Authorization: Bearer {token}
4. THE API SHALL proveer ejemplos de manejo de refresh token
5. THE API SHALL documentar códigos de error y cómo manejarlos
6. THE API SHALL proveer guía de migración paso a paso desde sistema actual
7. THE API SHALL mantener compatibilidad temporal con sistema antiguo durante período de transición configurable

### Requirement 23: Implementar Monitoreo de Seguridad

**User Story:** Como administrador del sistema, quiero alertas automáticas de eventos de seguridad sospechosos, para responder rápidamente a amenazas.

#### Acceptance Criteria

1. THE API SHALL detectar y alertar: múltiples intentos fallidos de login desde misma IP
2. THE API SHALL detectar y alertar: acceso desde ubicación geográfica inusual
3. THE API SHALL detectar y alertar: uso de token después de logout
4. THE API SHALL detectar y alertar: múltiples solicitudes de recuperación de contraseña
5. THE API SHALL enviar alertas por email o webhook configurable
6. THE API SHALL proveer dashboard de métricas de seguridad para ADMIN
7. THE API SHALL registrar todas las alertas en audit_log

### Requirement 24: Implementar Configuración de Seguridad

**User Story:** Como administrador del sistema, quiero configurar políticas de seguridad sin modificar código, para adaptar el sistema a diferentes entornos.

#### Acceptance Criteria

1. THE API SHALL permitir configurar por variable de entorno: JWT_ACCESS_TOKEN_EXPIRE_MINUTES
2. THE API SHALL permitir configurar por variable de entorno: JWT_REFRESH_TOKEN_EXPIRE_DAYS
3. THE API SHALL permitir configurar por variable de entorno: PASSWORD_MIN_LENGTH
4. THE API SHALL permitir configurar por variable de entorno: MAX_LOGIN_ATTEMPTS
5. THE API SHALL permitir configurar por variable de entorno: RATE_LIMIT_PER_MINUTE
6. THE API SHALL permitir configurar por variable de entorno: SESSION_TIMEOUT_MINUTES
7. THE API SHALL validar todas las configuraciones al iniciar y fallar rápido si son inválidas
8. THE API SHALL documentar todas las variables de entorno en README.md

### Requirement 25: Implementar Modo Offline y Sincronización en App Móvil

**User Story:** Como mecánico usando la app móvil en el taller, quiero que la app funcione sin conexión a internet y sincronice automáticamente cuando se recupere la conexión, para no perder productividad cuando hay problemas de red.

#### Acceptance Criteria

1. THE Mobile_App SHALL almacenar datos localmente usando SQLite o AsyncStorage cuando no hay conexión
2. THE Mobile_App SHALL detectar automáticamente cuando se pierde y recupera la conexión a internet
3. WHEN se pierde la conexión, THE Mobile_App SHALL permitir crear, editar y visualizar tickets en modo offline
4. WHEN se pierde la conexión, THE Mobile_App SHALL encolar operaciones de escritura (crear ticket, agregar foto, finalizar ticket) para sincronización posterior
5. WHEN se recupera la conexión, THE Mobile_App SHALL sincronizar automáticamente todas las operaciones pendientes en orden cronológico
6. THE Mobile_App SHALL mostrar indicador visual del estado de conexión (online/offline/sincronizando)
7. THE Mobile_App SHALL mostrar contador de operaciones pendientes de sincronización
8. WHEN una sincronización falla, THE Mobile_App SHALL reintentar con backoff exponencial (1s, 2s, 4s, 8s, máximo 30s)
9. THE Mobile_App SHALL resolver conflictos de sincronización usando estrategia "last write wins" con timestamp del servidor
10. THE Mobile_App SHALL permitir al usuario ver y gestionar operaciones pendientes de sincronización
11. THE Mobile_App SHALL mantener caché local de datos frecuentemente accedidos (lista de tickets, vehículos, mecánicos)
12. THE Mobile_App SHALL limpiar caché local después de sincronización exitosa de datos antiguos (>7 días)
13. THE API SHALL proveer endpoint POST /api/mobile/sync/batch para sincronización por lotes
14. THE API SHALL retornar en respuesta de sincronización: operaciones exitosas, fallidas, y conflictos detectados
15. THE API SHALL validar que operaciones sincronizadas tengan timestamp válido y no sean demasiado antiguas (>30 días)

## Special Requirements Guidance

### Parser and Serializer Requirements

Este proyecto no requiere parsers o serializers personalizados más allá de los provistos por Pydantic y FastAPI.

### Round-Trip Properties

Para validar la correcta implementación de JWT:

1. FOR ALL tokens JWT válidos, decodificar y codificar con la misma clave SHALL producir un token equivalente
2. FOR ALL contraseñas, hashear y verificar con bcrypt SHALL retornar True para la contraseña original
3. FOR ALL usuarios autenticados, obtener token, hacer request, y validar identidad SHALL retornar el mismo user_id

## Iteration and Feedback

Este documento está sujeto a revisión y refinamiento basado en feedback del equipo de desarrollo y stakeholders.
