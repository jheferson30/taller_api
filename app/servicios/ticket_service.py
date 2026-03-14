from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modelos.movimiento_caja import EstadoTicket, MovimientoCaja, TipoMovimiento
from app.modelos.ticket import Ticket
from app.modelos.ticket_cobro import TicketCobro


def finalizar_ticket(ticket: Ticket, db: Session) -> Ticket:
    """Lógica compartida de finalización de ticket para todas las rutas."""
    if not ticket.total_servicio:
        raise HTTPException(status_code=400, detail="Debes definir total del servicio antes de finalizar")

    cobros = db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket.id).all()
    total_cobros = sum(c.valor for c in cobros)
    saldo = ticket.total_servicio - (ticket.anticipo_recibido or 0) - total_cobros
    if saldo < 0:
        saldo = 0
    ticket.saldo_pendiente = saldo
    ticket.estado = "FINALIZADO"
    ticket.fecha_cierre = datetime.now(timezone.utc)

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
        db.add(movimiento)

    return ticket
