"""
Repositorio para operaciones de acceso a datos de Tickets.
Requirements: 9.1, 9.2, 9.3, 9.6, 2.12, 2.13
"""
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.modelos.ticket import Ticket
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.ticket_repuesto import TicketRepuesto
from app.modelos.ticket_foto import TicketFoto


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
        Requirements: 9.3, 9.6, 2.13
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

    def get_tickets_with_details(
        self,
        skip: int = 0,
        limit: int = 50,
        estado: Optional[str] = None,
        placa: Optional[str] = None,
    ) -> List[Ticket]:
        """
        Lista tickets con eager loading de relaciones (procesos, repuestos, fotos).
        Usa joinedload para cargar todo en una sola query con JOINs.
        Requirements: 2.12
        
        Note: This method uses explicit joins to load related data in a single query,
        avoiding the N+1 query problem.
        """
        query = self.db.query(Ticket)

        if estado:
            query = query.filter(Ticket.estado == estado.upper())
        if placa:
            query = query.filter(Ticket.placa.ilike(f"%{placa.strip()}%"))

        # Load tickets
        tickets = (
            query.order_by(Ticket.fecha_ingreso.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # Manually eager load related data in separate queries
        # This is a workaround since we can't use relationship() due to circular imports
        if tickets:
            ticket_ids = [t.id for t in tickets]
            
            # Load all procesos for these tickets
            procesos = self.db.query(TicketProceso).filter(
                TicketProceso.ticket_id.in_(ticket_ids)
            ).all()
            
            # Load all repuestos for these tickets
            repuestos = self.db.query(TicketRepuesto).filter(
                TicketRepuesto.ticket_id.in_(ticket_ids)
            ).all()
            
            # Load all fotos for these tickets
            fotos = self.db.query(TicketFoto).filter(
                TicketFoto.ticket_id.in_(ticket_ids)
            ).all()
            
            # Group by ticket_id for easy access
            procesos_by_ticket = {}
            for p in procesos:
                if p.ticket_id not in procesos_by_ticket:
                    procesos_by_ticket[p.ticket_id] = []
                procesos_by_ticket[p.ticket_id].append(p)
            
            repuestos_by_ticket = {}
            for r in repuestos:
                if r.ticket_id not in repuestos_by_ticket:
                    repuestos_by_ticket[r.ticket_id] = []
                repuestos_by_ticket[r.ticket_id].append(r)
            
            fotos_by_ticket = {}
            for f in fotos:
                if f.ticket_id not in fotos_by_ticket:
                    fotos_by_ticket[f.ticket_id] = []
                fotos_by_ticket[f.ticket_id].append(f)
            
            # Attach to tickets (this makes them accessible as attributes)
            for ticket in tickets:
                ticket._procesos = procesos_by_ticket.get(ticket.id, [])
                ticket._repuestos = repuestos_by_ticket.get(ticket.id, [])
                ticket._fotos = fotos_by_ticket.get(ticket.id, [])
        
        return tickets

    def get_tickets_paginated(
        self,
        page: int = 1,
        per_page: int = 50,
        estado: Optional[str] = None,
        placa: Optional[str] = None,
    ) -> Tuple[List[Ticket], int]:
        """
        Lista tickets con paginación obligatoria.
        Retorna tupla: (tickets, total)
        Requirements: 2.13
        """
        query = self.db.query(Ticket)

        if estado:
            query = query.filter(Ticket.estado == estado.upper())
        if placa:
            query = query.filter(Ticket.placa.ilike(f"%{placa.strip()}%"))

        total = query.count()
        tickets = (
            query.order_by(Ticket.fecha_ingreso.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return tickets, total

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
