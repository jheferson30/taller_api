#!/usr/bin/env python
"""
Script para generar reporte de métricas de seguridad.
Debe ejecutarse semanalmente (recomendado: lunes a las 8 AM).

Genera un reporte con:
- Intentos de login fallidos por IP
- Alertas de seguridad
- Usuarios creados/modificados
- Tokens blacklisted
- Solicitudes de password reset

Uso:
    python scripts/security_report.py [--days DAYS] [--output FILE]
"""

import sys
import os
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.base_datos import SessionLocal
from app.modelos.audit_log import AuditLog
from app.modelos.token_blacklist import TokenBlacklist
from sqlalchemy import func


def generate_security_report(days: int = 7, output_file: str = None):
    """
    Genera reporte de seguridad.
    
    Args:
        days: Número de días a incluir en el reporte
        output_file: Archivo de salida (opcional, default: stdout)
    """
    print(f"[{datetime.now(timezone.utc)}] Generando reporte de seguridad...")
    print(f"Período: últimos {days} días")
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    db = SessionLocal()
    try:
        # Recopilar métricas
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"REPORTE DE SEGURIDAD - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report_lines.append(f"Período: {cutoff_date.strftime('%Y-%m-%d')} a {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # 1. Intentos de login fallidos por IP
        report_lines.append("1. INTENTOS DE LOGIN FALLIDOS POR IP")
        report_lines.append("-" * 80)
        
        failed_logins = db.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('attempts')
        ).filter(
            AuditLog.action == 'LOGIN_FAILED',
            AuditLog.created_at >= cutoff_date
        ).group_by(
            AuditLog.ip_address
        ).order_by(
            func.count(AuditLog.id).desc()
        ).limit(20).all()
        
        if failed_logins:
            report_lines.append(f"{'IP Address':<20} {'Intentos':<10}")
            report_lines.append("-" * 80)
            for ip, attempts in failed_logins:
                report_lines.append(f"{ip:<20} {attempts:<10}")
        else:
            report_lines.append("No se encontraron intentos de login fallidos.")
        
        report_lines.append("")
        
        # 2. Alertas de seguridad
        report_lines.append("2. ALERTAS DE SEGURIDAD")
        report_lines.append("-" * 80)
        
        security_alerts = db.query(AuditLog).filter(
            AuditLog.action == 'SECURITY_ALERT',
            AuditLog.created_at >= cutoff_date
        ).order_by(AuditLog.created_at.desc()).all()
        
        if security_alerts:
            for alert in security_alerts:
                report_lines.append(f"[{alert.created_at}] {alert.details.get('alert_type', 'UNKNOWN')}")
                report_lines.append(f"  IP: {alert.ip_address}")
                report_lines.append(f"  Detalles: {alert.details.get('message', 'N/A')}")
                report_lines.append("")
        else:
            report_lines.append("No se encontraron alertas de seguridad.")
        
        report_lines.append("")
        
        # 3. Usuarios creados/modificados
        report_lines.append("3. GESTIÓN DE USUARIOS")
        report_lines.append("-" * 80)
        
        user_events = db.query(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.action.in_(['USER_CREATE', 'USER_UPDATE', 'USER_DEACTIVATE', 'ROLE_CHANGE']),
            AuditLog.created_at >= cutoff_date
        ).group_by(
            AuditLog.action
        ).all()
        
        if user_events:
            report_lines.append(f"{'Acción':<25} {'Cantidad':<10}")
            report_lines.append("-" * 80)
            for action, count in user_events:
                report_lines.append(f"{action:<25} {count:<10}")
        else:
            report_lines.append("No se encontraron eventos de gestión de usuarios.")
        
        report_lines.append("")
        
        # 4. Tokens blacklisted
        report_lines.append("4. TOKENS BLACKLISTED")
        report_lines.append("-" * 80)
        
        blacklisted_count = db.query(func.count(TokenBlacklist.id)).filter(
            TokenBlacklist.blacklisted_at >= cutoff_date
        ).scalar()
        
        expired_count = db.query(func.count(TokenBlacklist.id)).filter(
            TokenBlacklist.expires_at < datetime.now(timezone.utc)
        ).scalar()
        
        active_count = db.query(func.count(TokenBlacklist.id)).filter(
            TokenBlacklist.expires_at >= datetime.now(timezone.utc)
        ).scalar()
        
        report_lines.append(f"Tokens blacklisted en período: {blacklisted_count}")
        report_lines.append(f"Tokens expirados (pueden limpiarse): {expired_count}")
        report_lines.append(f"Tokens activos en blacklist: {active_count}")
        report_lines.append("")
        
        # 5. Solicitudes de password reset
        report_lines.append("5. SOLICITUDES DE PASSWORD RESET")
        report_lines.append("-" * 80)
        
        reset_requests = db.query(func.count(AuditLog.id)).filter(
            AuditLog.action == 'PASSWORD_RESET',
            AuditLog.created_at >= cutoff_date
        ).scalar()
        
        report_lines.append(f"Solicitudes de reset en período: {reset_requests}")
        report_lines.append("")
        
        # 6. Resumen de actividad
        report_lines.append("6. RESUMEN DE ACTIVIDAD")
        report_lines.append("-" * 80)
        
        total_events = db.query(func.count(AuditLog.id)).filter(
            AuditLog.created_at >= cutoff_date
        ).scalar()
        
        logins_success = db.query(func.count(AuditLog.id)).filter(
            AuditLog.action == 'LOGIN',
            AuditLog.created_at >= cutoff_date
        ).scalar()
        
        logins_failed = db.query(func.count(AuditLog.id)).filter(
            AuditLog.action == 'LOGIN_FAILED',
            AuditLog.created_at >= cutoff_date
        ).scalar()
        
        report_lines.append(f"Total de eventos de auditoría: {total_events}")
        report_lines.append(f"Logins exitosos: {logins_success}")
        report_lines.append(f"Logins fallidos: {logins_failed}")
        
        if logins_success + logins_failed > 0:
            success_rate = (logins_success / (logins_success + logins_failed)) * 100
            report_lines.append(f"Tasa de éxito de login: {success_rate:.1f}%")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        # Generar output
        report_text = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"Reporte guardado en: {output_file}")
        else:
            print(report_text)
        
        print(f"[{datetime.now(timezone.utc)}] Reporte generado exitosamente.")
        
        return total_events
        
    except Exception as e:
        print(f"[{datetime.now(timezone.utc)}] ERROR: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generar reporte de seguridad")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Número de días a incluir en el reporte (default: 7)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Archivo de salida (default: stdout)"
    )
    
    args = parser.parse_args()
    
    try:
        generate_security_report(days=args.days, output_file=args.output)
        sys.exit(0)
    except Exception as e:
        print(f"Error fatal: {str(e)}")
        sys.exit(1)
