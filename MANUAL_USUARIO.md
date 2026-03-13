# 📘 Manual de Usuario - Sistema de Gestión de Taller Mecánico

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Instalación y Configuración](#instalación-y-configuración)
3. [Módulo de Vehículos](#módulo-de-vehículos)
4. [Módulo de Citas](#módulo-de-citas)
5. [Módulo de Tickets](#módulo-de-tickets)
6. [Módulo de Economía](#módulo-de-economía)
7. [Sistema de Archivos](#sistema-de-archivos)
8. [Generación de PDFs](#generación-de-pdfs)
9. [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Introducción

Sistema completo de gestión para talleres mecánicos que incluye:
- Gestión de vehículos y clientes
- Sistema de citas con calendario
- Control de tickets de servicio
- Gestión financiera (ingresos y egresos)
- Generación de PDFs profesionales
- Sistema de seguridad para información sensible

---

## 🚀 Instalación y Configuración

### Requisitos Previos

- Python 3.8 o superior
- PostgreSQL 12 o superior
- Node.js 16 o superior
- npm o yarn

### Instalación del Backend

```bash
# Instalar dependencias de Python
pip install -r requirements.txt

# Configurar base de datos
# Ejecutar migraciones en orden:
psql -U tu_usuario -d tu_base_datos -f db/migracion_2026_02_28.sql
psql -U tu_usuario -d tu_base_datos -f db/migracion_cobros_2026_03_11.sql
psql -U tu_usuario -d tu_base_datos -f db/migracion_seguridad_2026_03_11.sql
psql -U tu_usuario -d tu_base_datos -f db/migracion_citas_2026_03_12.sql
psql -U tu_usuario -d tu_base_datos -f db/migracion_vehiculos_opcionales_2026_03_12.sql
psql -U tu_usuario -d tu_base_datos -f db/migracion_citas_vehiculo_2026_03_13.sql

# Iniciar servidor backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Instalación del Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

El sistema estará disponible en:
- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8000

---

## 🚗 Módulo de Vehículos

### Registrar un Vehículo

1. Ve a la página principal (Recepción)
2. Completa el formulario con:
   - **Placa** (obligatorio)
   - Marca, Modelo, Año
   - Cilindraje, Color
   - Nombre del propietario
   - Teléfono del propietario
3. Click en "Registrar Vehículo"

### Buscar un Vehículo

- Usa el campo de búsqueda en la parte superior
- Busca por placa, propietario o teléfono
- Los resultados se filtran en tiempo real

### Editar un Vehículo

1. Busca el vehículo
2. Click en el botón de editar (lápiz)
3. Modifica los campos necesarios
4. Click en "Actualizar"

---

## 📅 Módulo de Citas

### Crear una Cita

1. Ve a **Citas** → Click en "Nueva Cita"
2. **Datos del Vehículo:**
   - Ingresa la placa y click en "Buscar"
   - Si existe: se cargan todos los datos automáticamente
   - Si no existe: completa marca, modelo, año, cilindraje, color
3. **Datos del Cliente:**
   - Nombre completo
   - Teléfono de contacto
4. **Datos de la Cita:**
   - Fecha y hora
   - Motivo de la visita
   - Observaciones (opcional)
5. Click en "Agendar Cita"

### Estados de las Citas

- **PENDIENTE**: Cita recién creada, esperando confirmación
- **CONFIRMADA**: Cliente confirmó su asistencia
- **CONVERTIDA**: Ya se generó el ticket de ingreso
- **CANCELADA**: Cita cancelada

### Confirmar una Cita

1. En una cita con estado PENDIENTE
2. Click en "✓ Confirmar"
3. La cita cambia a CONFIRMADA

### Vista de Calendario

1. Click en el botón "📅 Calendario" (parte superior derecha)
2. Navega entre meses con "← Anterior" y "Siguiente →"
3. Los días con citas muestran:
   - Badge con cantidad de citas
   - Primeras 2 citas con hora y cliente
   - Indicador "+X más" si hay más citas

### Generar Ticket desde Cita

1. En una cita PENDIENTE o CONFIRMADA
2. Click en "🎫 Generar Ticket"
3. El sistema:
   - Crea el ticket automáticamente
   - Marca la cita como CONVERTIDA
   - Redirige a la página de tickets

---

## 🎫 Módulo de Tickets

### Crear Ticket de Ingreso

**Opción 1: Desde una Cita**
- Usa "Generar Ticket" en el módulo de citas

**Opción 2: Ingreso Directo**
1. Busca el vehículo por placa
2. Click en "Crear Ticket de Ingreso"
3. Completa:
   - Motivo de visita
   - Observaciones de recepción
   - Kilometraje
   - Estado inicial del vehículo
   - Anticipo recibido (opcional)
   - Método de pago del anticipo
   - Recepcionado por
4. Click en "Crear Ticket"

### Gestionar un Ticket

Un ticket tiene 5 pestañas principales:

#### 1. Procesos
- Agrega los trabajos realizados
- Campos: Nombre del proceso, Descripción, Mecánico
- Click en "Agregar Proceso"

#### 2. Repuestos
- Registra repuestos utilizados
- Campos: Nombre, Cantidad, Marca/Referencia
- Opcionalmente asocia a un proceso
- Click en "Agregar Repuesto"

#### 3. Fotos
- Sube fotos de evidencia del trabajo
- **Opción A**: Subir desde el equipo
  - Click en "Elegir archivo"
  - Selecciona la imagen
  - Verás un preview
- **Opción B**: Pegar URL de imagen externa
- Selecciona tipo: ANTES / DESPUES / OTRA
- Agrega descripción
- Click en "Agregar Foto"

#### 4. Compras
- Registra egresos del taller
- Campos:
  - Descripción de la compra
  - Valor
  - Responsable
  - Nota (opcional)
- **Soporte**: Sube factura o recibo
  - Opción A: Subir archivo desde el equipo
  - Opción B: Pegar URL
- Click en "Registrar Compra"

#### 5. Finanzas
- **Items de Cobro**: Define qué se le cobrará al cliente
  - Concepto (ej: "Mantenimiento", "Mano de obra")
  - Valor
  - El total se calcula automáticamente
- **Resumen Financiero**:
  - Total de cobros
  - Total de egresos (compras)
  - Ganancia estimada
- **Actualizar Finanzas**:
  - Total del servicio (editable)
  - Saldo pendiente
  - Método de pago final

### Estados del Ticket

- **ABIERTO**: Ticket recién creado
- **EN_PROCESO**: Trabajo en progreso
- **FINALIZADO**: Trabajo terminado, pendiente de entrega
- **ENTREGADO**: Vehículo entregado al cliente

### Finalizar un Ticket

1. Completa todos los datos necesarios
2. Ve a la pestaña "Finanzas"
3. Verifica el total del servicio
4. Ingresa método de pago final
5. Click en "Finalizar Ticket"
6. El sistema:
   - Cambia estado a FINALIZADO
   - Crea movimiento de caja (ingreso final)
   - Genera el PDF automáticamente

### Entregar un Ticket

1. Ticket debe estar en estado FINALIZADO
2. Ve a la pestaña "Entrega"
3. Completa:
   - Observaciones finales
   - Recomendaciones para el cliente
   - Próximo mantenimiento / Cita
   - Confirmado por (nombre del cliente)
4. **Firma del Cliente** (opcional):
   - Opción A: Subir imagen de firma
   - Opción B: Pegar URL
5. Click en "Marcar como Entregado"

---

## 💰 Módulo de Economía

### Configuración Inicial (Primera Vez)

1. Ve a **Economía**
2. Verás pantalla de "Crear Contraseña"
3. Ingresa:
   - Contraseña (mínimo 4 caracteres)
   - Palabra clave de recuperación (mínimo 3 caracteres)
4. Click en "Crear Contraseña"
5. Guarda tu palabra clave en un lugar seguro

### Acceso Normal

1. Ve a **Economía**
2. Ingresa tu contraseña
3. Click en "Ingresar"

### Recuperar Contraseña

1. En la pantalla de login, click en "¿Olvidaste tu contraseña?"
2. Ingresa tu palabra clave de recuperación
3. Ingresa una nueva contraseña
4. Click en "Restablecer Contraseña"

### Consultar Economía del Día

1. Selecciona la fecha que deseas consultar
2. Verás:
   - **Resumen del Día**:
     - Total ingresos (anticipos + cobros finales)
     - Total egresos
     - Balance del día
   - **Detalle de Ingresos**:
     - Anticipos recibidos
     - Cobros finales
   - **Detalle de Egresos**:
     - Agrupados por categoría
     - Detalle completo de cada egreso

### Descargar PDF de Economía

1. Selecciona la fecha
2. Click en "📥 Descargar PDF"
3. El PDF incluye:
   - Resumen ejecutivo
   - Estadísticas del día
   - Detalle de anticipos
   - Detalle de cobros finales
   - Egresos por categoría

---

## 📁 Sistema de Archivos

### Tipos de Archivos Soportados

- **Imágenes**: JPG, JPEG, PNG, GIF, WEBP
- **Documentos**: PDF
- **Tamaño máximo**: 10MB por archivo

### Estructura de Almacenamiento

```
uploads/
├── fotos/          # Fotos de evidencia de tickets
├── compras/        # Soportes de compras (facturas, recibos)
└── firmas/         # Firmas de entrega de clientes
```

### Subir Archivos

**Método 1: Desde el Equipo**
1. Click en "Elegir archivo"
2. Selecciona el archivo
3. Verás un preview (si es imagen)
4. Completa los campos adicionales
5. Click en el botón de guardar

**Método 2: URL Externa**
1. Pega la URL en el campo correspondiente
2. Completa los campos adicionales
3. Click en el botón de guardar

### Visualizar Archivos

- Las imágenes se muestran automáticamente en las tarjetas
- Click en una imagen para verla en tamaño completo
- Los PDFs se pueden descargar

---

## 📄 Generación de PDFs

### PDF del Cliente (Comprobante de Servicio)

**Cuándo se genera**: Al finalizar un ticket

**Cómo descargarlo**:
1. Ve a **Tickets**
2. Selecciona un ticket FINALIZADO
3. Ve a la pestaña "Entrega"
4. Click en "📄 Descargar PDF Completo"

**Contenido del PDF**:
1. **Encabezado**: Comprobante de Servicio - Taller Mecánico
2. **Información del Vehículo y Ticket**:
   - Código del ticket, Placa, Estado
   - Fecha de ingreso, Kilometraje
   - Propietario, Teléfono
   - Motivo de visita
   - Observaciones de recepción
3. **Procesos Realizados**:
   - Tabla con proceso, mecánico y observaciones
4. **Repuestos Utilizados**:
   - Combina repuestos normales + repuestos de compras
   - Muestra cantidad, marca y valor
5. **Compras Realizadas**:
   - Imágenes de soportes (3 por fila)
   - Descripción y valor
6. **Evidencia Fotográfica**:
   - Fotos ANTES / DESPUES / OTRA
   - 2 fotos por fila
   - Con descripciones
7. **Detalle de Cobros**:
   - Tabla con concepto y valor
   - Total destacado
8. **Resumen Financiero**:
   - Total del servicio
   - Anticipo recibido
   - Saldo pendiente
   - Método de pago
9. **Observaciones Finales**:
   - Notas del mecánico o taller
10. **Recomendaciones y Próxima Cita**:
    - Recomendaciones para el cliente
    - Próximo mantenimiento programado

**Características**:
- Diseño profesional en gris
- Tablas organizadas con colores alternados
- Imágenes proporcionales y bien distribuidas
- Listo para imprimir o enviar por email

### PDF de Economía

**Cuándo se genera**: Bajo demanda

**Cómo descargarlo**:
1. Ve a **Economía**
2. Ingresa contraseña
3. Selecciona la fecha
4. Click en "📥 Descargar PDF"

**Contenido del PDF**:
1. **Encabezado**: Reporte de Economía Diaria
2. **Resumen Ejecutivo**:
   - Ingresos por anticipos
   - Ingresos por cobros finales
   - Total ingresos
   - Total egresos
   - Balance del día (destacado)
3. **Estadísticas del Día**:
   - Tickets cerrados
   - Tickets abiertos con anticipo
   - Total anticipos recibidos
   - Total cobros finales
   - Total egresos registrados
4. **Detalle de Anticipos Recibidos**:
   - Tabla con ticket, placa, método de pago, responsable, valor
5. **Detalle de Cobros Finales**:
   - Tabla con ticket, placa, método de pago, responsable, valor
6. **Detalle de Egresos**:
   - Resumen por categoría
   - Detalle completo de cada egreso

**Características**:
- Colores diferenciados: verde para ingresos, rojo para egresos
- Diseño profesional y limpio
- Fácil de leer e imprimir

---

## 🔧 Solución de Problemas

### Backend no inicia

**Error: "Module not found"**
```bash
pip install -r requirements.txt
```

**Error: "Database connection failed"**
- Verifica que PostgreSQL esté corriendo
- Verifica las credenciales en `app/configuracion/base_datos.py`

### Frontend no inicia

**Error: "Cannot find module"**
```bash
cd frontend
rm -rf node_modules
npm install
```

**Error: "Port already in use"**
- Cambia el puerto en `frontend/vite.config.js`
- O detén el proceso que está usando el puerto 5173

### Las imágenes no se cargan

**Problema**: Las fotos no aparecen en el PDF o en la interfaz

**Solución**:
1. Verifica que la carpeta `uploads/` exista
2. Verifica permisos de escritura en la carpeta
3. Verifica que las URLs en la base de datos sean correctas
4. Revisa los logs del backend para errores

### No puedo acceder a Economía

**Problema**: Olvidé mi contraseña y palabra clave

**Solución**:
```sql
-- Conecta a la base de datos y ejecuta:
DELETE FROM configuracion_seguridad 
WHERE clave IN ('economia_password', 'economia_palabra_clave');
```
Luego recarga la página y crea una nueva contraseña.

### El PDF se descarga vacío

**Problema**: El PDF no tiene contenido

**Solución**:
1. Verifica que el ticket tenga datos (procesos, repuestos, etc.)
2. Revisa los logs del backend
3. Verifica que reportlab esté instalado: `pip install reportlab pillow`

### Error al subir archivos

**Problema**: "File too large" o "Invalid file type"

**Solución**:
- Tamaño máximo: 10MB
- Formatos permitidos: JPG, JPEG, PNG, GIF, WEBP, PDF
- Comprime la imagen si es muy grande

### Migraciones de base de datos

**Problema**: Error al ejecutar migraciones

**Solución**:
1. Ejecuta las migraciones en orden cronológico
2. Verifica que no haya errores en cada migración
3. Si una migración falla, revisa el error y corrígelo antes de continuar

---

## 📞 Soporte

Para soporte técnico o consultas:
- Revisa la documentación en `docs/`
- Consulta los logs del sistema
- Contacta al administrador del sistema

---

## 🔄 Flujo de Trabajo Recomendado

### Flujo Completo de un Servicio

1. **Cliente llama para agendar**
   - Crear cita con datos completos del vehículo
   - Estado: PENDIENTE

2. **Cliente confirma**
   - Confirmar cita
   - Estado: CONFIRMADA

3. **Cliente llega al taller**
   - Generar ticket desde la cita
   - Estado cita: CONVERTIDA
   - Estado ticket: ABIERTO

4. **Recepción del vehículo**
   - Completar datos de ingreso
   - Registrar anticipo si aplica
   - Cambiar estado a EN_PROCESO

5. **Durante el servicio**
   - Agregar procesos realizados
   - Agregar repuestos utilizados
   - Tomar fotos ANTES
   - Registrar compras (egresos)

6. **Al terminar el trabajo**
   - Tomar fotos DESPUES
   - Definir items de cobro
   - Actualizar finanzas
   - Finalizar ticket
   - Estado: FINALIZADO

7. **Entrega al cliente**
   - Completar observaciones finales
   - Agregar recomendaciones
   - Programar próxima cita
   - Obtener firma del cliente
   - Marcar como entregado
   - Descargar PDF para el cliente
   - Estado: ENTREGADO

8. **Cierre del día**
   - Revisar economía del día
   - Descargar PDF de economía
   - Verificar balance

---

## ✅ Checklist de Mantenimiento

### Diario
- [ ] Revisar tickets abiertos
- [ ] Confirmar citas del día
- [ ] Revisar balance de economía

### Semanal
- [ ] Backup de la base de datos
- [ ] Backup de la carpeta `uploads/`
- [ ] Revisar tickets pendientes de entrega

### Mensual
- [ ] Limpiar archivos antiguos no utilizados
- [ ] Revisar y actualizar datos de vehículos
- [ ] Generar reportes mensuales

---

**Versión del Manual**: 1.0  
**Última actualización**: Marzo 2026  
**Sistema**: Gestión de Taller Mecánico v1.0
