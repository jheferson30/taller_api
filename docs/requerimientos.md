# Requerimientos del Sistema - Taller Mecánico

## 1. Descripción General

Sistema de gestión integral para taller mecánico que permite administrar vehículos, tickets de servicio, procesos técnicos y economía diaria. Incluye frontend web para operadores y API móvil para consultas.

## 2. Requerimientos Funcionales

### 2.1 Gestión de Vehículos

#### RF-001: Búsqueda de Vehículos
- El sistema debe permitir buscar vehículos por placa
- Debe indicar si el vehículo existe o no en la base de datos
- La búsqueda debe normalizar la placa (mayúsculas, sin espacios)

#### RF-002: Registro de Vehículos
- El sistema debe permitir registrar nuevos vehículos con:
  - Placa (obligatorio, único)
  - Marca (obligatorio)
  - Modelo (obligatorio)
  - Año (obligatorio)
  - Cilindraje (opcional)
  - Color (opcional)
  - Nombre del propietario (opcional)
  - Teléfono del propietario (opcional)
- Debe validar que la placa no esté duplicada

#### RF-003: Actualización de Vehículos
- El sistema debe permitir actualizar datos de vehículos existentes
- Debe buscar el vehículo por placa
- Debe permitir actualización parcial de campos

#### RF-004: Ficha del Vehículo
- El sistema debe mostrar ficha completa del vehículo con:
  - Datos básicos del vehículo
  - Datos del propietario
  - Historial completo de visitas (tickets)
- El historial debe ordenarse por fecha de ingreso descendente

### 2.2 Recepción de Tickets

#### RF-005: Creación de Ticket de Ingreso
- El sistema debe crear tickets de ingreso vinculados a un vehículo existente
- Debe generar código único automático con formato: `TK-{PLACA}-{TIMESTAMP}`
- Debe registrar:
  - Motivo de visita (obligatorio)
  - Observaciones de recepción (opcional)
  - Kilometraje (opcional)
  - Estado inicial del vehículo (opcional)
  - Anticipo recibido (obligatorio, puede ser 0)
  - Método de pago del anticipo (opcional)
  - Persona que recepciona (opcional)
- Estado inicial del ticket: ABIERTO

#### RF-006: Registro Automático de Anticipo
- Si el anticipo es mayor a 0, el sistema debe crear automáticamente:
  - Movimiento de caja tipo INGRESO_ANTICIPO
  - Vinculado al ticket creado
  - Con el valor del anticipo y método de pago

### 2.3 Proceso Técnico

#### RF-007: Listado de Tickets Abiertos
- El sistema debe listar tickets en estado ABIERTO o EN_PROCESO
- Debe permitir filtrar por placa
- Debe ordenar por fecha de ingreso descendente
- Debe soportar paginación

#### RF-008: Búsqueda de Tickets
- El sistema debe permitir buscar tickets por:
  - Código de ticket
  - Placa
  - Estado
- Debe soportar búsqueda combinada de criterios

#### RF-009: Resumen de Ticket
- El sistema debe mostrar resumen completo del ticket con:
  - Datos del ticket
  - Lista de procesos realizados
  - Lista de repuestos utilizados
  - Lista de fotos de evidencia
  - Lista de compras asociadas

#### RF-010: Registro de Procesos
- El sistema debe permitir agregar procesos al ticket con:
  - Nombre del proceso (obligatorio)
  - Descripción (opcional)
  - Mecánico responsable (opcional)
- Al agregar el primer proceso, el ticket debe cambiar a estado EN_PROCESO
- No debe permitir agregar procesos a tickets FINALIZADOS o ENTREGADOS

#### RF-011: Catálogo de Procesos Rápidos
- El sistema debe proveer lista de procesos comunes:
  - Cambio de aceite
  - Lavado de frenos
  - Ajuste de frenos
  - Revisión general
  - Cambio de bujía
  - Ajuste de cadena
  - Engrase general

#### RF-012: Eliminación de Procesos
- El sistema debe permitir eliminar procesos de tickets no finalizados
- Debe validar que el proceso pertenezca al ticket

#### RF-013: Registro de Repuestos
- El sistema debe permitir agregar repuestos al ticket con:
  - Nombre del repuesto (obligatorio)
  - Cantidad (obligatorio, default 1)
  - Marca/referencia (opcional)
- Al agregar el primer repuesto, el ticket debe cambiar a estado EN_PROCESO
- No debe permitir agregar repuestos a tickets FINALIZADOS o ENTREGADOS

#### RF-014: Eliminación de Repuestos
- El sistema debe permitir eliminar repuestos de tickets no finalizados
- Debe validar que el repuesto pertenezca al ticket

#### RF-015: Registro de Fotos de Evidencia
- El sistema debe permitir agregar fotos al ticket con:
  - Tipo de foto (ANTES, DESPUES, OTRA)
  - URL del archivo (obligatorio)
  - Descripción (opcional)
- Al agregar la primera foto, el ticket debe cambiar a estado EN_PROCESO
- No debe permitir agregar fotos a tickets FINALIZADOS o ENTREGADOS

#### RF-016: Eliminación de Fotos
- El sistema debe permitir eliminar fotos de tickets no finalizados
- Debe validar que la foto pertenezca al ticket

#### RF-017: Registro de Compras
- El sistema debe permitir registrar compras asociadas al ticket con:
  - Descripción (obligatorio)
  - Valor (obligatorio)
  - URL de soporte (opcional)
  - Nota (opcional)
  - Responsable (opcional)
- Debe crear automáticamente movimiento de caja tipo EGRESO
- Al agregar la primera compra, el ticket debe cambiar a estado EN_PROCESO
- No debe permitir agregar compras a tickets FINALIZADOS o ENTREGADOS

#### RF-018: Actualización de Finanzas
- El sistema debe permitir definir finanzas del ticket:
  - Total del servicio (obligatorio)
  - Método de pago final (obligatorio)
- Debe calcular automáticamente saldo pendiente: total - anticipo
- Si el saldo es negativo, debe ajustarse a 0
- No debe permitir actualizar finanzas de tickets FINALIZADOS o ENTREGADOS

#### RF-019: Observaciones Finales
- El sistema debe permitir registrar:
  - Observaciones finales (opcional)
  - Recomendaciones (opcional)
  - Próximo mantenimiento (opcional)
- No debe permitir actualizar observaciones de tickets FINALIZADOS o ENTREGADOS

#### RF-020: Finalización de Ticket
- El sistema debe permitir finalizar tickets
- Debe validar que el total del servicio esté definido
- Debe cambiar estado a FINALIZADO
- Debe registrar fecha de cierre
- Si hay saldo pendiente > 0, debe crear movimiento de caja tipo INGRESO_FINAL
- No debe permitir finalizar tickets ya FINALIZADOS o ENTREGADOS

#### RF-021: Generación de PDF para Cliente
- El sistema debe generar PDF con resumen del servicio:
  - Datos del ticket (código, placa, fechas, estado)
  - Motivo de visita y observaciones
  - Lista de procesos realizados (máximo 20)
  - Lista de repuestos utilizados (máximo 20)
  - Totales financieros (total, anticipo, saldo)
  - Recomendaciones y próximo mantenimiento
- El PDF debe generarse en formato estándar PDF 1.4

#### RF-022: Entrega de Ticket
- El sistema debe permitir marcar ticket como ENTREGADO
- Solo debe permitir entregar tickets en estado FINALIZADO
- Debe registrar:
  - Persona que confirma entrega (obligatorio)
  - URL de firma de entrega (opcional)
  - Fecha de entrega
- Debe cambiar estado a ENTREGADO

### 2.4 Economía y Caja

#### RF-023: Resumen Diario de Economía
- El sistema debe calcular resumen del día con:
  - Total de ingresos por anticipos
  - Total de ingresos por cobros finales
  - Total de ingresos (suma de ambos)
  - Total de egresos
  - Balance del día (ingresos - egresos)
  - Cantidad de tickets cerrados en el día
  - Cantidad de tickets abiertos con anticipo en el día
- Debe permitir consultar por fecha específica (default: hoy)

#### RF-024: Detalle de Ingresos Diarios
- El sistema debe listar ingresos del día separados en:
  - Anticipos recibidos con: ticket, placa, valor, hora, responsable, estado, método de pago
  - Cobros finales con: ticket, placa, valor, hora, responsable, estado, método de pago, observación
- Debe permitir consultar por fecha específica (default: hoy)

#### RF-025: Detalle de Egresos Diarios
- El sistema debe listar egresos del día con:
  - Fecha y hora
  - Categoría (REPUESTO, PARTE, INSUMO, HERRAMIENTA, OTRO)
  - Concepto
  - Ticket asociado (si aplica)
  - Placa (si aplica)
  - Valor
  - Responsable
  - URL de soporte
  - Observación
- Debe permitir consultar por fecha específica (default: hoy)

#### RF-026: PDF de Cierre Diario
- El sistema debe generar PDF de cierre con:
  - Fecha del cierre
  - Resumen de ingresos (anticipos, cobros finales, total)
  - Resumen de egresos
  - Balance del día
  - Detalle de anticipos (máximo 10)
  - Detalle de cobros finales (máximo 10)
  - Detalle de egresos (máximo 10)
- Debe requerir password de PDF en header X-PDF-Password
- El PDF debe generarse en formato estándar PDF 1.4

#### RF-027: Histórico de Economía
- El sistema debe generar reporte histórico por rango de fechas
- Debe mostrar resumen diario para cada fecha en el rango
- Debe requerir password de administrador en header X-Admin-Password
- Debe validar que fecha_hasta >= fecha_desde

#### RF-028: Registro Manual de Movimientos
- El sistema debe permitir crear movimientos de caja manualmente
- Para ingresos (INGRESO_ANTICIPO, INGRESO_FINAL) debe requerir:
  - Código de ticket (obligatorio)
  - Placa (obligatorio)
  - Estado del ticket (obligatorio)
  - Valor (obligatorio)
  - Método de pago (opcional)
- Para egresos debe requerir:
  - Concepto (obligatorio)
  - Categoría de egreso (obligatorio)
  - Valor (obligatorio)

#### RF-029: Listado de Movimientos de Caja
- El sistema debe listar movimientos con filtros opcionales:
  - Tipo de movimiento
  - Estado del ticket
  - Categoría de egreso
  - Placa
  - Rango de fechas (desde/hasta)
- Debe soportar paginación
- Debe ordenar por fecha de creación descendente

#### RF-030: Corrección de Movimientos
- El sistema debe permitir corregir movimientos de caja existentes
- Debe requerir password de administrador
- Debe permitir modificar:
  - Valor
  - Observación
- Debe crear registro de auditoría con:
  - Motivo de la corrección (obligatorio)
  - Valor anterior y nuevo
  - Observación anterior y nueva
  - Usuario que actualiza
  - Fecha de la corrección

#### RF-031: Historial de Correcciones
- El sistema debe mostrar historial de cambios de un movimiento
- Debe requerir password de administrador
- Debe ordenar por fecha de creación descendente

### 2.5 API Móvil

#### RF-032: Health Check Móvil
- El sistema debe proveer endpoint de verificación de estado
- Debe retornar indicador de disponibilidad y scope

#### RF-033: Tickets Activos Móvil
- El sistema debe listar tickets activos (ABIERTO, EN_PROCESO)
- Debe permitir filtrar por placa
- Debe retornar: id, código, placa, estado, motivo, fecha de ingreso
- Debe limitar a 100 resultados
- Debe ordenar por fecha de ingreso descendente

#### RF-034: Timeline de Ticket Móvil
- El sistema debe mostrar línea de tiempo del ticket con:
  - Lista de procesos (id, nombre, descripción, mecánico, fecha)
  - Lista de fotos (id, tipo, URL, descripción, fecha)
- Debe ordenar por fecha de creación ascendente

## 3. Requerimientos No Funcionales

### 3.1 Tecnología

#### RNF-001: Stack Backend
- Framework: FastAPI (Python)
- ORM: SQLAlchemy
- Base de datos: PostgreSQL
- Servidor: Uvicorn
- Dependencias: psycopg2-binary

#### RNF-002: Stack Frontend
- Framework: React 18
- Routing: React Router DOM 6
- Build tool: Vite 5
- Lenguaje: JavaScript (JSX)

#### RNF-003: API REST
- Arquitectura: REST
- Formato de datos: JSON
- Documentación: OpenAPI (Swagger) automática
- CORS: Habilitado para localhost:5173

### 3.2 Seguridad

#### RNF-004: Autenticación por Password
- Endpoints administrativos protegidos con header X-Admin-Password
- PDF de economía protegido con header X-PDF-Password
- Passwords configurables (default: "1234")

#### RNF-005: Validación de Datos
- Validación de tipos con Pydantic schemas
- Validación de longitudes de campos
- Normalización de placas (mayúsculas)
- Validación de unicidad de placas y códigos de ticket

### 3.3 Base de Datos

#### RNF-006: Modelo de Datos
- Tablas principales:
  - vehiculos
  - tickets
  - movimientos_caja
  - ticket_procesos
  - ticket_repuestos
  - ticket_fotos
  - ticket_compras
  - cambios_movimiento_caja

#### RNF-007: Tipos Enumerados
- TipoMovimiento: INGRESO_ANTICIPO, INGRESO_FINAL, EGRESO
- EstadoTicket: ABIERTO, EN_PROCESO, FINALIZADO, ENTREGADO
- CategoriaEgreso: REPUESTO, PARTE, INSUMO, HERRAMIENTA, OTRO

#### RNF-008: Índices
- Índices en campos de búsqueda frecuente:
  - vehiculos.placa
  - tickets.vehiculo_id, ticket_codigo, placa, estado
  - movimientos_caja.ticket_id, ticket_codigo, placa
  - Todas las foreign keys

#### RNF-009: Integridad Referencial
- Foreign keys con referencias a tablas padre
- Cascadas no definidas (eliminación manual)
- Timestamps automáticos (created_at, updated_at)

### 3.4 Rendimiento

#### RNF-010: Paginación
- Listados con paginación configurable
- Límite máximo: 200 registros por página
- Default: 50 registros por página

#### RNF-011: Límites de Resultados
- Búsquedas limitadas a 100 resultados
- PDFs limitados a 20 items por sección
- API móvil limitada a 100 tickets activos

### 3.5 Auditoría

#### RNF-012: Trazabilidad
- Registro de fechas de creación en todas las entidades
- Registro de fechas de actualización donde aplique
- Auditoría completa de correcciones en movimientos de caja
- Registro de responsables en operaciones críticas

### 3.6 Usabilidad

#### RNF-013: Interfaz de Usuario
- Diseño responsivo con grid system
- Páginas separadas por función:
  - Página 1: Economía del día
  - Página 2: Recepción de vehículos
  - Página 3: Proceso de tickets
- Mensajes de estado para feedback de operaciones

#### RNF-014: Generación de Documentos
- PDFs generados en formato estándar PDF 1.4
- Encoding latin-1 para compatibilidad
- Escape de caracteres especiales en PDFs
- Nombres de archivo descriptivos con fecha/código

## 4. Reglas de Negocio

### RN-001: Flujo de Estados del Ticket
1. ABIERTO: Estado inicial al crear ticket
2. EN_PROCESO: Al agregar primer proceso/repuesto/foto/compra
3. FINALIZADO: Al ejecutar finalización (requiere total definido)
4. ENTREGADO: Al confirmar entrega (solo desde FINALIZADO)

### RN-002: Cálculo de Saldo Pendiente
- Saldo = Total del servicio - Anticipo recibido
- Si saldo < 0, se ajusta a 0
- El saldo se calcula al definir finanzas y al finalizar

### RN-003: Movimientos de Caja Automáticos
- Anticipo > 0 → Crea INGRESO_ANTICIPO al crear ticket
- Compra → Crea EGRESO al registrar compra
- Saldo > 0 → Crea INGRESO_FINAL al finalizar ticket

### RN-004: Edición de Tickets
- Solo tickets ABIERTOS o EN_PROCESO son editables
- Tickets FINALIZADOS o ENTREGADOS no permiten:
  - Agregar/eliminar procesos
  - Agregar/eliminar repuestos
  - Agregar/eliminar fotos
  - Agregar compras
  - Actualizar finanzas
  - Actualizar observaciones

### RN-005: Generación de Código de Ticket
- Formato: TK-{PLACA}-{TIMESTAMP}
- TIMESTAMP: YYYYMMDDHHMMSSffffff (UTC)
- Garantiza unicidad por combinación placa + microsegundos

### RN-006: Normalización de Placas
- Todas las placas se convierten a mayúsculas
- Se eliminan espacios al inicio y final
- Se aplica en búsquedas y registros

### RN-007: Economía Diaria
- Los cálculos se basan en fecha de creación del movimiento
- Se usa la fecha del servidor (UTC)
- Los totales incluyen todos los movimientos del día (00:00 a 23:59)

### RN-008: Correcciones con Auditoría
- Toda corrección de movimiento requiere motivo
- Se registra valor anterior y nuevo
- Se registra observación anterior y nueva
- Se registra usuario que realiza la corrección
- El historial es inmutable

## 5. Casos de Uso Principales

### CU-001: Recepción de Vehículo Nuevo
1. Operador busca vehículo por placa
2. Sistema indica que no existe
3. Operador completa datos del vehículo y propietario
4. Sistema crea vehículo
5. Operador completa datos del ticket de ingreso
6. Sistema crea ticket y registra anticipo en caja

### CU-002: Recepción de Vehículo Existente
1. Operador busca vehículo por placa
2. Sistema muestra ficha con historial
3. Operador actualiza datos si es necesario
4. Operador completa datos del ticket de ingreso
5. Sistema crea ticket y registra anticipo en caja

### CU-003: Proceso de Mantenimiento
1. Mecánico consulta tickets abiertos
2. Mecánico selecciona ticket a trabajar
3. Mecánico registra procesos realizados
4. Mecánico registra repuestos utilizados
5. Mecánico carga fotos de evidencia
6. Mecánico registra compras realizadas
7. Sistema actualiza estado y registra egresos

### CU-004: Cierre de Ticket
1. Operador define total del servicio y método de pago
2. Operador registra observaciones finales y recomendaciones
3. Operador finaliza ticket
4. Sistema calcula saldo y registra ingreso final
5. Sistema genera PDF para cliente
6. Cliente revisa y firma
7. Operador marca ticket como entregado

### CU-005: Cierre Diario de Caja
1. Administrador consulta resumen del día
2. Administrador revisa detalle de ingresos
3. Administrador revisa detalle de egresos
4. Administrador genera PDF de cierre con password
5. Sistema genera documento con todos los movimientos

## 6. Instalación y Configuración

### 6.1 Requisitos Previos
- Python 3.8+
- PostgreSQL 12+
- Node.js 16+
- npm o yarn

### 6.2 Configuración Backend
```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migración de base de datos
psql -U usuario -d nombre_db -f db/migracion_2026_02_28.sql

# Configurar variables de entorno
export DATABASE_URL="postgresql://usuario:password@localhost/nombre_db"
export PDF_PASSWORD="1234"
export ADMIN_PASSWORD="1234"

# Iniciar servidor
uvicorn app.main:app --reload
```

### 6.3 Configuración Frontend
```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev

# Build para producción
npm run build
```

### 6.4 Variables de Entorno
- `DATABASE_URL`: Conexión a PostgreSQL
- `PDF_PASSWORD`: Password para generar PDFs de economía
- `ADMIN_PASSWORD`: Password para endpoints administrativos
- `BASE_URL`: URL del backend (default: http://127.0.0.1:8000)

## 7. Endpoints de la API

### Vehículos
- `GET /vehiculos/buscar?placa={placa}` - Buscar vehículo
- `POST /vehiculos/` - Crear vehículo
- `GET /vehiculos/` - Listar vehículos
- `PUT /vehiculos/{placa}` - Actualizar vehículo
- `GET /vehiculos/{placa}` - Obtener vehículo
- `GET /vehiculos/{placa}/ficha` - Ficha completa
- `POST /vehiculos/{placa}/ticket-ingreso` - Crear ticket

### Tickets
- `GET /tickets/procesos-rapidos` - Catálogo de procesos
- `GET /tickets/abiertos` - Listar tickets abiertos
- `GET /tickets/buscar` - Buscar tickets
- `GET /tickets/{ticket_id}` - Obtener ticket
- `GET /tickets/{ticket_id}/resumen` - Resumen completo
- `POST /tickets/{ticket_id}/procesos` - Agregar proceso
- `DELETE /tickets/{ticket_id}/procesos/{proceso_id}` - Eliminar proceso
- `POST /tickets/{ticket_id}/repuestos` - Agregar repuesto
- `DELETE /tickets/{ticket_id}/repuestos/{repuesto_id}` - Eliminar repuesto
- `POST /tickets/{ticket_id}/fotos` - Agregar foto
- `DELETE /tickets/{ticket_id}/fotos/{foto_id}` - Eliminar foto
- `POST /tickets/{ticket_id}/compras` - Agregar compra
- `PUT /tickets/{ticket_id}/finanzas` - Actualizar finanzas
- `PUT /tickets/{ticket_id}/observaciones-finales` - Actualizar observaciones
- `POST /tickets/{ticket_id}/finalizar` - Finalizar ticket
- `GET /tickets/{ticket_id}/pdf` - Generar PDF cliente
- `POST /tickets/{ticket_id}/entregar` - Marcar entregado

### Economía
- `GET /economia-dia` - Resumen del día
- `GET /economia-dia/ingresos` - Detalle de ingresos
- `GET /economia-dia/egresos` - Detalle de egresos
- `GET /economia-dia/pdf` - PDF de cierre (requiere password)
- `GET /economia-dia/historico` - Histórico (requiere password admin)

### Movimientos de Caja
- `POST /movimientos-caja/` - Crear movimiento
- `GET /movimientos-caja/` - Listar movimientos
- `PUT /movimientos-caja/{movimiento_id}/corregir` - Corregir (requiere password admin)
- `GET /movimientos-caja/{movimiento_id}/cambios` - Historial de cambios (requiere password admin)

### API Móvil
- `GET /mobile/v1/health` - Health check
- `GET /mobile/v1/tickets/activos` - Tickets activos
- `GET /mobile/v1/tickets/{ticket_id}/timeline` - Timeline del ticket

## 8. Pruebas

Ver archivo `docs/pruebas_e2e_taller.md` para pruebas end-to-end completas que cubren:
- Flujo de recepción
- Flujo de proceso técnico
- Flujo de economía
- Validación de API móvil
