from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modelos.movimiento_caja import (
    CategoriaEgreso,
    EstadoTicket,
    MovimientoCaja,
    TipoMovimiento,
)
from app.modelos.ticket import Ticket
from app.modelos.ticket_cobro import TicketCobro
from app.modelos.ticket_compra import TicketCompra
from app.modelos.ticket_repuesto import TicketRepuesto


class TicketService:
    """Servicio de lógica de negocio para tickets."""

    def __init__(self, db: Session):
        self.db = db

    def calcular_saldo_pendiente(self, ticket: Ticket) -> int:
        """Calcula el saldo pendiente de un ticket."""
        if not ticket.total_servicio:
            return 0
        
        cobros = self.db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket.id).all()
        total_cobros = sum(c.valor for c in cobros)
        saldo = ticket.total_servicio - (ticket.anticipo_recibido or 0) - total_cobros
        return max(0, saldo)

    def asegurar_editable(self, ticket: Ticket):
        """Verifica que el ticket pueda ser editado."""
        if ticket.estado in ("FINALIZADO", "ENTREGADO"):
            raise HTTPException(
                status_code=400,
                detail="El ticket ya no permite edicion"
            )

    def actualizar_estado_ticket(self, ticket: Ticket):
        """Actualiza el estado del ticket de ABIERTO a EN_PROCESO si es necesario."""
        if ticket.estado == "ABIERTO":
            ticket.estado = "EN_PROCESO"

    def finalizar_ticket(self, ticket: Ticket) -> Ticket:
        """
        Finaliza un ticket y crea el movimiento de caja correspondiente.
        
        Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4
        """
        if not ticket.total_servicio:
            raise HTTPException(
                status_code=400,
                detail="Debes definir total del servicio antes de finalizar"
            )

        # Calcular saldo pendiente
        saldo = self.calcular_saldo_pendiente(ticket)
        ticket.saldo_pendiente = saldo
        ticket.estado = "FINALIZADO"
        ticket.fecha_cierre = datetime.now(timezone.utc)

        # Crear movimiento de caja para el ingreso final
        valor_ingreso = ticket.total_servicio - (ticket.anticipo_recibido or 0)
        if valor_ingreso > 0:
            movimiento = MovimientoCaja(
                tipo=TipoMovimiento.INGRESO_FINAL,
                ticket_id=ticket.id,
                ticket_codigo=ticket.ticket_codigo,
                placa=ticket.placa,
                estado_ticket=EstadoTicket.FINALIZADO,
                valor=valor_ingreso,
                metodo_pago=ticket.metodo_pago_final,
                responsable=ticket.recepcionado_por,
                concepto=f"Cobro final ticket {ticket.ticket_codigo}",
                observacion=ticket.observaciones_finales,
                creado_por=ticket.recepcionado_por,
            )
            self.db.add(movimiento)

        return ticket

    def entregar_ticket(
        self,
        ticket: Ticket,
        confirmado_entrega_por: str,
        firma_entrega_url: Optional[str] = None,
        observaciones_finales: Optional[str] = None,
        recomendaciones: Optional[str] = None,
        proximo_mantenimiento: Optional[str] = None,
    ) -> Ticket:
        """
        Marca un ticket como entregado.
        
        Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4
        """
        if ticket.estado != "FINALIZADO":
            raise HTTPException(
                status_code=400,
                detail="Solo puedes entregar tickets finalizados"
            )

        ticket.estado = "ENTREGADO"
        ticket.fecha_entrega = datetime.now(timezone.utc)
        ticket.confirmado_entrega_por = confirmado_entrega_por
        ticket.firma_entrega_url = firma_entrega_url

        if observaciones_finales is not None:
            ticket.observaciones_finales = observaciones_finales
        if recomendaciones is not None:
            ticket.recomendaciones = recomendaciones
        if proximo_mantenimiento is not None:
            ticket.proximo_mantenimiento = proximo_mantenimiento

        return ticket

    def actualizar_finanzas(
        self,
        ticket: Ticket,
        total_servicio: int,
        metodo_pago_final: Optional[str] = None,
    ) -> Ticket:
        """Actualiza las finanzas de un ticket."""
        self.asegurar_editable(ticket)
        
        ticket.total_servicio = total_servicio
        ticket.metodo_pago_final = metodo_pago_final
        
        # Recalcular saldo pendiente
        saldo = self.calcular_saldo_pendiente(ticket)
        ticket.saldo_pendiente = saldo

        return ticket

    def crear_compra_con_movimiento(
        self,
        ticket: Ticket,
        descripcion: str,
        valor: int,
        responsable: str,
        nota: Optional[str] = None,
        soporte_url: Optional[str] = None,
    ) -> TicketCompra:
        """
        Crea una compra y su movimiento de caja asociado.
        
        Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4
        """
        self.asegurar_editable(ticket)
        self.actualizar_estado_ticket(ticket)

        # Crear compra
        compra = TicketCompra(
            ticket_id=ticket.id,
            descripcion=descripcion,
            valor=valor,
            responsable=responsable,
            nota=nota,
            soporte_url=soporte_url,
        )
        self.db.add(compra)
        self.db.flush()

        # Crear movimiento de caja
        movimiento = MovimientoCaja(
            tipo=TipoMovimiento.EGRESO,
            ticket_id=ticket.id,
            ticket_codigo=ticket.ticket_codigo,
            placa=ticket.placa,
            estado_ticket=EstadoTicket.EN_PROCESO,
            valor=valor,
            categoria_egreso=CategoriaEgreso.OTRO,
            concepto=descripcion,
            responsable=responsable,
            observacion=nota,
            soporte_url=soporte_url,
            creado_por=responsable,
        )
        self.db.add(movimiento)

        return compra

    def eliminar_repuesto_con_compra(
        self,
        ticket: Ticket,
        repuesto: TicketRepuesto,
    ):
        """
        Elimina un repuesto y su compra asociada si existe.
        
        Requirements: 7.1, 7.2, 7.3, 7.4
        """
        self.asegurar_editable(ticket)

        # Buscar y eliminar compra asociada por nombre
        compra_asociada = self.db.query(TicketCompra).filter(
            TicketCompra.ticket_id == ticket.id,
            TicketCompra.descripcion == repuesto.nombre,
        ).first()
        
        if compra_asociada:
            self.db.delete(compra_asociada)
        
        self.db.delete(repuesto)


# Función legacy para compatibilidad con código existente
def finalizar_ticket(ticket: Ticket, db: Session) -> Ticket:
    """
    Función legacy para compatibilidad.
    Usa TicketService internamente.
    """
    service = TicketService(db)
    return service.finalizar_ticket(ticket)
