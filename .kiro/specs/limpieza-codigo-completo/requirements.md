
# Requirements Document

## Introduction

Este documento define los requisitos para realizar una auditoría exhaustiva y limpieza completa del código del sistema SaaS multi-tenant de gestión de talleres mecánicos. El objetivo es identificar y eliminar código duplicado, obsoleto y no utilizado, consolidando la funcionalidad en versiones únicas y actualizadas, mejorando así la mantenibilidad, seguridad y rendimiento del sistema.

El sistema está construido con FastAPI + PostgreSQL en el backend y React + Vite en el frontend, siguiendo una arquitectura de capas (Rutas → Servicios → Repositorios → Modelos) con seguridad multi-tenant estricta.

## Glossary

- **Sistema_Auditoria**: Herramienta automatizada que analiza el código fuente para detectar problemas de calidad
- **Codigo_Duplicado**: Funciones, clases, métodos o bloques de lógica que aparecen repetidos en múltiples ubicaciones del código
- **Codigo_Obsoleto**: Archivos, funciones, clases, imports o variables que ya no se utilizan en el sistema actual
- **Codigo_Basura**: Código temporal, comentarios extensos, código comentado, prints de debug, scripts de prueba no documentados
- **Analizador_Estatico**: Herramienta que examina el código sin ejecutarlo para detectar patrones problemáticos
- **Grafo_Dependencias**: Representación de las relaciones entre módulos, funciones y clases del sistema
- **Cobertura_Codigo**: Métrica que indica qué porcentaje del código está cubierto por tests
- **Endpoint_Huerfano**: Ruta HTTP registrada que no tiene tests ni referencias en el frontend
- **Import_No_Usado**: Declaración de importación que no se utiliza en el archivo
- **Funcion_Muerta**: Función o método que no es llamado desde ninguna parte del código
- **Modelo_Huerfano**: Modelo SQLAlchemy que no tiene repositorio, servicio ni ruta asociada
- **Schema_No_Usado**: Schema Pydantic que no es referenciado en ninguna ruta
- **Script_Temporal**: Script en `/scripts/` con prefijo `_` o nombres como `test_`, `check_`, `debug_` sin documentación
- **Ruta_Duplicada**: Múltiples endpoints HTTP que implementan la misma funcionalidad con diferentes implementaciones
- **Query_Duplicada**: Consultas SQL similares o idénticas en diferentes repositorios
- **Validacion_Duplicada**: Lógica de validación repetida en múltiples servicios o rutas
- **Componente_React_No_Usado**: Componente React que no es importado ni utilizado en ninguna página o componente padre
- **Test_Obsoleto**: Test que valida funcionalidad que ya no existe o que está duplicado
- **Dependencia_No_Usada**: Librería en `requirements.txt` o `package.json` que no se importa en ningún archivo
- **Archivo_Generado**: Archivos en `__pycache__`, `.pytest_cache`, `node_modules`, `dist`, `coverage` que no deben auditarse
- **Migracion_Huerfana**: Archivo de migración de Alembic que no está referenciado en la cadena de migraciones
- **Configuracion_Duplicada**: Variables de entorno o configuraciones definidas en múltiples lugares
- **Metrica_Complejidad**: Medida de complejidad ciclomática que indica cuán difícil es mantener una función
- **Umbral_Duplicacion**: Porcentaje mínimo de similitud (85%) para considerar dos bloques de código como duplicados
- **Reporte_Auditoria**: Documento generado que lista todos los problemas encontrados con ubicaciones y recomendaciones
- **Plan_Limpieza**: Documento que prioriza las acciones de limpieza según impacto y riesgo
- **Backup_Seguridad**: Copia completa del código antes de iniciar la limpieza para permitir rollback
- **Test_Regresion**: Suite de tests que se ejecuta después de cada cambio para verificar que no se rompió funcionalidad existente

## Requirements

### Requirement 1: Detección de Código Duplicado

**User Story:** Como desarrollador, quiero identificar todo el código duplicado en el proyecto, para consolidarlo en implementaciones únicas y reducir la deuda técnica.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL analizar todos los archivos Python en `/app/rutas/`, `/app/servicios/`, `/app/repositorios/`, `/app/modelos/`, `/app/esquemas/`, `/app/seguridad/`, `/app/utils/`, `/app/tasks/` y `/app/configuracion/`
2. THE Sistema_Auditoria SHALL analizar todos los archivos JavaScript/JSX en `/frontend/src/`
3. WHEN dos bloques de código tienen similitud mayor o igual al Umbral_Duplicacion, THE Sistema_Auditoria SHALL marcarlos como Codigo_Duplicado
4. THE Sistema_Auditoria SHALL detectar Ruta_Duplicada comparando decoradores de ruta, métodos HTTP y lógica de negocio
5. THE Sistema_Auditoria SHALL detectar Query_Duplicada comparando consultas SQLAlchemy en todos los repositorios
6. THE Sistema_Auditoria SHALL detectar Validacion_Duplicada comparando lógica de validación en servicios y rutas
7. THE Sistema_Auditoria SHALL detectar funciones helper duplicadas en `/app/utils/`
8. THE Sistema_Auditoria SHALL generar un reporte con ubicación exacta (archivo, línea) de cada duplicación encontrada
9. THE Sistema_Auditoria SHALL calcular el porcentaje de código duplicado del proyecto total
10. FOR ALL Codigo_Duplicado detectado, THE Sistema_Auditoria SHALL sugerir cuál versión mantener basándose en: fecha de última modificación, cobertura de tests, y número de referencias

### Requirement 2: Detección de Código Obsoleto en Backend

**User Story:** Como desarrollador, quiero identificar código obsoleto en el backend, para eliminar funcionalidad que ya no se utiliza y simplificar el sistema.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL construir un Grafo_Dependencias completo del código Python
2. THE Sistema_Auditoria SHALL identificar toda Funcion_Muerta que no tiene referencias en el Grafo_Dependencias
3. THE Sistema_Auditoria SHALL identificar todo Import_No_Usado en cada archivo Python
4. THE Sistema_Auditoria SHALL identificar todo Modelo_Huerfano que no tiene repositorio asociado
5. THE Sistema_Auditoria SHALL identificar todo Schema_No_Usado que no es referenciado en ninguna ruta
6. THE Sistema_Auditoria SHALL identificar todo Endpoint_Huerfano que no tiene tests ni referencias en el frontend
7. THE Sistema_Auditoria SHALL identificar variables de clase o módulo que no se utilizan
8. THE Sistema_Auditoria SHALL identificar decoradores o middlewares que no se aplican en ninguna ruta
9. THE Sistema_Auditoria SHALL identificar métodos de repositorio que no son llamados desde ningún servicio
10. THE Sistema_Auditoria SHALL identificar servicios que no son llamados desde ninguna ruta
11. THE Sistema_Auditoria SHALL excluir de análisis todos los Archivo_Generado
12. FOR ALL Codigo_Obsoleto detectado, THE Sistema_Auditoria SHALL verificar si tiene tests asociados antes de marcarlo para eliminación

### Requirement 3: Detección de Código Obsoleto en Frontend

**User Story:** Como desarrollador, quiero identificar código obsoleto en el frontend, para eliminar componentes y utilidades que ya no se utilizan.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL construir un Grafo_Dependencias completo del código JavaScript/JSX
2. THE Sistema_Auditoria SHALL identificar todo Componente_React_No_Usado que no es importado en ningún archivo
3. THE Sistema_Auditoria SHALL identificar todo Import_No_Usado en cada archivo JavaScript/JSX
4. THE Sistema_Auditoria SHALL identificar funciones helper en `/frontend/src/services/` que no se utilizan
5. THE Sistema_Auditoria SHALL identificar archivos CSS con estilos que no se aplican a ningún componente existente
6. THE Sistema_Auditoria SHALL identificar assets en `/frontend/public/` que no son referenciados
7. THE Sistema_Auditoria SHALL identificar páginas en `/frontend/src/pages/` que no están en el router
8. THE Sistema_Auditoria SHALL excluir de análisis `node_modules`, `dist`, `coverage`

### Requirement 4: Detección de Scripts Obsoletos

**User Story:** Como desarrollador, quiero identificar scripts obsoletos o temporales, para mantener solo los scripts de utilidad documentados y necesarios.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL listar todos los archivos en `/scripts/`
2. THE Sistema_Auditoria SHALL marcar como Script_Temporal todo archivo con prefijo `_` o nombres que contengan `test_`, `check_`, `debug_`, `temp_`, `old_`
3. THE Sistema_Auditoria SHALL verificar si cada script tiene documentación en `scripts/README.md` o `scripts/CRON_JOBS.md`
4. THE Sistema_Auditoria SHALL identificar scripts que no se ejecutan en ningún cron job, CI/CD, o `docker-compose.yml`
5. THE Sistema_Auditoria SHALL identificar scripts duplicados que realizan la misma función
6. THE Sistema_Auditoria SHALL identificar scripts que usan credenciales hardcodeadas o configuración obsoleta
7. FOR ALL Script_Temporal sin documentación, THE Sistema_Auditoria SHALL marcarlo para revisión manual o eliminación

### Requirement 5: Detección de Tests Obsoletos

**User Story:** Como desarrollador, quiero identificar tests obsoletos o duplicados, para mantener una suite de tests limpia y eficiente.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL listar todos los archivos de test en `/tests/`
2. THE Sistema_Auditoria SHALL identificar Test_Obsoleto que valida funcionalidad que ya no existe en el código
3. THE Sistema_Auditoria SHALL identificar tests duplicados que validan exactamente la misma funcionalidad
4. THE Sistema_Auditoria SHALL identificar tests que importan módulos que ya no existen
5. THE Sistema_Auditoria SHALL identificar fixtures en `conftest.py` que no se utilizan en ningún test
6. THE Sistema_Auditoria SHALL calcular la Cobertura_Codigo actual del proyecto
7. THE Sistema_Auditoria SHALL identificar código de producción sin ningún test asociado

### Requirement 6: Detección de Dependencias No Utilizadas

**User Story:** Como desarrollador, quiero identificar dependencias no utilizadas, para reducir el tamaño de las imágenes Docker y mejorar la seguridad.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL listar todas las dependencias en `requirements.txt`
2. THE Sistema_Auditoria SHALL listar todas las dependencias en `frontend/package.json`
3. THE Sistema_Auditoria SHALL verificar si cada dependencia Python es importada en al menos un archivo del proyecto
4. THE Sistema_Auditoria SHALL verificar si cada dependencia JavaScript es importada en al menos un archivo del frontend
5. THE Sistema_Auditoria SHALL identificar dependencias de desarrollo que están en dependencias de producción
6. THE Sistema_Auditoria SHALL identificar versiones duplicadas de la misma librería
7. THE Sistema_Auditoria SHALL verificar si hay dependencias con vulnerabilidades conocidas usando herramientas de seguridad

### Requirement 7: Detección de Configuración Duplicada

**User Story:** Como desarrollador, quiero identificar configuración duplicada, para consolidarla en un único lugar y evitar inconsistencias.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL analizar `.env`, `.env.example`, `.env.production.example`, `.env.test.example`
2. THE Sistema_Auditoria SHALL analizar `frontend/.env`, `frontend/.env.example`, `frontend/.env.production.local`
3. THE Sistema_Auditoria SHALL identificar Configuracion_Duplicada definida en múltiples archivos de entorno
4. THE Sistema_Auditoria SHALL identificar variables de entorno definidas pero no utilizadas en el código
5. THE Sistema_Auditoria SHALL identificar variables de entorno utilizadas en el código pero no documentadas en `.env.example`
6. THE Sistema_Auditoria SHALL identificar configuraciones hardcodeadas en el código que deberían estar en variables de entorno
7. THE Sistema_Auditoria SHALL verificar consistencia entre configuración de desarrollo, test y producción

### Requirement 8: Análisis de Complejidad de Código

**User Story:** Como desarrollador, quiero identificar código excesivamente complejo, para refactorizarlo y mejorar la mantenibilidad.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL calcular la Metrica_Complejidad ciclomática de todas las funciones Python
2. WHEN una función tiene Metrica_Complejidad mayor a 10, THE Sistema_Auditoria SHALL marcarla como candidata a refactorización
3. THE Sistema_Auditoria SHALL identificar funciones con más de 50 líneas de código
4. THE Sistema_Auditoria SHALL identificar funciones con más de 5 parámetros
5. THE Sistema_Auditoria SHALL identificar clases con más de 10 métodos públicos
6. THE Sistema_Auditoria SHALL identificar archivos con más de 500 líneas de código
7. THE Sistema_Auditoria SHALL identificar niveles de indentación mayores a 4 en cualquier función

### Requirement 9: Generación de Reporte de Auditoría

**User Story:** Como desarrollador, quiero un reporte completo de auditoría, para entender el estado actual del código y priorizar acciones de limpieza.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL generar un Reporte_Auditoria en formato Markdown
2. THE Reporte_Auditoria SHALL incluir un resumen ejecutivo con métricas clave: total de archivos analizados, porcentaje de código duplicado, número de funciones muertas, número de imports no usados, número de dependencias no usadas
3. THE Reporte_Auditoria SHALL incluir una sección detallada por cada tipo de problema encontrado
4. FOR ALL problema detectado, THE Reporte_Auditoria SHALL incluir: ubicación exacta (archivo y línea), descripción del problema, nivel de severidad (crítico, alto, medio, bajo), y recomendación de acción
5. THE Reporte_Auditoria SHALL incluir un índice de calidad de código general (0-100)
6. THE Reporte_Auditoria SHALL incluir gráficos de distribución de problemas por categoría
7. THE Reporte_Auditoria SHALL incluir comparación con métricas de proyectos similares (benchmarks de industria)
8. THE Reporte_Auditoria SHALL guardarse en `.kiro/specs/limpieza-codigo-completo/auditoria-report.md`

### Requirement 10: Generación de Plan de Limpieza

**User Story:** Como desarrollador, quiero un plan de limpieza priorizado, para ejecutar las acciones de forma segura y ordenada.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL generar un Plan_Limpieza en formato Markdown
2. THE Plan_Limpieza SHALL priorizar acciones según: impacto en mantenibilidad, riesgo de romper funcionalidad, y esfuerzo requerido
3. THE Plan_Limpieza SHALL agrupar acciones en fases: Fase 1 (bajo riesgo), Fase 2 (riesgo medio), Fase 3 (alto riesgo)
4. FOR ALL acción de limpieza, THE Plan_Limpieza SHALL incluir: descripción, archivos afectados, pasos específicos, tests de regresión requeridos, y criterios de éxito
5. THE Plan_Limpieza SHALL incluir una sección de "Acciones Automatizables" que pueden ejecutarse con scripts
6. THE Plan_Limpieza SHALL incluir una sección de "Acciones Manuales" que requieren revisión humana
7. THE Plan_Limpieza SHALL incluir estimación de tiempo para cada fase
8. THE Plan_Limpieza SHALL incluir procedimiento de rollback para cada fase
9. THE Plan_Limpieza SHALL guardarse en `.kiro/specs/limpieza-codigo-completo/plan-limpieza.md`

### Requirement 11: Validación de Seguridad Multi-Tenant

**User Story:** Como desarrollador, quiero validar que ningún código obsoleto o duplicado comprometa el aislamiento multi-tenant, para mantener la seguridad del sistema.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL verificar que todo Codigo_Duplicado relacionado con autenticación o autorización use la versión más segura
2. THE Sistema_Auditoria SHALL verificar que no existan rutas sin `@require_auth` o `@require_role` que deberían tenerlos
3. THE Sistema_Auditoria SHALL verificar que no existan queries sin filtro por `taller_id` en repositorios de datos operativos
4. THE Sistema_Auditoria SHALL verificar que no existan endpoints que acepten `taller_id` del cliente en lugar del JWT
5. THE Sistema_Auditoria SHALL verificar que no existan funciones de validación duplicadas con diferentes niveles de seguridad
6. IF se detecta código duplicado en módulos de seguridad, THEN THE Sistema_Auditoria SHALL marcarlo como severidad crítica
7. THE Sistema_Auditoria SHALL verificar que todo código de SUPER_ADMIN esté correctamente aislado de código de taller

### Requirement 12: Ejecución Segura de Limpieza

**User Story:** Como desarrollador, quiero ejecutar la limpieza de forma segura, para poder revertir cambios si algo sale mal.

#### Acceptance Criteria

1. BEFORE iniciar cualquier limpieza, THE Sistema_Auditoria SHALL crear un Backup_Seguridad completo del código
2. THE Sistema_Auditoria SHALL crear una rama Git específica para la limpieza con nombre `limpieza-codigo-{fecha}`
3. THE Sistema_Auditoria SHALL ejecutar la suite completa de tests antes de iniciar la limpieza
4. AFTER cada acción de limpieza, THE Sistema_Auditoria SHALL ejecutar Test_Regresion para verificar que no se rompió funcionalidad
5. IF algún Test_Regresion falla, THEN THE Sistema_Auditoria SHALL revertir el último cambio automáticamente
6. THE Sistema_Auditoria SHALL generar un commit separado por cada tipo de limpieza realizada
7. THE Sistema_Auditoria SHALL mantener un log detallado de todas las acciones ejecutadas en `.kiro/specs/limpieza-codigo-completo/limpieza-log.md`
8. THE Sistema_Auditoria SHALL verificar que el proyecto siga compilando después de cada cambio
9. THE Sistema_Auditoria SHALL verificar que `docker-compose up` funcione correctamente después de cada fase

### Requirement 13: Métricas de Mejora

**User Story:** Como desarrollador, quiero métricas de mejora después de la limpieza, para cuantificar el impacto de las acciones realizadas.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL generar un reporte de métricas antes y después de la limpieza
2. THE Sistema_Auditoria SHALL medir reducción en: líneas de código total, número de archivos, porcentaje de código duplicado, número de dependencias, tamaño de imágenes Docker
3. THE Sistema_Auditoria SHALL medir mejora en: cobertura de tests, índice de calidad de código, complejidad ciclomática promedio
4. THE Sistema_Auditoria SHALL medir tiempo de ejecución de tests antes y después
5. THE Sistema_Auditoria SHALL medir tiempo de build de Docker antes y después
6. THE Sistema_Auditoria SHALL generar un reporte comparativo en `.kiro/specs/limpieza-codigo-completo/metricas-mejora.md`

### Requirement 14: Documentación de Cambios

**User Story:** Como desarrollador, quiero documentación completa de todos los cambios realizados, para entender qué se eliminó y por qué.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL generar un documento `CHANGELOG-LIMPIEZA.md` en la raíz del proyecto
2. THE CHANGELOG-LIMPIEZA SHALL listar todos los archivos eliminados con justificación
3. THE CHANGELOG-LIMPIEZA SHALL listar todas las funciones eliminadas con justificación
4. THE CHANGELOG-LIMPIEZA SHALL listar todas las dependencias eliminadas con justificación
5. THE CHANGELOG-LIMPIEZA SHALL listar todo código consolidado indicando qué versiones se eliminaron y cuál se mantuvo
6. THE CHANGELOG-LIMPIEZA SHALL incluir enlaces a los commits específicos de cada cambio
7. THE CHANGELOG-LIMPIEZA SHALL incluir una sección de "Posibles Impactos" para cambios de alto riesgo

### Requirement 15: Herramientas de Análisis Estático

**User Story:** Como desarrollador, quiero utilizar herramientas de análisis estático estándar de la industria, para asegurar la calidad del análisis.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL utilizar `pylint` para análisis de código Python
2. THE Sistema_Auditoria SHALL utilizar `flake8` para detección de problemas de estilo Python
3. THE Sistema_Auditoria SHALL utilizar `bandit` para análisis de seguridad Python
4. THE Sistema_Auditoria SHALL utilizar `radon` para cálculo de complejidad ciclomática Python
5. THE Sistema_Auditoria SHALL utilizar `vulture` para detección de código muerto Python
6. THE Sistema_Auditoria SHALL utilizar `eslint` para análisis de código JavaScript/JSX
7. THE Sistema_Auditoria SHALL utilizar `depcheck` para detección de dependencias no usadas en Node.js
8. THE Sistema_Auditoria SHALL consolidar resultados de todas las herramientas en un único Reporte_Auditoria
9. THE Sistema_Auditoria SHALL configurar todas las herramientas para respetar las convenciones del proyecto (nombres en español, arquitectura multi-tenant)

### Requirement 16: Exclusiones y Casos Especiales

**User Story:** Como desarrollador, quiero que el sistema de auditoría respete exclusiones necesarias, para no marcar como obsoleto código que es necesario por razones específicas.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL excluir de análisis: `__pycache__`, `.pytest_cache`, `node_modules`, `dist`, `coverage`, `.venv`, `.git`, `.hypothesis`
2. THE Sistema_Auditoria SHALL excluir archivos de migración de Alembic del análisis de código muerto
3. THE Sistema_Auditoria SHALL excluir modelos SQLAlchemy del análisis de complejidad
4. THE Sistema_Auditoria SHALL excluir fixtures de pytest del análisis de funciones no usadas
5. THE Sistema_Auditoria SHALL excluir archivos `__init__.py` del análisis de imports no usados
6. THE Sistema_Auditoria SHALL excluir scripts documentados en `scripts/README.md` o `scripts/CRON_JOBS.md` del análisis de scripts obsoletos
7. THE Sistema_Auditoria SHALL permitir configurar exclusiones adicionales mediante archivo `.auditoria-ignore`
8. THE Sistema_Auditoria SHALL respetar comentarios especiales en el código como `# noqa`, `# type: ignore`, `# pylint: disable`

### Requirement 17: Integración con CI/CD

**User Story:** Como desarrollador, quiero que la auditoría de código se ejecute automáticamente en CI/CD, para prevenir la introducción de nuevo código duplicado u obsoleto.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL proporcionar un script ejecutable `scripts/run_auditoria.sh`
2. THE Sistema_Auditoria SHALL retornar código de salida 0 si no hay problemas críticos
3. THE Sistema_Auditoria SHALL retornar código de salida 1 si hay problemas críticos que bloquean el merge
4. THE Sistema_Auditoria SHALL generar un reporte en formato JSON para integración con herramientas de CI/CD
5. THE Sistema_Auditoria SHALL permitir configurar umbrales de calidad mínimos (ej: máximo 5% de código duplicado)
6. THE Sistema_Auditoria SHALL generar badges de calidad de código para incluir en el README
7. THE Sistema_Auditoria SHALL enviar notificaciones cuando se detecten regresiones en métricas de calidad

### Requirement 18: Análisis de Migraciones de Base de Datos

**User Story:** Como desarrollador, quiero identificar migraciones obsoletas o problemáticas, para mantener un historial de migraciones limpio.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL listar todas las migraciones en `/alembic/versions/`
2. THE Sistema_Auditoria SHALL verificar que cada migración tenga `upgrade()` y `downgrade()` implementados
3. THE Sistema_Auditoria SHALL identificar Migracion_Huerfana que no está en la cadena de migraciones
4. THE Sistema_Auditoria SHALL identificar migraciones que crean tablas que ya no existen en los modelos
5. THE Sistema_Auditoria SHALL identificar migraciones que modifican columnas que ya no existen
6. THE Sistema_Auditoria SHALL verificar que no haya migraciones con operaciones destructivas sin comentarios de advertencia
7. THE Sistema_Auditoria SHALL verificar que todas las migraciones tengan nombres descriptivos

### Requirement 19: Análisis de Archivos de Configuración

**User Story:** Como desarrollador, quiero identificar configuraciones obsoletas o inconsistentes, para mantener la configuración del sistema limpia y coherente.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL analizar `docker-compose.yml`, `Dockerfile`, `alembic.ini`, `.dockerignore`, `.gitignore`
2. THE Sistema_Auditoria SHALL identificar servicios definidos en `docker-compose.yml` que no se utilizan
3. THE Sistema_Auditoria SHALL identificar volúmenes definidos que no se montan en ningún servicio
4. THE Sistema_Auditoria SHALL identificar variables de entorno en `docker-compose.yml` que no existen en `.env.example`
5. THE Sistema_Auditoria SHALL identificar puertos expuestos que no se utilizan
6. THE Sistema_Auditoria SHALL verificar consistencia entre `requirements.txt` y `Dockerfile`
7. THE Sistema_Auditoria SHALL verificar que `.gitignore` incluya todos los Archivo_Generado

### Requirement 20: Recomendaciones de Refactorización

**User Story:** Como desarrollador, quiero recomendaciones específicas de refactorización, para mejorar la arquitectura del código más allá de solo eliminar código obsoleto.

#### Acceptance Criteria

1. THE Sistema_Auditoria SHALL identificar oportunidades para extraer funciones comunes de código duplicado
2. THE Sistema_Auditoria SHALL identificar oportunidades para crear clases base de código similar
3. THE Sistema_Auditoria SHALL identificar oportunidades para usar decoradores en lugar de código repetitivo
4. THE Sistema_Auditoria SHALL identificar oportunidades para consolidar validaciones en schemas Pydantic
5. THE Sistema_Auditoria SHALL identificar oportunidades para mover lógica de rutas a servicios
6. THE Sistema_Auditoria SHALL identificar oportunidades para mover queries de servicios a repositorios
7. THE Sistema_Auditoria SHALL sugerir patrones de diseño aplicables (Factory, Strategy, Repository, etc.)
8. FOR ALL recomendación de refactorización, THE Sistema_Auditoria SHALL incluir: problema actual, solución propuesta, beneficios esperados, y esfuerzo estimado
