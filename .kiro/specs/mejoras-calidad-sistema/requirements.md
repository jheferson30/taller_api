# Requirements Document

## Introduction

Este documento define los requisitos para implementar 9 mejoras no críticas de calidad, mantenibilidad y preparación para producción identificadas en la auditoría del sistema (AUDITORIA_SISTEMA_COMPLETA.md). Estas mejoras son de prioridad MEDIA/BAJA y deben implementarse DESPUÉS de las correcciones críticas de seguridad del spec "correcciones-auditoria-sistema".

Las mejoras abarcan: gestión de secretos, contenedorización, migraciones de base de datos, validación de entrada, compresión HTTP, procesamiento asíncrono, calidad de código, y documentación de API.

## Glossary

- **Sistema**: La aplicación completa de gestión de taller mecánico (backend FastAPI + frontend React + app móvil)
- **Backend**: API REST construida con FastAPI y Python
- **Secrets_Manager**: Servicio de gestión de secretos (Azure Key Vault o AWS Secrets Manager)
- **Docker**: Plataforma de contenedorización para empaquetar aplicaciones
- **Alembic**: Herramienta de migraciones de base de datos para SQLAlchemy
- **Sanitizer**: Componente que limpia y valida entrada de usuario para prevenir XSS
- **GZipMiddleware**: Middleware de FastAPI para compresión HTTP
- **Celery**: Sistema de cola de tareas distribuidas para procesamiento asíncrono
- **Type_Hints**: Anotaciones de tipo en Python (PEP 484)
- **Ruff**: Linter y formateador de código Python de alta velocidad
- **OpenAPI**: Especificación para documentación de APIs REST (Swagger)
- **PDF_Generator**: Componente que genera reportes PDF de tickets
- **Redis**: Base de datos en memoria usada como broker para Celery
- **Environment_Variable**: Variable de configuración almacenada en archivo .env
- **Plain_Text**: Texto sin cifrar, legible directamente
- **MIME_Type**: Identificador de tipo de archivo (e.g., image/jpeg, application/pdf)
- **HTML_Injection**: Ataque donde se inyecta código HTML malicioso en campos de texto
- **File_Upload**: Funcionalidad que permite subir archivos (fotos, documentos)
- **Coverage**: Porcentaje de código cubierto por type hints o tests
- **Production_Environment**: Entorno donde la aplicación es usada por usuarios reales

## Requirements

### Requirement 1: Secrets Manager Integration

**User Story:** Como administrador de sistemas, quiero que las contraseñas y secretos se almacenen en un servicio de gestión de secretos, para que no estén expuestas en texto plano en archivos .env

#### Acceptance Criteria

1. THE Sistema SHALL integrar Azure Key Vault o AWS Secrets Manager para almacenamiento de secretos
2. WHEN el Backend inicia, THE Sistema SHALL recuperar secretos desde el Secrets_Manager en lugar de Environment_Variables
3. THE Sistema SHALL almacenar en el Secrets_Manager: ADMIN_PASSWORD, PDF_PASSWORD, JWT_SECRET_KEY, DATABASE_PASSWORD
4. WHERE Azure Key Vault es usado, THE Sistema SHALL autenticarse usando DefaultAzureCredential
5. WHERE AWS Secrets Manager es usado, THE Sistema SHALL autenticarse usando boto3 con IAM roles
6. IF el Secrets_Manager no está disponible, THEN THE Sistema SHALL registrar un error y fallar el inicio
7. THE Sistema SHALL mantener compatibilidad con Environment_Variables en entorno de desarrollo local
8. THE Sistema SHALL documentar el proceso de configuración del Secrets_Manager en README.md

### Requirement 2: Full Docker Containerization

**User Story:** Como desarrollador, quiero un entorno Docker completo con docker-compose, para que pueda levantar toda la aplicación con un solo comando

#### Acceptance Criteria

1. THE Sistema SHALL proporcionar un Dockerfile para el Backend que use Python 3.11-slim como imagen base
2. THE Sistema SHALL proporcionar un docker-compose.yml que incluya servicios: api, db (PostgreSQL), redis
3. WHEN un desarrollador ejecuta `docker-compose up`, THE Sistema SHALL iniciar todos los servicios necesarios
4. THE Docker configuration SHALL montar volúmenes para persistencia de datos de PostgreSQL
5. THE Docker configuration SHALL exponer puertos: 8000 (API), 5432 (PostgreSQL), 6379 (Redis)
6. THE Docker configuration SHALL configurar variables de entorno desde archivo .env
7. THE Sistema SHALL proporcionar un Dockerfile.prod optimizado para producción con gunicorn
8. THE Sistema SHALL documentar comandos Docker en README.md con ejemplos de uso

### Requirement 3: Alembic Database Migrations

**User Story:** Como desarrollador, quiero migraciones de base de datos versionadas con Alembic, para que pueda aplicar y revertir cambios de esquema de forma controlada

#### Acceptance Criteria

1. THE Sistema SHALL configurar Alembic para gestión de migraciones de base de datos
2. THE Sistema SHALL generar una migración inicial que refleje el esquema actual de la base de datos
3. WHEN un desarrollador ejecuta `alembic upgrade head`, THE Sistema SHALL aplicar todas las migraciones pendientes
4. WHEN un desarrollador ejecuta `alembic downgrade -1`, THE Sistema SHALL revertir la última migración
5. THE Sistema SHALL almacenar scripts de migración en directorio `migrations/versions/`
6. THE Sistema SHALL registrar en tabla `alembic_version` la versión actual del esquema
7. THE Sistema SHALL proporcionar comando `alembic revision --autogenerate` para generar migraciones automáticamente
8. THE Sistema SHALL documentar el flujo de trabajo de migraciones en README.md

### Requirement 4: Input Validation and Sanitization

**User Story:** Como usuario del sistema, quiero que mis datos de entrada sean validados y sanitizados, para que el sistema esté protegido contra inyecciones HTML y archivos maliciosos

#### Acceptance Criteria

1. THE Sanitizer SHALL eliminar todas las etiquetas HTML de campos de texto usando bleach
2. WHEN un usuario envía texto con HTML, THE Sanitizer SHALL retornar texto plano sin etiquetas
3. THE Sistema SHALL aplicar sanitización a campos: motivo_visita, observaciones, descripcion_proceso, notas
4. THE File_Upload SHALL validar que el tamaño de archivo no exceda 10 MB
5. THE File_Upload SHALL validar que el MIME_Type sea uno de: image/jpeg, image/png, image/webp, application/pdf
6. IF un archivo excede el tamaño máximo, THEN THE Sistema SHALL retornar error HTTP 413 con mensaje descriptivo
7. IF un archivo tiene MIME_Type no permitido, THEN THE Sistema SHALL retornar error HTTP 415 con mensaje descriptivo
8. THE Sistema SHALL definir constantes MAX_FILE_SIZE y ALLOWED_MIME_TYPES en archivo de configuración

### Requirement 5: HTTP Compression

**User Story:** Como usuario con conexión lenta, quiero que las respuestas HTTP estén comprimidas, para que la aplicación cargue más rápido

#### Acceptance Criteria

1. THE Backend SHALL agregar GZipMiddleware a la aplicación FastAPI
2. THE GZipMiddleware SHALL comprimir respuestas mayores a 1000 bytes
3. WHEN un cliente envía header `Accept-Encoding: gzip`, THE Backend SHALL retornar respuesta comprimida con header `Content-Encoding: gzip`
4. THE GZipMiddleware SHALL reducir el tamaño de respuestas JSON en al menos 60%
5. THE Sistema SHALL configurar nivel de compresión en 6 (balance entre velocidad y ratio)
6. THE Sistema SHALL NO comprimir respuestas que ya están comprimidas (imágenes, PDFs)
7. THE Sistema SHALL medir y registrar ratio de compresión en logs de desarrollo

### Requirement 6: Async PDF Generation

**User Story:** Como usuario generando reportes PDF, quiero que la generación sea asíncrona, para que no bloquee mi navegador mientras se procesa

#### Acceptance Criteria

1. THE Sistema SHALL configurar Celery con Redis como broker para tareas asíncronas
2. THE PDF_Generator SHALL ejecutarse como tarea Celery en lugar de síncronamente
3. WHEN un usuario solicita generar PDF, THE Backend SHALL retornar inmediatamente un task_id
4. THE Backend SHALL proporcionar endpoint `/tasks/{task_id}/status` para consultar estado de tarea
5. WHEN la generación de PDF completa, THE Backend SHALL almacenar el archivo y actualizar estado a "completed"
6. THE Backend SHALL proporcionar endpoint `/tasks/{task_id}/result` para descargar el PDF generado
7. IF la generación de PDF falla, THEN THE Backend SHALL actualizar estado a "failed" con mensaje de error
8. THE Sistema SHALL configurar timeout de 5 minutos para tareas de generación de PDF
9. THE Sistema SHALL limpiar archivos PDF generados después de 24 horas

### Requirement 7: Complete Type Hints

**User Story:** Como desarrollador, quiero que todas las funciones tengan type hints, para que el IDE pueda detectar errores de tipo y mejorar el autocompletado

#### Acceptance Criteria

1. THE Backend SHALL agregar type hints a todas las funciones en módulos: servicios, repositorios, rutas
2. THE Backend SHALL usar tipos de `typing` module: Optional, List, Dict, Tuple, Union cuando sea necesario
3. THE Backend SHALL alcanzar al menos 90% de Coverage de type hints en el código
4. THE Backend SHALL usar herramienta `mypy` para verificación estática de tipos
5. WHEN se ejecuta `mypy app/`, THE Sistema SHALL reportar 0 errores de tipo
6. THE Backend SHALL documentar tipos de retorno de todas las funciones públicas
7. THE Backend SHALL usar tipos específicos de SQLAlchemy para modelos (e.g., `Optional[User]`)
8. THE Sistema SHALL configurar mypy en modo estricto en archivo `pyproject.toml`

### Requirement 8: Linter Configuration

**User Story:** Como desarrollador, quiero un linter configurado que verifique calidad de código, para que el equipo mantenga estándares consistentes

#### Acceptance Criteria

1. THE Sistema SHALL configurar Ruff como linter y formateador de código
2. THE Sistema SHALL definir configuración de Ruff en archivo `pyproject.toml`
3. THE Ruff configuration SHALL habilitar reglas: pycodestyle (E/W), pyflakes (F), isort (I), flake8-bugbear (B)
4. THE Ruff configuration SHALL establecer longitud máxima de línea en 100 caracteres
5. WHEN se ejecuta `ruff check app/`, THE Sistema SHALL reportar violaciones de estilo
6. WHEN se ejecuta `ruff format app/`, THE Sistema SHALL formatear código automáticamente
7. THE Sistema SHALL ignorar regla E501 (line too long) para líneas con URLs o strings largos
8. THE Sistema SHALL configurar pre-commit hook para ejecutar Ruff antes de cada commit
9. THE Sistema SHALL documentar comandos de Ruff en README.md

### Requirement 9: API Documentation

**User Story:** Como desarrollador frontend, quiero documentación completa de la API con ejemplos, para que pueda integrar endpoints correctamente sin consultar el código backend

#### Acceptance Criteria

1. THE Backend SHALL mejorar documentación OpenAPI con descripciones detalladas de cada endpoint
2. THE Backend SHALL agregar ejemplos de request y response a todos los endpoints principales
3. THE Backend SHALL documentar códigos de error posibles (400, 401, 403, 404, 422, 500) con mensajes
4. THE Backend SHALL agrupar endpoints por tags: Authentication, Tickets, Vehicles, Payments, Users
5. THE Backend SHALL documentar modelos Pydantic con Field descriptions y ejemplos
6. THE Backend SHALL incluir ejemplos de autenticación JWT en documentación Swagger
7. WHEN un desarrollador accede a `/docs`, THE Backend SHALL mostrar documentación interactiva completa
8. THE Backend SHALL proporcionar archivo `openapi.json` exportable para generación de clientes
9. THE Backend SHALL documentar rate limits de cada endpoint en descripción

