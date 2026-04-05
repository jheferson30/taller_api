# Plan de Implementación: Mejoras de Seguridad JWT y Auditoría

## Resumen

Este plan implementa la migración completa del sistema de autenticación SHA256 a JWT con bcrypt, sistema de roles y permisos, audit trail completo, rate limiting granular, arquitectura en capas, y modo offline para la app móvil. El plan está organizado en fases incrementales que minimizan breaking changes y permiten validación continua.

## Tareas

### Fase 1: Infraestructura Base y Modelos

- [ ] 1. Crear migración de base de datos y modelos SQLAlchemy
  - [x] 1.1 Crear script de migración SQL con tablas: users, roles, user_roles, audit_log, token_blacklist, password_reset_tokens
    - Incluir todos los índices especificados en el diseño
    - Agregar índice a movimientos_caja.fecha_creacion
    - Insertar roles por defecto: ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA
    - _Requirements: 14.1, 14.2, 15.1, 20.1, 12.5_
  
  - [x] 1.2 Crear modelos SQLAlchemy en app/modelos/
    - Crear User model con relación a roles
    - Crear Role y UserRole models
    - Crear AuditLog model (inmutable)
    - Crear TokenBlacklist model
    - Crear PasswordResetToken model
    - Usar DateTime(timezone=True) en todos los timestamps
    - _Requirements: 14.2, 15.1, 20.1, 11.3_
  
  - [ ]* 1.3 Escribir property test para modelos de datos
    - **Property 23: Timezone-aware datetimes**
    - **Valida: Requirements 11.2**

### Fase 2: Componentes de Autenticación Core

- [ ] 2. Implementar Password Hasher y Token Manager
  - [x] 2.1 Crear app/seguridad/password_hasher.py con clase PasswordHasher
    - Implementar hash_password() usando bcrypt con cost factor 12
    - Implementar verify_password() con timing-safe comparison
    - Generar salt único automáticamente
    - _Requirements: 1.1, 1.2_
  
  - [x]* 2.2 Escribir property tests para PasswordHasher
    - **Property 1: Password hashing produces verifiable hashes**
    - **Valida: Requirements 1.1**
  
  - [x]* 2.3 Escribir property test para unique salt generation
    - **Property 2: Unique salt generation**
    - **Valida: Requirements 1.2**
  
  - [x] 2.4 Crear app/seguridad/token_manager.py con clase TokenManager
    - Implementar generate_access_token() con expiración 15 minutos
    - Implementar generate_refresh_token() con expiración 7 días
    - Implementar decode_token() con validación de firma y expiración
    - Incluir en payload: user_id, username, roles, exp, iat, jti (UUID)
    - Usar JWT_SECRET_KEY de variable de entorno
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.7_
  
  - [x]* 2.5 Escribir property tests para TokenManager
    - **Property 3: Access token expiration time**
    - **Property 4: Refresh token expiration time**
    - **Property 5: JWT token verification round-trip**
    - **Property 6: JWT payload completeness**
    - **Property 48: Unique JWT ID**
    - **Valida: Requirements 1.3, 1.4, 1.5, 1.6, 20.6**

### Fase 3: Capa de Repositorio




- [x] 3. Implementar repositorios de acceso a datos
  - [x] 3.1 Crear app/repositorios/user_repository.py
    - Implementar UserRepository con métodos: get_by_id, get_by_username, get_by_email, get_all, create, update, delete (soft)
    - Incluir paginación en get_all
    - _Requirements: 9.1, 9.2, 9.3, 9.6_
  
  - [x] 3.2 Crear app/repositorios/role_repository.py
    - Implementar RoleRepository con métodos básicos CRUD
    - _Requirements: 9.1, 9.2_
  
  - [x] 3.3 Crear app/repositorios/audit_log_repository.py
    - Implementar AuditLogRepository con SOLO métodos create y read (inmutable)
    - Implementar get_by_user, get_by_action, get_by_date_range con paginación
    - NO implementar update() ni delete()
    - _Requirements: 9.1, 9.2, 15.5_
  
  - [x] 3.4 Crear app/repositorios/token_blacklist_repository.py
    - Implementar TokenBlacklistRepository con métodos: add_to_blacklist, is_blacklisted, cleanup_expired
    - Optimizar is_blacklisted con índice en jti
    - _Requirements: 9.1, 9.2, 20.1_
  
  - [x] 3.5 Crear app/repositorios/password_reset_repository.py
    - Implementar PasswordResetTokenRepository con métodos CRUD
    - _Requirements: 9.1, 9.2_
  
  - [ ]* 3.6 Escribir unit tests para repositorios
    - Test de paginación consistente
    - Test de soft delete en UserRepository
    - Test de inmutabilidad en AuditLogRepository
    - _Requirements: 9.6_

### Fase 4: Capa de Servicios Core

- [ ] 4. Implementar AuditService
  - [x] 4.1 Crear app/servicios/audit_service.py
    - Implementar log_event() con todos los campos requeridos
    - Soportar eventos: LOGIN, LOGOUT, LOGIN_FAILED, USER_CREATE, USER_UPDATE, USER_DEACTIVATE, ROLE_CHANGE, PASSWORD_CHANGE, PASSWORD_RESET, TICKET_CREATE, TICKET_UPDATE, TICKET_FINALIZE, CONFIG_CHANGE
    - _Requirements: 15.1, 15.2, 15.3_
  
  - [ ]* 4.2 Escribir property tests para AuditService
    - **Property 29: Audit log completeness**
    - **Property 30: Sensitive data changes are audited**
    - **Property 31: Failed authentication attempts are audited with IP**
    - **Property 32: Audit trail immutability**
    - **Valida: Requirements 15.1, 15.2, 15.3, 15.4, 15.5**

- [x] 5. Implementar AuthService
  - [x] 5.1 Crear app/servicios/auth_service.py
    - Implementar authenticate() con verificación de contraseña y generación de tokens
    - Implementar migración automática de SHA256 a bcrypt en login exitoso
    - Implementar refresh_access_token() con validación de blacklist
    - Implementar logout() que agrega token a blacklist
    - Implementar forgot_password() con generación de token de recuperación
    - Implementar reset_password() con validación y uso único de token
    - Usar mensajes de error genéricos para prevenir enumeración
    - Registrar todos los eventos en audit_log
    - _Requirements: 1.3, 1.4, 1.8, 1.9, 1.10, 2.4, 6.1, 6.2, 6.4, 19.1-19.7_
  
  - [ ]* 5.2 Escribir property tests para AuthService
    - **Property 7: Token validation rejects invalid tokens**
    - **Property 8: Logout invalidates refresh token**
    - **Property 9: Automatic password migration on login**
    - **Property 10: Password migration logging**
    - **Property 12: Generic authentication error messages**
    - **Property 14: Failed login attempts are audited**
    - **Property 45: Logout blacklists refresh token**
    - **Valida: Requirements 1.7, 1.10, 2.4, 2.5, 6.1, 6.4, 20.2**
  
  - [ ]* 5.3 Escribir unit tests para AuthService
    - Test login exitoso retorna tokens
    - Test login con username inválido retorna error genérico
    - Test login con password incorrecta retorna error genérico
    - Test refresh token válido genera nuevo access token
    - Test refresh token blacklisted falla
    - Test logout agrega token a blacklist
    - Test forgot_password no revela si email existe
    - Test reset_password invalida token después de uso
    - _Requirements: 1.8, 1.9, 1.10, 6.1, 19.1-19.7_

- [x] 6. Implementar UserService
  - [x] 6.1 Crear app/servicios/user_service.py
    - Implementar create_user() con validaciones de username único, email válido, password complejo
    - Implementar update_user_roles() con registro en audit_log
    - Implementar deactivate_user() que invalida todos los tokens del usuario
    - Implementar change_password() que requiere contraseña actual
    - _Requirements: 18.1-18.10, 14.7_
  
  - [ ]* 6.2 Escribir property tests para UserService
    - **Property 28: Role changes are audited**
    - **Property 37: Username uniqueness validation**
    - **Property 38: Email format validation**
    - **Property 39: Password complexity validation**
    - **Property 40: Password change requires current password**
    - **Property 46: User deactivation blacklists all tokens**
    - **Valida: Requirements 14.7, 18.6, 18.7, 18.8, 18.10, 20.3**
  
  - [ ]* 6.3 Escribir unit tests para UserService
    - Test create_user con datos válidos
    - Test create_user con username duplicado lanza error
    - Test create_user con email duplicado lanza error
    - Test create_user con email inválido lanza ValidationError
    - Test create_user con password débil lanza ValidationError
    - Test update_user_roles crea audit log
    - Test deactivate_user invalida tokens
    - _Requirements: 18.1-18.10_

### Fase 5: Middleware y Decoradores de Autenticación

- [ ] 7. Implementar Auth Middleware y decoradores
  - [x] 7.1 Crear app/seguridad/auth_middleware.py
    - Implementar AuthMiddleware que extrae token del header Authorization
    - Validar token con TokenManager
    - Verificar que token no esté en blacklist
    - Inyectar user context en request.state.user
    - Retornar 401 si token inválido/expirado/faltante
    - _Requirements: 1.7, 3.6, 20.4_
  
  - [x] 7.2 Implementar decoradores @require_auth y @require_role
    - Crear decorador require_auth para endpoints que requieren autenticación
    - Crear decorador require_role(*roles) para control de acceso basado en roles
    - Retornar 403 si usuario no tiene rol requerido
    - _Requirements: 14.4, 14.5_
  
  - [ ] 7.3 Escribir property tests para Auth Middleware
    - **Property 11: Protected endpoints require authentication**
    - **Property 27: Role-based access control**
    - **Property 47: Blacklist verification in token validation**
    - **Valida: Requirements 3.1-3.6, 14.4, 14.5, 20.4**
  
  - [ ]* 7.4 Escribir unit tests para Auth Middleware
    - Test request con token válido pasa
    - Test request sin token retorna 401
    - Test request con token expirado retorna 401
    - Test request con token blacklisted retorna 401
    - Test require_role permite usuario con rol correcto
    - Test require_role bloquea usuario sin rol correcto (403)
    - _Requirements: 1.7, 3.6, 14.4, 14.5_

### Fase 6: Endpoints de Autenticación

- [-] 8. Crear endpoints de autenticación en app/rutas/auth_ruta.py
  - [x] 8.1 Implementar POST /auth/login
    - Validar schema con Pydantic
    - Llamar a AuthService.authenticate()
    - Retornar access_token, refresh_token, user
    - Capturar IP y user agent del request
    - _Requirements: 1.8_
  
  - [x] 8.2 Implementar POST /auth/refresh
    - Validar refresh_token
    - Llamar a AuthService.refresh_access_token()
    - Retornar nuevo access_token
    - _Requirements: 1.9_
  
  - [x] 8.3 Implementar POST /auth/logout
    - Requerir autenticación con @require_auth
    - Llamar a AuthService.logout()
    - Retornar 204 No Content
    - _Requirements: 1.10_
  
  - [x] 8.4 Implementar POST /auth/forgot-password
    - Validar email
    - Llamar a AuthService.forgot_password()
    - Retornar mensaje genérico sin revelar si email existe
    - _Requirements: 19.1, 19.7_
  
  - [x] 8.5 Implementar POST /auth/reset-password
    - Validar token y nueva contraseña
    - Llamar a AuthService.reset_password()
    - Retornar mensaje de éxito
    - _Requirements: 19.4_
  
  - [ ]* 8.6 Escribir property tests para endpoints de autenticación
    - **Property 13: Generic password recovery error messages**
    - **Property 41: Password reset token expiration**
    - **Property 42: Password reset token single use**
    - **Property 44: Password reset email enumeration prevention**
    - **Valida: Requirements 6.2, 19.2, 19.5, 19.7**

### Fase 7: Endpoints de Gestión de Usuarios

- [-] 9. Crear endpoints de usuarios en app/rutas/users_ruta.py
  - [x] 9.1 Implementar POST /users (requiere rol ADMIN)
    - Validar schema con Pydantic
    - Llamar a UserService.create_user()
    - Retornar 201 Created con usuario creado
    - _Requirements: 18.1_
  
  - [x] 9.2 Implementar GET /users (requiere rol ADMIN)
    - Soportar paginación con query params skip y limit
    - Llamar a UserRepository.get_all()
    - Retornar lista de usuarios y total
    - _Requirements: 18.2_
  
  - [x] 9.3 Implementar GET /users/{id}
    - Permitir a usuarios ver su propio perfil
    - Requerir ADMIN para ver otros usuarios
    - _Requirements: 18.3_
  
  - [x] 9.4 Implementar PATCH /users/{id} (requiere rol ADMIN)
    - Permitir actualizar email y roles
    - Llamar a UserService.update_user_roles() si se cambian roles
    - Retornar usuario actualizado
    - _Requirements: 18.4_
  
  - [x] 9.5 Implementar DELETE /users/{id} (requiere rol ADMIN)
    - Soft delete: marcar usuario como inactivo
    - Llamar a UserService.deactivate_user()
    - Retornar 204 No Content
    - _Requirements: 18.5, 10.4_
  
  - [x] 9.6 Implementar POST /users/me/change-password
    - Requerir autenticación
    - Validar contraseña actual
    - Llamar a UserService.change_password()
    - _Requirements: 18.9, 18.10_

### Fase 8: Rate Limiting

- [-] 10. Implementar rate limiting con slowapi
  - [x] 10.1 Configurar slowapi en app/main.py
    - Instalar slowapi y configurar limiter
    - Configurar storage backend (memoria o Redis)
    - Leer límites de variables de entorno
    - _Requirements: 16.5, 16.6_
  
  - [x] 10.2 Aplicar rate limiting a endpoints de autenticación
    - POST /auth/login: 5 requests/minuto por IP
    - POST /auth/refresh: 10 requests/minuto por IP
    - POST /auth/forgot-password: 3 requests/hora por email
    - Retornar 429 Too Many Requests con header Retry-After
    - _Requirements: 16.1, 16.4, 19.6_
  
  - [x] 10.3 Aplicar rate limiting a endpoints de creación
    - 30 requests/minuto por usuario autenticado
    - _Requirements: 16.2_
  
  - [x] 10.4 Aplicar rate limiting a endpoints de lectura
    - 100 requests/minuto por usuario autenticado
    - _Requirements: 16.3_
  
  - [x] 10.5 Implementar whitelist de IPs
    - Leer IPs de variable de entorno RATE_LIMIT_WHITELIST_IPS
    - Excluir IPs whitelisted de rate limiting
    - _Requirements: 16.7_
  
  - [ ]* 10.6 Escribir property tests para rate limiting
    - **Property 15: Authentication rate limiting**
    - **Property 33: Rate limiting for authentication endpoints**
    - **Property 34: Rate limiting for creation endpoints**
    - **Property 35: Rate limiting for read endpoints**
    - **Property 36: Whitelist exemption from rate limiting**
    - **Property 43: Password reset rate limiting**
    - **Valida: Requirements 6.5, 16.1, 16.2, 16.3, 16.4, 16.7, 19.6**

### Fase 9: Script de Migración de Contraseñas

- [x] 11. Crear script de migración de contraseñas existentes
  - [x] 11.1 Crear scripts/migrate_passwords.py
    - Leer registros de configuracion_seguridad
    - Para cada contraseña, crear usuario en tabla users con hash SHA256 temporal
    - Marcar is_migrated=False
    - Asignar rol ADMIN por defecto
    - Registrar cada migración en audit_log
    - Generar reporte de migración
    - _Requirements: 2.1, 2.2, 2.3, 2.5_

- [x] 12. Checkpoint - Validar infraestructura de autenticación
  - Ejecutar migración de base de datos
  - Ejecutar script de migración de contraseñas
  - Ejecutar todos los tests de autenticación
  - Verificar que login, refresh y logout funcionan correctamente
  - Preguntar al usuario si hay dudas o problemas

### Fase 10: Refactoring a Arquitectura en Capas

- [x] 13. Extraer lógica de negocio de tickets a TicketService
  - [x] 13.1 Crear app/servicios/ticket_service.py
    - Implementar calcular_saldo_pendiente()
    - Implementar finalizar_ticket() con creación de MovimientoCaja
    - Implementar entregar_ticket() con validaciones de estado
    - Consolidar lógica duplicada entre ticket_ruta y mobile_api_ruta
    - Registrar eventos en audit_log
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4_
  
  - [x] 13.2 Refactorizar app/rutas/ticket_ruta.py para usar TicketService
    - Delegar toda lógica de negocio a TicketService
    - Mantener solo: parsing de requests, validación de schemas, formateo de responses
    - _Requirements: 7.4, 7.5, 8.5_
  
  - [x] 13.3 Refactorizar app/rutas/mobile_api_ruta.py para usar TicketService
    - Delegar toda lógica de negocio a TicketService
    - Eliminar código duplicado
    - _Requirements: 7.4, 7.5, 8.5_
  
  - [ ]* 13.4 Escribir unit tests para TicketService
    - Test calcular_saldo_pendiente con diferentes escenarios
    - Test finalizar_ticket crea MovimientoCaja correcto
    - Test entregar_ticket valida estado FINALIZADO
    - Test transiciones de estado inválidas lanzan error
    - _Requirements: 7.6, 8.1-8.4_

- [x] 14. Crear servicios adicionales
  - [x] 14.1 Crear app/servicios/cita_service.py
    - Extraer lógica de negocio de citas_ruta
    - Implementar validaciones de negocio
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 14.2 Crear app/servicios/movimiento_caja_service.py
    - Extraer lógica de cálculos financieros
    - Implementar validaciones de negocio
    - _Requirements: 8.1, 8.3, 8.4_
  
  - [x] 14.3 Crear app/servicios/vehiculo_service.py
    - Extraer lógica de negocio de vehiculos
    - Implementar validaciones de negocio
    - _Requirements: 8.1, 8.2_

- [x] 15. Crear repositorios adicionales
  - [x] 15.1 Crear app/repositorios/ticket_repository.py
    - Implementar métodos CRUD y find_by_criteria
    - Incluir paginación
    - _Requirements: 9.1, 9.2, 9.3, 9.6_
  
  - [x] 15.2 Crear app/repositorios/cita_repository.py
    - Implementar métodos CRUD y queries específicas
    - _Requirements: 9.1, 9.2, 9.3_
  
  - [x] 15.3 Crear app/repositorios/movimiento_caja_repository.py
    - Implementar métodos CRUD
    - Implementar get_historico_economico() con GROUP BY optimizado
    - _Requirements: 9.1, 9.2, 9.3, 12.3_
  
  - [x] 15.4 Crear app/repositorios/vehiculo_repository.py
    - Implementar métodos CRUD y búsqueda por placa
    - _Requirements: 9.1, 9.2, 9.3_

### Fase 11: Proteger Endpoints Existentes

- [x] 16. Agregar autenticación JWT a endpoints sensibles
  - [x] 16.1 Proteger endpoints de citas en app/rutas/citas_ruta.py
    - Agregar @require_auth a todos los endpoints
    - Actualizar documentación OpenAPI
    - _Requirements: 3.1, 3.8_
  
  - [x] 16.2 Proteger endpoints de upload en app/rutas/upload_ruta.py
    - Agregar @require_auth a todos los endpoints
    - Cambiar contraseña PDF de query param a header X-PDF-Password
    - Rechazar requests con contraseña en query param (400)
    - _Requirements: 3.2, 5.1, 5.2, 5.3_
  
  - [x] 16.3 Proteger endpoints de movimiento-caja en app/rutas/movimiento_caja_ruta.py
    - Agregar @require_auth a POST /crear-movimiento-caja
    - Agregar @require_auth a POST /cobro-rapido
    - _Requirements: 3.3, 3.4_
  
  - [x] 16.4 Proteger o eliminar endpoint GET /info
    - Agregar @require_auth o eliminar endpoint
    - Si se mantiene, retornar solo información no sensible
    - Remover información personal del desarrollador
    - _Requirements: 3.5, 4.1, 4.2, 4.3_
  
  - [ ]* 16.5 Escribir property test para protección de endpoints
    - **Property 16: PDF password header enforcement**
    - **Property 17: No PII in public responses**
    - **Valida: Requirements 5.1, 5.2, 5.3, 4.3**

### Fase 12: Mejoras de Consistencia REST

- [x] 17. Mejorar convenciones REST en endpoints existentes
  - [x] 17.1 Cambiar DELETE /citas/{id} a PATCH /citas/{id} con estado CANCELADA
    - Actualizar endpoint en app/rutas/citas_ruta.py
    - Mantener DELETE como deprecated temporalmente
    - _Requirements: 10.1_
  
  - [x] 17.2 Cambiar PUT /mecanicos/{id} a PATCH /mecanicos/{id} con activo=false
    - Actualizar endpoint correspondiente
    - _Requirements: 10.2_
  
  - [x] 17.3 Cambiar URLs de kebab-case a snake_case
    - Cambiar /cobro-rapido a /cobro_rapido
    - Cambiar /movimiento-caja a /movimiento_caja
    - Mantener URLs antiguas como deprecated temporalmente
    - _Requirements: 10.3_
  
  - [x] 17.4 Estandarizar códigos de respuesta HTTP
    - DELETE exitoso retorna 204 No Content
    - POST exitoso retorna 201 Created con objeto creado
    - PATCH/PUT exitoso retorna 200 OK con objeto actualizado
    - Validar que todos los endpoints usen códigos correctos
    - _Requirements: 10.4, 10.5, 10.6_
  
  - [x] 17.5 Actualizar documentación OpenAPI
    - Documentar status codes posibles para cada endpoint
    - Documentar qué endpoints requieren autenticación
    - Documentar roles requeridos
    - _Requirements: 3.8, 10.7_
  
  - [ ]* 17.6 Escribir property tests para consistencia REST
    - **Property 19: Consistent URL naming convention**
    - **Property 20: DELETE returns 204 No Content**
    - **Property 21: POST/PUT/PATCH returns created/updated object**
    - **Property 22: Correct HTTP status codes**
    - **Valida: Requirements 10.3, 10.4, 10.5, 10.6**

### Fase 13: Optimizaciones de Performance

- [x] 18. Optimizar query de histórico económico
  - [x] 18.1 Refactorizar endpoint GET /economia/historico en app/rutas/economia_ruta.py
    - Reemplazar loop while con query GROUP BY DATE(fecha_creacion)
    - Usar agregaciones SQL (SUM, COUNT) en lugar de iterar en Python
    - Llamar a MovimientoCajaRepository.get_historico_economico()
    - _Requirements: 12.1, 12.2, 12.3_
  
  - [ ]* 18.2 Escribir property tests para optimización de histórico
    - **Property 24: Optimized historical query performance**
    - **Property 25: Historical query response time**
    - **Valida: Requirements 12.3, 12.4**
  
  - [ ]* 18.3 Escribir unit tests para histórico económico
    - Test query retorna datos correctos para 30 días
    - Test query retorna datos correctos para 90 días
    - Test performance: respuesta en <500ms para 90 días
    - _Requirements: 12.3, 12.4_

### Fase 14: Corrección de datetime Deprecado

- [x] 19. Reemplazar datetime.utcnow() con datetime.now(timezone.utc)
  - [x] 19.1 Buscar y reemplazar todas las instancias de datetime.utcnow()
    - Usar grep para encontrar todas las ocurrencias
    - Reemplazar con datetime.now(timezone.utc)
    - _Requirements: 11.1, 11.2_
  
  - [x] 19.2 Actualizar modelos SQLAlchemy para usar DateTime(timezone=True)
    - Verificar que todos los campos DateTime tengan timezone=True
    - _Requirements: 11.3_
  
  - [ ]* 19.3 Escribir tests de validación de timezone-aware datetimes
    - Test que todos los datetimes creados sean timezone-aware
    - _Requirements: 11.4_

### Fase 15: Mejora de Manejo de multipart/form-data

- [x] 20. Refactorizar endpoints con multipart/form-data
  - [x] 20.1 Actualizar endpoints en app/rutas/upload_ruta.py
    - Usar parámetros Form() y File() de FastAPI
    - Eliminar parsing manual de request.form()
    - Eliminar condicionales if "multipart/form-data" in content_type
    - _Requirements: 13.1, 13.2, 13.4_
  
  - [x] 20.2 Separar endpoints si JSON y multipart tienen schemas diferentes
    - Crear endpoints específicos para cada tipo de content
    - _Requirements: 13.3_
  
  - [ ]* 20.3 Verificar documentación OpenAPI de form-data
    - Validar que parámetros de form-data se documenten automáticamente
    - _Requirements: 13.5_

### Fase 16: Sistema de Detección de Seguridad

- [x] 21. Implementar detección de eventos de seguridad
  - [x] 21.1 Crear app/servicios/security_detection_service.py
    - Implementar detect_brute_force(): detectar >5 intentos fallidos en 10 min desde misma IP
    - Implementar detect_token_reuse(): detectar uso de token después de logout
    - Implementar detect_password_reset_abuse(): detectar >3 solicitudes en 1 hora
    - Generar alertas y registrar en audit_log
    - _Requirements: 23.1, 23.3, 23.4_
  
  - [x] 21.2 Integrar detección en AuthService
    - Llamar a SecurityDetectionService después de eventos relevantes
    - _Requirements: 23.1, 23.3, 23.4_
  
  - [ ]* 21.3 Escribir property tests para detección de seguridad
    - **Property 49: Brute force detection alert**
    - **Property 50: Token reuse after logout alert**
    - **Property 51: Password reset abuse detection alert**
    - **Property 52: Security alerts are audited**
    - **Valida: Requirements 23.1, 23.3, 23.4, 23.7**

### Fase 17: Endpoint de Audit Log

- [x] 22. Crear endpoint de consulta de audit log
  - [x] 22.1 Implementar GET /audit-log en app/rutas/audit_ruta.py
    - Requerir rol ADMIN
    - Soportar filtros: user_id, action, start_date, end_date
    - Soportar paginación con skip y limit
    - Retornar logs y total
    - _Requirements: 15.6_

- [x] 23. Checkpoint - Validar backend completo
  - Ejecutar todos los tests (unit y property)
  - Verificar cobertura de tests >75%
  - Probar flujos completos: login, crear ticket, finalizar ticket, logout
  - Verificar audit_log se está poblando correctamente
  - Verificar rate limiting funciona
  - Preguntar al usuario si hay dudas o problemas

### Fase 18: Configuración y Variables de Entorno

- [x] 24. Configurar variables de entorno y validación
  - [x] 24.1 Actualizar .env.example con todas las variables nuevas
    - JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS
    - PASSWORD_HASHER, BCRYPT_COST_FACTOR
    - PASSWORD_MIN_LENGTH, PASSWORD_REQUIRE_UPPERCASE, PASSWORD_REQUIRE_LOWERCASE, PASSWORD_REQUIRE_DIGIT
    - RATE_LIMIT_AUTH_PER_MINUTE, RATE_LIMIT_CREATE_PER_MINUTE, RATE_LIMIT_READ_PER_MINUTE, RATE_LIMIT_WHITELIST_IPS
    - ENVIRONMENT, MAX_LOGIN_ATTEMPTS, LOGIN_ATTEMPT_WINDOW_MINUTES
    - PASSWORD_RESET_TOKEN_EXPIRE_HOURS, PASSWORD_RESET_MAX_REQUESTS_PER_HOUR
    - SESSION_TIMEOUT_MINUTES, AUDIT_LOG_RETENTION_DAYS
    - ENABLE_LEGACY_AUTH (para período de transición)
    - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    - _Requirements: 24.1-24.8_
  
  - [x] 24.2 Crear app/configuracion/config_validator.py
    - Implementar validate_config() que verifica variables requeridas al iniciar
    - Validar JWT_SECRET_KEY tiene al menos 32 caracteres
    - Validar ENVIRONMENT es 'development' o 'production'
    - Fallar rápido si configuración es inválida
    - _Requirements: 24.7_
  
  - [x] 24.3 Llamar a validate_config() en app/main.py al iniciar
    - _Requirements: 24.7_

### Fase 19: Manejo de Errores Global

- [x] 25. Implementar manejo de errores consistente
  - [x] 25.1 Crear app/utils/exceptions.py con excepciones de dominio
    - InvalidCredentialsError, InsufficientPermissionsError, ValidationError, ResourceNotFoundError, DuplicateError
    - _Requirements: 8.7_
  
  - [x] 25.2 Crear global exception handler en app/main.py
    - Convertir excepciones de dominio a HTTPException con códigos apropiados
    - En producción: ocultar stack traces, retornar mensajes genéricos
    - En desarrollo: incluir stack traces para debugging
    - Registrar todos los errores con contexto completo
    - _Requirements: 4.4, 4.5_
  
  - [ ]* 25.3 Escribir property test para manejo de errores
    - **Property 18: No stack traces in production**
    - **Valida: Requirements 4.4**

### Fase 20: Modo Offline y Sincronización (App Móvil)

- [x] 26. Implementar endpoint de sincronización por lotes
  - [x] 26.1 Crear POST /api/mobile/sync/batch en app/rutas/mobile_api_ruta.py
    - Aceptar lista de operaciones pendientes
    - Validar timestamps no sean demasiado antiguos (>30 días)
    - Procesar operaciones en orden cronológico
    - Detectar conflictos (recurso modificado en servidor)
    - Retornar resultados: success, failed, conflicts
    - _Requirements: 25.13, 25.14, 25.15_
  
  - [ ]* 26.2 Escribir unit tests para sincronización por lotes
    - Test sincronización exitosa de múltiples operaciones
    - Test detección de conflictos
    - Test rechazo de operaciones con timestamp antiguo
    - Test resolución de conflictos con "last write wins"
    - _Requirements: 25.9, 25.13, 25.14, 25.15_

### Fase 21: Documentación de Migración para Clientes

- [x] 27. Crear documentación de migración a JWT
  - [x] 27.1 Crear docs/MIGRACION_JWT.md
    - Documentar cambios en la API
    - Proveer ejemplos de código para móvil (React Native)
    - Proveer ejemplos de código para web (React)
    - Documentar formato del header Authorization: Bearer {token}
    - Documentar manejo de refresh token
    - Documentar códigos de error y cómo manejarlos
    - Proveer guía paso a paso de migración
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5, 22.6_
  
  - [x] 27.2 Actualizar README.md
    - Documentar todas las variables de entorno
    - Documentar proceso de deployment
    - Documentar proceso de migración de contraseñas
    - _Requirements: 24.8_

### Fase 22: Tests de Integración End-to-End

- [ ] 28. Escribir tests de integración completos
  - [ ]* 28.1 Test de flujo completo de autenticación
    - Login → access token → request autenticado → refresh token → logout
    - _Requirements: 1.8, 1.9, 1.10_
  
  - [ ]* 28.2 Test de flujo de password reset
    - Forgot password → reset token → reset password → login con nueva contraseña
    - _Requirements: 19.1-19.7_
  
  - [ ]* 28.3 Test de flujo de gestión de usuarios
    - Crear usuario → asignar roles → cambiar roles → desactivar usuario
    - _Requirements: 18.1-18.5, 14.7_
  
  - [ ]* 28.4 Test de flujo de tickets con auditoría
    - Crear ticket → agregar proceso → finalizar ticket → entregar ticket
    - Verificar que todos los eventos se registran en audit_log
    - _Requirements: 15.1, 15.2_
  
  - [ ]* 28.5 Test de rate limiting end-to-end
    - Hacer múltiples requests y verificar que se aplica rate limiting
    - Verificar header Retry-After en respuesta 429
    - _Requirements: 16.1-16.4_

### Fase 23: Tareas de Deployment

- [x] 29. Preparar deployment a producción
  - [x] 29.1 Crear script de deployment deploy.sh
    - Backup de base de datos
    - Ejecutar migración SQL
    - Ejecutar migración de contraseñas
    - Deploy de backend
    - Verificar health check
    - _Requirements: N/A (deployment)_
  
  - [x] 29.2 Crear script de rollback rollback.sh
    - Revertir código
    - Habilitar modo legacy (ENABLE_LEGACY_AUTH=true)
    - Revertir base de datos si es necesario
    - _Requirements: N/A (deployment)_
  
  - [x] 29.3 Configurar tareas periódicas (cron jobs)
    - Token blacklist cleanup (diario a las 2 AM)
    - Audit log archival (mensual)
    - Security metrics report (semanal)
    - _Requirements: 15.7_
  
  - [x] 29.4 Configurar monitoreo y alertas
    - Configurar logging de errores
    - Configurar métricas de aplicación
    - Configurar alertas de seguridad
    - _Requirements: 23.5, 23.6_

### Fase 24: Migración de Clientes (Mobile App)

- [x] 30. Actualizar app móvil para usar JWT
  - [x] 30.1 Implementar AuthService en mobile_app/src/services/authService.js
    - Implementar login() que almacena tokens en Keychain/Keystore
    - Implementar logout() que limpia tokens
    - Implementar refreshAccessToken() automático
    - Implementar authenticatedRequest() que agrega header Authorization
    - _Requirements: 17.1, 17.2, 17.3, 17.6_
  
  - [x] 30.2 Implementar OfflineService en mobile_app/src/services/offlineService.js
    - Detectar estado de conexión con NetInfo
    - Implementar enqueueOperation() para operaciones offline
    - Implementar syncPendingOperations() con backoff exponencial
    - Implementar caché local con SQLite
    - _Requirements: 25.1, 25.2, 25.3, 25.4, 25.5, 25.8, 25.11_
  
  - [x] 30.3 Crear hook useOffline() en mobile_app/src/hooks/useOffline.js
    - Exponer estado: isOnline, isSyncing, pendingCount
    - _Requirements: 25.6, 25.7_
  
  - [x] 30.4 Crear componente ConnectionIndicator
    - Mostrar indicador visual de estado de conexión
    - Mostrar contador de operaciones pendientes
    - _Requirements: 25.6, 25.7, 25.10_
  
  - [x] 30.5 Actualizar todas las llamadas a API para usar authenticatedRequest()
    - Reemplazar fetch directo con authService.authenticatedRequest()
    - _Requirements: 17.2_
  
  - [x] 30.6 Implementar pantalla de login
    - Usar AuthService.login()
    - Manejar errores de autenticación
    - _Requirements: 17.1_
  
  - [x] 30.7 Implementar manejo de sesión expirada
    - Redirigir a login cuando refresh token expira
    - _Requirements: 17.6_

### Fase 25: Migración de Clientes (Web Frontend)

- [x] 31. Actualizar frontend web para usar JWT
  - [x] 31.1 Implementar AuthService en frontend/src/services/authService.js
    - Implementar login() que almacena tokens en localStorage
    - Implementar logout() que limpia tokens
    - Configurar axios interceptors para agregar token y refrescar automáticamente
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_
  
  - [x] 31.2 Implementar ProtectedRoute component
    - Verificar autenticación antes de renderizar rutas protegidas
    - Redirigir a login si no está autenticado
    - _Requirements: 17.4_
  
  - [x] 31.3 Actualizar todas las rutas para usar ProtectedRoute
    - Envolver rutas sensibles con ProtectedRoute
    - _Requirements: 17.4_
  
  - [x] 31.4 Implementar pantalla de login
    - Usar AuthService.login()
    - Manejar errores de autenticación
    - _Requirements: 17.1_
  
  - [x] 31.5 Actualizar llamadas a API para enviar contraseña PDF por header
    - Cambiar de query param ?token= a header X-PDF-Password
    - _Requirements: 5.4_

### Fase 26: Tests de Seguridad Completos

- [x] 32. Escribir suite completa de tests de seguridad
  - [x]* 32.1 Tests de protección de endpoints
    - Test endpoints protegidos rechazan requests sin token (401)
    - Test tokens expirados son rechazados (401)
    - Test tokens con firma inválida son rechazados (401)
    - Test tokens en lista negra son rechazados (401)
    - _Requirements: 21.1, 21.2, 21.3, 21.4_
  
  - [x]* 32.2 Tests de roles y permisos
    - Test usuario sin rol ADMIN no puede acceder a /users (403)
    - Test usuario con rol correcto puede acceder
    - _Requirements: 21.6_
  
  - [x]* 32.3 Tests de hashing de contraseñas
    - Test contraseñas son hasheadas con bcrypt
    - Test verify_password funciona correctamente
    - _Requirements: 21.7_
  
  - [x]* 32.4 Tests de mensajes de error
    - Test login fallido no revela si usuario existe
    - Test password reset no revela si email existe
    - _Requirements: 21.8_

### Fase 27: Validación Final y Documentación

- [x] 33. Ejecutar análisis de seguridad y validación final
  - [x] 33.1 Ejecutar bandit para análisis de seguridad estático
    - Corregir cualquier vulnerabilidad detectada
    - _Requirements: N/A (quality assurance)_
  
  - [x] 33.2 Ejecutar safety para verificar dependencias
    - Actualizar dependencias con vulnerabilidades conocidas
    - _Requirements: N/A (quality assurance)_
  
  - [x] 33.3 Verificar cobertura de tests
    - Service Layer: >80%
    - Repository Layer: >70%
    - Middleware: >90%
    - Routes: >70%
    - _Requirements: 7.6_
  
  - [x] 33.4 Ejecutar todos los tests (unit + property + integration)
    - Verificar que todos los tests pasan
    - _Requirements: N/A (quality assurance)_
  
  - [x] 33.5 Actualizar documentación OpenAPI
    - Verificar que todos los endpoints están documentados
    - Verificar que security schemes están configurados
    - _Requirements: 3.8, 10.7_
  
  - [x] 33.6 Crear checklist de deployment
    - Pre-deployment checklist
    - Deployment steps
    - Post-deployment verification
    - Rollback plan
    - _Requirements: N/A (deployment)_

- [x] 34. Checkpoint final - Validación completa del sistema
  - Ejecutar todos los tests y verificar que pasan
  - Probar flujos end-to-end manualmente
  - Verificar que audit_log registra todos los eventos
  - Verificar que rate limiting funciona correctamente
  - Verificar que modo offline funciona en app móvil
  - Verificar que documentación está completa
  - Preguntar al usuario si está listo para deployment

## Notas Importantes

### Sobre Tests Opcionales (marcados con *)

Los tests marcados con `*` son opcionales y pueden omitirse para un MVP más rápido. Sin embargo, se recomienda implementarlos para garantizar la correctitud del sistema, especialmente los property tests que validan propiedades universales.

### Sobre Propiedades de Correctitud

Este plan incluye la implementación de 52 propiedades de correctitud del documento de diseño. Cada property test está anotado con:
- Número de propiedad
- Título de la propiedad
- Requirements que valida

### Sobre Breaking Changes

Las siguientes tareas introducen breaking changes que requieren coordinación con clientes:
- Fase 11: Proteger endpoints existentes (requiere JWT en clientes)
- Fase 12: Mejoras REST (cambios en URLs y métodos HTTP)
- Fase 24-25: Migración de clientes (requiere actualización de apps)

Se recomienda mantener compatibilidad temporal con `ENABLE_LEGACY_AUTH=true` durante el período de transición.

### Sobre Período de Transición

Durante la migración, el sistema soportará tanto autenticación legacy (SHA256) como JWT:
- Usuarios con contraseñas SHA256 pueden hacer login
- En el primer login exitoso, la contraseña se migra automáticamente a bcrypt
- Después de 30 días, se puede deshabilitar el modo legacy

### Sobre Checkpoints

Los checkpoints están estratégicamente ubicados para:
- Validar que la implementación funciona antes de continuar
- Permitir al usuario hacer preguntas o reportar problemas
- Asegurar que no hay errores acumulados

### Sobre Cobertura de Requirements

Este plan cubre todos los 25 requirements del documento de requirements:
- Requirement 1-6: Autenticación y seguridad básica
- Requirement 7-9: Arquitectura en capas
- Requirement 10-13: Mejoras REST y optimizaciones
- Requirement 14-16: Roles, auditoría y rate limiting
- Requirement 17-24: Gestión de usuarios y configuración
- Requirement 25: Modo offline y sincronización

Cada tarea referencia explícitamente los requirements que implementa para trazabilidad completa.
