"""Script para verificar que la migración b2c3d4e5f6a7 se aplicó correctamente."""
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:123456@localhost:5432/taller_v3?client_encoding=utf8"
engine = create_engine(DB_URL)

with engine.connect() as conn:
    print("=== TALLERES — campos nuevos ===")
    result = conn.execute(text(
        "SELECT column_name, data_type, is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_name = 'talleres' "
        "AND column_name IN ('estado','fecha_inicio_trial','dias_trial','fecha_suspension',"
        "'fecha_cancelacion','bloqueado_emergencia','fecha_bloqueo_emergencia','motivo_bloqueo_emergencia') "
        "ORDER BY column_name"
    ))
    rows = result.fetchall()
    for row in rows:
        print(f"  {row[0]:45} {row[1]:20} nullable={row[2]}")

    print()
    print("=== USERS — taller_id nullable ===")
    result = conn.execute(text(
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name = 'users' AND column_name = 'taller_id'"
    ))
    for row in result.fetchall():
        print(f"  {row[0]:45} {row[1]:20} nullable={row[2]}")

    print()
    print("=== CONFIGURACION_TALLER — campos de localización ===")
    result = conn.execute(text(
        "SELECT column_name, data_type, is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_name = 'configuracion_taller' "
        "AND column_name IN ('moneda','idioma','timezone') "
        "ORDER BY column_name"
    ))
    for row in result.fetchall():
        print(f"  {row[0]:45} {row[1]:20} nullable={row[2]} default={row[3]}")

    print()
    print("=== ÍNDICE ix_talleres_estado ===")
    result = conn.execute(text(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename = 'talleres' AND indexname = 'ix_talleres_estado'"
    ))
    rows = result.fetchall()
    if rows:
        print("  ✅ Índice ix_talleres_estado existe")
    else:
        print("  ❌ Índice ix_talleres_estado NO encontrado")

print()
print("✅ Verificación completa")
