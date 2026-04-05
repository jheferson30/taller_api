# Guía de Migración a Autenticación JWT

## Resumen de Cambios

El sistema ha migrado de autenticación basada en contraseña SHA256 a un sistema moderno de autenticación JWT (JSON Web Tokens) con bcrypt. Esta guía te ayudará a actualizar tus aplicaciones cliente (móvil y web) para usar el nuevo sistema.

## Cambios Principales

1. **Autenticación con JWT**: Tokens de acceso y refresh en lugar de contraseña en cada request
2. **Hashing seguro**: bcrypt en lugar de SHA256
3. **Sistema de roles**: Control de acceso basado en roles (ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA)
4. **Rate limiting**: Límites de solicitudes por minuto/hora
5. **Audit trail**: Registro completo de eventos de seguridad
6. **Modo offline**: Sincronización por lotes para operaciones offline (app móvil)

## Endpoints de Autenticación

### 1. Login

**Endpoint**: `POST /auth/login`

**Request**:
```json
{
  "username": "admin",
  "password": "tu_contraseña"
}
```

**Response exitosa (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@taller.com",
    "roles": ["ADMIN"],
    "is_active": true
  }
}
```

**Errores comunes**:
- `401`: Credenciales inválidas o usuario inactivo
- `429`: Demasiados intentos de login (5 por minuto por IP)

### 2. Refresh Token

**Endpoint**: `POST /auth/refresh`

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response exitosa (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```


**Errores comunes**:
- `401`: Refresh token inválido, expirado o en lista negra
- `429`: Demasiadas solicitudes (10 por minuto por IP)

### 3. Logout

**Endpoint**: `POST /auth/logout`

**Headers requeridos**:
```
Authorization: Bearer {access_token}
```

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response exitosa (204)**: Sin contenido

**Errores comunes**:
- `401`: Token de acceso inválido o faltante

### 4. Recuperación de Contraseña

**Endpoint**: `POST /auth/forgot-password`

**Request**:
```json
{
  "email": "usuario@example.com"
}
```

**Response exitosa (200)**:
```json
{
  "message": "Si el email existe, recibirás instrucciones para restablecer tu contraseña"
}
```

**Nota**: El mensaje es genérico para prevenir enumeración de usuarios.

**Errores comunes**:
- `429`: Demasiadas solicitudes (3 por hora por email)

### 5. Restablecer Contraseña

**Endpoint**: `POST /auth/reset-password`

**Request**:
```json
{
  "token": "token_recibido_por_email",
  "new_password": "NuevaContraseña123!"
}
```

**Response exitosa (200)**:
```json
{
  "message": "Contraseña restablecida exitosamente"
}
```

**Errores comunes**:
- `400`: Token inválido, expirado o ya usado
- `400`: Contraseña no cumple requisitos de complejidad



## Formato del Header Authorization

Todos los endpoints protegidos requieren el header `Authorization` con el formato:

```
Authorization: Bearer {access_token}
```

**Ejemplo**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZXMiOlsiQURNSU4iXSwiZXhwIjoxNzExODk2MDAwLCJpYXQiOjE3MTE4OTUxMDAsImp0aSI6ImFiYzEyMyJ9.signature
```

## Ciclo de Vida de Tokens

1. **Access Token**: Expira en 15 minutos
2. **Refresh Token**: Expira en 7 días
3. **Flujo recomendado**:
   - Usar access token para todas las requests
   - Cuando access token expira (401), usar refresh token para obtener nuevo access token
   - Cuando refresh token expira, solicitar login nuevamente

## Códigos de Error HTTP

| Código | Significado | Acción Recomendada |
|--------|-------------|-------------------|
| 401 | No autenticado o token inválido | Redirigir a login |
| 403 | Sin permisos suficientes | Mostrar mensaje de acceso denegado |
| 429 | Rate limit excedido | Esperar tiempo indicado en header `Retry-After` |
| 400 | Datos inválidos | Mostrar errores de validación |
| 404 | Recurso no encontrado | Mostrar mensaje apropiado |
| 409 | Conflicto (duplicado o sincronización) | Resolver conflicto |
| 500 | Error interno del servidor | Mostrar mensaje genérico |

## Estructura de Respuestas de Error

Todas las respuestas de error siguen este formato:

```json
{
  "error": "error_code",
  "message": "Mensaje descriptivo",
  "details": {},
  "error_id": "uuid-del-error"
}
```

**Nota**: En producción, `details` y `traceback` están ocultos por seguridad.



## Migración de App Móvil (React Native)

### 1. Instalar Dependencias

```bash
npm install @react-native-async-storage/async-storage
# o
yarn add @react-native-async-storage/async-storage
```

### 2. Crear AuthService

Crea `src/services/authService.js`:

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = 'http://tu-servidor:8000';

class AuthService {
  async login(username, password) {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Error de autenticación');
    }

    const data = await response.json();
    
    // Guardar tokens en AsyncStorage
    await AsyncStorage.setItem('access_token', data.access_token);
    await AsyncStorage.setItem('refresh_token', data.refresh_token);
    await AsyncStorage.setItem('user', JSON.stringify(data.user));
    
    return data;
  }

  async logout() {
    const refreshToken = await AsyncStorage.getItem('refresh_token');
    const accessToken = await AsyncStorage.getItem('access_token');
    
    if (refreshToken && accessToken) {
      try {
        await fetch(`${API_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch (error) {
        console.error('Error al hacer logout:', error);
      }
    }
    
    // Limpiar tokens locales
    await AsyncStorage.multiRemove(['access_token', 'refresh_token', 'user']);
  }

  async refreshAccessToken() {
    const refreshToken = await AsyncStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      // Refresh token expirado, limpiar y redirigir a login
      await this.logout();
      throw new Error('Session expired');
    }

    const data = await response.json();
    await AsyncStorage.setItem('access_token', data.access_token);
    
    return data.access_token;
  }

  async authenticatedRequest(url, options = {}) {
    let accessToken = await AsyncStorage.getItem('access_token');
    
    // Agregar header Authorization
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`,
    };

    let response = await fetch(url, { ...options, headers });

    // Si recibimos 401, intentar refresh
    if (response.status === 401) {
      try {
        accessToken = await this.refreshAccessToken();
        headers['Authorization'] = `Bearer ${accessToken}`;
        response = await fetch(url, { ...options, headers });
      } catch (error) {
        // Refresh falló, redirigir a login
        throw new Error('Session expired');
      }
    }

    return response;
  }

  async getUser() {
    const userStr = await AsyncStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  async isAuthenticated() {
    const accessToken = await AsyncStorage.getItem('access_token');
    return !!accessToken;
  }
}

export default new AuthService();
```



### 3. Actualizar Llamadas a API

**Antes**:
```javascript
const response = await fetch(`${API_URL}/api/mobile/tickets`);
```

**Después**:
```javascript
import authService from './services/authService';

const response = await authService.authenticatedRequest(
  `${API_URL}/api/mobile/tickets`
);
```

### 4. Implementar Pantalla de Login

```javascript
import React, { useState } from 'react';
import { View, TextInput, Button, Alert } from 'react-native';
import authService from '../services/authService';

export default function LoginScreen({ navigation }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    try {
      await authService.login(username, password);
      navigation.replace('Home');
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <TextInput
        placeholder="Usuario"
        value={username}
        onChangeText={setUsername}
        autoCapitalize="none"
      />
      <TextInput
        placeholder="Contraseña"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      <Button
        title={loading ? "Iniciando..." : "Iniciar Sesión"}
        onPress={handleLogin}
        disabled={loading}
      />
    </View>
  );
}
```

### 5. Modo Offline - Sincronización por Lotes

Para operaciones offline, usa el endpoint de sincronización:

```javascript
async function syncOfflineOperations(operations) {
  const response = await authService.authenticatedRequest(
    `${API_URL}/api/mobile/sync/batch`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operaciones: operations }),
    }
  );

  const result = await response.json();
  
  // Procesar resultados
  console.log(`Sincronizadas: ${result.exitosas}/${result.total}`);
  console.log(`Fallidas: ${result.fallidas}`);
  console.log(`Conflictos: ${result.conflictos}`);
  
  return result;
}
```

**Formato de operación offline**:
```javascript
{
  id: "uuid-generado-en-cliente",
  tipo: "crear_proceso", // o "crear_repuesto", "subir_foto", "crear_compra", "actualizar_estado"
  ticket_id: 123,
  timestamp: "2026-03-31T10:30:00Z",
  datos: {
    nombre: "Cambio de aceite",
    descripcion: "Aceite 10W-40",
    mecanico: "Juan"
  }
}
```



### 6. Manejo de Sesión Expirada

```javascript
// En tu componente principal o navegación
import { useEffect } from 'react';
import authService from './services/authService';

function App() {
  useEffect(() => {
    const checkAuth = async () => {
      const isAuth = await authService.isAuthenticated();
      if (!isAuth) {
        // Redirigir a login
        navigation.replace('Login');
      }
    };
    
    checkAuth();
  }, []);

  // ... resto del componente
}
```

## Migración de Frontend Web (React)

### 1. Instalar Dependencias

```bash
npm install axios
# o
yarn add axios
```

### 2. Crear AuthService

Crea `src/services/authService.js`:

```javascript
import axios from 'axios';

const API_URL = 'http://tu-servidor:8000';

class AuthService {
  constructor() {
    // Configurar interceptor para agregar token automáticamente
    axios.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Configurar interceptor para refresh automático
    axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Si recibimos 401 y no hemos intentado refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = localStorage.getItem('refresh_token');
            const response = await axios.post(`${API_URL}/auth/refresh`, {
              refresh_token: refreshToken,
            });

            const { access_token } = response.data;
            localStorage.setItem('access_token', access_token);

            // Reintentar request original con nuevo token
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return axios(originalRequest);
          } catch (refreshError) {
            // Refresh falló, limpiar y redirigir a login
            this.logout();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  async login(username, password) {
    const response = await axios.post(`${API_URL}/auth/login`, {
      username,
      password,
    });

    const { access_token, refresh_token, user } = response.data;

    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    localStorage.setItem('user', JSON.stringify(user));

    return response.data;
  }

  async logout() {
    const refreshToken = localStorage.getItem('refresh_token');

    if (refreshToken) {
      try {
        await axios.post(`${API_URL}/auth/logout`, {
          refresh_token: refreshToken,
        });
      } catch (error) {
        console.error('Error al hacer logout:', error);
      }
    }

    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  getUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  isAuthenticated() {
    return !!localStorage.getItem('access_token');
  }
}

export default new AuthService();
```



### 3. Crear ProtectedRoute Component

Crea `src/components/ProtectedRoute.jsx`:

```javascript
import { Navigate } from 'react-router-dom';
import authService from '../services/authService';

export default function ProtectedRoute({ children }) {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
```

### 4. Actualizar Rutas

```javascript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import TicketsPage from './pages/TicketsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <HomePage />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/tickets"
          element={
            <ProtectedRoute>
              <TicketsPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

### 5. Implementar Pantalla de Login

Crea `src/pages/LoginPage.jsx`:

```javascript
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login(username, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.message || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h1>Iniciar Sesión</h1>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div>
          <label>Usuario:</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
        </div>
        
        <div>
          <label>Contraseña:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Iniciando...' : 'Iniciar Sesión'}
        </button>
      </form>
    </div>
  );
}
```

### 6. Actualizar Llamadas a API

**Antes**:
```javascript
const response = await fetch('/api/tickets');
```

**Después**:
```javascript
import axios from 'axios';

const response = await axios.get('/api/tickets');
// El token se agrega automáticamente por el interceptor
```



## Requisitos de Contraseña

Las contraseñas deben cumplir los siguientes requisitos de complejidad:

- **Longitud mínima**: 8 caracteres
- **Al menos una letra mayúscula** (A-Z)
- **Al menos una letra minúscula** (a-z)
- **Al menos un dígito** (0-9)

**Ejemplos válidos**:
- `MiContraseña123`
- `Password2024!`
- `Segura99`

**Ejemplos inválidos**:
- `password` (sin mayúscula ni dígito)
- `PASSWORD123` (sin minúscula)
- `Pass1` (muy corta)

## Manejo de Errores Específicos

### Rate Limiting (429)

Cuando recibes un error 429, el servidor incluye un header `Retry-After` que indica cuántos segundos debes esperar:

```javascript
try {
  await authService.login(username, password);
} catch (error) {
  if (error.response?.status === 429) {
    const retryAfter = error.response.headers['retry-after'];
    alert(`Demasiados intentos. Espera ${retryAfter} segundos.`);
  }
}
```

### Validación de Datos (400)

Los errores de validación incluyen detalles específicos:

```json
{
  "error": "validation_error",
  "message": "Datos inválidos",
  "details": {
    "password": ["La contraseña debe tener al menos 8 caracteres", "La contraseña debe incluir al menos un dígito"]
  },
  "error_id": "uuid-del-error"
}
```

### Conflictos de Sincronización (409)

Cuando hay conflictos en sincronización offline:

```javascript
const result = await syncOfflineOperations(operations);

result.resultados.forEach(resultado => {
  if (resultado.status === 'conflict') {
    console.log(`Conflicto en operación ${resultado.id}:`);
    console.log(`Razón: ${resultado.error}`);
    // Implementar estrategia de resolución (last write wins, manual, etc.)
  }
});
```

## Cambios en Endpoints Existentes

### Contraseña PDF en Header

**Antes** (query parameter):
```
GET /pdf/ticket/123?token=mi_contraseña
```

**Después** (header):
```
GET /pdf/ticket/123
Headers:
  Authorization: Bearer {access_token}
  X-PDF-Password: mi_contraseña
```

**Código de ejemplo**:
```javascript
// React Native
const response = await authService.authenticatedRequest(
  `${API_URL}/pdf/ticket/${ticketId}`,
  {
    headers: {
      'X-PDF-Password': pdfPassword,
    },
  }
);

// React Web
const response = await axios.get(`/pdf/ticket/${ticketId}`, {
  headers: {
    'X-PDF-Password': pdfPassword,
  },
});
```

### URLs Actualizadas

Algunos endpoints han cambiado de kebab-case a snake_case:

| Antes | Después |
|-------|---------|
| `/cobro-rapido` | `/cobro_rapido` |
| `/movimiento-caja` | `/movimiento_caja` |

**Nota**: Las URLs antiguas siguen funcionando temporalmente pero están marcadas como deprecated.

## Guía Paso a Paso de Migración

### Para App Móvil (React Native)

1. **Instalar dependencias**:
   ```bash
   npm install @react-native-async-storage/async-storage @react-native-community/netinfo
   ```

2. **Copiar AuthService** del ejemplo anterior a `src/services/authService.js`

3. **Implementar OfflineService** (opcional, para modo offline):
   ```javascript
   import NetInfo from '@react-native-community/netinfo';
   import AsyncStorage from '@react-native-async-storage/async-storage';
   import authService from './authService';

   class OfflineService {
     async enqueueOperation(operation) {
       const queue = await this.getPendingOperations();
       queue.push({
         ...operation,
         id: generateUUID(),
         timestamp: new Date().toISOString(),
       });
       await AsyncStorage.setItem('offline_queue', JSON.stringify(queue));
     }

     async getPendingOperations() {
       const queueStr = await AsyncStorage.getItem('offline_queue');
       return queueStr ? JSON.parse(queueStr) : [];
     }

     async syncPendingOperations() {
       const queue = await this.getPendingOperations();
       if (queue.length === 0) return { success: true, synced: 0 };

       try {
         const response = await authService.authenticatedRequest(
           `${API_URL}/api/mobile/sync/batch`,
           {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({ operaciones: queue }),
           }
         );

         const result = await response.json();
         
         // Remover operaciones exitosas de la cola
         const failedIds = result.resultados
           .filter(r => r.status === 'error' || r.status === 'conflict')
           .map(r => r.id);
         
         const remainingQueue = queue.filter(op => failedIds.includes(op.id));
         await AsyncStorage.setItem('offline_queue', JSON.stringify(remainingQueue));

         return result;
       } catch (error) {
         console.error('Error al sincronizar:', error);
         return { success: false, error: error.message };
       }
     }

     async startAutoSync() {
       NetInfo.addEventListener(state => {
         if (state.isConnected) {
           this.syncPendingOperations();
         }
       });
     }
   }

   export default new OfflineService();
   ```

4. **Actualizar App.js** para inicializar servicios:
   ```javascript
   import { useEffect } from 'react';
   import authService from './services/authService';
   import offlineService from './services/offlineService';

   function App() {
     useEffect(() => {
       offlineService.startAutoSync();
     }, []);

     // ... resto del componente
   }
   ```

5. **Actualizar todas las llamadas a API** para usar `authService.authenticatedRequest()`

6. **Implementar pantalla de login** usando el ejemplo anterior

7. **Probar flujo completo**: Login → Operaciones → Logout

### Para Frontend Web (React)

1. **Instalar dependencias**:
   ```bash
   npm install axios react-router-dom
   ```

2. **Copiar AuthService** del ejemplo anterior a `src/services/authService.js`

3. **Copiar ProtectedRoute** del ejemplo anterior a `src/components/ProtectedRoute.jsx`

4. **Actualizar rutas** en `App.jsx` para usar ProtectedRoute

5. **Implementar pantalla de login** usando el ejemplo anterior

6. **Actualizar todas las llamadas a API** para usar axios (los interceptors agregan el token automáticamente)

7. **Actualizar llamadas de PDF** para enviar contraseña por header:
   ```javascript
   const response = await axios.get(`/pdf/ticket/${ticketId}`, {
     headers: {
       'X-PDF-Password': pdfPassword,
     },
     responseType: 'blob',
   });
   ```

8. **Probar flujo completo**: Login → Operaciones → Logout

## Período de Transición

Durante la migración, el sistema soporta ambos métodos de autenticación:

1. **Usuarios existentes**: Pueden hacer login con sus contraseñas actuales
2. **Migración automática**: En el primer login exitoso, la contraseña se migra automáticamente a bcrypt
3. **Nuevos usuarios**: Usan bcrypt desde el inicio
4. **Modo legacy**: Después de 30 días, se puede deshabilitar con `ENABLE_LEGACY_AUTH=false`

## Troubleshooting

### Error: "Invalid token"

**Causa**: Token expirado o inválido

**Solución**: Usar refresh token para obtener nuevo access token. Si refresh token también expiró, solicitar login nuevamente.

### Error: "Too many requests"

**Causa**: Rate limit excedido

**Solución**: Esperar el tiempo indicado en header `Retry-After` antes de reintentar.

### Error: "Insufficient permissions"

**Causa**: Usuario no tiene el rol requerido para la operación

**Solución**: Contactar al administrador para solicitar permisos necesarios.

### Sincronización offline falla

**Causa**: Operaciones muy antiguas (>30 días) o conflictos con datos del servidor

**Solución**: 
- Verificar que las operaciones no sean muy antiguas
- Revisar los conflictos en la respuesta y resolverlos manualmente
- Implementar estrategia de resolución de conflictos (last write wins, manual, etc.)

## Soporte

Para preguntas o problemas durante la migración, contacta al equipo de desarrollo.
