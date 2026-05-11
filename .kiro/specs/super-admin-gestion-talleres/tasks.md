# Tareas de Implementación: Super Admin — Gestión de Talleres

## Resumen

Implementación del panel de administración del SUPER_ADMIN. Las tareas están ordenadas para que cada una sea ejecutable sin romper el sistema existente. Prerequisito: spec `multi-tenant-taller-id` completamente implementado.

**Reglas obligatorias durante implementación:**
- Todas las rutas del SUPER_ADMIN van bajo `/super-admin/`
- El SUPER_ADMIN nunca accede a datos operativos (tickets, vehículos, caja)
- `taller_id = NULL` para el SUPER_ADMIN — nunca forzar un taller
- Migraciones solo aditivas — nunca modificar migraciones existentes
- Uploads en `uploads/talleres/{taller_id}/{tipo}/`

---

## Tareas

- [x] 1. Actualizar modelos SQLAlchemy
  - [x] 1.1 Agregar enum `EstadoTaller` (`TRIAL`, `ACTIVO`, `SUSPENDIDO`, `CANCELADO`) y campos de ciclo de vida a `app/modelos/taller.py`: `estado`, `fecha_inicio_trial`, `dias_trial`, `fecha_suspension`, `fecha_cancelacion`
  - [x] 1.2 Agregar campos de bloqueo de emergencia a `app/modelos/taller.py`: `bloqueado_emergencia`, `fecha_bloqueo_emergencia`, `motivo_bloqueo_emergencia`
  - [x] 1.3 Hacer `taller_id` nullable en `app/modelos/user.py` para soportar SUPER_ADMIN con `taller_id = NULL`
  - [x] 1.4 Agregar campos de localización a `app/modelos/configuracion_taller.py`: `moneda` (default `COP`), `idioma` (default `es`), `timezone` (default `America/Bogota`)
  - [x] 1.5 Agregar nuevas acciones al enum `AuditAction` en `app/modelos/audit_log.py`: `TALLER_ACTIVATE`, `TALLER_SUSPEND`, `TALLER_CANCEL`, `TALLER_EMERGENCY_BLOCK`, `TALLER_EMERGENCY_UNBLOCK`, `PASSWORD_RESET_FORCED`, `PASSWORD_RESET_MASS`

- [x] 2. Actualizar AuthMiddleware para SUPER_ADMIN
  - [x] 2.1 Modificar `app/seguridad/auth_middleware.py` para omitir verificación de taller cuando el usuario tiene rol `SUPER_ADMIN` (su `taller_id = NULL`)
  - [x] 2.2 Agregar verificación de `bloqueado_emergencia` en el middleware — retornar HTTP 403 si el taller está bloqueado de emergencia (tiene prioridad sobre el estado)
  - [x] 2.3 Agregar verificación de `estado` del taller en el middleware — retornar HTTP 403 si `estado = SUSPENDIDO` o `CANCELADO`
  - [x] 2.4 Inyectar `request.state.is_super_admin` (boolean) en cada request autenticado

- [x] 3. Crear migración Alembic para campos nuevos
  - [x] 3.1 Crear `migrations/versions/b2c3d4e5f6a7_super_admin_fields.py` con `upgrade()` que: hace `taller_id` nullable en `users`, crea el tipo enum `estadotaller`, agrega campos de ciclo de vida y bloqueo a `talleres`, agrega campos de localización a `configuracion_taller`, crea índice en `talleres.estado`
  - [x] 3.2 Implementar `downgrade()` en la misma migración que revierte todos los cambios en orden inverso

- [x] 4. Actualizar esquemas Pydantic
  - [x] 4.1 Actualizar `app/esquemas/taller_schema.py` — agregar `EstadoTallerEnum`, actualizar `TallerCreate` con `dias_trial`, actualizar `TallerUpdate` con `estado` y `dias_trial`, actualizar `TallerResponse` con todos los campos nuevos incluyendo `dias_restantes_trial` calculado
  - [x] 4.2 Agregar nuevos schemas a `app/esquemas/taller_schema.py`: `TallerMetricasResponse`, `MetricasGlobalesResponse`, `TallerRecursosResponse`, `BloqueoEmergenciaRequest`, `CrearAdminTallerRequest`

- [x] 5. Extender TallerRepository con métodos de métricas
  - [x] 5.1 Agregar `get_metricas(taller_id)` a `app/repositorios/taller_repository.py` — retorna `usuarios_activos`, `tickets_historicos`, `tickets_mes_actual` usando agregaciones SQL en una sola query
  - [x] 5.2 Agregar `get_metricas_globales()` a `app/repositorios/taller_repository.py` — retorna totales de la plataforma con `GROUP BY estado`
  - [x] 5.3 Agregar `get_ultimo_acceso(taller_id)` a `app/repositorios/taller_repository.py` — consulta Audit_Log por último `LOGIN` exitoso del taller

- [x] 6. Extender TallerService con nuevos métodos
  - [x] 6.1 Agregar `cambiar_estado(taller_id, nuevo_estado, ...)` — valida transición de estado, registra en Audit_Log con acción correspondiente
  - [x] 6.2 Agregar `activar_bloqueo_emergencia(taller_id, motivo, ...)` — establece `bloqueado_emergencia = true`, invalida todos los tokens JWT del taller en `token_blacklist`, registra `TALLER_EMERGENCY_BLOCK` en Audit_Log
  - [x] 6.3 Agregar `levantar_bloqueo_emergencia(taller_id, ...)` — establece `bloqueado_emergencia = false`, limpia campos de bloqueo, registra `TALLER_EMERGENCY_UNBLOCK` en Audit_Log
  - [x] 6.4 Agregar `obtener_metricas(taller_id)` — llama al repositorio y calcula `dias_restantes_trial`
  - [x] 6.5 Agregar `obtener_metricas_globales()` — llama al repositorio
  - [x] 6.6 Agregar `obtener_recursos(taller_id)` — calcula almacenamiento recorriendo `uploads/talleres/{taller_id}/` con `os.walk()`
  - [x] 6.7 Agregar `crear_admin_taller(taller_id, username, email, password, ...)` — crea usuario con rol `ADMIN` asignando `taller_id` del path, nunca del body
  - [x] 6.8 Agregar `forzar_reset_password(taller_id, usuario_id, ...)` — invalida tokens del usuario y genera token de reset de 24h
  - [x] 6.9 Agregar `forzar_reset_password_masivo(taller_id, ...)` — invalida tokens de todos los usuarios del taller
  - [x] 6.10 Agregar `obtener_intentos_fallidos(taller_id, desde, page, page_size)` — consulta Audit_Log por `LOGIN_FAILED` del taller
  - [x] 6.11 Agregar `obtener_auditoria_global(filtros, page, page_size)` — consulta Audit_Log con filtros opcionales: `taller_id`, `user_id`, `accion`, `desde`, `hasta`

- [x] 7. Crear utilidad de uploads por taller
  - [x] 7.1 Crear `app/utils/upload_utils.py` con función `get_upload_path(taller_id, tipo)` que retorna `uploads/talleres/{taller_id}/{tipo}/` y crea el directorio con `os.makedirs(path, exist_ok=True)`
  - [x] 7.2 Actualizar `app/rutas/upload_ruta.py` para usar `get_upload_path(request.state.taller_id, tipo)` en lugar de rutas hardcodeadas
  - [x] 7.3 Actualizar `app/rutas/configuracion_ruta.py` endpoint de logo para usar `get_upload_path(taller_id, "logos")`

- [x] 8. Crear router del SUPER_ADMIN
  - [x] 8.1 Crear `app/rutas/super_admin_ruta.py` con `router = APIRouter(prefix="/super-admin", tags=["Super Admin"])` y todos los endpoints protegidos con `@require_role("SUPER_ADMIN")`
  - [x] 8.2 Implementar endpoints de gestión de talleres: `GET /super-admin/talleres`, `POST /super-admin/talleres`, `GET /super-admin/talleres/{taller_id}`, `PATCH /super-admin/talleres/{taller_id}`, `PATCH /super-admin/talleres/{taller_id}/estado`
  - [x] 8.3 Implementar endpoints de onboarding: `POST /super-admin/talleres/{taller_id}/usuarios`, `POST /super-admin/talleres/{taller_id}/logo`
  - [x] 8.4 Implementar endpoints de métricas: `GET /super-admin/talleres/{taller_id}/metricas`, `GET /super-admin/metricas/global`
  - [x] 8.5 Implementar endpoint de recursos: `GET /super-admin/talleres/{taller_id}/recursos`
  - [x] 8.6 Implementar endpoints de gestión de usuarios: `POST /super-admin/talleres/{taller_id}/usuarios/{uid}/reset-password`, `POST /super-admin/talleres/{taller_id}/reset-passwords`
  - [x] 8.7 Implementar endpoints de bloqueo de emergencia: `POST /super-admin/talleres/{taller_id}/bloqueo-emergencia`, `DELETE /super-admin/talleres/{taller_id}/bloqueo-emergencia`
  - [x] 8.8 Implementar endpoint de seguridad: `GET /super-admin/talleres/{taller_id}/seguridad/intentos-fallidos`
  - [x] 8.9 Implementar endpoint de auditoría global: `GET /super-admin/auditoria`
  - [x] 8.10 Registrar `super_admin_ruta.router` en `app/main.py`

- [x] 9. Crear script SQL del SUPER_ADMIN
  - [x] 9.1 Crear `scripts/crear_super_admin.sql` — script idempotente con `ON CONFLICT DO UPDATE` que crea el usuario SUPER_ADMIN con `taller_id = NULL`, asigna rol `SUPER_ADMIN`, incluye comentarios de uso y advertencias de seguridad
  - [x] 9.2 Crear `scripts/generar_hash_bcrypt.py` — script Python auxiliar que genera el hash bcrypt de una contraseña para usar en el script SQL

- [x] 10. Aplicar migración a la BD taller_v3
  - [x] 10.1 Ejecutar `alembic upgrade head` contra la BD `taller_v3` para aplicar la migración `b2c3d4e5f6a7`
  - [x] 10.2 Verificar que los campos nuevos existen en las tablas `talleres`, `users` y `configuracion_taller`
  - [x] 10.3 Ejecutar `scripts/crear_super_admin.sql` contra `taller_v3` para crear el usuario SUPER_ADMIN

- [x] 11. Escribir tests de propiedades (PBT)
  - [x] 11.1 Crear `tests/test_super_admin_isolation.py` con test P_SA1: el JWT del SUPER_ADMIN con `taller_id = null` no es rechazado por el AuthMiddleware
  - [x] 11.2 Agregar test P_SA2: si `bloqueado_emergencia = true`, el acceso es rechazado con HTTP 403 independientemente del `estado` del taller
  - [x] 11.3 Agregar test P_SA3: si `estado = SUSPENDIDO` o `CANCELADO`, todos los requests de usuarios del taller retornan HTTP 403
  - [x] 11.4 Agregar test P_SA4: `GET /super-admin/talleres/{id}/metricas` retorna solo conteos enteros, nunca strings con nombres o contenido de tickets
  - [x] 11.5 Agregar test P_SA5: después de `POST /super-admin/talleres/{id}/reset-passwords`, ningún token JWT previo de usuarios del taller es válido
  - [x] 11.6 Agregar test P_SA6: un archivo subido por el taller A nunca se almacena en la carpeta del taller B
