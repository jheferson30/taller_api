"""encrypt_pii_vehiculos

Revision ID: a1b2c3d4e5f6
Revises: 288ae5386f15
Create Date: 2026-05-06 10:00:00.000000-05:00

Migración para encriptar campos PII existentes en la tabla vehiculos.

Esta migración:
1. Agrega columnas temporales encriptadas (_enc)
2. Migra datos existentes en lotes de 100 usando PIIEncryptor
3. Maneja tres casos: None → None, ya encriptado → copiar, plaintext → encriptar
4. Elimina columnas originales y renombra las temporales

**Validates: Requirement 4.9**
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '288ae5386f15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Encripta los campos PII existentes en la tabla vehiculos.
    
    Estrategia:
    - Agregar columnas temporales encriptadas
    - Migrar datos en lotes de 100 registros
    - Usar PIIEncryptor.is_encrypted() para detectar valores ya encriptados
    - Renombrar columnas al finalizar
    """
    # 1. Agregar columnas temporales encriptadas
    op.add_column("vehiculos", sa.Column("nombre_propietario_enc", sa.String(500), nullable=True))
    op.add_column("vehiculos", sa.Column("telefono_propietario_enc", sa.String(500), nullable=True))

    # 2. Migrar datos existentes en lotes de 100
    connection = op.get_bind()
    
    # Importar PIIEncryptor y SecretsManager
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from app.utils.pii_encryptor import PIIEncryptor
    from app.configuracion.secrets_manager import SecretsManager
    
    encryptor = PIIEncryptor(SecretsManager())
    
    offset = 0
    batch_size = 100
    total_processed = 0
    
    while True:
        # Usar text() para raw SQL queries (requerido por Alembic moderno)
        rows = connection.execute(
            text(
                "SELECT id, nombre_propietario, telefono_propietario "
                "FROM vehiculos "
                "ORDER BY id "
                "LIMIT :limit OFFSET :offset"
            ),
            {"limit": batch_size, "offset": offset}
        ).fetchall()
        
        if not rows:
            break
        
        for row in rows:
            # Procesar nombre_propietario
            nombre_enc = None
            if row.nombre_propietario is not None:
                if encryptor.is_encrypted(row.nombre_propietario):
                    # Ya está encriptado → copiar tal cual
                    nombre_enc = row.nombre_propietario
                else:
                    # Plaintext → encriptar
                    nombre_enc = encryptor.encrypt(row.nombre_propietario)
            
            # Procesar telefono_propietario
            telefono_enc = None
            if row.telefono_propietario is not None:
                if encryptor.is_encrypted(row.telefono_propietario):
                    # Ya está encriptado → copiar tal cual
                    telefono_enc = row.telefono_propietario
                else:
                    # Plaintext → encriptar
                    telefono_enc = encryptor.encrypt(row.telefono_propietario)
            
            # Actualizar el registro con los valores encriptados
            connection.execute(
                text(
                    "UPDATE vehiculos "
                    "SET nombre_propietario_enc = :n, telefono_propietario_enc = :t "
                    "WHERE id = :id"
                ),
                {
                    "n": nombre_enc,
                    "t": telefono_enc,
                    "id": row.id,
                }
            )
        
        total_processed += len(rows)
        offset += batch_size
        
        # Log de progreso cada 1000 registros
        if total_processed % 1000 == 0:
            print(f"✅ Procesados {total_processed} vehículos...")
    
    print(f"✅ Migración PII completada: {total_processed} vehículos procesados")

    # 3. Eliminar columnas originales
    op.drop_column("vehiculos", "nombre_propietario")
    op.drop_column("vehiculos", "telefono_propietario")

    # 4. Renombrar columnas temporales a los nombres originales
    op.alter_column("vehiculos", "nombre_propietario_enc", new_column_name="nombre_propietario")
    op.alter_column("vehiculos", "telefono_propietario_enc", new_column_name="telefono_propietario")


def downgrade() -> None:
    """
    Downgrade de encriptación PII requiere proceso manual controlado.
    
    El downgrade automático no es seguro porque:
    1. Requiere acceso a la PII_MASTER_KEY (que puede no estar disponible)
    2. Expone datos sensibles en texto plano en la BD
    3. Puede causar pérdida de datos si la clave no es la correcta
    
    Para realizar un downgrade manual:
    1. Verificar que la PII_MASTER_KEY está disponible
    2. Crear un script de migración manual que desencripte los datos
    3. Validar que todos los datos se desencriptaron correctamente
    4. Ejecutar el script en un entorno de staging primero
    5. Documentar el proceso en el runbook correspondiente
    
    Ver: docs/runbooks/pii-encryption-rollback.md
    """
    raise NotImplementedError(
        "Downgrade de encriptación PII requiere proceso manual controlado. "
        "Ver runbook: docs/runbooks/pii-encryption-rollback.md"
    )
