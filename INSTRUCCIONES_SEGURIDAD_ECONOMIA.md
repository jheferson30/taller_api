## Sistema de Seguridad para Economía Implementado

## ✅ Protección con Contraseña

Hemos implementado un sistema de seguridad robusto para proteger el acceso a la información financiera:

1. **Contraseña de acceso** - Requerida para ver la página de economía
2. **Palabra clave de recuperación** - Para restablecer la contraseña si se olvida
3. **Primera vez** - Crea contraseña y palabra clave
4. **Recuperación** - Cambia la contraseña usando la palabra clave
5. **Almacenamiento seguro** - Contraseñas hasheadas con SHA256

## Instalación

### 1. Ejecutar migración de base de datos

Abre pgAdmin y ejecuta el script:

```sql
-- Archivo: db/migracion_seguridad_2026_03_11.sql
```

O desde la terminal (si tienes psql configurado):

```bash
psql -U postgres -d nombre_de_tu_base_datos -f db/migracion_seguridad_2026_03_11.sql
```

### 2. Reiniciar el backend

```bash
uvicorn app.main:app --reload
```

### 3. Reiniciar el frontend

```bash
cd frontend
npm run dev
```

## Cómo Funciona

### Primera Vez (Crear Contraseña)

1. Al entrar a **Economía** por primera vez, verás una pantalla para crear contraseña
2. Ingresa una contraseña (mínimo 4 caracteres)
3. Ingresa una palabra clave de recuperación (mínimo 3 caracteres)
4. Click en **Crear Contraseña**
5. Automáticamente accederás a la página de economía

### Acceso Normal (Login)

1. Al entrar a **Economía**, verás la pantalla de login
2. Ingresa tu contraseña
3. Click en **Ingresar**
4. Accederás a la página de economía

### Recuperar Contraseña

1. En la pantalla de login, click en **¿Olvidaste tu contraseña?**
2. Ingresa tu palabra clave de recuperación
3. Ingresa una nueva contraseña
4. Click en **Restablecer Contraseña**
5. Vuelve al login con tu nueva contraseña

## Características de Seguridad

- **Hash SHA256** - Las contraseñas nunca se almacenan en texto plano
- **Validación** - Contraseña mínimo 4 caracteres, palabra clave mínimo 3
- **Sesión** - La autenticación dura mientras la página esté abierta
- **Sin tokens** - Sistema simple sin JWT ni cookies
- **Recuperación segura** - Solo con palabra clave correcta

## API Endpoints

### Verificar si tiene contraseña
```
GET /seguridad/economia/tiene-password
Response: { "tiene_password": true/false }
```

### Crear contraseña inicial
```
POST /seguridad/economia/crear-password
Body: {
  "password": "mi_contraseña",
  "palabra_clave": "mi_palabra_clave"
}
```

### Validar contraseña
```
POST /seguridad/economia/validar-password
Body: {
  "password": "mi_contraseña"
}
```

### Recuperar/cambiar contraseña
```
POST /seguridad/economia/recuperar-password
Body: {
  "palabra_clave": "mi_palabra_clave",
  "nueva_password": "nueva_contraseña"
}
```

## Notas Importantes

- La contraseña se solicita cada vez que se recarga la página
- No hay "recordar sesión" por seguridad
- La palabra clave es la única forma de recuperar acceso
- Guarda tu palabra clave en un lugar seguro
- Las contraseñas son case-sensitive (distinguen mayúsculas/minúsculas)

## Solución de Problemas

### Error: "Ya existe una contraseña configurada"
- Ya se creó una contraseña anteriormente
- Usa el modo login normal

### Error: "Contraseña incorrecta"
- Verifica que estés escribiendo correctamente
- Usa la opción de recuperar contraseña

### Error: "Palabra clave incorrecta"
- La palabra clave no coincide con la registrada
- No hay forma de recuperar sin la palabra clave correcta
- Contacta al administrador del sistema

### Olvidé mi palabra clave
- Si olvidaste la palabra clave, necesitarás acceso a la base de datos
- Elimina los registros de la tabla `configuracion_seguridad`
- Vuelve a crear la contraseña desde cero

```sql
DELETE FROM configuracion_seguridad 
WHERE clave IN ('economia_password', 'economia_palabra_clave');
```

## Ventajas del Sistema

✅ Protege información financiera sensible
✅ Fácil de usar
✅ Sistema de recuperación integrado
✅ No requiere configuración externa
✅ Contraseñas hasheadas (seguras)
✅ Interfaz intuitiva
✅ Sin dependencias adicionales
