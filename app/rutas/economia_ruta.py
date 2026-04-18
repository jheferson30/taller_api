from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from fastapi_cache.decorator import cache
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.modelos.movimiento_caja import MovimientoCaja, TipoMovimiento
from app.modelos.ticket import Ticket
from app.modelos.ticket_proceso import TicketProceso
from app.seguridad.dependencias import requerir_password_admin
from app.utils.pdf_economia import generar_pdf_economia_profesional

router = APIRouter(prefix="/economia-dia", tags=["Economia"])


def _base_query_dia(db: Session, fecha_objetivo: date):
    return db.query(MovimientoCaja).filter(
        func.date(MovimientoCaja.fecha_creacion) == fecha_objetivo
    )


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


def _resumen_economia(db: Session, fecha_objetivo: date) -> dict[str, int]:
    ingreso_anticipo = _sumar_por_tipo(db, fecha_objetivo, TipoMovimiento.INGRESO_ANTICIPO)
    ingreso_final = _sumar_por_tipo(db, fecha_objetivo, TipoMovimiento.INGRESO_FINAL)
    ingreso_rapido = _sumar_por_tipo(db, fecha_objetivo, TipoMovimiento.INGRESO_RAPIDO)
    egresos = _sumar_por_tipo(db, fecha_objetivo, TipoMovimiento.EGRESO)
    ingresos = ingreso_anticipo + ingreso_final + ingreso_rapido

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
        "ingreso_rapido": ingreso_rapido,
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
    rapidos = (
        _base_query_dia(db, fecha_objetivo)
        .filter(MovimientoCaja.tipo == TipoMovimiento.INGRESO_RAPIDO)
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
        "cobros_rapidos": [
            {
                "id": m.id,
                "placa": m.placa,
                "descripcion": m.concepto,
                "valor": m.valor,
                "hora": m.fecha_creacion.isoformat() if m.fecha_creacion else None,
                "metodo_pago": m.metodo_pago,
            }
            for m in rapidos
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
    _: bool = Depends(requerir_password_admin),
):
    resumen = _resumen_economia(db, fecha)
    ingresos = _detalle_ingresos(db, fecha)
    egresos_list = _detalle_egresos(db, fecha)

    config_taller = db.query(ConfiguracionTaller).first()
    datos_taller = {
        "nombre": config_taller.nombre_taller if config_taller else "Taller Mecánico",
        "direccion": config_taller.direccion if config_taller else "",
        "telefono": config_taller.telefono if config_taller else "",
        "nit": config_taller.nit if config_taller else "",
        "logo_url": config_taller.logo_url if config_taller else "",
    }

    pdf_bytes = generar_pdf_economia_profesional(
        fecha=fecha.isoformat(),
        resumen=resumen,
        ingresos=ingresos,
        egresos=egresos_list,
        datos_taller=datos_taller,
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


@router.get("/estadisticas")
@cache(expire=300)  # Cachear por 5 minutos (300 segundos)
def obtener_estadisticas(
    periodo: str = Query(default="semana", pattern="^(semana|mes)$"),
    db: Session = Depends(obtener_db),
    _: bool = Depends(requerir_password_admin),
):
    hoy = date.today()
    dias = 7 if periodo == "semana" else 30
    fecha_desde = hoy - timedelta(days=dias - 1)

    # Ingresos por día
    tipos_ingreso = [
        TipoMovimiento.INGRESO_ANTICIPO,
        TipoMovimiento.INGRESO_FINAL,
        TipoMovimiento.INGRESO_RAPIDO,
    ]
    rows_ingresos = (
        db.query(
            func.date(MovimientoCaja.fecha_creacion).label("dia"),
            func.sum(MovimientoCaja.valor).label("total"),
        )
        .filter(
            func.date(MovimientoCaja.fecha_creacion) >= fecha_desde,
            func.date(MovimientoCaja.fecha_creacion) <= hoy,
            MovimientoCaja.tipo.in_(tipos_ingreso),
        )
        .group_by(func.date(MovimientoCaja.fecha_creacion))
        .all()
    )
    ingresos_map = {str(r.dia): int(r.total) for r in rows_ingresos}
    ingresos_por_dia = []
    actual = fecha_desde
    while actual <= hoy:
        ingresos_por_dia.append(
            {"fecha": actual.isoformat(), "total": ingresos_map.get(actual.isoformat(), 0)}
        )
        actual += timedelta(days=1)

    # Top servicios (motivo_visita de tickets en el período)
    rows_servicios = (
        db.query(
            Ticket.motivo_visita,
            func.count(Ticket.id).label("cantidad"),
        )
        .filter(
            func.date(Ticket.fecha_ingreso) >= fecha_desde,
            func.date(Ticket.fecha_ingreso) <= hoy,
        )
        .group_by(Ticket.motivo_visita)
        .order_by(func.count(Ticket.id).desc())
        .limit(5)
        .all()
    )
    servicios_frecuentes = [
        {"servicio": r.motivo_visita, "cantidad": int(r.cantidad)} for r in rows_servicios
    ]

    # Ranking mecánicos por procesos en el período
    rows_mecanicos = (
        db.query(
            TicketProceso.mecanico,
            func.count(TicketProceso.id).label("procesos"),
        )
        .filter(
            TicketProceso.mecanico.isnot(None),
            TicketProceso.mecanico != "",
            func.date(TicketProceso.fecha_creacion) >= fecha_desde,
            func.date(TicketProceso.fecha_creacion) <= hoy,
        )
        .group_by(TicketProceso.mecanico)
        .order_by(func.count(TicketProceso.id).desc())
        .limit(5)
        .all()
    )
    mecanicos_ranking = [
        {"mecanico": r.mecanico, "procesos": int(r.procesos)} for r in rows_mecanicos
    ]

    return {
        "periodo": periodo,
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": hoy.isoformat(),
        "ingresos_por_dia": ingresos_por_dia,
        "servicios_frecuentes": servicios_frecuentes,
        "mecanicos_ranking": mecanicos_ranking,
    }


@router.get("/historico")
def obtener_historico_economia(
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    db: Session = Depends(obtener_db),
    _: bool = Depends(requerir_password_admin),
):
    if fecha_hasta < fecha_desde:
        return {"detalle": "Rango de fechas invalido", "items": []}

    # Usar query optimizada del repositorio con GROUP BY
    from app.repositorios.movimiento_caja_repository import MovimientoCajaRepository

    repo = MovimientoCajaRepository(db)
    items = repo.get_historico_economico(fecha_desde, fecha_hasta)

    return {
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "items": items,
    }
