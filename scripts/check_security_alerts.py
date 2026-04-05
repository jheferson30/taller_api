#!/usr/bin/env python
"""
Script para verificar alertas de seguridad recientes y enviar notificaciones.
Debe ejecutarse cada hora.

Uso:
    python scripts/check_security_alerts.py [--hours HOURS] [--email EMAIL]
"""

import sys
import os
import argparse
from datetime import datetime, timezone, timedelta

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.base_datos import SessionLocal
from app.modelos.audit_log import AuditLog


def check_security_alerts(hours: int = 24, email: str = None):
    """
    Verifica alertas de seguridad recientes.
    
    Args:
        hours: Número de horas a revisar
        email: Email para enviar notificaciones (opcional)
    """
    print(f"[{datetime.now(timezone.utc)}] Verificando alertas de seguridad...")
    print(f"Período: últimas {hours} horas")
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    db = SessionLocal()
    try:
        # Buscar alertas recientes
        alerts = db.query(AuditLog).filter(
            AuditLog.action == 'SECURITY_ALERT',
            AuditLog.created_at >= cutoff
        ).order_by(AuditLog.created_at.desc()).all()
        
        if not alerts:
            print("No se encontraron alertas de seguridad.")
            return 0
        
        print(f"\n{'='*80}")
        print(f"ALERTAS DE SEGURIDAD DETECTADAS: {len(alerts)}")
        print(f"{'='*80}\n")
        
        # Agrupar por tipo
        alerts_by_type = {}
        for alert in alerts:
            alert_type = alert.details.get('alert_type', 'UNKNOWN')
            if alert_type not in alerts_by_type:
                alerts_by_type[alert_type] = []
            alerts_by_type[alert_type].append(alert)
        
        # Mostrar alertas agrupadas
        for alert_type, type_alerts in alerts_by_type.items():
            print(f"\n{alert_type}: {len(type_alerts)} alertas")
            print("-" * 80)
            
            for alert in type_alerts[:5]:  # Mostrar máximo 5 por tipo
                print(f"  [{alert.created_at}]")
                print(f"  IP: {alert.ip_address}")
                print(f"  Mensaje: {alert.details.get('message', 'N/A')}")
                print()
            
            if len(type_alerts) > 5:
                print(f"  ... y {len(type_alerts) - 5} alertas más de este tipo\n")
        
        # Enviar notificación por email si se configuró
        if email:
            try:
                send_email_notification(alerts, email)
                print(f"Notificación enviada a: {email}")
            except Exception as e:
                print(f"Error al enviar email: {str(e)}")
        
        print(f"\n[{datetime.now(timezone.utc)}] Verificación completada.")
        return len(alerts)
        
    except Exception as e:
        print(f"[{datetime.now(timezone.utc)}] ERROR: {str(e)}")
        raise
    finally:
        db.close()


def send_email_notification(alerts, recipient_email: str):
    """Envía notificación por email sobre alertas."""
    import smtplib
    from email.mime.text import MIMEText
    from app.configuracion.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    
    # Construir mensaje
    message_lines = [
        f"Se detectaron {len(alerts)} alertas de seguridad:",
        "",
    ]
    
    # Agrupar por tipo
    alerts_by_type = {}
    for alert in alerts:
        alert_type = alert.details.get('alert_type', 'UNKNOWN')
        if alert_type not in alerts_by_type:
            alerts_by_type[alert_type] = []
        alerts_by_type[alert_type].append(alert)
    
    for alert_type, type_alerts in alerts_by_type.items():
        message_lines.append(f"{alert_type}: {len(type_alerts)} alertas")
        for alert in type_alerts[:3]:  # Mostrar máximo 3 por tipo
            message_lines.append(f"  - [{alert.created_at}] IP: {alert.ip_address}")
            message_lines.append(f"    {alert.details.get('message', 'N/A')}")
        if len(type_alerts) > 3:
            message_lines.append(f"  ... y {len(type_alerts) - 3} más")
        message_lines.append("")
    
    message_lines.append("Revisa el sistema para más detalles:")
    message_lines.append("  SELECT * FROM audit_log WHERE action = 'SECURITY_ALERT' ORDER BY created_at DESC;")
    
    message_text = "\n".join(message_lines)
    
    # Enviar email
    msg = MIMEText(message_text)
    msg['Subject'] = f'[ALERTA SEGURIDAD] {len(alerts)} alertas detectadas - Taller API'
    msg['From'] = SMTP_FROM
    msg['To'] = recipient_email
    
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verificar alertas de seguridad")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Número de horas a revisar (default: 24)"
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Email para enviar notificaciones (opcional)"
    )
    
    args = parser.parse_args()
    
    try:
        alert_count = check_security_alerts(hours=args.hours, email=args.email)
        sys.exit(0 if alert_count == 0 else 1)
    except Exception as e:
        print(f"Error fatal: {str(e)}")
        sys.exit(1)
