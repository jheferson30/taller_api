"""
Script de migración one-shot: cifra campos PII en texto plano.

Problema: los datos migrados del mono-tenant (taller_id != 1) tienen
nombre_propietario y telefono_propietario en texto plano. El sistema v3
usa EncryptedString (AES-256-GCM) y falla al intentar descifrarlos.

Solución: detectar valores no cifrados con PIIEncryptor.is_encrypted()
y cifrarlos in-place usando la misma PII_MASTER_KEY del entorno.

Uso:
    docker exec taller-backend-dev python /app/scripts/cifrar_pii_migracion.py

Seguridad:
    - Idempotente: valores ya cifrados se saltan sin modificar.
    - Transaccional: si falla cualquier UPDATE, hace rollback completo.
    - No expone valores en logs — solo cuenta de filas procesadas.
"""

import logging
import os
import sys

# Asegurar que el path de la app esté disponible
sys.path.insert(0, "/app")

from sqlalchemy import create_engine, text

from app.utils.pii_encryptor import PIIEncryptor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL no está configurada.")
        sys.exit(1)

    pii_master_key = os.getenv("PII_MASTER_KEY")
    if not pii_master_key:
        logger.error("PII_MASTER_KEY no está configurada.")
        sys.exit(1)

    encryptor = PIIEncryptor(secrets_manager=None)
    engine = create_engine(database_url)

    logger.info("Iniciando migración de cifrado PII en tabla 'vehiculos'...")

    with engine.begin() as conn:
        # Leer todos los registros con al menos un campo en texto plano
        rows = conn.execute(
            text(
                "SELECT id, nombre_propietario, telefono_propietario "
                "FROM vehiculos "
                "WHERE nombre_propietario IS NOT NULL "
                "   OR telefono_propietario IS NOT NULL"
            )
        ).fetchall()

        total = len(rows)
        cifrados = 0
        saltados = 0

        for row in rows:
            vehiculo_id = row[0]
            nombre = row[1]
            telefono = row[2]

            nuevo_nombre = nombre
            nuevo_telefono = telefono
            necesita_update = False

            # Cifrar nombre si está en texto plano
            if nombre is not None and not encryptor.is_encrypted(nombre):
                nuevo_nombre = encryptor.encrypt(nombre)
                necesita_update = True

            # Cifrar teléfono si está en texto plano
            if telefono is not None and not encryptor.is_encrypted(telefono):
                nuevo_telefono = encryptor.encrypt(telefono)
                necesita_update = True

            if necesita_update:
                conn.execute(
                    text(
                        "UPDATE vehiculos "
                        "SET nombre_propietario = :nombre, "
                        "    telefono_propietario = :telefono "
                        "WHERE id = :id"
                    ),
                    {
                        "nombre": nuevo_nombre,
                        "telefono": nuevo_telefono,
                        "id": vehiculo_id,
                    },
                )
                cifrados += 1
            else:
                saltados += 1

        logger.info(
            "Migración completada: %d/%d filas cifradas, %d ya estaban cifradas.",
            cifrados,
            total,
            saltados,
        )

    logger.info("Verificando que todos los valores son ahora válidos...")
    with engine.connect() as conn:
        rows_check = conn.execute(
            text(
                "SELECT id, nombre_propietario, telefono_propietario "
                "FROM vehiculos "
                "WHERE nombre_propietario IS NOT NULL "
                "   OR telefono_propietario IS NOT NULL"
            )
        ).fetchall()

        errores = 0
        for row in rows_check:
            vehiculo_id, nombre, telefono = row[0], row[1], row[2]
            if nombre is not None and not encryptor.is_encrypted(nombre):
                logger.error("vehiculo id=%d: nombre_propietario sigue en texto plano.", vehiculo_id)
                errores += 1
            if telefono is not None and not encryptor.is_encrypted(telefono):
                logger.error("vehiculo id=%d: telefono_propietario sigue en texto plano.", vehiculo_id)
                errores += 1

        if errores:
            logger.error("Verificación FALLIDA: %d campos sin cifrar.", errores)
            sys.exit(1)
        else:
            logger.info("Verificación OK: todos los campos PII están cifrados correctamente.")


if __name__ == "__main__":
    main()
