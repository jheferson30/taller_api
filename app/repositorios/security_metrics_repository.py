"""
Repositorio de métricas de seguridad para el Security Dashboard.

Todas las queries operan sobre la tabla ``audit_log`` y son de solo lectura.
No se modifican ni crean registros en este repositorio.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Session

from app.modelos.audit_log import AuditAction, AuditLog


class SecurityMetricsRepository:
    """
    Repositorio de solo lectura para métricas de seguridad.

    Agrega datos de la tabla ``audit_log`` para el dashboard del SUPER_ADMIN.
    Todas las queries usan parámetros — nunca concatenación de strings.
    """

    def __init__(self, db: Session):
        """
        Inicializa el repositorio con una sesión de base de datos.

        Args:
            db: Sesión de SQLAlchemy activa.
        """
        self.db = db

    # ------------------------------------------------------------------
    # Rate limit violations — últimas 24 horas, agrupadas por hora
    # ------------------------------------------------------------------

    def get_rate_limit_violations_24h(self) -> list[dict]:
        """
        Retorna violaciones de rate limit de las últimas 24 horas agrupadas por hora.

        Filtra por:
        - action = SECURITY_ALERT
        - details->alert_type = 'rate_limit_exceeded'

        Returns:
            Lista de dicts con claves ``hour`` (datetime UTC) y ``count`` (int).
        """
        since = datetime.now(UTC) - timedelta(hours=24)

        rows = (
            self.db.query(
                func.date_trunc("hour", AuditLog.timestamp).label("hour"),
                func.count(AuditLog.id).label("count"),
            )
            .filter(
                and_(
                    AuditLog.action == AuditAction.SECURITY_ALERT,
                    AuditLog.details["alert_type"].astext == "rate_limit_exceeded",
                    AuditLog.timestamp >= since,
                )
            )
            .group_by(func.date_trunc("hour", AuditLog.timestamp))
            .order_by(func.date_trunc("hour", AuditLog.timestamp))
            .all()
        )

        return [{"hour": row.hour, "count": row.count} for row in rows]

    # ------------------------------------------------------------------
    # Cross-tenant attempts — últimos 30 días, agrupados por día
    # ------------------------------------------------------------------

    def get_cross_tenant_attempts_30d(self) -> list[dict]:
        """
        Retorna intentos de acceso cross-tenant de los últimos 30 días agrupados por día.

        Filtra por:
        - details->alert_type = 'cross_tenant_access_attempt'

        Returns:
            Lista de dicts con claves ``day`` (datetime UTC) y ``count`` (int).
        """
        since = datetime.now(UTC) - timedelta(days=30)

        rows = (
            self.db.query(
                func.date_trunc("day", AuditLog.timestamp).label("day"),
                func.count(AuditLog.id).label("count"),
            )
            .filter(
                and_(
                    AuditLog.details["alert_type"].astext == "cross_tenant_access_attempt",
                    AuditLog.timestamp >= since,
                )
            )
            .group_by(func.date_trunc("day", AuditLog.timestamp))
            .order_by(func.date_trunc("day", AuditLog.timestamp))
            .all()
        )

        return [{"day": row.day, "count": row.count} for row in rows]

    # ------------------------------------------------------------------
    # Failed auth attempts — últimas 24 horas, agrupados por hora
    # ------------------------------------------------------------------

    def get_failed_auth_attempts_24h(self) -> list[dict]:
        """
        Retorna intentos de autenticación fallidos de las últimas 24 horas agrupados por hora.

        Filtra por:
        - action = LOGIN_FAILED

        Returns:
            Lista de dicts con claves ``hour`` (datetime UTC) y ``count`` (int).
        """
        since = datetime.now(UTC) - timedelta(hours=24)

        rows = (
            self.db.query(
                func.date_trunc("hour", AuditLog.timestamp).label("hour"),
                func.count(AuditLog.id).label("count"),
            )
            .filter(
                and_(
                    AuditLog.action == AuditAction.LOGIN_FAILED,
                    AuditLog.timestamp >= since,
                )
            )
            .group_by(func.date_trunc("hour", AuditLog.timestamp))
            .order_by(func.date_trunc("hour", AuditLog.timestamp))
            .all()
        )

        return [{"hour": row.hour, "count": row.count} for row in rows]

    # ------------------------------------------------------------------
    # Top 10 IPs por violaciones de rate limit — últimas 24 horas
    # ------------------------------------------------------------------

    def get_top_ips_by_violations(self, limit: int = 10) -> list[dict]:
        """
        Retorna las IPs con más violaciones de rate limit en las últimas 24 horas.

        Filtra por:
        - action = SECURITY_ALERT
        - details->alert_type = 'rate_limit_exceeded'

        Args:
            limit: Número máximo de IPs a retornar (por defecto 10).

        Returns:
            Lista de dicts con claves ``ip_address`` (str) y ``total_violations`` (int),
            ordenada de mayor a menor.
        """
        since = datetime.now(UTC) - timedelta(hours=24)

        rows = (
            self.db.query(
                AuditLog.ip_address,
                func.count(AuditLog.id).label("total_violations"),
            )
            .filter(
                and_(
                    AuditLog.action == AuditAction.SECURITY_ALERT,
                    AuditLog.details["alert_type"].astext == "rate_limit_exceeded",
                    AuditLog.timestamp >= since,
                    AuditLog.ip_address.isnot(None),
                )
            )
            .group_by(AuditLog.ip_address)
            .order_by(func.count(AuditLog.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {"ip_address": row.ip_address, "total_violations": row.total_violations}
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Top 10 usuarios por violaciones de rate limit — últimas 24 horas
    # ------------------------------------------------------------------

    def get_top_users_by_violations(self, limit: int = 10) -> list[dict]:
        """
        Retorna los usuarios con más violaciones de rate limit en las últimas 24 horas.

        Filtra por:
        - action = SECURITY_ALERT
        - details->alert_type = 'rate_limit_exceeded'

        Args:
            limit: Número máximo de usuarios a retornar (por defecto 10).

        Returns:
            Lista de dicts con claves ``user_id`` (int) y ``total_violations`` (int),
            ordenada de mayor a menor. Solo incluye registros con user_id no nulo.
        """
        since = datetime.now(UTC) - timedelta(hours=24)

        rows = (
            self.db.query(
                AuditLog.user_id,
                func.count(AuditLog.id).label("total_violations"),
            )
            .filter(
                and_(
                    AuditLog.action == AuditAction.SECURITY_ALERT,
                    AuditLog.details["alert_type"].astext == "rate_limit_exceeded",
                    AuditLog.timestamp >= since,
                    AuditLog.user_id.isnot(None),
                )
            )
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {"user_id": row.user_id, "total_violations": row.total_violations}
            for row in rows
        ]
