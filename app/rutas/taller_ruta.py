"""
Endpoints de gestión de Talleres (tenants).
Solo accesible por SUPER_ADMIN.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.taller_schema import TallerCreate, TallerResponse, TallerUpdate
from app.repositorios.audit_log_repository import AuditLogRepository
from app.repositorios.taller_repository import TallerRepository
from app.seguridad.auth_middleware import require_auth, require_role
from app.servicios.audit_service import AuditService
from app.servicios.taller_service import TallerService

router = APIRouter(prefix="/talleres", tags=["Talleres"])


def get_taller_service(db: Session = Depends(obtener_db)) -> TallerService:
    taller_repo = TallerRepository(db)
    audit_log_repo = AuditLogRepository(db)
    audit_service = AuditService(audit_log_repo)
    return TallerService(taller_repo=taller_repo, audit_service=audit_service, db=db)


@router.post("", response_model=TallerResponse, status_code=status.HTTP_201_CREATED)
@require_auth
@require_role("SUPER_ADMIN")
async def crear_taller(
    request: Request,
    datos: TallerCreate,
    db: Session = Depends(obtener_db),
    taller_service: TallerService = Depends(get_taller_service),
):
    try:
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        taller = taller_service.crear_taller(
            nombre=datos.nombre,
            nit=datos.nit,
            direccion=datos.direccion,
            telefono=datos.telefono,
            created_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        db.refresh(taller)
        return taller
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[TallerResponse])
@require_auth
@require_role("SUPER_ADMIN")
async def listar_talleres(
    request: Request,
    taller_service: TallerService = Depends(get_taller_service),
):
    return taller_service.listar_talleres()


@router.get("/{taller_id}", response_model=TallerResponse)
@require_auth
@require_role("SUPER_ADMIN")
async def obtener_taller(
    request: Request,
    taller_id: int,
    taller_service: TallerService = Depends(get_taller_service),
):
    taller = taller_service.obtener_taller(taller_id)
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    return taller


@router.patch("/{taller_id}", response_model=TallerResponse)
@require_auth
@require_role("SUPER_ADMIN")
async def actualizar_taller(
    request: Request,
    taller_id: int,
    datos: TallerUpdate,
    db: Session = Depends(obtener_db),
    taller_service: TallerService = Depends(get_taller_service),
):
    try:
        current_user = request.state.user
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        if datos.activo is False:
            taller = taller_service.desactivar_taller(
                taller_id=taller_id,
                updated_by=current_user.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        else:
            taller = taller_service.actualizar_taller(
                taller_id=taller_id,
                nombre=datos.nombre,
                nit=datos.nit,
                direccion=datos.direccion,
                telefono=datos.telefono,
                updated_by=current_user.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        db.commit()
        db.refresh(taller)
        return taller
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
