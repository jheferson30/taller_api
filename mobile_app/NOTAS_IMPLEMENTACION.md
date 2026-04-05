# Notas de Implementación - App Móvil JWT

## Archivos Creados

### Servicios
- `src/services/authService.js` - Servicio de autenticación con JWT
  - login(), logout(), refreshAccessToken()
  - authenticatedRequest() con retry automático en 401
  - Almacenamiento seguro de tokens en AsyncStorage

- `src/services/offlineService.js` - Servicio de sincronización offline
  - Detección de conexión con NetInfo
  - Cola de operaciones pendientes
  - Sincronización automática con backoff exponencial
  - Caché local de datos

### Hooks
- `src/hooks/useOffline.js` - Hook para acceder al estado offline
  - Expone: isOnline, isSyncing, pendingCount

### Componentes
- `src/components/ConnectionIndicator.jsx` - Indicador visual de conexión
  - Muestra estado online/offline
  - Contador de operaciones pendientes

### Pantallas
- `src/screens/LoginScreen.js` - Pantalla de login con JWT
- `src/screens/ConfiguracionScreen.js` - Configuración con logout

### Actualizaciones
- `App.js` - Integración de autenticación y offline service
- `src/api.js` - Migrado de X-Admin-Password a Authorization Bearer
- `package.json` - Agregada dependencia @react-native-community/netinfo

## Pendiente en Backend

Para que la app móvil funcione completamente, el backend necesita:

### 1. Endpoint de Sincronización por Lotes
```
POST /api/mobile/sync/batch
```
Debe aceptar:
```json
{
  "operations": [
    {
      "id": "unique-id",
      "type": "create_ticket|add_photo|etc",
      "endpoint": "/tickets/123/fotos",
      "method": "POST",
      "data": {...},
      "timestamp": "2026-03-31T10:00:00Z"
    }
  ]
}
```

Debe retornar:
```json
{
  "successful": ["id1", "id2"],
  "failed": [
    {"id": "id3", "error": "Validation error"}
  ],
  "conflicts": []
}
```

### 2. Actualizar Endpoints Móviles
Los siguientes endpoints deben aceptar `Authorization: Bearer {token}` en lugar de `X-Admin-Password`:
- GET /api/mobile/estadisticas
- GET /api/mobile/tickets
- POST /api/mobile/tickets/{id}/procesos
- POST /api/mobile/tickets/{id}/fotos
- DELETE /api/mobile/tickets/{id}/compras/{compra_id}
- etc.

### 3. Endpoint de PDF con Token
Actualizar:
```
GET /tickets/{id}/pdf
```
Para aceptar token JWT en query param o header Authorization.

## Flujo de Autenticación

1. Usuario abre app → Verifica si hay tokens guardados
2. Si no hay tokens → Muestra LoginScreen
3. Usuario ingresa credenciales → authService.login()
4. Backend retorna access_token y refresh_token
5. Tokens se guardan en AsyncStorage
6. Todas las requests usan authenticatedRequest()
7. Si 401 → Intenta refresh automático
8. Si refresh falla → Logout y redirige a Login

## Flujo Offline

1. offlineService detecta pérdida de conexión
2. Operaciones de escritura se encolan localmente
3. ConnectionIndicator muestra estado offline
4. Cuando se recupera conexión → Sincronización automática
5. Operaciones se envían en batch al backend
6. Backend procesa y retorna resultados
7. Operaciones exitosas se remueven de la cola

## Testing Recomendado

1. Probar login con credenciales válidas e inválidas
2. Probar refresh automático de token
3. Probar logout y limpieza de tokens
4. Probar operaciones offline y sincronización
5. Probar manejo de sesión expirada
6. Probar indicador de conexión

## Dependencias Instaladas

- @react-native-community/netinfo@^11.3.1 - Detección de conexión
- @react-native-async-storage/async-storage@2.2.0 - Ya instalado
