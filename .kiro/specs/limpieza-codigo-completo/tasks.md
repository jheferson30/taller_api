# Implementation Tasks — Limpieza de Código Completo

## Tasks

- [x] 1. Fase 0 — Preparación y baseline
  - [x] 1.1 Ejecutar suite de tests completa y registrar cuántos pasan como baseline
  - [x] 1.2 Registrar métricas baseline: total líneas de código Python, total archivos, total archivos JS/JSX
  - [x] 1.3 Instalar herramientas de análisis estático: vulture, radon, bandit en el entorno virtual
  - _Requirements: 12, 13_

- [x] 2. Fase 1 — Auditoría automatizada del backend
  - [x] 2.1 Ejecutar vulture sobre app/ con min-confidence 80 y guardar reporte en .kiro/specs/limpieza-codigo-completo/vulture-report.txt
  - [x] 2.2 Ejecutar radon cc sobre app/ y guardar reporte de complejidad ciclomática en .kiro/specs/limpieza-codigo-completo/radon-report.txt
  - [x] 2.3 Ejecutar bandit -r app/ y guardar reporte de seguridad en .kiro/specs/limpieza-codigo-completo/bandit-report.txt
  - [x] 2.4 Buscar imports no usados en todos los archivos Python de app/ usando grep y registrar hallazgos
  - [x] 2.5 Verificar seguridad multi-tenant: buscar endpoints sin @require_auth que no sean públicos (login, health, docs)
  - [x] 2.6 Verificar seguridad multi-tenant: buscar queries en repositorios sin filtro taller_id en tablas operativas
  - [x] 2.7 Verificar seguridad multi-tenant: buscar uso de datos.taller_id o taller_id del cliente en lugar del JWT
  - [x] 2.8 Verificar seguridad multi-tenant: buscar @require_role que mezcle SUPER_ADMIN con roles de taller
  - _Requirements: 1, 2, 11, 15_

- [x] 3. Fase 1 — Auditoría manual de duplicaciones conocidas
  - [x] 3.1 Leer y comparar app/rutas/mobile_ruta.py vs app/rutas/mobile_api_ruta.py — determinar cuál está registrado en main.py y cuál es redundante
  - [x] 3.2 Leer y comparar app/servicios/whatsapp_service.py vs app/servicios/twilio_whatsapp_service.py — determinar cuál provider está activo
  - [x] 3.3 Leer y comparar app/utils/pdf_generator.py vs app/utils/pdf_economia.py — determinar si tienen responsabilidades distintas o hay duplicación
  - [x] 3.4 Verificar si app/repositorios/tenant_repository.py es importado en algún servicio o ruta
  - [x] 3.5 Buscar el patrón de validación de taller_id duplicado en servicios: objeto = query.filter(id).first(); if not objeto or objeto.taller_id != taller_id
  - _Requirements: 1, 2, 20_

- [x] 4. Fase 1 — Auditoría de scripts
  - [x] 4.1 Leer scripts/README.md y scripts/CRON_JOBS.md para identificar qué scripts están documentados como necesarios
  - [x] 4.2 Leer y comparar scripts/seed_admin.py vs scripts/seed_demo.py — determinar si seed_admin.py sigue siendo necesario
  - [x] 4.3 Leer scripts/crear_super_admin_py.py y determinar si es redundante con scripts/crear_super_admin.sql (el .sql es el canónico)
  - [x] 4.4 Leer scripts/crear_v3.py y determinar si es un script de migración ya ejecutado o sigue siendo necesario
  - [x] 4.5 Leer y comparar scripts/apply_db_indexes.sh, scripts/apply_indexes_python.py y scripts/create_all_indexes.py — confirmar que create_all_indexes.py es el canónico
  - _Requirements: 4_

- [x] 5. Fase 1 — Auditoría del frontend
  - [x] 5.1 Leer App.jsx y listar todas las rutas registradas en el router para identificar páginas sin ruta
  - [x] 5.2 Buscar en todos los archivos JSX si EconomiaAuth.jsx, EstadisticasDashboard.jsx, PageHero.jsx y Starfield.jsx son importados
  - [x] 5.3 Leer api.js y authService.js y verificar si hay lógica de autenticación duplicada entre ambos
  - [x] 5.4 Ejecutar depcheck en frontend/ y guardar reporte de dependencias no usadas
  - [x] 5.5 Verificar si qrcode.react se usa en algún componente o página del frontend
  - _Requirements: 3, 6_

- [x] 6. Fase 1 — Auditoría de dependencias del backend
  - [x] 6.1 Buscar en todo el código Python si Flask y Werkzeug son importados directamente en algún archivo de app/
  - [x] 6.2 Buscar en todo el código Python si nltk es importado en algún archivo de app/
  - [x] 6.3 Buscar en todo el código Python si ecdsa es importado directamente en algún archivo de app/
  - [x] 6.4 Verificar si gunicorn se usa junto a uvicorn o si es redundante en el contexto actual
  - [x] 6.5 Identificar todas las dependencias de requirements.txt que son solo de desarrollo (pytest, mypy, pre-commit, safety, bandit, ruff, pylint, radon, vulture)
  - _Requirements: 6_

- [x] 7. Fase 2 — Generar reporte de auditoría consolidado
  - [x] 7.1 Crear .kiro/specs/limpieza-codigo-completo/auditoria-report.md con resumen ejecutivo: total archivos analizados, hallazgos por severidad (crítico/alto/medio/bajo)
  - [x] 7.2 Agregar al reporte sección de scripts obsoletos con lista de archivos a eliminar y justificación
  - [x] 7.3 Agregar al reporte sección de código duplicado con ubicaciones exactas y decisión de cuál mantener
  - [x] 7.4 Agregar al reporte sección de imports no usados con archivo y línea
  - [x] 7.5 Agregar al reporte sección de dependencias no usadas (backend y frontend)
  - [x] 7.6 Agregar al reporte sección de hallazgos de seguridad multi-tenant con severidad crítica si aplica
  - [x] 7.7 Agregar al reporte sección de componentes y páginas frontend no usados
  - _Requirements: 9_

- [x] 8. Fase 3A — Eliminar scripts obsoletos (bajo riesgo)
  - [x] 8.1 Eliminar scripts/_aplicar_columnas_faltantes.py
  - [x] 8.2 Eliminar scripts/_check_audit.py
  - [x] 8.3 Eliminar scripts/_check_db.py
  - [x] 8.4 Eliminar scripts/_check_login.py
  - [x] 8.5 Eliminar scripts/_check_which_db.py
  - [x] 8.6 Eliminar scripts/_test_auth_full.py
  - [x] 8.7 Eliminar scripts/_test_auth_runtime.py
  - [x] 8.8 Eliminar scripts/_test_login.py
  - [x] 8.9 Eliminar scripts/apply_db_indexes.sh (consolidado en create_all_indexes.py)
  - [x] 8.10 Eliminar scripts/apply_indexes_python.py (consolidado en create_all_indexes.py)
  - [x] 8.11 Eliminar scripts/crear_super_admin_py.py si la auditoría confirmó que el .sql es el canónico
  - [x] 8.12 Ejecutar pytest tests/ -q y verificar que todos los tests siguen pasando después de eliminar scripts
  - [x] 8.13 Actualizar scripts/README.md para reflejar los scripts eliminados
  - _Requirements: 4, 12, 14_

- [x] 9. Fase 3B — Limpiar imports no usados (riesgo medio)
  - [x] 9.1 Instalar autoflake y ejecutarlo en modo check sobre app/ para listar imports no usados sin modificar archivos
  - [x] 9.2 Aplicar autoflake para eliminar imports no usados en app/rutas/ y verificar que el servidor arranca
  - [x] 9.3 Aplicar autoflake para eliminar imports no usados en app/servicios/ y verificar que el servidor arranca
  - [x] 9.4 Aplicar autoflake para eliminar imports no usados en app/repositorios/ y verificar que el servidor arranca
  - [x] 9.5 Aplicar autoflake para eliminar imports no usados en app/esquemas/ y app/utils/ y verificar que el servidor arranca
  - [x] 9.6 Ejecutar pytest tests/ -q y verificar que todos los tests siguen pasando
  - _Requirements: 2, 12_

- [x] 10. Fase 3B — Eliminar código muerto identificado por vulture (riesgo medio)
  - [x] 10.1 Revisar el reporte de vulture y eliminar funciones muertas con confianza ≥ 80% en app/servicios/
  - [x] 10.2 Revisar el reporte de vulture y eliminar funciones muertas con confianza ≥ 80% en app/repositorios/
  - [x] 10.3 Revisar el reporte de vulture y eliminar funciones muertas con confianza ≥ 80% en app/rutas/
  - [x] 10.4 Revisar el reporte de vulture y eliminar funciones muertas con confianza ≥ 80% en app/utils/
  - [x] 10.5 Ejecutar pytest tests/ -q y verificar que todos los tests siguen pasando
  - _Requirements: 2, 12_

- [x] 11. Fase 3B — Limpiar frontend (riesgo medio)
  - [x] 11.1 Eliminar componentes React confirmados como no usados en la auditoría (los que no tienen ningún import en el proyecto)
  - [x] 11.2 Eliminar páginas React confirmadas como sin ruta en App.jsx
  - [x] 11.3 Eliminar imports no usados en archivos JSX identificados en la auditoría
  - [x] 11.4 Ejecutar npm run test en frontend/ y verificar que todos los tests siguen pasando
  - _Requirements: 3, 12_

- [-] 12. Fase 3B — Limpiar dependencias (riesgo medio)
  - [x] 12.1 Crear requirements-dev.txt con las dependencias solo de desarrollo: pytest, mypy, pre-commit, safety, bandit, ruff, pylint, radon, vulture, hypothesis
  - [x] 12.2 Eliminar de requirements.txt las dependencias confirmadas como no usadas en el código de producción (Flask, Werkzeug si no se importan, nltk si no se importa)
  - [x] 12.3 Verificar que el backend arranca correctamente después de modificar requirements.txt
  - [x] 12.4 Eliminar de frontend/package.json las dependencias confirmadas como no usadas (qrcode.react si no se usa)
  - [x] 12.5 Ejecutar pytest tests/ -q y npm run test para verificar que todo sigue funcionando
  - _Requirements: 6, 12_

- [x] 13. Fase 3C — Consolidar rutas mobile duplicadas (alto riesgo)
  - [x] 13.1 Leer main.py y confirmar cuál de las dos rutas mobile está registrada (mobile_ruta.py o mobile_api_ruta.py)
  - [x] 13.2 Eliminar la ruta mobile que no está registrada en main.py
  - [x] 13.3 Si ambas están registradas, leer ambos archivos completos, identificar endpoints únicos de cada uno y consolidarlos en un solo archivo
  - [x] 13.4 Ejecutar pytest tests/ -q y verificar que todos los tests siguen pasando
  - _Requirements: 1, 12_

- [x] 14. Fase 3C — Consolidar servicios WhatsApp duplicados (alto riesgo)
  - [x] 14.1 Leer ambos servicios de WhatsApp completos y determinar cuál está activo según la configuración actual
  - [x] 14.2 Consolidar en app/servicios/whatsapp_service.py manteniendo la implementación activa como principal
  - [x] 14.3 Si ambos providers son necesarios, implementar patrón Strategy con función get_whatsapp_provider() que retorna el servicio correcto según variable de entorno WHATSAPP_PROVIDER
  - [x] 14.4 Actualizar todas las importaciones en rutas que usen el servicio eliminado
  - [x] 14.5 Eliminar el archivo del servicio redundante
  - [x] 14.6 Ejecutar pytest tests/ -q y verificar que todos los tests siguen pasando
  - _Requirements: 1, 12, 20_

- [x] 15. Fase 3C — Extraer helper tenant_guard para eliminar validación duplicada (alto riesgo)
  - [x] 15.1 Buscar en todos los servicios el patrón: objeto = query.filter(id).first(); if not objeto or objeto.taller_id != taller_id: raise HTTPException(404)
  - [x] 15.2 Crear app/utils/tenant_guard.py con función verificar_pertenencia(objeto, taller_id, nombre_recurso) que lanza HTTPException 404 si el objeto no pertenece al taller
  - [x] 15.3 Reemplazar el patrón duplicado en app/servicios/ticket_service.py con la llamada a verificar_pertenencia()
  - [x] 15.4 Reemplazar el patrón duplicado en app/servicios/vehiculo_service.py con la llamada a verificar_pertenencia()
  - [x] 15.5 Reemplazar el patrón duplicado en los demás servicios donde se encontró el patrón
  - [x] 15.6 Escribir tests unitarios para tenant_guard.py verificando que lanza 404 cuando taller_id no coincide
  - [x] 15.7 Ejecutar pytest tests/ -q y verificar que todos los tests siguen pasando
  - _Requirements: 1, 11, 12, 20_

- [x] 16. Fase 3C — Resolver generadores de PDF duplicados (alto riesgo)
  - [x] 16.1 Leer app/utils/pdf_generator.py y app/utils/pdf_economia.py completos y determinar si hay funcionalidad duplicada
  - [x] 16.2 Si hay duplicación real, consolidar la funcionalidad común en pdf_generator.py y hacer que pdf_economia.py use pdf_generator.py como base
  - [x] 16.3 Eliminar funciones duplicadas del archivo que quede como secundario
  - [x] 16.4 Ejecutar pytest tests/ -q y verificar que todos los tests siguen pasando
  - _Requirements: 1, 12_

- [x] 17. Generar documentación final de cambios
  - [x] 17.1 Crear CHANGELOG-LIMPIEZA.md en la raíz del proyecto listando todos los archivos eliminados con justificación
  - [x] 17.2 Agregar al CHANGELOG-LIMPIEZA.md la lista de funciones eliminadas con justificación
  - [x] 17.3 Agregar al CHANGELOG-LIMPIEZA.md la lista de dependencias eliminadas con justificación
  - [x] 17.4 Agregar al CHANGELOG-LIMPIEZA.md la lista de código consolidado indicando qué versiones se eliminaron y cuál se mantuvo
  - [x] 17.5 Registrar métricas finales: total líneas de código, total archivos, tests pasando — y comparar con el baseline de la Fase 0
  - _Requirements: 13, 14_
