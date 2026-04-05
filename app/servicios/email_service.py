"""
Servicio de envío de emails via SMTP (Gmail).

Usa smtplib de la librería estándar de Python, sin dependencias externas.
La configuración se lee primero de la DB (configuracion_taller) y como
fallback del .env.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_smtp_config():
    """Lee config SMTP desde la DB, con fallback al .env."""
    try:
        from app.configuracion.base_datos import SessionLocal
        from app.modelos.configuracion_taller import ConfiguracionTaller
        db = SessionLocal()
        cfg = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.id == 1).first()
        db.close()
        if cfg and cfg.smtp_user and cfg.smtp_password:
            return {
                "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
                "port": int(os.getenv("SMTP_PORT", "587")),
                "user": cfg.smtp_user,
                "password": cfg.smtp_password,
                "from": cfg.smtp_from or cfg.smtp_user,
            }
    except Exception:
        pass
    # Fallback al .env
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")),
    }


def enviar_email(destinatario: str, asunto: str, cuerpo_html: str) -> bool:
    """Envía un email via SMTP."""
    config = _get_smtp_config()
    if not config["user"] or not config["password"]:
        print("[EMAIL] Credenciales SMTP no configuradas")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = config["from"]
    msg["To"] = destinatario
    msg.attach(MIMEText(cuerpo_html, "html"))

    try:
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(config["user"], config["password"])
            server.sendmail(config["from"], destinatario, msg.as_string())
        print(f"[EMAIL] Correo enviado a {destinatario}")
        return True
    except Exception as e:
        print(f"[EMAIL] Error enviando correo a {destinatario}: {e}")
        return False


def enviar_recuperacion_contrasena(destinatario: str, token: str, nombre: str = "") -> bool:
    """
    Envía el email de recuperación de contraseña con el link y token.
    """
    app_url = os.getenv("APP_URL", "http://localhost:8000")
    link = f"{app_url}/reset-password?token={token}"

    saludo = f"Hola {nombre}," if nombre else "Hola,"

    cuerpo = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #1e40af;">Recuperación de contraseña</h2>
        <p>{saludo}</p>
        <p>Recibimos una solicitud para restablecer tu contraseña. Haz clic en el botón para continuar:</p>
        <a href="{link}" style="display:inline-block; margin: 16px 0; padding: 12px 24px; background:#1e40af; color:#fff; border-radius:6px; text-decoration:none; font-weight:bold;">
            Restablecer contraseña
        </a>
        <p style="color:#64748b; font-size:0.85rem;">O copia este enlace en tu navegador:<br><code>{link}</code></p>
        <p style="color:#64748b; font-size:0.85rem;">Este enlace expira en <strong>1 hora</strong>. Si no solicitaste esto, ignora este correo.</p>
    </div>
    """

    return enviar_email(destinatario, "Recuperación de contraseña - Taller", cuerpo)
