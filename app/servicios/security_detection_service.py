"""
Servicio de detección de eventos de seguridad.
Requirements: 23.1, 23.3, 23.4
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.repositorios.audit_log_repository import AuditLogRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.modelos.audit_log import AuditAction


class SecurityDetectionService:
    """Servicio para detectar eventos de seguridad sospechosos."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_log_repo = AuditLogRepository(db)
        self.token_blacklist_repo = TokenBlacklistRepository(db)

    def detect_brute_force(
        self,
        ip_address: str,
        time_window_minutes: int = 10,
        max_attempts: int = 5
    ) -> bool:
        """
        Detecta intentos de fuerza bruta.
        Retorna True si se detecta un ataque (>5 intentos fallidos en 10 min desde misma IP).
        Requirements: 23.1
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        
        # Contar intentos fallidos desde esta IP en la ventana de tiempo
        failed_attempts = self.audit_log_repo.count_by_action_and_ip(
            action=AuditAction.LOGIN_FAILED,
            ip_address=ip_address,
            since=cutoff_time
        )
        
        if failed_attempts > max_attempts:
            # Registrar alerta de seguridad
            self.audit_log_repo.create(
                action=AuditAction.SECURITY_ALERT,
                user_id=None,
                ip_address=ip_address,
                user_agent=None,
                details={
                    "alert_type": "brute_force_detected",
                    "failed_attempts": failed_attempts,
                    "time_window_minutes": time_window_minutes,
                    "threshold": max_attempts
                }
            )
            return True
        
        return False

    def detect_token_reuse(
        self,
        jti: str,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Detecta uso de token después de logout.
        Retorna True si el token está en la blacklist (intento de reuso).
        Requirements: 23.3
        """
        is_blacklisted = self.token_blacklist_repo.is_blacklisted(jti)
        
        if is_blacklisted:
            # Registrar alerta de seguridad
            self.audit_log_repo.create(
                action=AuditAction.SECURITY_ALERT,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "alert_type": "token_reuse_detected",
                    "jti": jti,
                    "message": "Attempt to use blacklisted token"
                }
            )
            return True
        
        return False

    def detect_password_reset_abuse(
        self,
        email: str,
        time_window_hours: int = 1,
        max_requests: int = 3
    ) -> bool:
        """
        Detecta abuso de solicitudes de reset de contraseña.
        Retorna True si se detecta abuso (>3 solicitudes en 1 hora).
        Requirements: 23.4
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        
        # Contar solicitudes de reset desde este email en la ventana de tiempo
        reset_requests = self.audit_log_repo.count_by_action_and_details(
            action=AuditAction.PASSWORD_RESET,
            details_key="email",
            details_value=email,
            since=cutoff_time
        )
        
        if reset_requests > max_requests:
            # Registrar alerta de seguridad
            self.audit_log_repo.create(
                action=AuditAction.SECURITY_ALERT,
                user_id=None,
                ip_address=None,
                user_agent=None,
                details={
                    "alert_type": "password_reset_abuse_detected",
                    "email": email,
                    "reset_requests": reset_requests,
                    "time_window_hours": time_window_hours,
                    "threshold": max_requests
                }
            )
            return True
        
        return False

    def check_all_detections(
        self,
        ip_address: Optional[str] = None,
        jti: Optional[str] = None,
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        """
        Ejecuta todas las detecciones aplicables y retorna resultados.
        """
        results = {
            "brute_force_detected": False,
            "token_reuse_detected": False,
            "password_reset_abuse_detected": False
        }
        
        if ip_address:
            results["brute_force_detected"] = self.detect_brute_force(ip_address)
        
        if jti and user_id:
            results["token_reuse_detected"] = self.detect_token_reuse(
                jti, user_id, ip_address, user_agent
            )
        
        if email:
            results["password_reset_abuse_detected"] = self.detect_password_reset_abuse(email)
        
        return results
