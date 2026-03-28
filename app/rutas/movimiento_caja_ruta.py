from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.movimiento_caja_schema import (
    CambioMovimientoCajaRespuesta,
    MovimientoCajaCrear,
    MovimientoCajaCorregir,
    MovimientoCajaRespuesta,
)
from app.modelos.cambio_movimiento_caja import CambioMovimientoCaja
from app.modelos.movimiento_caja import (
    CategoriaEgreso,
    EstadoTicket,
    MovimientoCaja,
    TipoMovimiento,
)
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
            raise HTTPException(status_code=400, detail="ticket_codigo es obligatorio para ingresos")
        if not datos.placa:
            raise HTTPException(status_code=400, detail="placa es obligatoria para ingresos")
        if not datos.estado_ticket:
            raise HTTPException(status_code=400, detail="estado_ticket es obligatorio para ingresos")
    if datos.tipo == TipoMovimiento.EGRESO:
        if not datos.concepto:
            raise HTTPException(status_code=400, detail="concepto es obligatorio para egresos")
        if not datos.categoria_egreso:
            raise HTTPException(status_code=400, detail="categoria_egreso es obligatoria para egresos")


@router.get("/cobros-rapidos")
def listar_cobros_rapidos(
    db: Session = Depends(obtener_db),
    placa: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    query = db.query(MovimientoCaja).filter(MovimientoCaja.tipo == TipoMovimiento.INGRESO_RAPIDO)
    if placa:
        query = query.filter(MovimientoCaja.placa == placa.upper())
    if fecha_desde:
        query = query.filter(func.date(MovimientoCaja.fecha_creacion) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(MovimientoCaja.fecha_creacion) <= fecha_hasta)
    return (
        query.order_by(MovimientoCaja.fecha_creacion.desc())
        .offset(skip).limit(limit).all()
    )


@router.post("/cobro-rapido", response_model=MovimientoCajaRespuesta)
def crear_cobro_rapido(
    datos: CobroRapidoCrear,
    db: Session = Depends(obtener_db),
):
    nuevo = MovimientoCaja(
        tipo=TipoMovimiento.INGRESO_RAPIDO,
        placa=datos.placa.upper().strip(),
        concepto=datos.descripcion,
        valor=datos.valor,
        metodo_pago=datos.metodo_pago,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.post("/", response_model=MovimientoCajaRespuesta)
def crear_movimiento_caja(
    datos: MovimientoCajaCrear,
    db: Session = Depends(obtener_db),
):
    _validar_movimiento(datos)
    nuevo = MovimientoCaja(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/", response_model=List[MovimientoCajaRespuesta])
def listar_movimientos_caja(
    db: Session = Depends(obtener_db),
    tipo: Optional[TipoMovimiento] = Query(None),
    estado_ticket: Optional[EstadoTicket] = Query(None),
    categoria_egreso: Optional[CategoriaEgreso] = Query(None),
    placa: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    query = db.query(MovimientoCaja)

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

    return (
        query.order_by(MovimientoCaja.fecha_creacion.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.put("/{movimiento_id}/corregir", response_model=MovimientoCajaRespuesta)
def corregir_movimiento_caja(
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
    return movimiento


@router.get("/{movimiento_id}/cambios", response_model=List[CambioMovimientoCajaRespuesta])
def listar_cambios_movimiento(
    movimiento_id: int,
    db: Session = Depends(obtener_db),
    _: bool = Depends(requerir_password_admin),
):
    return (
        db.query(CambioMovimientoCaja)
        .filter(CambioMovimientoCaja.movimiento_id == movimiento_id)
        .order_by(CambioMovimientoCaja.fecha_creacion.desc())
        .all()
    )
