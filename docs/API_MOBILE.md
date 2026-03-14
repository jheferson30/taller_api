# 📱 API Mobile - PULGA Mecánica Fi

## Descripción

API REST simplificada para aplicaciones móviles que permite gestionar tickets desde dispositivos móviles conectándose al backend local.

**Base URL**: `http://127.0.0.1:8000/api/mobile`

---

## 🔌 Conexión

La app móvil debe conectarse al servidor local donde corre el backend:

```
http://127.0.0.1:8000/api/mobile
```

O si el servidor está en otra máquina de la red local:

```
http://192.168.1.X:8000/api/mobile
```

---

## 📋 Endpoints Disponibles

### 1. Listar Tickets

**GET** `/api/mobile/tickets`

Lista todos los tickets con información básica.

**Query Parameters:**
- `estado` (opcional): Filtra por estado (ABIERTO, EN_PROCESO, FINALIZADO, ENTREGADO)

**Ejemplo:**
```bash
GET /api/mobile/tickets?estado=EN_PROCESO
```

**Response:**
```json
[
  {
    "id": 1,
    "ticket_codigo": "TK-ABC123-20260313120000",
    "placa": "ABC123",
    "motivo_visita": "Mantenimiento preventivo",
    "estado": "EN_PROCESO",
    "fecha_ingreso": "2026-03-13T12:00:00",
    "nombre_propietario": "Juan Pérez",
    "telefono_propietario": "3001234567"
  }
]
```

---

### 2. Obtener Detalle de Ticket

**GET** `/api/mobile/tickets/{ticket_id}`

Obtiene los detalles completos de un ticket específico.

**Ejemplo:**
```bash
GET /api/mobile/tickets/1
```

**Response:**
```json
{
  "id": 1,
  "ticket_codigo": "TK-ABC123-20260313120000",
  "placa": "ABC123",
  "motivo_visita": "Mantenimiento preventivo",
  "estado": "EN_PROCESO",
  "fecha_ingreso": "2026-03-13T12:00:00",
  "observaciones_recepcion": "Cliente reporta ruido en motor",
  "kilometraje": 50000,
  "estado_inicial": "Bueno",
  "anticipo_recibido": 100000,
  "total_servicio": 250000,
  "saldo_pendiente": 150000,
  "nombre_propietario": "Juan Pérez",
  "telefono_propietario": "3001234567"
}
```

---

### 3. Listar Procesos de un Ticket

**GET** `/api/mobile/tickets/{ticket_id}/procesos`

Lista todos los procesos realizados en un ticket.

**Ejemplo:**
```bash
GET /api/mobile/tickets/1/procesos
```

**Response:**
```json
[
  {
    "id": 1,
    "nombre": "Cambio de aceite",
    "descripcion": "Aceite 20W50 sintético",
    "mecanico": "Carlos Rodríguez"
  }
]
```

---

### 4. Crear Proceso

**POST** `/api/mobile/tickets/{ticket_id}/procesos`

Agrega un nuevo proceso a un ticket.

**Body:**
```json
{
  "nombre": "Cambio de frenos",
  "descripcion": "Pastillas delanteras y traseras",
  "mecanico": "Pedro Gómez"
}
```

**Response:**
```json
{
  "id": 2,
  "nombre": "Cambio de frenos",
  "descripcion": "Pastillas delanteras y traseras",
  "mecanico": "Pedro Gómez"
}
```

---

### 5. Listar Repuestos de un Ticket

**GET** `/api/mobile/tickets/{ticket_id}/repuestos`

Lista todos los repuestos utilizados en un ticket.

**Ejemplo:**
```bash
GET /api/mobile/tickets/1/repuestos
```

**Response:**
```json
[
  {
    "id": 1,
    "nombre": "Filtro de aceite",
    "cantidad": 1,
    "marca_referencia": "Mann W719/30"
  }
]
```

---

### 6. Agregar Repuesto

**POST** `/api/mobile/tickets/{ticket_id}/repuestos`

Agrega un repuesto a un ticket.

**Body:**
```json
{
  "nombre": "Pastillas de freno",
  "cantidad": 4,
  "marca_referencia": "Brembo P23 123",
  "proceso_id": 2
}
```

**Response:**
```json
{
  "id": 2,
  "nombre": "Pastillas de freno",
  "cantidad": 4,
  "marca_referencia": "Brembo P23 123"
}
```

---

### 7. Listar Fotos de un Ticket

**GET** `/api/mobile/tickets/{ticket_id}/fotos`

Lista todas las fotos de evidencia de un ticket.

**Ejemplo:**
```bash
GET /api/mobile/tickets/1/fotos
```

**Response:**
```json
[
  {
    "id": 1,
    "tipo": "ANTES",
    "archivo_url": "http://127.0.0.1:8000/uploads/fotos/20260313_120000_abc123.jpg",
    "descripcion": "Estado inicial del motor"
  }
]
```

---

### 8. Actualizar Estado del Ticket

**PATCH** `/api/mobile/tickets/{ticket_id}/estado`

Cambia el estado de un ticket.

**Body:**
```json
{
  "estado": "EN_PROCESO"
}
```

**Estados válidos:**
- `ABIERTO`
- `EN_PROCESO`
- `FINALIZADO`
- `ENTREGADO`

**Response:**
```json
{
  "message": "Estado actualizado correctamente",
  "nuevo_estado": "EN_PROCESO"
}
```

---

### 9. Obtener Resumen del Ticket

**GET** `/api/mobile/tickets/{ticket_id}/resumen`

Obtiene un resumen completo con contadores y finanzas.

**Ejemplo:**
```bash
GET /api/mobile/tickets/1/resumen
```

**Response:**
```json
{
  "ticket_id": 1,
  "ticket_codigo": "TK-ABC123-20260313120000",
  "placa": "ABC123",
  "estado": "EN_PROCESO",
  "contadores": {
    "procesos": 3,
    "repuestos": 5,
    "fotos": 8,
    "compras": 2
  },
  "finanzas": {
    "anticipo": 100000,
    "total_egresos": 80000,
    "total_cobros": 250000,
    "total_servicio": 250000,
    "saldo_pendiente": 150000
  }
}
```

---

### 10. Obtener Estadísticas Generales

**GET** `/api/mobile/estadisticas`

Obtiene estadísticas generales para el dashboard móvil.

**Ejemplo:**
```bash
GET /api/mobile/estadisticas
```

**Response:**
```json
{
  "total_tickets": 45,
  "por_estado": {
    "abiertos": 5,
    "en_proceso": 12,
    "finalizados": 8,
    "entregados": 20
  }
}
```

---

## 🔐 Autenticación

Actualmente la API no requiere autenticación ya que está diseñada para uso en red local. Si necesitas agregar autenticación, considera:

- JWT tokens
- API keys
- OAuth2

---

## 🌐 CORS

El backend ya está configurado para aceptar peticiones desde cualquier origen en red local. Si necesitas agregar más orígenes, edita `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "*"  # Permite todos los orígenes (solo para desarrollo)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📱 Ejemplo de Uso en App Móvil

### React Native / Expo

```javascript
const API_BASE_URL = 'http://192.168.1.100:8000/api/mobile';

// Listar tickets
async function getTickets(estado = null) {
  const url = estado 
    ? `${API_BASE_URL}/tickets?estado=${estado}`
    : `${API_BASE_URL}/tickets`;
  
  const response = await fetch(url);
  const data = await response.json();
  return data;
}

// Obtener detalle de ticket
async function getTicketDetail(ticketId) {
  const response = await fetch(`${API_BASE_URL}/tickets/${ticketId}`);
  const data = await response.json();
  return data;
}

// Crear proceso
async function createProceso(ticketId, proceso) {
  const response = await fetch(`${API_BASE_URL}/tickets/${ticketId}/procesos`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(proceso),
  });
  const data = await response.json();
  return data;
}

// Actualizar estado
async function updateEstado(ticketId, nuevoEstado) {
  const response = await fetch(`${API_BASE_URL}/tickets/${ticketId}/estado`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ estado: nuevoEstado }),
  });
  const data = await response.json();
  return data;
}
```

### Flutter

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class MobileAPI {
  static const String baseUrl = 'http://192.168.1.100:8000/api/mobile';
  
  // Listar tickets
  static Future<List<dynamic>> getTickets({String? estado}) async {
    final url = estado != null 
      ? '$baseUrl/tickets?estado=$estado'
      : '$baseUrl/tickets';
    
    final response = await http.get(Uri.parse(url));
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Error al cargar tickets');
    }
  }
  
  // Obtener detalle de ticket
  static Future<Map<String, dynamic>> getTicketDetail(int ticketId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/tickets/$ticketId')
    );
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Error al cargar ticket');
    }
  }
  
  // Crear proceso
  static Future<Map<String, dynamic>> createProceso(
    int ticketId, 
    Map<String, dynamic> proceso
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/tickets/$ticketId/procesos'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(proceso),
    );
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Error al crear proceso');
    }
  }
}
```

---

## 🧪 Pruebas con cURL

```bash
# Listar todos los tickets
curl http://127.0.0.1:8000/api/mobile/tickets

# Listar tickets en proceso
curl http://127.0.0.1:8000/api/mobile/tickets?estado=EN_PROCESO

# Obtener detalle de ticket
curl http://127.0.0.1:8000/api/mobile/tickets/1

# Crear proceso
curl -X POST http://127.0.0.1:8000/api/mobile/tickets/1/procesos \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Cambio de aceite","mecanico":"Carlos"}'

# Actualizar estado
curl -X PATCH http://127.0.0.1:8000/api/mobile/tickets/1/estado \
  -H "Content-Type: application/json" \
  -d '{"estado":"EN_PROCESO"}'

# Obtener resumen
curl http://127.0.0.1:8000/api/mobile/tickets/1/resumen

# Obtener estadísticas
curl http://127.0.0.1:8000/api/mobile/estadisticas
```

---

## 📝 Notas Importantes

1. **Red Local**: La app móvil debe estar en la misma red WiFi que el servidor
2. **IP del Servidor**: Reemplaza `192.168.1.100` con la IP real de tu servidor
3. **Puerto**: El backend corre en el puerto `8000` por defecto
4. **HTTPS**: Para producción, considera usar HTTPS con certificados SSL
5. **Firewall**: Asegúrate de que el puerto 8000 esté abierto en el firewall

---

## 🚀 Próximas Mejoras

- [ ] Autenticación con JWT
- [ ] Subida de fotos desde móvil
- [ ] Notificaciones push
- [ ] Sincronización offline
- [ ] Firma digital del cliente
- [ ] Geolocalización de servicios

---

**Versión**: 1.0  
**Última actualización**: Marzo 2026
