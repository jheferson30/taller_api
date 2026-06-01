"""
Endpoints REST para notificaciones internas del sistema.

Implementa los endpoints para consultar notificaciones no leídas y marcarlas
como leídas, aplicando aislamiento multi-tenant estricto mediante taller_id del JWT.

Requirements: 4.1, 4.2, 4.5, 5.1, 5.2, 5.3, 9.1, 9.3, 9.4
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.notificacion_schema import (
    NotificacionRespuesta,
    NotificacionesNoLeidasRespuesta,
)
from app.seguridad.auth_middleware import require_auth, require_role
from app.servicios.notificacion_service import NotificacionService

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


def get_notificacion_service(request: Request, db: Session = Depends(obtener_db)) -> NotificacionService:
    """
    Dependency para obtener instancia de NotificacionService.

    Obtiene taller_id del JWT y rechaza SUPER_ADMIN (taller_id = null) con HTTP 403.
    Si el usuario no está autenticado, deja que @require_auth maneje el 401.

    Args:
        request: Request de FastAPI (contiene taller_id en request.state)
        db: Sesión de base de datos

    Returns:
        NotificacionService configurado con taller_id del JWT

    Raises:
        HTTPException 401: Si el usuario no está autenticado (sin JWT)
        HTTPException 403: Si el usuario es SUPER_ADMIN (taller_id = null)
    """
    # Si no hay usuario autenticado, dejar que @require_auth maneje el 401
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    taller_id = request.state.taller_id

    # Rechazar SUPER_ADMIN (taller_id = null) con HTTP 403
    if taller_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los endpoints de notificaciones no están disponibles para SUPER_ADMIN",
        )

    return NotificacionService(db, taller_id)


@router.get(
    "/no-leidas",
    response_model=NotificacionesNoLeidasRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Obtener notificaciones no leídas del usuario",
    description="""
    Obtiene todas las notificaciones no leídas del usuario autenticado.

    **Autenticación requerida:** Sí (Bearer token en Authorization header)
    **Roles permitidos:** ADMIN, MECANICO

    **Proceso:**
    1. Obtiene user_id y taller_id del JWT
    2. Filtra notificaciones por taller_id, user_id y leida=false
    3. Retorna lista de notificaciones + conteo total

    **Seguridad:**
    - Solo retorna notificaciones del taller y usuario del JWT
    - SUPER_ADMIN (taller_id=null) recibe HTTP 403
    - Sin JWT válido retorna HTTP 401

    **Uso típico:**
    - Polling cada 30 segundos desde el frontend para actualizar badge
    - Responde en <300ms bajo carga normal
    """,
    responses={
        200: {
            "description": "Lista de notificaciones no leídas",
            "content": {
                "application/json": {
                    "example": {
                        "total": 2,
                        "notificaciones": [
                            {
                                "id": 1,
                                "tipo": "TICKET_ASIGNADO",
                                "titulo": "Ticket asignado",
                                "mensaje": "Se te ha asignado el ticket #T-001",
                                "leida": False,
                                "fecha_creacion": "2026-04-15T10:30:00Z",
                                "referencia_id": 123,
                            },
                            {
                                "id": 2,
                                "tipo": "RENOVACION_PLAN",
                                "titulo": "Renovación de plan requerida",
                                "mensaje": "Tu plan vence en 2 día(s). Renueva para continuar usando el servicio.",
                                "leida": False,
                                "fecha_creacion": "2026-04-15T08:00:00Z",
                                "referencia_id": 5,
                            },
                        ],
                    }
                }
            },
        },
        401: {
            "description": "No autenticado o token inválido",
            "content": {
                "application/json": {
                    "example": {"detail": "Authentication required"}
                }
            },
        },
        403: {
            "description": "SUPER_ADMIN no puede acceder a notificaciones",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Los endpoints de notificaciones no están disponibles para SUPER_ADMIN"
                    }
                }
            },
        },
    },
)
@require_auth
@require_role("ADMIN", "MECANICO", "RECEPCIONISTA")
async def obtener_no_leidas(
    request: Request,
    notificacion_service: NotificacionService = Depends(get_notificacion_service),
):
    """
    Obtiene todas las notificaciones no leídas del usuario autenticado.

    Protegido con @require_auth y @require_role("ADMIN", "MECANICO", "RECEPCIONISTA").
    Rechaza SUPER_ADMIN (taller_id=null) con HTTP 403.

    Args:
        request: Request de FastAPI (contiene user autenticado)
        notificacion_service: Servicio de notificaciones

    Returns:
        NotificacionesNoLeidasRespuesta con total y lista de notificaciones

    Raises:
        HTTPException 401: Si no está autenticado
        HTTPException 403: Si es SUPER_ADMIN o no tiene rol ADMIN/MECANICO
    """
    user = request.state.user
    resultado = notificacion_service.obtener_no_leidas(user.id)

    return NotificacionesNoLeidasRespuesta(
        total=resultado["total"],
        notificaciones=resultado["notificaciones"],
    )


@router.get(
    "/todas",
    response_model=NotificacionesNoLeidasRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Obtener todas las notificaciones del usuario",
    description="""
    Obtiene TODAS las notificaciones del usuario autenticado (leídas y no leídas).

    **Autenticación requerida:** Sí (Bearer token en Authorization header)
    **Roles permitidos:** ADMIN, MECANICO

    **Proceso:**
    1. Obtiene user_id y taller_id del JWT
    2. Filtra notificaciones por taller_id y user_id (sin filtro de leida)
    3. Retorna lista completa de notificaciones + conteo total

    **Seguridad:**
    - Solo retorna notificaciones del taller y usuario del JWT
    - SUPER_ADMIN (taller_id=null) recibe HTTP 403
    - Sin JWT válido retorna HTTP 401

    **Uso típico:**
    - Mostrar historial completo de notificaciones en dropdown
    - Estilo Facebook: badge muestra no leídas, dropdown muestra todas
    """,
    responses={
        200: {
            "description": "Lista de todas las notificaciones",
            "content": {
                "application/json": {
                    "example": {
                        "total": 5,
                        "notificaciones": [
                            {
                                "id": 1,
                                "tipo": "TICKET_ASIGNADO",
                                "titulo": "Ticket asignado",
                                "mensaje": "Se te ha asignado el ticket #T-001",
                                "leida": True,
                                "fecha_creacion": "2026-04-15T10:30:00Z",
                                "referencia_id": 123,
                            },
                            {
                                "id": 2,
                                "tipo": "RENOVACION_PLAN",
                                "titulo": "Renovación de plan requerida",
                                "mensaje": "Tu plan vence en 2 día(s). Renueva para continuar usando el servicio.",
                                "leida": False,
                                "fecha_creacion": "2026-04-15T08:00:00Z",
                                "referencia_id": 5,
                            },
                        ],
                    }
                }
            },
        },
        401: {
            "description": "No autenticado o token inválido",
            "content": {
                "application/json": {
                    "example": {"detail": "Authentication required"}
                }
            },
        },
        403: {
            "description": "SUPER_ADMIN no puede acceder a notificaciones",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Los endpoints de notificaciones no están disponibles para SUPER_ADMIN"
                    }
                }
            },
        },
    },
)
@require_auth
@require_role("ADMIN", "MECANICO", "RECEPCIONISTA")
async def obtener_todas(
    request: Request,
    notificacion_service: NotificacionService = Depends(get_notificacion_service),
):
    """
    Obtiene TODAS las notificaciones del usuario autenticado (leídas y no leídas).

    Protegido con @require_auth y @require_role("ADMIN", "MECANICO", "RECEPCIONISTA").
    Rechaza SUPER_ADMIN (taller_id=null) con HTTP 403.

    Args:
        request: Request de FastAPI (contiene user autenticado)
        notificacion_service: Servicio de notificaciones

    Returns:
        NotificacionesNoLeidasRespuesta con total y lista de notificaciones

    Raises:
        HTTPException 401: Si no está autenticado
        HTTPException 403: Si es SUPER_ADMIN o no tiene rol ADMIN/MECANICO
    """
    user = request.state.user
    resultado = notificacion_service.obtener_todas(user.id)

    return NotificacionesNoLeidasRespuesta(
        total=resultado["total"],
        notificaciones=resultado["notificaciones"],
    )


@router.patch(
    "/{id}/leer",
    response_model=NotificacionRespuesta,
    status_code=status.HTTP_200_OK,
    summary="Marcar una notificación como leída",
    description="""
    Marca una notificación específica como leída.

    **Autenticación requerida:** Sí (Bearer token en Authorization header)
    **Roles permitidos:** ADMIN, MECANICO

    **Proceso:**
    1. Obtiene user_id y taller_id del JWT
    2. Verifica que la notificación pertenezca al usuario y taller del JWT
    3. Marca la notificación como leida=true
    4. Retorna la notificación actualizada

    **Seguridad:**
    - Solo puede marcar notificaciones propias del mismo taller
    - Retorna HTTP 404 si la notificación no pertenece al usuario/taller
    - HTTP 404 (no 403) para no revelar existencia de recursos ajenos
    - SUPER_ADMIN (taller_id=null) recibe HTTP 403

    **Uso típico:**
    - Al hacer clic en una notificación en la UI
    - Al cerrar un banner de notificación
    """,
    responses={
        200: {
            "description": "Notificación marcada como leída",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "tipo": "TICKET_ASIGNADO",
                        "titulo": "Ticket asignado",
                        "mensaje": "Se te ha asignado el ticket #T-001",
                        "leida": True,
                        "fecha_creacion": "2026-04-15T10:30:00Z",
                        "referencia_id": 123,
                    }
                }
            },
        },
        401: {
            "description": "No autenticado o token inválido",
            "content": {
                "application/json": {
                    "example": {"detail": "Authentication required"}
                }
            },
        },
        403: {
            "description": "SUPER_ADMIN no puede acceder a notificaciones",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Los endpoints de notificaciones no están disponibles para SUPER_ADMIN"
                    }
                }
            },
        },
        404: {
            "description": "Notificación no encontrada o no pertenece al usuario/taller",
            "content": {
                "application/json": {
                    "example": {"detail": "Notificación no encontrada"}
                }
            },
        },
    },
)
@require_auth
@require_role("ADMIN", "MECANICO", "RECEPCIONISTA")
async def marcar_como_leida(
    id: int,
    request: Request,
    notificacion_service: NotificacionService = Depends(get_notificacion_service),
):
    """
    Marca una notificación como leída.

    Protegido con @require_auth y @require_role("ADMIN", "MECANICO", "RECEPCIONISTA").
    Rechaza SUPER_ADMIN (taller_id=null) con HTTP 403.

    Args:
        id: ID de la notificación a marcar como leída
        request: Request de FastAPI (contiene user autenticado)
        notificacion_service: Servicio de notificaciones

    Returns:
        NotificacionRespuesta con la notificación actualizada

    Raises:
        HTTPException 401: Si no está autenticado
        HTTPException 403: Si es SUPER_ADMIN o no tiene rol ADMIN/MECANICO
        HTTPException 404: Si la notificación no pertenece al usuario/taller
    """
    user = request.state.user
    notificacion = notificacion_service.marcar_como_leida(id, user.id)

    return NotificacionRespuesta.model_validate(notificacion)


@router.patch(
    "/leer-todas",
    status_code=status.HTTP_200_OK,
    summary="Marcar todas las notificaciones como leídas",
    description="""
    Marca todas las notificaciones no leídas del usuario como leídas.

    **Autenticación requerida:** Sí (Bearer token en Authorization header)
    **Roles permitidos:** ADMIN, MECANICO

    **Proceso:**
    1. Obtiene user_id y taller_id del JWT
    2. Marca todas las notificaciones no leídas del usuario como leida=true
    3. Retorna el número de notificaciones marcadas

    **Seguridad:**
    - Solo marca notificaciones del usuario y taller del JWT
    - No afecta notificaciones de otros usuarios del mismo taller
    - SUPER_ADMIN (taller_id=null) recibe HTTP 403

    **Uso típico:**
    - Botón "Marcar todas como leídas" en la UI
    - Limpiar badge de notificaciones
    """,
    responses={
        200: {
            "description": "Notificaciones marcadas como leídas",
            "content": {
                "application/json": {
                    "example": {"marcadas": 5}
                }
            },
        },
        401: {
            "description": "No autenticado o token inválido",
            "content": {
                "application/json": {
                    "example": {"detail": "Authentication required"}
                }
            },
        },
        403: {
            "description": "SUPER_ADMIN no puede acceder a notificaciones",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Los endpoints de notificaciones no están disponibles para SUPER_ADMIN"
                    }
                }
            },
        },
    },
)
@require_auth
@require_role("ADMIN", "MECANICO", "RECEPCIONISTA")
async def marcar_todas_como_leidas(
    request: Request,
    notificacion_service: NotificacionService = Depends(get_notificacion_service),
):
    """
    Marca todas las notificaciones no leídas del usuario como leídas.

    Protegido con @require_auth y @require_role("ADMIN", "MECANICO", "RECEPCIONISTA").
    Rechaza SUPER_ADMIN (taller_id=null) con HTTP 403.

    Args:
        request: Request de FastAPI (contiene user autenticado)
        notificacion_service: Servicio de notificaciones

    Returns:
        Dict con el número de notificaciones marcadas

    Raises:
        HTTPException 401: Si no está autenticado
        HTTPException 403: Si es SUPER_ADMIN o no tiene rol ADMIN/MECANICO
    """
    user = request.state.user
    marcadas = notificacion_service.marcar_todas_como_leidas(user.id)

    return {"marcadas": marcadas}


@router.delete(
    "/limpiar-leidas",
    status_code=status.HTTP_200_OK,
    summary="Limpiar notificaciones leídas (solo ADMIN)",
    description="""
    Elimina todas las notificaciones leídas del taller actual.

    **Autenticación requerida:** Sí (Bearer token en Authorization header)
    **Roles permitidos:** ADMIN

    **Proceso:**
    1. Obtiene taller_id del JWT
    2. Elimina todas las notificaciones con leida=true del taller
    3. Retorna el número de notificaciones eliminadas

    **Seguridad:**
    - Solo elimina notificaciones del taller del JWT
    - Solo ADMIN puede ejecutar esta acción
    - Las notificaciones NO leídas se preservan
    - SUPER_ADMIN (taller_id=null) recibe HTTP 403

    **Uso típico:**
    - Limpieza manual del historial de notificaciones
    - Testing del job de limpieza automática
    - Mantenimiento del sistema

    **Nota:** Este endpoint ejecuta manualmente la misma limpieza que el job
    nocturno automático (00:00). Útil para testing o limpieza bajo demanda.
    """,
    responses={
        200: {
            "description": "Notificaciones eliminadas",
            "content": {
                "application/json": {
                    "example": {"eliminadas": 15}
                }
            },
        },
        401: {
            "description": "No autenticado o token inválido",
            "content": {
                "application/json": {
                    "example": {"detail": "Authentication required"}
                }
            },
        },
        403: {
            "description": "SUPER_ADMIN o usuario sin rol ADMIN",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Los endpoints de notificaciones no están disponibles para SUPER_ADMIN"
                    }
                }
            },
        },
    },
)
@require_auth
@require_role("ADMIN")
async def limpiar_notificaciones_leidas(
    request: Request,
    notificacion_service: NotificacionService = Depends(get_notificacion_service),
):
    """
    Elimina todas las notificaciones leídas del taller actual.

    Protegido con @require_auth y @require_role("ADMIN").
    Rechaza SUPER_ADMIN (taller_id=null) con HTTP 403.

    Args:
        request: Request de FastAPI (contiene user autenticado)
        notificacion_service: Servicio de notificaciones

    Returns:
        Dict con el número de notificaciones eliminadas

    Raises:
        HTTPException 401: Si no está autenticado
        HTTPException 403: Si es SUPER_ADMIN o no tiene rol ADMIN
    """
    eliminadas = notificacion_service.limpiar_leidas()

    return {"eliminadas": eliminadas}
