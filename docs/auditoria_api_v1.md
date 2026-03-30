# Auditoría API — Taller Mecánico v1.0

**Fecha:** Marzo 2026  
**Evaluador:** Kiro AI  
**Versión analizada:** 1.1.0

---

## Calificación General: 7.8 / 10

Para un proyecto de taller mecánico local con app móvil, está muy por encima del promedio. La arquitectura es coherente, el código es legible, y hay decisiones técnicas maduras. Para despliegue en red local es apto para venta como v1.0.

---

## Calificaciones por Módulo

| Módulo | Calificación | Resumen |
|--------|-------------|---------|
| `main.py` | 8.5/10 | Muy bien estructurado, lifespan correcto, tokens QR elegantes |
| `ticket_ruta.py` | 8.0/10 | Sólido, helpers bien definidos, timing-safe en PDF |
| `mobile_api_ruta.py` | 7.0/10 | Funcional pero con duplicación respecto a ticket_ruta |
| `citas_ruta.py` | 7.5/10 | Limpio, buena cobertura de casos edge, sin autenticación |
| `economia_ruta.py` | 9.0/10 | El mejor módulo, helpers bien separados y reutilizables |
| `movimiento_caja_ruta.py` | 7.5/10 | Buen audit trail, validación centralizada |
| `seguridad_ruta.py` | 6.5/10 | SHA256 sin salt es el problema principal |
| `configuracion_ruta.py` | 8.0/10 | Limpio y conciso, creación lazy correcta |
| `upload_ruta.py` | 8.5/10 | Destaca por path traversal prevention y validaciones |
| `vehiculo_ruta.py` | 8.0/10 | Bien estructurado, ficha con historial útil |

---

## Hallazgos por Categoría

### 🔴 Seguridad — 6.5/10

| Severidad | Módulo | Hallazgo |
|-----------|--------|----------|
| Alta | `seguridad_ruta.py` | SHA256 sin salt para contraseñas. Vulnerable a rainbow tables. Usar `bcrypt` o `argon2`. |
| Alta | `upload_ruta.py` | Sin autenticación. Cualquier persona en la red puede subir archivos al servidor. |
| Alta | `citas_ruta.py` | Sin autenticación en ningún endpoint. Cualquiera puede crear, modificar o cancelar citas. |
| Media | `ticket_ruta.py` | PDF acepta contraseña por query param `?token=`. Queda expuesta en logs y en historial del browser. |
| Media | `main.py` | `/info` expone nombre, WhatsApp y correo del desarrollador en endpoint público sin auth. |
| Media | `seguridad_ruta.py` | Mensajes de error distinguen "no hay contraseña" vs "contraseña incorrecta" — filtra información. |
| Baja | `movimiento_caja_ruta.py` | `crear_movimiento_caja` y `crear_cobro_rapido` no requieren autenticación. |

---

### 🟡 Arquitectura — 7.5/10

| Severidad | Módulo | Hallazgo |
|-----------|--------|----------|
| Alta | `mobile_api_ruta.py` | Duplica ~60% de la lógica de `ticket_ruta.py`. Cambios en reglas de negocio hay que hacerlos en dos lugares. |
| Media | Rutas en general | Lógica de negocio mezclada en rutas (cálculo de `saldo_pendiente`, creación de `MovimientoCaja`). Debería estar en servicios. |
| Media | Rutas en general | No hay capa de repositorio. Las rutas hacen queries directas a la DB — dificulta testing y reutilización. |
| Baja | `mobile_api_ruta.py` | Manejo manual de `multipart/form-data` vs JSON con `if/else` en content-type. FastAPI tiene mecanismos nativos. |

---

### 🟡 Consistencia REST — 7/10

| Severidad | Módulo | Hallazgo |
|-----------|--------|----------|
| Media | `citas_ruta.py` | `DELETE /citas/{id}` hace soft-delete — semánticamente debería ser `PATCH /citas/{id}/cancelar`. |
| Media | `configuracion_ruta.py` | `PUT /mecanicos/{id}` hace toggle implícito sin body — no es RESTful. Debería ser `PATCH` con `{ "activo": false }`. |
| Baja | `movimiento_caja_ruta.py` | `POST /cobro-rapido` usa kebab-case mientras el resto usa snake_case en las URLs. |
| Baja | Rutas en general | Algunos endpoints retornan `{"ok": True}` y otros retornan el objeto completo para la misma operación (DELETE). Inconsistente. |

---

### 🟢 Calidad de Código — 8/10

| Severidad | Módulo | Hallazgo |
|-----------|--------|----------|
| Media | `vehiculo_ruta.py` | Usa `datetime.utcnow()` deprecado en Python 3.12+. Cambiar a `datetime.now(timezone.utc)`. |
| Media | `economia_ruta.py` | `/historico` itera día a día con `while` loop — hace N queries individuales. Una query con `GROUP BY DATE` sería más eficiente. |
| Baja | `mobile_api_ruta.py` | `obtener_resumen_ticket` usa subqueries escalares anidadas — funciona pero difícil de mantener. |
| Baja | Rutas en general | Docstrings inconsistentes: algunos endpoints tienen descripción, otros no. |

---

## Lo que está bien hecho ✅

- `hmac.compare_digest` para comparar contraseñas (timing-safe) en el PDF
- Tokens QR de un solo uso con TTL de 5 minutos
- `_safe_filepath` en upload previene path traversal
- Audit trail completo en `CambioMovimientoCaja`
- Rate limiting aplicado en endpoints sensibles
- Validación de variables de entorno al arrancar con `lifespan`
- Paginación con `skip/limit` en los listados
- Transiciones de estado validadas explícitamente en la app móvil
- CORS configurado con regex para red local

---

## Roadmap de Mejoras

### Antes de v1.0 (bloqueantes para venta)
- [ ] Remover datos personales del endpoint `/info`
- [ ] Corregir bug del anticipo en sección de cobros (frontend y móvil)

### v1.1 (mejoras de seguridad)
- [ ] Migrar SHA256 a `bcrypt` o `argon2` en `seguridad_ruta.py`
- [ ] Agregar autenticación a `citas_ruta.py`
- [ ] Agregar autenticación a `upload_ruta.py`
- [ ] Mover contraseña del PDF de query param a header

### v1.2 (mejoras de arquitectura)
- [ ] Unificar lógica duplicada entre `ticket_ruta.py` y `mobile_api_ruta.py`
- [ ] Extraer lógica de negocio a capa de servicios
- [ ] Optimizar query de `/historico` con GROUP BY

---

## Veredicto para v1.0

**Para despliegue en red local de talleres:** ✅ Apto para venta  
**Para despliegue en internet / SaaS:** ⚠️ Requiere resolver hallazgos de seguridad Alta primero
