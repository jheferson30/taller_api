"""
Endpoints para consulta de audit log.
Requirements: 15.6
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.repositorios.audit_log_repository import AuditLogRepository
from app.seguridad.auth_middleware import require_role

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


class AuditLogResponse(BaseModel):
    """Schema de respuesta para audit log."""

    id: int
    user_id: int | None
    action: str
    resource_type: str | None
    resource_id: int | None
    ip_address: str
    user_agent: str | None
    details: dict | None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Schema de respuesta para lista de audit logs."""

    logs: list[AuditLogResponse]
    total: int
    skip: int
    limit: int


@router.get("", response_model=AuditLogListResponse)
@require_role("ADMIN")
def get_audit_logs(
    request: Request,
    user_id: int | None = Query(None, description="Filtrar por ID de usuario"),
    action: str | None = Query(None, description="Filtrar por tipo de acción"),
    start_date: datetime | None = Query(None, description="Fecha de inicio (ISO 8601)"),
    end_date: datetime | None = Query(None, description="Fecha de fin (ISO 8601)"),
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(50, ge=1, le=200, description="Número máximo de registros a retornar"),
    db: Session = Depends(obtener_db),
):
    """
    Obtiene logs de auditoría con filtros opcionales.

    Requiere rol ADMIN.

    Filtros disponibles:
    - user_id: Filtrar por usuario específico
    - action: Filtrar por tipo de acción (LOGIN, LOGOUT, etc.)
    - start_date: Fecha de inicio del rango
    - end_date: Fecha de fin del rango

    Soporta paginación con skip y limit.

    Requirements: 15.6
    """
    repo = AuditLogRepository(db)

    # Aplicar filtros según lo especificado
    if user_id is not None:
        logs = repo.get_by_user(user_id, skip=skip, limit=limit)
        # Contar total para este usuario
        total = (
            db.query(
                db.query(db.func.count()).select_from(
                    db.query(db.literal(1))
                    .filter(db.query(db.literal(1)).c.user_id == user_id)
                    .subquery()
                )
            ).scalar()
            or 0
        )
    elif action is not None:
        logs = repo.get_by_action(action, skip=skip, limit=limit)
        # Contar total para esta acción
        from app.modelos.audit_log import AuditLog

        total = db.query(AuditLog).filter(AuditLog.action == action).count()
    elif start_date is not None and end_date is not None:
        logs = repo.get_by_date_range(start_date, end_date, skip=skip, limit=limit)
        # Contar total en este rango
        from sqlalchemy import and_

        from app.modelos.audit_log import AuditLog

        total = (
            db.query(AuditLog)
            .filter(and_(AuditLog.timestamp >= start_date, AuditLog.timestamp <= end_date))
            .count()
        )
    else:
        # Sin filtros, retornar todos los logs
        from app.modelos.audit_log import AuditLog

        logs = (
            db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
        )
        total = db.query(AuditLog).count()

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )
