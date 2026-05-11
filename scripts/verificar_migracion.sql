-- ============================================================================
-- Script de Verificación Post-Migración
-- ============================================================================
-- 
-- Uso:
--   psql -U postgres -d taller_db -f scripts/verificar_migracion.sql
--
-- O desde Docker:
--   docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d taller_db -f /scripts/verificar_migracion.sql
--

\echo '=========================================='
\echo '🔍 VERIFICACIÓN DE MIGRACIÓN'
\echo '=========================================='
\echo ''

-- Solicitar taller_id
\prompt 'Ingrese el ID del taller a verificar: ' taller_id

\echo ''
\echo '1️⃣  INFORMACIÓN DEL TALLER'
\echo '=========================================='

SELECT 
    id,
    nombre,
    email,
    telefono,
    estado,
    plan,
    fecha_inicio_plan,
    fecha_fin_plan,
    created_at
FROM talleres 
WHERE id = :taller_id;

\echo ''
\echo '2️⃣  CONTEO DE REGISTROS'
\echo '=========================================='

SELECT 
    'Usuarios' as tabla,
    COUNT(*) as total
FROM usuarios 
WHERE taller_id = :taller_id

UNION ALL

SELECT 
    'Clientes' as tabla,
    COUNT(*) as total
FROM clientes 
WHERE taller_id = :taller_id

UNION ALL

SELECT 
    'Vehículos' as tabla,
    COUNT(*) as total
FROM vehiculos 
WHERE taller_id = :taller_id

UNION ALL

SELECT 
    'Tickets' as tabla,
    COUNT(*) as total
FROM tickets 
WHERE taller_id = :taller_id

UNION ALL

SELECT 
    'Repuestos' as tabla,
    COUNT(*) as total
FROM repuestos 
WHERE taller_id = :taller_id

UNION ALL

SELECT 
    'Citas' as tabla,
    COUNT(*) as total
FROM citas 
WHERE taller_id = :taller_id

UNION ALL

SELECT 
    'Movimientos Caja' as tabla,
    COUNT(*) as total
FROM movimientos_caja 
WHERE taller_id = :taller_id

UNION ALL

SELECT 
    'Notificaciones' as tabla,
    COUNT(*) as total
FROM notificaciones 
WHERE taller_id = :taller_id;

\echo ''
\echo '3️⃣  USUARIOS Y ROLES'
\echo '=========================================='

SELECT 
    u.id,
    u.username,
    u.email,
    u.nombre_completo,
    u.activo,
    STRING_AGG(r.nombre, ', ') as roles
FROM usuarios u
LEFT JOIN usuario_roles ur ON ur.user_id = u.id
LEFT JOIN roles r ON r.id = ur.role_id
WHERE u.taller_id = :taller_id
GROUP BY u.id, u.username, u.email, u.nombre_completo, u.activo
ORDER BY u.id;

\echo ''
\echo '4️⃣  INTEGRIDAD REFERENCIAL'
\echo '=========================================='

\echo 'Verificando vehículos sin cliente...'
SELECT COUNT(*) as vehiculos_huerfanos
FROM vehiculos v
WHERE v.taller_id = :taller_id
  AND v.cliente_id NOT IN (
      SELECT id FROM clientes WHERE taller_id = :taller_id
  );

\echo ''
\echo 'Verificando tickets sin vehículo...'
SELECT COUNT(*) as tickets_huerfanos
FROM tickets t
WHERE t.taller_id = :taller_id
  AND t.vehiculo_id NOT IN (
      SELECT id FROM vehiculos WHERE taller_id = :taller_id
  );

\echo ''
\echo 'Verificando repuestos sin ticket...'
SELECT COUNT(*) as repuestos_huerfanos
FROM repuestos r
WHERE r.taller_id = :taller_id
  AND r.ticket_id NOT IN (
      SELECT id FROM tickets WHERE taller_id = :taller_id
  );

\echo ''
\echo '5️⃣  AISLAMIENTO MULTI-TENANT'
\echo '=========================================='

\echo 'Verificando que no hay datos de otros talleres accesibles...'
SELECT 
    'Usuarios' as tabla,
    COUNT(*) as registros_otros_talleres
FROM usuarios 
WHERE taller_id != :taller_id

UNION ALL

SELECT 
    'Clientes' as tabla,
    COUNT(*) as registros_otros_talleres
FROM clientes 
WHERE taller_id != :taller_id

UNION ALL

SELECT 
    'Vehículos' as tabla,
    COUNT(*) as registros_otros_talleres
FROM vehiculos 
WHERE taller_id != :taller_id

UNION ALL

SELECT 
    'Tickets' as tabla,
    COUNT(*) as registros_otros_talleres
FROM tickets 
WHERE taller_id != :taller_id;

\echo ''
\echo '6️⃣  TICKETS POR ESTADO'
\echo '=========================================='

SELECT 
    estado,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as porcentaje
FROM tickets
WHERE taller_id = :taller_id
GROUP BY estado
ORDER BY total DESC;

\echo ''
\echo '7️⃣  ÚLTIMOS 5 TICKETS'
\echo '=========================================='

SELECT 
    t.id,
    t.estado,
    v.placa,
    c.nombre || ' ' || c.apellido as cliente,
    t.fecha_ingreso,
    t.costo_total
FROM tickets t
JOIN vehiculos v ON v.id = t.vehiculo_id
JOIN clientes c ON c.id = v.cliente_id
WHERE t.taller_id = :taller_id
ORDER BY t.fecha_ingreso DESC
LIMIT 5;

\echo ''
\echo '8️⃣  CLIENTES CON MÁS VEHÍCULOS'
\echo '=========================================='

SELECT 
    c.id,
    c.nombre || ' ' || c.apellido as cliente,
    c.email,
    COUNT(v.id) as total_vehiculos
FROM clientes c
LEFT JOIN vehiculos v ON v.cliente_id = c.id
WHERE c.taller_id = :taller_id
GROUP BY c.id, c.nombre, c.apellido, c.email
HAVING COUNT(v.id) > 0
ORDER BY total_vehiculos DESC
LIMIT 10;

\echo ''
\echo '=========================================='
\echo '✅ VERIFICACIÓN COMPLETADA'
\echo '=========================================='
\echo ''
\echo 'Si todos los conteos son correctos y no hay registros huérfanos,'
\echo 'la migración fue exitosa.'
\echo ''
\echo 'Próximos pasos:'
\echo '1. Probar el login con usuarios del taller'
\echo '2. Verificar que solo ven sus propios datos'
\echo '3. Migrar archivos (fotos, PDFs)'
\echo '4. Notificar a los usuarios'
\echo ''
