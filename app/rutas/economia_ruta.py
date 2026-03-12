from datetime import date
from typing import Dict, List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.modelos.movimiento_caja import MovimientoCaja, TipoMovimiento
from app.seguridad.dependencias import requerir_password_admin, requerir_password_pdf
from app.utils.pdf_economia import generar_pdf_economia_profesional

router = APIRouter(prefix="/economia-dia", tags=["Economia"])


def _base_query_dia(db: Session, fecha_objetivo: date):
    return db.query(MovimientoCaja).filter(func.date(MovimientoCaja.fecha_creacion) == fecha_objetivo)


def _sumar_por_tipo(db: Session, fecha_objetivo: date, tipo: TipoMovimiento) -> int:
    total = (
        db.query(func.coalesce(func.sum(MovimientoCaja.valor), 0))
        .filter(
            func.date(MovimientoCaja.fecha_creacion) == fecha_objetivo,
            MovimientoCaja.tipo == tipo,
        )
        .scalar()
    )
    return int(total or 0)


def _resumen_economia(db: Session, fecha_objetivo: date) -> Dict[str, int]:
    ingreso_anticipo = _sumar_por_tipo(db, fecha_objetivo, TipoMovimiento.INGRESO_ANTICIPO)
    ingreso_final = _sumar_por_tipo(db, fecha_objetivo, TipoMovimiento.INGRESO_FINAL)
    egresos = _sumar_por_tipo(db, fecha_objetivo, TipoMovimiento.EGRESO)
    ingresos = ingreso_anticipo + ingreso_final

    tickets_cerrados_hoy = (
        db.query(func.count(func.distinct(MovimientoCaja.ticket_codigo)))
        .filter(
            func.date(MovimientoCaja.fecha_creacion) == fecha_objetivo,
            MovimientoCaja.tipo == TipoMovimiento.INGRESO_FINAL,
            MovimientoCaja.ticket_codigo.isnot(None),
        )
        .scalar()
    )
    tickets_abiertos_anticipo_hoy = (
        db.query(func.count(func.distinct(MovimientoCaja.ticket_codigo)))
        .filter(
            func.date(MovimientoCaja.fecha_creacion) == fecha_objetivo,
            MovimientoCaja.tipo == TipoMovimiento.INGRESO_ANTICIPO,
            MovimientoCaja.ticket_codigo.isnot(None),
        )
        .scalar()
    )

    return {
        "ingreso_anticipo": ingreso_anticipo,
        "ingreso_final": ingreso_final,
        "ingresos": ingresos,
        "egresos": egresos,
        "balance": ingresos - egresos,
        "tickets_cerrados_hoy": int(tickets_cerrados_hoy or 0),
        "tickets_abiertos_con_anticipo_hoy": int(tickets_abiertos_anticipo_hoy or 0),
    }


def _detalle_ingresos(db: Session, fecha_objetivo: date):
    anticipos = (
        _base_query_dia(db, fecha_objetivo)
        .filter(MovimientoCaja.tipo == TipoMovimiento.INGRESO_ANTICIPO)
        .order_by(MovimientoCaja.fecha_creacion.desc())
        .all()
    )
    finales = (
        _base_query_dia(db, fecha_objetivo)
        .filter(MovimientoCaja.tipo == TipoMovimiento.INGRESO_FINAL)
        .order_by(MovimientoCaja.fecha_creacion.desc())
        .all()
    )

    return {
        "anticipos": [
            {
                "id": m.id,
                "ticket_codigo": m.ticket_codigo,
                "placa": m.placa,
                "valor_anticipo": m.valor,
                "hora": m.fecha_creacion.isoformat() if m.fecha_creacion else None,
                "responsable": m.responsable,
                "estado_ticket": m.estado_ticket,
                "metodo_pago": m.metodo_pago,
            }
            for m in anticipos
        ],
        "cobros_finales": [
            {
                "id": m.id,
                "ticket_codigo": m.ticket_codigo,
                "placa": m.placa,
                "valor_final_cobrado": m.valor,
                "hora": m.fecha_creacion.isoformat() if m.fecha_creacion else None,
                "responsable": m.responsable,
                "estado_ticket": m.estado_ticket,
                "metodo_pago": m.metodo_pago,
                "observacion": m.observacion,
            }
            for m in finales
        ],
    }


def _detalle_egresos(db: Session, fecha_objetivo: date):
    egresos = (
        _base_query_dia(db, fecha_objetivo)
        .filter(MovimientoCaja.tipo == TipoMovimiento.EGRESO)
        .order_by(MovimientoCaja.fecha_creacion.desc())
        .all()
    )

    return [
        {
            "id": m.id,
            "fecha": m.fecha_creacion.isoformat() if m.fecha_creacion else None,
            "categoria": m.categoria_egreso,
            "concepto": m.concepto,
            "ticket_codigo": m.ticket_codigo,
            "placa": m.placa,
            "valor": m.valor,
            "responsable": m.responsable,
            "soporte_url": m.soporte_url,
            "observacion": m.observacion,
        }
        for m in egresos
    ]


@router.get("/pdf")
def generar_pdf_economia_dia(
    fecha: date = Query(default_factory=date.today),
    db: Session = Depends(obtener_db),
    _: bool = Depends(requerir_password_pdf),
):
    resumen = _resumen_economia(db, fecha)
    ingresos = _detalle_ingresos(db, fecha)
    egresos_list = _detalle_egresos(db, fecha)

    # Usar el nuevo generador profesional
    pdf_bytes = generar_pdf_economia_profesional(
        fecha=fecha.isoformat(),
        resumen=resumen,
        ingresos=ingresos,
        egresos=egresos_list
    )
    
    nombre_archivo = f"economia_{fecha.isoformat()}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("")
def obtener_resumen_economia_dia(
    fecha: date = Query(default_factory=date.today),
    db: Session = Depends(obtener_db),
):
    resumen = _resumen_economia(db, fecha)
    return {"fecha": fecha.isoformat(), **resumen}


@router.get("/ingresos")
def obtener_detalle_ingresos_dia(
    fecha: date = Query(default_factory=date.today),
    db: Session = Depends(obtener_db),
):
    return {"fecha": fecha.isoformat(), **_detalle_ingresos(db, fecha)}


@router.get("/egresos")
def obtener_detalle_egresos_dia(
    fecha: date = Query(default_factory=date.today),
    db: Session = Depends(obtener_db),
):
    return {"fecha": fecha.isoformat(), "egresos": _detalle_egresos(db, fecha)}


@router.get("/historico")
def obtener_historico_economia(
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    db: Session = Depends(obtener_db),
    _: bool = Depends(requerir_password_admin),
):
    if fecha_hasta < fecha_desde:
        return {"detalle": "Rango de fechas invalido", "items": []}

    items = []
    actual = fecha_desde
    while actual <= fecha_hasta:
        resumen = _resumen_economia(db, actual)
        items.append({"fecha": actual.isoformat(), **resumen})
        actual = date.fromordinal(actual.toordinal() + 1)
    return {"fecha_desde": fecha_desde.isoformat(), "fecha_hasta": fecha_hasta.isoformat(), "items": items}
