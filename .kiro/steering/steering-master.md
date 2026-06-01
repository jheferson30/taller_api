---
inclusion: always
---

# Steering Maestro — Taller API SaaS

Este es el documento de reglas globales del proyecto. Aplica a **todo el código** que se escriba,
modifique o revise — sin excepción. No son sugerencias, son invariantes del sistema.

El estándar de calidad es el de un desarrollador senior en una empresa de software seria.
Cuando existan múltiples formas de hacer algo, siempre elegir la más profesional y mantenible,
no la más rápida.

---

## 1. Seguridad — Todo Endpoint Nuevo

Cada endpoint creado debe cumplir **todos** estos puntos antes de considerarse completo:

**Autenticación y autorización:**
- Usar `@require_auth` en todo endpoint que no sea explícitamente público (login, /health, /docs)
- Usar `@require_role` con el rol **más restrictivo** posible — nunca dar más acceso del necesario
- El contexto del usuario siempre viene de `request.state.user` y `request.state.taller_id` — nunca del body, query params ni headers del cliente
- Los guards de taller deben rechazar tokens con `taller_id = null` (SUPER_ADMIN no opera en talleres)

**Inputs:**
- Validar y sanitizar todos los inputs con `input_validator.py` antes de procesar
- Nunca concatenar strings para construir queries SQL — usar parámetros siempre
- Nunca confiar en datos del cliente sin validar, incluso si vienen de un token válido

**Respuestas:**
- Nunca exponer en respuestas: hashes de contraseñas, tokens completos, stack traces, IDs internos innecesarios ni datos de otros tenants
- Errores 4xx/5xx deben tener mensajes genéricos al cliente — los detalles van solo en logs internos
- Usar `HTTP 404` en lugar de `403` para recursos de otro tenant — no revelar que existen

**Audit log:**
- Registrar en audit log toda acción sensible: login, logout, cambio de contraseña, creación/eliminación de recursos críticos, errores de autenticación, acciones del SUPER_ADMIN
- Usar las `AuditAction` tipadas existentes — no strings literales

**Rate limiting:**
- Aplicar rate limiting en todo endpoint de login, reset de contraseña y cualquier endpoint que consuma recursos significativos

**Comparaciones seguras:**
- Usar `hmac.compare_digest` para comparar contraseñas, tokens o cualquier secreto — nunca `==`

**Secretos:**
- Usar `SecretsManager` o variables de entorno — nunca hardcodear claves, tokens ni contraseñas en el código

**Checklist antes de terminar cualquier endpoint:**
```
[ ] Tiene @require_auth
[ ] Tiene @require_role con el rol más restrictivo
[ ] Los inputs están validados con input_validator.py
[ ] No expone datos sensibles en la respuesta
[ ] Registra en audit log si es una acción crítica
[ ] Las queries usan parámetros, no concatenación
[ ] Tiene rate limiting si es un endpoint sensible
```

---

## 2. Arquitectura Multi-Tenant — Reglas de Aislamiento

Este sistema es SaaS multi-tenant. El aislamiento entre talleres es una invariante del sistema
que nunca puede romperse.

**Row-Level Security:**
```python
# ✅ CORRECTO — siempre filtrar por taller_id del JWT
query = db.query(Ticket).filter(Ticket.taller_id == request.state.taller_id)

# ❌ INCORRECTO — nunca usar taller_id del body o params
query = db.query(Ticket).filter(Ticket.taller_id == datos.taller_id)
```

**SUPER_ADMIN:**
- Solo accede a métricas agregadas y metadatos — nunca a tickets, repuestos, caja, fotos, vehículos ni clientes
- Se crea únicamente por el script SQL `scripts/crear_super_admin.sql` — no existe ningún endpoint HTTP para esto
- Su JWT incluye `"roles": ["SUPER_ADMIN"]` y `"taller_id": null`
- Guard separado `@require_role("SUPER_ADMIN")` — nunca mezclar con roles de taller:
```python
# ✅ CORRECTO
@require_role("SUPER_ADMIN")
async def listar_talleres(request: Request): ...

# ❌ INCORRECTO — nunca mezclar SUPER_ADMIN con roles de taller
@require_role("ADMIN", "SUPER_ADMIN")
async def listar_tickets(request: Request): ...
```

**Suspensión de talleres:**
- Es un flag `estado = SUSPENDIDO` validado en `AuthMiddleware` — nunca borrar ni archivar datos
- Devuelve `403 Forbidden` al autenticar usuarios de un taller suspendido

**Límites del plan:**
- Se validan en la capa de servicio (`/app/servicios/`) — no en rutas ni middleware
- Llamar `verificar_limite_plan(taller_id, recurso)` antes de persistir cualquier recurso limitado
- Lanzar `HTTP 402 Payment Required` si el límite está superado

**Índices únicos:**
- Usar índices compuestos con `taller_id` cuando el contexto lo requiere:
```python
# ✅ CORRECTO — dos talleres pueden tener la misma placa
UniqueConstraint('taller_id', 'placa', name='uq_vehiculo_placa_taller')
```

---

## 3. Estructura de Código — Separación de Responsabilidades

Cada capa del proyecto tiene una responsabilidad única. No mezclarlas.

```
app/rutas/          → solo HTTP: recibir request, validar schema, llamar servicio, retornar response
app/servicios/      → lógica de negocio, validaciones de dominio, orquestación
app/repositorios/   → queries a la base de datos, nada más
app/modelos/        → definición de tablas SQLAlchemy
app/schemas/        → Pydantic: validación de entrada y serialización de salida
app/seguridad/      → autenticación, autorización, hashing, JWT
```

**Reglas:**
- Las rutas no hacen queries directas a la BD — siempre a través de servicios
- Los servicios no construyen respuestas HTTP — eso es responsabilidad de las rutas
- Los repositorios no contienen lógica de negocio — solo SQL
- Un servicio puede llamar a otros servicios, pero no a rutas
- Nombres en español para el dominio de negocio: `taller`, `ticket`, `cita`, `mecanico`, `repuesto`

---

## 4. Rutas HTTP — Estándar RESTful

Todo endpoint debe declarar su método HTTP y ruta completa antes de implementarse.

**Convenciones:**
- Rutas del SUPER_ADMIN: prefijo `/super-admin/`
- Rutas de operación de taller: prefijo `/api/v1/` (versionado)
- Usar jerarquía de recursos: `POST /talleres/{id}/usuarios` no `POST /usuarios?taller_id=x`
- Verbos HTTP semánticamente correctos: GET (leer), POST (crear), PUT (reemplazar), PATCH (actualizar parcial), DELETE (eliminar)
- Respuestas con códigos HTTP correctos: 200 (ok), 201 (creado), 204 (sin contenido), 400 (input inválido), 401 (no autenticado), 403 (sin permiso), 404 (no existe), 409 (conflicto), 422 (validación), 502 (error externo)

**Rutas SUPER_ADMIN:**
```
GET    /super-admin/talleres
POST   /super-admin/talleres
GET    /super-admin/talleres/{taller_id}
PATCH  /super-admin/talleres/{taller_id}
PATCH  /super-admin/talleres/{taller_id}/estado
GET    /super-admin/talleres/{taller_id}/metricas
GET    /super-admin/talleres/{taller_id}/recursos
POST   /super-admin/talleres/{taller_id}/usuarios
POST   /super-admin/talleres/{taller_id}/notificaciones
POST   /super-admin/talleres/{taller_id}/bloqueo-emergencia
DELETE /super-admin/talleres/{taller_id}/bloqueo-emergencia
GET    /super-admin/metricas/global
GET    /super-admin/auditoria
```

---

## 5. Base de Datos — Migraciones y Modelos

**Migraciones:**
- Solo aditivas — nunca modificar migraciones existentes, siempre crear nuevas
- Cada nueva entidad o cambio de esquema tiene su propio archivo de migración con nombre descriptivo
- Toda migración incluye `upgrade()` y `downgrade()` completos y probados
- Nombre de archivo: `{hash}_{descripcion_en_snake_case}.py`

**Modelos:**
- Columnas nullable deben tener razón de negocio documentada en comentario
- Relaciones explícitas con `relationship()` y `back_populates`
- `created_at` y `updated_at` en toda tabla de entidad de negocio
- `taller_id` como foreign key en toda tabla de datos operativos

---

## 6. Docker y Despliegue — Sin Configuración Manual

Todo cambio que afecte infraestructura debe quedar declarado para que `docker-compose up`
levante el sistema completo sin ningún paso adicional.

**Reglas:**
- Nueva librería Python → agregarla a `requirements.txt` en el mismo commit
- Nuevo servicio de infraestructura → declararlo en `docker-compose.yml` con red, volúmenes y variables
- Nueva variable de entorno → documentarla en `.env.example` con valor de ejemplo y comentario
- Archivos generados en runtime → guardarlos dentro de volúmenes ya mapeados:
```
uploads/talleres/{taller_id}/logos/
uploads/talleres/{taller_id}/fotos/
uploads/talleres/{taller_id}/pdfs/
uploads/talleres/{taller_id}/exports/
```
- Crear directorios con `os.makedirs(path, exist_ok=True)` — nunca asumir que existen:
```python
def get_upload_path(taller_id: int, tipo: str) -> str:
    path = os.path.join("uploads", "talleres", str(taller_id), tipo)
    os.makedirs(path, exist_ok=True)
    return path
```

---

## 7. Calidad de Código — Estándar Senior

**Legibilidad:**
- Nombres descriptivos — el código debe leerse como prosa, no como puzzle
- Funciones con una sola responsabilidad — si hace más de una cosa, dividir
- Máximo 3 niveles de indentación — si hay más, refactorizar
- Sin comentarios que expliquen el qué (eso lo hace el nombre) — solo comentarios que expliquen el porqué

**Docstrings:**
- Todo método público de servicios y repositorios debe tener docstring
- Formato: descripción en una línea + parámetros si no son obvios + qué lanza

**Manejo de errores:**
- Capturar excepciones específicas — nunca `except Exception` sin loguear
- Usar las excepciones HTTP de FastAPI (`HTTPException`) con códigos y mensajes claros
- Los errores de BD deben capturarse en el repositorio y relanzarse como excepciones de dominio

**Tests:**
- Todo servicio nuevo debe tener tests unitarios
- Usar property-based testing (Hypothesis) para validar invariantes de seguridad y aislamiento
- Los tests deben poder correr con `pytest` sin configuración adicional

---

## 8. Mejoras de Seguridad Continua

En cada cambio de código, evaluar si aplica alguna de estas mejoras sin romper funcionalidad:

- **Headers de seguridad HTTP:** `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`
- **Rotación de refresh tokens:** invalidar el token anterior al emitir uno nuevo
- **CORS estricto:** solo los orígenes necesarios en producción
- **Detección de anomalías:** múltiples IPs para el mismo usuario, cambios de user-agent
- **2FA para roles ADMIN:** considerar en talleres con datos sensibles
- **Cifrado de PII en BD:** datos personales de clientes

---

## Regla de Oro

Antes de dar por terminada cualquier tarea, responder estas preguntas:

1. ¿Tiene seguridad completa? (auth, roles, validación, audit log)
2. ¿Está aislado por taller correctamente?
3. ¿Funciona con `docker-compose up` sin pasos manuales?
4. ¿La ruta HTTP está declarada y es RESTful?
5. ¿El código lo entendería un desarrollador que no conoce el proyecto?

Si alguna respuesta es no — no está terminado.
