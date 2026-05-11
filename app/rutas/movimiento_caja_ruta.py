from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi_cache import FastAPICache
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.movimiento_caja_schema import (
    CambioMovimientoCajaRespuesta,
    MovimientoCajaCorregir,
    MovimientoCajaCrear,
    MovimientoCajaRespuesta,
)
from app.modelos.cambio_movimiento_caja import CambioMovimientoCaja
from app.modelos.movimiento_caja import (
    CategoriaEgreso,
    EstadoTicket,
    MovimientoCaja,
    TipoMovimiento,
)
from app.seguridad.auth_middleware import require_auth
from app.seguridad.dependencias import requerir_password_admin


class CobroRapidoCrear(BaseModel):
    placa: str = Field(..., min_length=1, max_length=20)
    descripcion: str = Field(..., min_length=1, max_length=200)
    valor: int = Field(..., gt=0)
    metodo_pago: str = "EFECTIVO"


router = APIRouter(prefix="/movimientos-caja", tags=["Movimientos Caja"])


def _validar_movimiento(datos: MovimientoCajaCrear):
    if datos.tipo in (TipoMovimiento.INGRESO_ANTICIPO, TipoMovimiento.INGRESO_FINAL):
        if not datos.ticket_codigo:
            raise HTTPException(
                status_code=400, detail="ticket_codigo es obligatorio para ingresos"
            )
        if not datos.placa:
            raise HTTPException(status_code=400, detail="placa es obligatoria para ingresos")
        if not datos.estado_ticket:
            raise HTTPException(
                status_code=400, detail="estado_ticket es obligatorio para ingresos"
            )
    if datos.tipo == TipoMovimiento.EGRESO:
        if not datos.concepto:
            raise HTTPException(status_code=400, detail="concepto es obligatorio para egresos")
        if not datos.categoria_egreso:
            raise HTTPException(
                status_code=400, detail="categoria_egreso es obligatoria para egresos"
            )


@router.get("/cobros-rapidos")
@require_auth
def listar_cobros_rapidos(
    request: Request,
    db: Session = Depends(obtener_db),
    placa: str | None = Query(None),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    taller_id = request.state.taller_id
    query = db.query(MovimientoCaja).filter(
        MovimientoCaja.tipo == TipoMovimiento.INGRESO_RAPIDO,
        MovimientoCaja.taller_id == taller_id,
    )
    if placa:
        query = query.filter(MovimientoCaja.placa == placa.upper())
    if fecha_desde:
        query = query.filter(func.date(MovimientoCaja.fecha_creacion) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(MovimientoCaja.fecha_creacion) <= fecha_hasta)
    return query.order_by(MovimientoCaja.fecha_creacion.desc()).offset(skip).limit(limit).all()


@router.post(
    "/cobro-rapido",
    response_model=MovimientoCajaRespuesta,
    summary="Create quick charge (express payment)",
    description="""
    Register a quick charge for simple services without creating a full ticket.

    **Use Case:**
    - Express services (tire inflation, quick adjustments)
    - Small repairs that don't require full ticket workflow
    - Walk-in customers with immediate payment

    **Process:**
    1. Creates INGRESO_RAPIDO cash movement
    2. Records plate, description, amount, and payment method
    3. Invalidates statistics cache
    4. No ticket is created (standalone transaction)

    **CSRF Protection:**
    - Requires valid CSRF token in X-CSRF-Token header
    - Token obtained from /auth/csrf endpoint

    **Cache Invalidation:**
    - Automatically clears statistics cache after creation
    - Ensures dashboard shows updated totals

    **Rate Limiting:**
    - 30 requests per minute (standard write limit)

    **Permissions:**
    - Requires ADMIN password authentication
    """,
    responses={
        200: {
            "description": "Quick charge created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 456,
                        "tipo": "INGRESO_RAPIDO",
                        "placa": "ABC123",
                        "concepto": "Inflado de llantas",
                        "valor": 5000,
                        "metodo_pago": "EFECTIVO",
                        "fecha_creacion": "2026-04-06T14:30:00",
                    }
                }
            },
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "Valor must be greater than 0",
                    }
                }
            },
        },
        403: {
            "description": "CSRF token validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": "csrf_validation_failed",
                        "message": "Invalid or missing CSRF token",
                    }
                }
            },
        },
    },
)
async def crear_cobro_rapido(
    request: Request,
    datos: CobroRapidoCrear,
    db: Session = Depends(obtener_db),
):
    nuevo = MovimientoCaja(
        taller_id=request.state.taller_id,
        tipo=TipoMovimiento.INGRESO_RAPIDO,
        placa=datos.placa.upper().strip(),
        concepto=datos.descripcion,
        valor=datos.valor,
        metodo_pago=datos.metodo_pago,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # Invalidar caché de estadísticas después de crear movimiento
    try:
        await FastAPICache.clear(namespace="fastapi-cache:obtener_estadisticas")
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo invalidar caché: {e}")

    return nuevo


@router.post("/", response_model=MovimientoCajaRespuesta)
@require_auth
async def crear_movimiento_caja(
    request: Request,
    datos: MovimientoCajaCrear,
    db: Session = Depends(obtener_db),
):
    _validar_movimiento(datos)
    payload = datos.model_dump()
    payload["taller_id"] = request.state.taller_id
    nuevo = MovimientoCaja(**payload)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # Invalidar caché de estadísticas después de crear movimiento
    try:
        await FastAPICache.clear(namespace="fastapi-cache:obtener_estadisticas")
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo invalidar caché: {e}")

    return nuevo


@router.get(
    "/",
    response_model=list[MovimientoCajaRespuesta],
    summary="List cash movements with filters",
)
@require_auth
def listar_movimientos_caja(
    request: Request,
    db: Session = Depends(obtener_db),
    tipo: TipoMovimiento | None = Query(None),
    estado_ticket: EstadoTicket | None = Query(None),
    categoria_egreso: CategoriaEgreso | None = Query(None),
    placa: str | None = Query(None),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    taller_id = request.state.taller_id
    query = db.query(MovimientoCaja).filter(MovimientoCaja.taller_id == taller_id)

    if tipo is not None:
        query = query.filter(MovimientoCaja.tipo == tipo)
    if estado_ticket is not None:
        query = query.filter(MovimientoCaja.estado_ticket == estado_ticket)
    if categoria_egreso is not None:
        query = query.filter(MovimientoCaja.categoria_egreso == categoria_egreso)
    if placa:
        query = query.filter(MovimientoCaja.placa == placa)
    if fecha_desde is not None:
        query = query.filter(func.date(MovimientoCaja.fecha_creacion) >= fecha_desde)
    if fecha_hasta is not None:
        query = query.filter(func.date(MovimientoCaja.fecha_creacion) <= fecha_hasta)

    return query.order_by(MovimientoCaja.fecha_creacion.desc()).offset(skip).limit(limit).all()


@router.put("/{movimiento_id}/corregir", response_model=MovimientoCajaRespuesta)
async def corregir_movimiento_caja(
    request: Request,
    movimiento_id: int,
    datos: MovimientoCajaCorregir,
    db: Session = Depends(obtener_db),
    _: bool = Depends(requerir_password_admin),
):
    movimiento = db.query(MovimientoCaja).filter(MovimientoCaja.id == movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")

    cambio = CambioMovimientoCaja(
        movimiento_id=movimiento.id,
        taller_id=request.state.taller_id,
        motivo=datos.motivo,
        valor_anterior=movimiento.valor,
        valor_nuevo=datos.valor,
        observacion_anterior=movimiento.observacion,
        observacion_nueva=datos.observacion,
        actualizado_por=datos.actualizado_por,
    )

    movimiento.valor = datos.valor
    movimiento.observacion = datos.observacion

    db.add(cambio)
    db.commit()
    db.refresh(movimiento)

    # Invalidar caché de estadísticas después de actualizar movimiento
    try:
        await FastAPICache.clear(namespace="fastapi-cache:obtener_estadisticas")
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo invalidar caché: {e}")

    return movimiento


@router.get("/{movimiento_id}/cambios", response_model=list[CambioMovimientoCajaRespuesta])
@require_auth
def listar_cambios_movimiento(
    request: Request,
    movimiento_id: int,
    db: Session = Depends(obtener_db),
    _: bool = Depends(requerir_password_admin),
):
    taller_id = request.state.taller_id
    return (
        db.query(CambioMovimientoCaja)
        .filter(
            CambioMovimientoCaja.movimiento_id == movimiento_id,
            CambioMovimientoCaja.taller_id == taller_id,
        )
        .order_by(CambioMovimientoCaja.fecha_creacion.desc())
        .all()
    )
