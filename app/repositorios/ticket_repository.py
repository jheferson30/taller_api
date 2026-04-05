"""
Repositorio para operaciones de acceso a datos de Tickets.
Requirements: 9.1, 9.2, 9.3, 9.6
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.modelos.ticket import Ticket


class TicketRepository:
    """Repositorio para gestión de tickets."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Obtiene un ticket por ID."""
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()

    def get_by_codigo(self, ticket_codigo: str) -> Optional[Ticket]:
        """Obtiene un ticket por código."""
        return self.db.query(Ticket).filter(
            Ticket.ticket_codigo == ticket_codigo.strip().upper()
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        estado: Optional[str] = None,
        placa: Optional[str] = None,
    ) -> List[Ticket]:
        """
        Lista tickets con paginación y filtros opcionales.
        Requirements: 9.3, 9.6
        """
        query = self.db.query(Ticket)

        if estado:
            query = query.filter(Ticket.estado == estado.upper())
        if placa:
            query = query.filter(Ticket.placa.ilike(f"%{placa.strip()}%"))

        return (
            query.order_by(Ticket.fecha_ingreso.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def find_by_criteria(
        self,
        ticket_codigo: Optional[str] = None,
        placa: Optional[str] = None,
        estado: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[Ticket]:
        """
        Busca tickets por múltiples criterios.
        Requirements: 9.3
        """
        query = self.db.query(Ticket)

        if ticket_codigo:
            query = query.filter(Ticket.ticket_codigo == ticket_codigo.strip().upper())
        if placa:
            query = query.filter(Ticket.placa.ilike(f"%{placa.strip()}%"))
        if estado:
            query = query.filter(Ticket.estado == estado.upper())
        if fecha_desde:
            query = query.filter(Ticket.fecha_ingreso >= fecha_desde)
        if fecha_hasta:
            # Incluir todo el día hasta
            hasta = fecha_hasta.replace(hour=23, minute=59, second=59)
            query = query.filter(Ticket.fecha_ingreso <= hasta)

        return query.order_by(Ticket.fecha_ingreso.desc()).limit(limit).all()

    def create(self, ticket: Ticket) -> Ticket:
        """
        Crea un nuevo ticket.
        Requirements: 9.1
        """
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def update(self, ticket: Ticket) -> Ticket:
        """
        Actualiza un ticket existente.
        Requirements: 9.2
        """
        self.db.flush()
        return ticket

    def count(self, estado: Optional[str] = None) -> int:
        """Cuenta tickets, opcionalmente filtrados por estado."""
        query = self.db.query(Ticket)
        if estado:
            query = query.filter(Ticket.estado == estado.upper())
        return query.count()
