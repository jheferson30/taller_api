"""
Servicio de lógica de negocio para Movimientos de Caja.
Requirements: 8.1, 8.3, 8.4
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modelos.movimiento_caja import (
    MovimientoCaja,
    TipoMovimiento,
)


class MovimientoCajaService:
    """Servicio de lógica de negocio para movimientos de caja."""

    def __init__(self, db: Session):
        self.db = db

    def validar_movimiento(self, movimiento: MovimientoCaja):
        """
        Valida que un movimiento tenga todos los campos requeridos según su tipo.
        Requirements: 8.1, 8.3
        """
        if movimiento.tipo in (TipoMovimiento.INGRESO_ANTICIPO, TipoMovimiento.INGRESO_FINAL):
            if not movimiento.ticket_codigo:
                raise HTTPException(
                    status_code=400,
                    detail="ticket_codigo es obligatorio para ingresos"
                )
            if not movimiento.placa:
                raise HTTPException(
                    status_code=400,
                    detail="placa es obligatoria para ingresos"
                )
            if not movimiento.estado_ticket:
                raise HTTPException(
                    status_code=400,
                    detail="estado_ticket es obligatorio para ingresos"
                )

        if movimiento.tipo == TipoMovimiento.EGRESO:
            if not movimiento.concepto:
                raise HTTPException(
                    status_code=400,
                    detail="concepto es obligatorio para egresos"
                )
            if not movimiento.categoria_egreso:
                raise HTTPException(
                    status_code=400,
                    detail="categoria_egreso es obligatoria para egresos"
                )

    def crear_cobro_rapido(
        self,
        placa: str,
        descripcion: str,
        valor: int,
        metodo_pago: str = "EFECTIVO",
    ) -> MovimientoCaja:
        """
        Crea un cobro rápido (ingreso sin ticket).
        Requirements: 8.1, 8.4
        """
        if valor <= 0:
            raise HTTPException(
                status_code=400,
                detail="El valor debe ser mayor a 0"
            )

        movimiento = MovimientoCaja(
            tipo=TipoMovimiento.INGRESO_RAPIDO,
            placa=placa.upper().strip(),
            concepto=descripcion,
            valor=valor,
            metodo_pago=metodo_pago,
        )

        self.db.add(movimiento)
        return movimiento

    def corregir_movimiento(
        self,
        movimiento: MovimientoCaja,
        nuevo_valor: int,
        nueva_observacion: str,
        motivo: str,
        actualizado_por: str,
    ) -> MovimientoCaja:
        """
        Corrige un movimiento existente y registra el cambio.
        Requirements: 8.4
        """
        from app.modelos.cambio_movimiento_caja import CambioMovimientoCaja

        # Crear registro de cambio
        cambio = CambioMovimientoCaja(
            movimiento_id=movimiento.id,
            motivo=motivo,
            valor_anterior=movimiento.valor,
            valor_nuevo=nuevo_valor,
            observacion_anterior=movimiento.observacion,
            observacion_nueva=nueva_observacion,
            actualizado_por=actualizado_por,
        )

        # Actualizar movimiento
        movimiento.valor = nuevo_valor
        movimiento.observacion = nueva_observacion

        self.db.add(cambio)
        return movimiento
