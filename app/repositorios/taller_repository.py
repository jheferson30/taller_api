"""
Repositorio para operaciones de acceso a datos de Talleres.
El TallerRepository NO hereda de TenantRepository porque los talleres
son la entidad raíz del tenant (no pertenecen a un taller).
"""
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.modelos.taller import Taller


class TallerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, taller_id: int) -> Taller | None:
        return self.db.query(Taller).filter(Taller.id == taller_id).first()

    def get_all(self) -> list[Taller]:
        return self.db.query(Taller).order_by(Taller.nombre).all()

    def get_by_nombre(self, nombre: str) -> Taller | None:
        return self.db.query(Taller).filter(Taller.nombre == nombre).first()

    def create(self, taller: Taller) -> Taller:
        self.db.add(taller)
        self.db.flush()
        return taller

    def update(self, taller: Taller) -> Taller:
        self.db.flush()
        return taller

    def get_metricas(self, taller_id: int) -> dict:
        """
        Retorna conteos operativos del taller en una sola query por tabla.
        Solo devuelve enteros — nunca datos privados de usuarios o tickets.
        """
        from app.modelos.ticket import Ticket
        from app.modelos.user import User

        ahora = datetime.now(timezone.utc)
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        usuarios_activos = (
            self.db.query(func.count(User.id))
            .filter(User.taller_id == taller_id, User.is_active == True)
            .scalar()
        ) or 0

        tickets_historicos = (
            self.db.query(func.count(Ticket.id))
            .filter(Ticket.taller_id == taller_id)
            .scalar()
        ) or 0

        tickets_mes_actual = (
            self.db.query(func.count(Ticket.id))
            .filter(
                Ticket.taller_id == taller_id,
                Ticket.fecha_ingreso >= inicio_mes,
            )
            .scalar()
        ) or 0

        return {
            "usuarios_activos": usuarios_activos,
            "tickets_historicos": tickets_historicos,
            "tickets_mes_actual": tickets_mes_actual,
        }

    def get_metricas_globales(self) -> dict:
        """
        Retorna métricas agregadas de toda la plataforma con GROUP BY estado.
        Una sola operación de base de datos para totales y desglose por estado.
        """
        from app.modelos.user import User

        total_talleres = self.db.query(func.count(Taller.id)).scalar() or 0

        por_estado = (
            self.db.query(Taller.estado, func.count(Taller.id))
            .group_by(Taller.estado)
            .all()
        )

        total_usuarios_activos = (
            self.db.query(func.count(User.id))
            .filter(User.is_active == True)
            .scalar()
        ) or 0

        total_usuarios = (
            self.db.query(func.count(User.id))
            .filter(User.is_active == True)
            .scalar()
        ) or 0

        return {
            "total_talleres": total_talleres,
            "talleres_por_estado": {str(estado): count for estado, count in por_estado},
            "total_usuarios_activos": total_usuarios_activos,
            "total_usuarios": total_usuarios,
        }

    def get_ultimo_acceso(self, taller_id: int) -> datetime | None:
        """
        Retorna el timestamp del último LOGIN exitoso registrado en Audit_Log
        para cualquier usuario del taller.
        """
        from app.modelos.audit_log import AuditLog, AuditAction

        resultado = (
            self.db.query(func.max(AuditLog.timestamp))
            .filter(
                AuditLog.taller_id == taller_id,
                AuditLog.action == AuditAction.LOGIN,
            )
            .scalar()
        )
        return resultado
