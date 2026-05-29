from datetime import UTC, datetime

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
from app.repositorios.ticket_repository import TicketRepository
from app.utils.input_validator import InputSanitizer


class TicketService:
    """Servicio de lógica de negocio para tickets."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = TicketRepository(db)

    def get_tickets_paginated(
        self,
        page: int = 1,
        per_page: int = 50,
        estado: str | None = None,
        placa: str | None = None,
    ) -> tuple[list[Ticket], int]:
        """
        Obtiene tickets con paginación.
        Requirements: 2.13
        """
        return self.repository.get_tickets_paginated(page, per_page, estado, placa)

    def calcular_saldo_pendiente(self, ticket: Ticket) -> int:
        """Calcula el saldo pendiente de un ticket."""
        if not ticket.total_servicio:
            return 0

        cobros = self.db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket.id).all()
        total_cobros = sum(c.valor or 0 for c in cobros)
        saldo = ticket.total_servicio - (ticket.anticipo_recibido or 0) - total_cobros
        return max(0, saldo)

    def asegurar_editable(self, ticket: Ticket) -> None:
        """Verifica que el ticket pueda ser editado."""
        if ticket.estado in ("FINALIZADO", "ENTREGADO"):
            raise HTTPException(status_code=400, detail="El ticket ya no permite edicion")

    def actualizar_estado_ticket(self, ticket: Ticket) -> None:
        """Actualiza el estado del ticket de ABIERTO a EN_PROCESO si es necesario."""
        if ticket.estado == "ABIERTO":
            ticket.estado = "EN_PROCESO"

    def finalizar_ticket(self, ticket: Ticket) -> Ticket:
        """
        Finaliza un ticket (trabajo terminado). El ingreso se registra al entregar.

        Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4
        """
        if not ticket.total_servicio:
            raise HTTPException(
                status_code=400, detail="Debes definir total del servicio antes de finalizar"
            )

        # Calcular saldo pendiente
        saldo = self.calcular_saldo_pendiente(ticket)
        ticket.saldo_pendiente = saldo
        ticket.estado = "FINALIZADO"
        ticket.fecha_cierre = datetime.now(UTC)

        # El ingreso final se registra cuando el cliente recoge el vehículo (entregar_ticket)
        return ticket

    def entregar_ticket(
        self,
        ticket: Ticket,
        confirmado_entrega_por: str,
        firma_entrega_url: str | None = None,
        observaciones_finales: str | None = None,
        recomendaciones: str | None = None,
        proximo_mantenimiento: str | None = None,
        metodo_pago_final: str | None = None,
    ) -> Ticket:
        """
        Marca un ticket como entregado y registra el ingreso final en caja.

        Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4
        """
        if ticket.estado != "FINALIZADO":
            raise HTTPException(status_code=400, detail="Solo puedes entregar tickets finalizados")

        ticket.estado = "ENTREGADO"
        ticket.fecha_entrega = datetime.now(UTC)
        ticket.confirmado_entrega_por = (
            InputSanitizer.sanitize_html(confirmado_entrega_por)
            if confirmado_entrega_por
            else confirmado_entrega_por
        )
        # firma_entrega_url: solo permitir URLs relativas internas o https
        if firma_entrega_url and not (
            firma_entrega_url.startswith("/uploads/") or firma_entrega_url.startswith("https://")
        ):
            raise HTTPException(status_code=400, detail="URL de firma no válida")
        ticket.firma_entrega_url = firma_entrega_url

        if metodo_pago_final is not None:
            # Validar que sea un método de pago permitido
            metodos_permitidos = {"EFECTIVO", "NEQUI", "DAVIPLATA", "TRANSFERENCIA", "TARJETA"}
            valor_upper = metodo_pago_final.strip().upper()
            if valor_upper not in metodos_permitidos:
                raise HTTPException(status_code=400, detail="Método de pago no válido")
            ticket.metodo_pago_final = valor_upper

        # Sanitize text fields to prevent XSS
        if observaciones_finales is not None:
            ticket.observaciones_finales = InputSanitizer.sanitize_html(observaciones_finales)
        if recomendaciones is not None:
            ticket.recomendaciones = InputSanitizer.sanitize_html(recomendaciones)
        if proximo_mantenimiento is not None:
            ticket.proximo_mantenimiento = InputSanitizer.sanitize_html(proximo_mantenimiento)

        # Registrar en caja solo el saldo que queda pendiente al momento de la entrega.
        # Los cobros parciales ya fueron registrados como MovimientoCaja al agregarse.
        saldo_al_entregar = self.calcular_saldo_pendiente(ticket)
        if saldo_al_entregar > 0:
            movimiento = MovimientoCaja(
                taller_id=ticket.taller_id,
                tipo=TipoMovimiento.INGRESO_FINAL,
                ticket_id=ticket.id,
                ticket_codigo=ticket.ticket_codigo,
                placa=ticket.placa,
                estado_ticket=EstadoTicket.ENTREGADO,
                valor=saldo_al_entregar,
                metodo_pago=ticket.metodo_pago_final,
                responsable=ticket.recepcionado_por,
                concepto=f"Cobro final ticket {ticket.ticket_codigo}",
                observacion=ticket.observaciones_finales,
                creado_por=confirmado_entrega_por,
            )
            self.db.add(movimiento)

        return ticket

    def actualizar_finanzas(
        self,
        ticket: Ticket,
        total_servicio: int,
        metodo_pago_final: str | None = None,
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
        nota: str | None = None,
        soporte_url: str | None = None,
        responsable_user_id: int | None = None,
    ) -> TicketCompra:
        """
        Crea una compra y su movimiento de caja asociado.

        Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4
        """
        self.asegurar_editable(ticket)
        self.actualizar_estado_ticket(ticket)

        # Sanitize text fields to prevent XSS
        descripcion_sanitized = InputSanitizer.sanitize_html(descripcion)
        nota_sanitized = InputSanitizer.sanitize_html(nota) if nota else None

        # Crear compra
        compra = TicketCompra(
            ticket_id=ticket.id,
            taller_id=ticket.taller_id,
            descripcion=descripcion_sanitized,
            valor=valor,
            responsable=responsable,
            responsable_user_id=responsable_user_id,
            nota=nota_sanitized,
            soporte_url=soporte_url,
        )
        self.db.add(compra)
        self.db.flush()

        # Crear movimiento de caja
        movimiento = MovimientoCaja(
            taller_id=ticket.taller_id,
            tipo=TipoMovimiento.EGRESO,
            ticket_id=ticket.id,
            ticket_codigo=ticket.ticket_codigo,
            placa=ticket.placa,
            estado_ticket=EstadoTicket.EN_PROCESO,
            valor=valor,
            categoria_egreso=CategoriaEgreso.OTRO,
            concepto=descripcion_sanitized,
            responsable=responsable,
            observacion=nota_sanitized,
            soporte_url=soporte_url,
            creado_por=responsable,
        )
        self.db.add(movimiento)

        return compra

    def eliminar_repuesto_con_compra(
        self,
        ticket: Ticket,
        repuesto: TicketRepuesto,
    ) -> None:
        """
        Elimina un repuesto y su compra asociada si existe.

        Requirements: 7.1, 7.2, 7.3, 7.4
        """
        self.asegurar_editable(ticket)

        # Buscar y eliminar compra asociada por nombre
        compra_asociada = (
            self.db.query(TicketCompra)
            .filter(
                TicketCompra.ticket_id == ticket.id,
                TicketCompra.descripcion == repuesto.nombre,
            )
            .first()
        )

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
