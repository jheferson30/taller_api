"""
Repositorio para operaciones de acceso a datos de Movimientos de Caja.
Requirements: 9.1, 9.2, 9.3, 12.3
"""

from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modelos.movimiento_caja import (
    CategoriaEgreso,
    EstadoTicket,
    MovimientoCaja,
    TipoMovimiento,
)


class MovimientoCajaRepository:
    """Repositorio para gestión de movimientos de caja."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, movimiento_id: int) -> MovimientoCaja | None:
        """Obtiene un movimiento por ID."""
        return self.db.query(MovimientoCaja).filter(MovimientoCaja.id == movimiento_id).first()

    def get_all(
        self,
        tipo: TipoMovimiento | None = None,
        estado_ticket: EstadoTicket | None = None,
        categoria_egreso: CategoriaEgreso | None = None,
        placa: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[MovimientoCaja]:
        """
        Lista movimientos con paginación y filtros.
        Requirements: 9.3
        """
        query = self.db.query(MovimientoCaja)

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

    def get_cobros_rapidos(
        self,
        placa: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MovimientoCaja]:
        """Lista cobros rápidos con filtros."""
        query = self.db.query(MovimientoCaja).filter(
            MovimientoCaja.tipo == TipoMovimiento.INGRESO_RAPIDO
        )

        if placa:
            query = query.filter(MovimientoCaja.placa == placa.upper())
        if fecha_desde:
            query = query.filter(func.date(MovimientoCaja.fecha_creacion) >= fecha_desde)
        if fecha_hasta:
            query = query.filter(func.date(MovimientoCaja.fecha_creacion) <= fecha_hasta)

        return query.order_by(MovimientoCaja.fecha_creacion.desc()).offset(skip).limit(limit).all()

    def get_historico_economico(
        self,
        fecha_desde: date,
        fecha_hasta: date,
    ) -> list[dict[str, Any]]:
        """
        Obtiene histórico económico agrupado por fecha usando GROUP BY.
        Optimizado para reemplazar loop while en endpoint.
        Requirements: 12.3
        """
        # Query optimizada con GROUP BY y agregaciones SQL
        resultados = (
            self.db.query(
                func.date(MovimientoCaja.fecha_creacion).label("fecha"),
                func.sum(
                    func.case(
                        (
                            MovimientoCaja.tipo.in_(
                                [
                                    TipoMovimiento.INGRESO_ANTICIPO,
                                    TipoMovimiento.INGRESO_FINAL,
                                    TipoMovimiento.INGRESO_RAPIDO,
                                ]
                            ),
                            MovimientoCaja.valor,
                        ),
                        else_=0,
                    )
                ).label("total_ingresos"),
                func.sum(
                    func.case(
                        (MovimientoCaja.tipo == TipoMovimiento.EGRESO, MovimientoCaja.valor),
                        else_=0,
                    )
                ).label("total_egresos"),
                func.count(MovimientoCaja.id).label("total_movimientos"),
            )
            .filter(
                func.date(MovimientoCaja.fecha_creacion) >= fecha_desde,
                func.date(MovimientoCaja.fecha_creacion) <= fecha_hasta,
            )
            .group_by(func.date(MovimientoCaja.fecha_creacion))
            .order_by(func.date(MovimientoCaja.fecha_creacion).asc())
            .all()
        )

        # Convertir a lista de diccionarios
        return [
            {
                "fecha": r.fecha.isoformat(),
                "total_ingresos": r.total_ingresos or 0,
                "total_egresos": r.total_egresos or 0,
                "total_movimientos": r.total_movimientos or 0,
                "balance": (r.total_ingresos or 0) - (r.total_egresos or 0),
            }
            for r in resultados
        ]

    def create(self, movimiento: MovimientoCaja) -> MovimientoCaja:
        """
        Crea un nuevo movimiento.
        Requirements: 9.1
        """
        self.db.add(movimiento)
        self.db.flush()
        return movimiento

    def update(self, movimiento: MovimientoCaja) -> MovimientoCaja:
        """
        Actualiza un movimiento existente.
        Requirements: 9.2
        """
        self.db.flush()
        return movimiento
