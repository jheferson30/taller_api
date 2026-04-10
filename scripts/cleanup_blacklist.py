#!/usr/bin/env python
"""
Script para limpiar tokens blacklisted expirados.
Debe ejecutarse diariamente (recomendado: 2 AM).

Uso:
    python scripts/cleanup_blacklist.py
"""

import os
import sys
from datetime import UTC, datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.base_datos import SessionLocal
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository


def cleanup_expired_tokens():
    """Limpia tokens blacklisted que ya expiraron."""
    print(f"[{datetime.now(UTC)}] Iniciando limpieza de tokens blacklisted expirados...")

    db = SessionLocal()
    try:
        repo = TokenBlacklistRepository(db)
        deleted_count = repo.cleanup_expired()

        print(f"[{datetime.now(UTC)}] Limpieza completada: {deleted_count} tokens eliminados.")

        return deleted_count
    except Exception as e:
        print(f"[{datetime.now(UTC)}] ERROR: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        deleted = cleanup_expired_tokens()
        sys.exit(0)
    except Exception as e:
        print(f"Error fatal: {str(e)}")
        sys.exit(1)
