"""
Router del SUPER_ADMIN — Panel de administración de la plataforma SaaS.

Todos los endpoints están protegidos con @require_role("SUPER_ADMIN").
El SUPER_ADMIN no accede a datos operativos de talleres (tickets, vehículos, caja).
Solo gestiona talleres, usuarios, métricas agregadas y configuración de plataforma.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.taller_schema import (
    BloqueoEmergenciaRequest,
    CambiarEstadoRequest,
    CrearAdminTallerRequest,
    EstadoTallerEnum,
    MetricasGlobalesResponse,
    NotificacionMasivaRequest,
    NotificacionMasivaResponse,
    TallerCreate,
    TallerMetricasResponse,
    TallerRecursosResponse,
    TallerResponse,
    TallerUpdate,
)
from app.repositorios.audit_log_repository import AuditLogRepository
from app.repositorios.role_repository import RoleRepository
from app.repositorios.taller_repository import TallerRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.user_repository import UserRepository
from app.esquemas.user_schema import ChangePasswordRequest
from app.seguridad.auth_middleware import require_role
from app.seguridad.password_hasher import PasswordHasher
from app.servicios.audit_service import AuditService
from app.servicios.user_service import UserService, ValidationError
from app.servicios.taller_service import TallerService
from app.modelos.user import User
from app.utils.upload_utils import get_upload_path

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])


def _get_taller_service(db: Session) -> TallerService:
    """Factory para TallerService con dependencias."""
    from app.repositorios.audit_log_repository import AuditLogRepository
    taller_repo = TallerRepository(db)
    audit_repo = AuditLogRepository(db)
    audit_service = AuditService(audit_repo)
    return TallerService(taller_repo, audit_service, db)


def _get_ip(request: Request) -> str:
    """Obtiene la IP del cliente de forma segura."""
    return request.client.host if request.client else "unknown"


# ============================================================================
# Gestión de talleres
# ============================================================================


@router.get("/talleres", response_model=list[TallerResponse])
@require_role("SUPER_ADMIN")
async def listar_talleres(
    request: Request,
    db: Session = Depends(obtener_db),
):
    """Lista todos los talleres de la plataforma con métricas básicas."""
    service = _get_taller_service(db)
    talleres = service.listar_talleres()

    resultado = []
    for taller in talleres:
        taller_dict = TallerResponse.model_validate(taller).model_dump()
        if taller.estado == EstadoTallerEnum.TRIAL and taller.fecha_inicio_trial and taller.dias_trial:
            ahora = datetime.now(taller.fecha_inicio_trial.tzinfo)
            fecha_fin = taller.fecha_inicio_trial + timedelta(days=taller.dias_trial)
            taller_dict["dias_restantes_trial"] = max(0, (fecha_fin - ahora).days)
        else:
            taller_dict["dias_restantes_trial"] = None
        resultado.append(TallerResponse(**taller_dict))

    return resultado


@router.post("/talleres", response_model=TallerResponse, status_code=201)
@require_role("SUPER_ADMIN")
async def crear_taller(
    request: Request,
    datos: TallerCreate,
    db: Session = Depends(obtener_db),
):
    """Crea un nuevo taller. Inicia en estado TRIAL con fecha_inicio_trial = NOW()."""
    service = _get_taller_service(db)
    try:
        taller = service.crear_taller(
            nombre=datos.nombre,
            nit=datos.nit,
            direccion=datos.direccion,
            telefono=datos.telefono,
            dias_trial=datos.dias_trial,
            created_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return TallerResponse.model_validate(taller)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/talleres/{taller_id}", response_model=TallerResponse)
@require_role("SUPER_ADMIN")
async def obtener_taller(
    request: Request,
    taller_id: int,
    db: Session = Depends(obtener_db),
):
    """Obtiene el detalle completo de un taller."""
    service = _get_taller_service(db)
    taller = service.obtener_taller(taller_id)
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")

    taller_dict = TallerResponse.model_validate(taller).model_dump()
    if taller.estado == EstadoTallerEnum.TRIAL and taller.fecha_inicio_trial and taller.dias_trial:
        ahora = datetime.now(taller.fecha_inicio_trial.tzinfo)
        fecha_fin = taller.fecha_inicio_trial + timedelta(days=taller.dias_trial)
        taller_dict["dias_restantes_trial"] = max(0, (fecha_fin - ahora).days)
    else:
        taller_dict["dias_restantes_trial"] = None

    return TallerResponse(**taller_dict)


@router.patch("/talleres/{taller_id}", response_model=TallerResponse)
@require_role("SUPER_ADMIN")
async def actualizar_taller(
    request: Request,
    taller_id: int,
    datos: TallerUpdate,
    db: Session = Depends(obtener_db),
):
    """Actualiza datos de un taller (actualización parcial)."""
    service = _get_taller_service(db)
    try:
        taller = service.actualizar_taller(
            taller_id=taller_id,
            nombre=datos.nombre,
            nit=datos.nit,
            direccion=datos.direccion,
            telefono=datos.telefono,
            updated_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return TallerResponse.model_validate(taller)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/talleres/{taller_id}/estado", response_model=TallerResponse)
@require_role("SUPER_ADMIN")
async def cambiar_estado_taller(
    request: Request,
    taller_id: int,
    body: CambiarEstadoRequest,
    db: Session = Depends(obtener_db),
):
    """Cambia el estado del taller (TRIAL → ACTIVO → SUSPENDIDO → CANCELADO)."""
    service = _get_taller_service(db)
    try:
        taller = service.cambiar_estado(
            taller_id=taller_id,
            nuevo_estado=body.estado,
            updated_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return TallerResponse.model_validate(taller)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Onboarding de nuevo cliente
# ============================================================================


@router.get("/talleres/{taller_id}/usuarios")
@require_role("SUPER_ADMIN")
async def listar_usuarios_taller(
    request: Request,
    taller_id: int,
    db: Session = Depends(obtener_db),
):
    """Lista todos los usuarios de un taller."""
    usuarios = db.query(User).filter(
        User.taller_id == taller_id,
        User.is_active == True,
    ).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "nombre_completo": u.nombre_completo,
            "roles": [r.name for r in u.roles],
            "is_active": u.is_active,
        }
        for u in usuarios
    ]


@router.post("/talleres/{taller_id}/usuarios", status_code=201)
@require_role("SUPER_ADMIN")
async def crear_admin_taller(
    request: Request,
    taller_id: int,
    datos: CrearAdminTallerRequest,
    db: Session = Depends(obtener_db),
):
    """Crea el primer usuario ADMIN de un taller. El taller_id viene del path."""
    service = _get_taller_service(db)
    try:
        usuario = service.crear_admin_taller(
            taller_id=taller_id,
            username=datos.username,
            email=datos.email,
            password=datos.password,
            nombre_completo=datos.nombre_completo,
            created_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return {
            "id": usuario.id,
            "username": usuario.username,
            "email": usuario.email,
            "taller_id": usuario.taller_id,
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/talleres/{taller_id}/logo")
@require_role("SUPER_ADMIN")
async def subir_logo_taller(
    request: Request,
    taller_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(obtener_db),
):
    """Sube el logo de un taller. Almacena en uploads/talleres/{taller_id}/logos/"""
    import os
    import uuid
    from app.modelos.configuracion_taller import ConfiguracionTaller

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=400,
            detail="Formato de imagen no permitido. Use jpg, jpeg, png o webp",
        )

    service = _get_taller_service(db)
    taller = service.obtener_taller(taller_id)
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")

    logo_dir = get_upload_path(taller_id, "logos")
    filename = f"logo_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(logo_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    logo_url = f"/uploads/talleres/{taller_id}/logos/{filename}"
    config = db.query(ConfiguracionTaller).filter(ConfiguracionTaller.taller_id == taller_id).first()
    if config:
        config.logo_url = logo_url
        db.commit()

    return {"logo_url": logo_url}


# ============================================================================
# Métricas
# ============================================================================


@router.get("/talleres/{taller_id}/metricas", response_model=TallerMetricasResponse)
@require_role("SUPER_ADMIN")
async def obtener_metricas_taller(
    request: Request,
    taller_id: int,
    db: Session = Depends(obtener_db),
):
    """Retorna métricas operativas del taller (solo conteos, sin datos privados)."""
    service = _get_taller_service(db)
    try:
        metricas = service.obtener_metricas(taller_id)
        return TallerMetricasResponse(**metricas)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/metricas/global", response_model=MetricasGlobalesResponse)
@require_role("SUPER_ADMIN")
async def obtener_metricas_globales(
    request: Request,
    db: Session = Depends(obtener_db),
):
    """Retorna métricas agregadas de toda la plataforma."""
    service = _get_taller_service(db)
    metricas = service.obtener_metricas_globales()
    return MetricasGlobalesResponse(**metricas)


# ============================================================================
# Recursos
# ============================================================================


@router.get("/talleres/{taller_id}/recursos", response_model=TallerRecursosResponse)
@require_role("SUPER_ADMIN")
async def obtener_recursos_taller(
    request: Request,
    taller_id: int,
    db: Session = Depends(obtener_db),
):
    """Retorna uso de almacenamiento y tickets del mes vs límite del plan."""
    service = _get_taller_service(db)
    try:
        recursos = service.obtener_recursos(taller_id)
        return TallerRecursosResponse(**recursos)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Gestión de usuarios por taller
# ============================================================================


@router.post("/talleres/{taller_id}/usuarios/{usuario_id}/reset-password")
@require_role("SUPER_ADMIN")
async def forzar_reset_password(
    request: Request,
    taller_id: int,
    usuario_id: int,
    db: Session = Depends(obtener_db),
):
    """Invalida tokens del usuario y genera token de reset de 24h."""
    service = _get_taller_service(db)
    try:
        token = service.forzar_reset_password(
            taller_id=taller_id,
            usuario_id=usuario_id,
            updated_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return {"reset_token": token, "expires_in_hours": 24}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/talleres/{taller_id}/reset-passwords")
@require_role("SUPER_ADMIN")
async def forzar_reset_password_masivo(
    request: Request,
    taller_id: int,
    db: Session = Depends(obtener_db),
):
    """Invalida tokens de todos los usuarios del taller."""
    service = _get_taller_service(db)
    try:
        cantidad = service.forzar_reset_password_masivo(
            taller_id=taller_id,
            updated_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return {"usuarios_afectados": cantidad}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Bloqueo de emergencia
# ============================================================================


@router.post("/talleres/{taller_id}/bloqueo-emergencia", response_model=TallerResponse)
@require_role("SUPER_ADMIN")
async def activar_bloqueo_emergencia(
    request: Request,
    taller_id: int,
    datos: BloqueoEmergenciaRequest,
    db: Session = Depends(obtener_db),
):
    """Bloqueo inmediato por seguridad. Invalida todos los tokens del taller."""
    service = _get_taller_service(db)
    try:
        taller = service.activar_bloqueo_emergencia(
            taller_id=taller_id,
            motivo=datos.motivo,
            updated_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return TallerResponse.model_validate(taller)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/talleres/{taller_id}/bloqueo-emergencia", response_model=TallerResponse)
@require_role("SUPER_ADMIN")
async def levantar_bloqueo_emergencia(
    request: Request,
    taller_id: int,
    db: Session = Depends(obtener_db),
):
    """Levanta el bloqueo de emergencia del taller."""
    service = _get_taller_service(db)
    try:
        taller = service.levantar_bloqueo_emergencia(
            taller_id=taller_id,
            updated_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return TallerResponse.model_validate(taller)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Seguridad
# ============================================================================


@router.get("/talleres/{taller_id}/seguridad/intentos-fallidos")
@require_role("SUPER_ADMIN")
async def obtener_intentos_fallidos(
    request: Request,
    taller_id: int,
    desde: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(obtener_db),
):
    """Retorna intentos de login fallidos del taller desde Audit_Log."""
    service = _get_taller_service(db)
    registros = service.obtener_intentos_fallidos(
        taller_id=taller_id,
        desde=desde,
        page=page,
        page_size=page_size,
    )
    return {
        "taller_id": taller_id,
        "page": page,
        "page_size": page_size,
        "registros": [
            {
                "timestamp": r.timestamp,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "details": r.details,
            }
            for r in registros
        ],
    }


# ============================================================================
# Auditoría global
# ============================================================================


@router.get("/auditoria")
@require_role("SUPER_ADMIN")
async def obtener_auditoria_global(
    request: Request,
    taller_id: int | None = None,
    user_id: int | None = None,
    accion: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(obtener_db),
):
    """Auditoría cruzada global con filtros opcionales. Máximo 100 por página."""
    service = _get_taller_service(db)
    try:
        registros = service.obtener_auditoria_global(
            taller_id=taller_id,
            user_id=user_id,
            accion=accion,
            desde=desde,
            hasta=hasta,
            page=page,
            page_size=min(page_size, 100),
        )
        return {
            "page": page,
            "page_size": page_size,
            "filtros": {
                "taller_id": taller_id,
                "user_id": user_id,
                "accion": accion,
                "desde": desde,
                "hasta": hasta,
            },
            "registros": [
                {
                    "id": r.id,
                    "timestamp": r.timestamp,
                    "taller_id": r.taller_id,
                    "user_id": r.user_id,
                    "action": r.action,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "ip_address": r.ip_address,
                    "details": r.details,
                }
                for r in registros
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Notificaciones masivas
# ============================================================================


@router.post("/notificaciones/masivas", response_model=NotificacionMasivaResponse, status_code=201)
@require_role("SUPER_ADMIN")
async def enviar_notificacion_masiva(
    request: Request,
    datos: NotificacionMasivaRequest,
    db: Session = Depends(obtener_db),
):
    """
    Envía una notificación masiva a usuarios de talleres.

    **Autenticación requerida:** Sí (Bearer token)
    **Rol requerido:** SUPER_ADMIN

    **Parámetros:**
    - titulo: Título de la notificación (5-200 caracteres)
    - mensaje: Mensaje de la notificación (10-500 caracteres)
    - solo_admins: Si True, solo envía a usuarios ADMIN. Si False, a todos los usuarios activos
    - talleres_ids: Lista de IDs de talleres específicos. Si None, envía a todos los talleres activos

    **Proceso:**
    1. Filtra talleres activos (opcionalmente por IDs específicos)
    2. Filtra usuarios activos de esos talleres (opcionalmente solo ADMIN)
    3. Crea una notificación para cada usuario
    4. Registra la acción en audit log

    **Casos de uso:**
    - Anuncio de mantenimiento programado
    - Nuevas funcionalidades de la plataforma
    - Cambios en términos de servicio
    - Alertas de seguridad
    - Recordatorios de renovación

    **Seguridad:**
    - Solo SUPER_ADMIN puede enviar notificaciones masivas
    - Las notificaciones se crean con tipo MENSAJE_PLATAFORMA
    - Se registra en audit log con detalles completos
    - Los usuarios las verán en su campanita de notificaciones

    **Ejemplo de uso:**
    ```json
    {
      "titulo": "Mantenimiento programado",
      "mensaje": "El sistema estará en mantenimiento el 15 de mayo de 2:00 AM a 4:00 AM. Disculpe las molestias.",
      "solo_admins": true,
      "talleres_ids": null
    }
    ```
    """
    service = _get_taller_service(db)
    try:
        resultado = service.enviar_notificacion_masiva(
            titulo=datos.titulo,
            mensaje=datos.mensaje,
            solo_admins=datos.solo_admins,
            talleres_ids=datos.talleres_ids,
            created_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.commit()
        return NotificacionMasivaResponse(**resultado)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/talleres/{taller_id}/importar-bd", status_code=200)
@require_role("SUPER_ADMIN")
async def importar_bd_taller(
    request: Request,
    taller_id: int,
    archivo_sql: UploadFile = File(...),
    db: Session = Depends(obtener_db),
):
    """
    Importa datos desde un archivo SQL (backup mono-tenant) al taller.
    
    El archivo SQL debe ser un backup de una BD mono-tenant (sin taller_id).
    Este endpoint:
    1. Sube el archivo SQL
    2. Crea una BD temporal
    3. Restaura el backup en la BD temporal
    4. Migra los datos agregando taller_id automáticamente
    5. Elimina la BD temporal
    
    Formatos soportados: .sql, .dump
    """
    import os
    import tempfile
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Validar formato de archivo
    if not archivo_sql.filename.endswith(('.sql', '.dump')):
        raise HTTPException(
            status_code=400,
            detail="Formato de archivo no soportado. Use .sql o .dump"
        )
    
    # Verificar que el taller existe
    service = _get_taller_service(db)
    taller = service.obtener_taller(taller_id)
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    
    temp_file_path = None
    temp_dir = None
    
    # Guardar archivo temporalmente
    try:
        logger.info(f"[IMPORTAR] Iniciando importación para taller {taller_id}, archivo: {archivo_sql.filename}")
        
        # Crear directorio temporal
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, archivo_sql.filename)
        
        logger.info(f"[IMPORTAR] Guardando archivo en: {temp_file_path}")
        
        # Guardar archivo
        with open(temp_file_path, 'wb') as f:
            contenido = await archivo_sql.read()
            f.write(contenido)
        
        logger.info(f"[IMPORTAR] Archivo guardado, tamaño: {len(contenido)} bytes")
        logger.info(f"[IMPORTAR] Ejecutando importación...")
        
        # Ejecutar importación
        resultado = service.importar_bd_desde_sql(
            taller_id=taller_id,
            sql_file_path=temp_file_path,
            created_by=request.state.user.id,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        
        logger.info(f"[IMPORTAR] Importación completada: {resultado}")
        
        db.commit()
        
        return {
            "mensaje": "Importación completada exitosamente",
            "taller_id": taller_id,
            "taller_nombre": taller.nombre,
            "archivo": archivo_sql.filename,
            "estadisticas": resultado,
        }
        
    except ValueError as e:
        logger.error(f"[IMPORTAR] ValueError: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[IMPORTAR] Exception: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al importar BD: {str(e)}"
        )
    finally:
        # Limpiar archivo temporal
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"[IMPORTAR] Archivo temporal eliminado: {temp_file_path}")
            if temp_dir and os.path.exists(temp_dir):
                os.rmdir(temp_dir)
                logger.info(f"[IMPORTAR] Directorio temporal eliminado: {temp_dir}")
        except Exception as cleanup_error:
            logger.warning(f"[IMPORTAR] Error al limpiar archivos temporales: {cleanup_error}")


# ============================================================================
# Mi cuenta — SUPER_ADMIN
# ============================================================================


def _get_user_service(db: Session) -> UserService:
    """Factory para UserService con dependencias."""
    return UserService(
        user_repo=UserRepository(db),
        role_repo=RoleRepository(db),
        token_blacklist_repo=TokenBlacklistRepository(db),
        password_hasher=PasswordHasher(),
        audit_service=AuditService(AuditLogRepository(db)),
        db=db,
    )


@router.patch("/mi-cuenta/password", status_code=200)
@require_role("SUPER_ADMIN")
async def cambiar_password_super_admin(
    request: Request,
    datos: ChangePasswordRequest,
    db: Session = Depends(obtener_db),
):
    """
    Cambia la contraseña del SUPER_ADMIN autenticado.

    Requiere la contraseña actual para confirmar la identidad antes de
    permitir el cambio. Registra el evento en el audit log.

    - **current_password**: Contraseña actual
    - **new_password**: Nueva contraseña (mínimo 8 caracteres, mayúscula, minúscula y número)
    """
    user_service = _get_user_service(db)
    try:
        user_service.change_password(
            user_id=request.state.user.id,
            current_password=datos.current_password,
            new_password=datos.new_password,
            ip_address=_get_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        return {"mensaje": "Contraseña actualizada correctamente"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
