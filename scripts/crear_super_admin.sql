-- ============================================================================
-- SCRIPT DE CREACIÓN DEL SUPER_ADMIN
-- ============================================================================
--
-- PROPÓSITO:
--   Crear el usuario administrador de la plataforma SaaS (SUPER_ADMIN).
--   Este usuario no pertenece a ningún taller (taller_id = NULL) y tiene
--   control total sobre todos los tenants de la plataforma.
--
-- ADVERTENCIAS DE SEGURIDAD:
--   ⚠️  Este es el ÚNICO método autorizado para crear un SUPER_ADMIN.
--   ⚠️  NUNCA exponer un endpoint HTTP para crear usuarios SUPER_ADMIN.
--   ⚠️  CAMBIAR la contraseña por defecto ANTES de usar en producción.
--   ⚠️  Guardar la contraseña en un gestor de contraseñas seguro (1Password,
--       Bitwarden, AWS Secrets Manager, etc.).
--   ⚠️  Este script es idempotente: puede ejecutarse múltiples veces sin
--       duplicar datos. Si el SUPER_ADMIN ya existe, actualiza la contraseña.
--
-- INSTRUCCIONES DE USO:
--   1. Generar el hash bcrypt de la contraseña con el script auxiliar:
--        python scripts/generar_hash_bcrypt.py
--   2. Reemplazar el valor de v_password_hash con el hash generado.
--   3. Ejecutar este script contra la base de datos:
--        psql -U postgres -d taller_v3 -f scripts/crear_super_admin.sql
--   4. Verificar la creación:
--        psql -U postgres -d taller_v3 -c "SELECT id, username, email, taller_id FROM users WHERE username = 'superadmin';"
--
-- REQUISITOS:
--   - La tabla `users` debe existir (ejecutar migraciones primero).
--   - La tabla `roles` debe existir con el rol SUPER_ADMIN.
--   - La tabla `user_roles` debe existir.
--
-- ============================================================================

DO $$
DECLARE
    v_role_id   INTEGER;
    v_user_id   INTEGER;
    -- ⚠️  Hash bcrypt generado para la contraseña: SuperAdmin2024!
    -- Cambiar esta contraseña en producción usando: python scripts/generar_hash_bcrypt.py
    v_password_hash TEXT := '$2b$12$pGporIi9SAKvf59e4sSxtOV5GqPxEv/l50JaRt6BQ14CflHpNaS8e';
BEGIN
    -- Verificar que la tabla users existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'users'
    ) THEN
        RAISE EXCEPTION 'La tabla users no existe. Ejecutar las migraciones primero: alembic upgrade head';
    END IF;

    -- Verificar que la tabla roles existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'roles'
    ) THEN
        RAISE EXCEPTION 'La tabla roles no existe. Ejecutar las migraciones primero: alembic upgrade head';
    END IF;

    -- 1. Asegurar que el rol SUPER_ADMIN existe
    INSERT INTO roles (name, description)
    VALUES (
        'SUPER_ADMIN',
        'Administrador de la plataforma SaaS. Sin afiliación a ningún taller. Acceso total a configuración y métricas de la plataforma.'
    )
    ON CONFLICT (name) DO NOTHING;

    SELECT id INTO v_role_id FROM roles WHERE name = 'SUPER_ADMIN';

    IF v_role_id IS NULL THEN
        RAISE EXCEPTION 'No se pudo crear o encontrar el rol SUPER_ADMIN';
    END IF;

    -- 2. Crear o actualizar el usuario SUPER_ADMIN
    --    taller_id = NULL: el SUPER_ADMIN no pertenece a ningún taller
    INSERT INTO users (
        taller_id,
        username,
        email,
        password_hash,
        is_active,
        is_migrated
    )
    VALUES (
        NULL,
        'superadmin',
        'admin@plataforma.com',
        v_password_hash,
        TRUE,
        TRUE
    )
    ON CONFLICT (username) DO UPDATE
        SET password_hash = EXCLUDED.password_hash,
            is_active     = TRUE,
            taller_id     = NULL;

    SELECT id INTO v_user_id FROM users WHERE username = 'superadmin';

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'No se pudo crear o encontrar el usuario superadmin';
    END IF;

    -- 3. Asignar rol SUPER_ADMIN (idempotente)
    INSERT INTO user_roles (user_id, role_id)
    VALUES (v_user_id, v_role_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;

    -- 4. Confirmación
    RAISE NOTICE '✅ SUPER_ADMIN creado/actualizado exitosamente';
    RAISE NOTICE '   user_id  : %', v_user_id;
    RAISE NOTICE '   username : superadmin';
    RAISE NOTICE '   email    : admin@plataforma.com';
    RAISE NOTICE '   taller_id: NULL (sin afiliación a taller)';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANTE: Cambiar la contraseña por defecto antes de usar en producción.';
    RAISE NOTICE '   Usar: python scripts/generar_hash_bcrypt.py para generar un nuevo hash.';

END $$;
