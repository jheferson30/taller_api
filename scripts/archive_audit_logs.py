#!/usr/bin/env python
"""
Script para archivar logs de auditoría antiguos.
Debe ejecutarse mensualmente (recomendado: primer día del mes a las 3 AM).

Este script exporta logs antiguos a archivos JSON y opcionalmente los elimina de la BD.

Uso:
    python scripts/archive_audit_logs.py [--retention-days DAYS] [--delete]
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone, timedelta

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.base_datos import SessionLocal
from app.modelos.audit_log import AuditLog
from app.configuracion.config import AUDIT_LOG_RETENTION_DAYS


def archive_old_logs(retention_days: int = None, delete_after_archive: bool = False):
    """
    Archiva logs de auditoría antiguos.
    
    Args:
        retention_days: Días de retención (default: desde config)
        delete_after_archive: Si True, elimina logs después de archivar
    """
    if retention_days is None:
        retention_days = AUDIT_LOG_RETENTION_DAYS
    
    if retention_days == 0:
        print("AUDIT_LOG_RETENTION_DAYS=0 (retención infinita). No se archivará nada.")
        return 0
    
    print(f"[{datetime.now(timezone.utc)}] Iniciando archival de logs de auditoría...")
    print(f"Retención configurada: {retention_days} días")
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    print(f"Archivando logs anteriores a: {cutoff_date}")
    
    db = SessionLocal()
    try:
        # Obtener logs antiguos
        old_logs = db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).all()
        
        if not old_logs:
            print("No hay logs antiguos para archivar.")
            return 0
        
        print(f"Encontrados {len(old_logs)} logs para archivar.")
        
        # Crear directorio de archivos
        archive_dir = "audit_archives"
        os.makedirs(archive_dir, exist_ok=True)
        
        # Crear archivo de archivo
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_file = os.path.join(archive_dir, f"audit_logs_{timestamp}.json")
        
        # Serializar logs
        logs_data = []
        for log in old_logs:
            logs_data.append({
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })
        
        # Guardar a archivo
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, indent=2, ensure_ascii=False)
        
        print(f"Logs archivados en: {archive_file}")
        
        # Eliminar de BD si se solicitó
        if delete_after_archive:
            print("Eliminando logs archivados de la base de datos...")
            for log in old_logs:
                db.delete(log)
            db.commit()
            print(f"{len(old_logs)} logs eliminados de la base de datos.")
        else:
            print("Logs mantenidos en la base de datos (usa --delete para eliminarlos).")
        
        print(f"[{datetime.now(timezone.utc)}] Archival completado.")
        return len(old_logs)
        
    except Exception as e:
        print(f"[{datetime.now(timezone.utc)}] ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archivar logs de auditoría antiguos")
    parser.add_argument(
        "--retention-days",
        type=int,
        help=f"Días de retención (default: {AUDIT_LOG_RETENTION_DAYS} desde config)"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Eliminar logs de la BD después de archivar"
    )
    
    args = parser.parse_args()
    
    try:
        archived = archive_old_logs(
            retention_days=args.retention_days,
            delete_after_archive=args.delete
        )
        sys.exit(0)
    except Exception as e:
        print(f"Error fatal: {str(e)}")
        sys.exit(1)
