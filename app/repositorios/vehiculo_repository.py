"""
Repositorio para operaciones de acceso a datos de Vehículos.
Requirements: 9.1, 9.2, 9.3
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.modelos.vehiculo import Vehiculo


class VehiculoRepository:
    """Repositorio para gestión de vehículos."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, vehiculo_id: int) -> Optional[Vehiculo]:
        """Obtiene un vehículo por ID."""
        return self.db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()

    def get_by_placa(self, placa: str) -> Optional[Vehiculo]:
        """
        Obtiene un vehículo por placa.
        Requirements: 9.3
        """
        return self.db.query(Vehiculo).filter(
            Vehiculo.placa == placa.strip().upper()
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        placa: Optional[str] = None,
    ) -> List[Vehiculo]:
        """
        Lista vehículos con paginación y filtros opcionales.
        Requirements: 9.3
        """
        query = self.db.query(Vehiculo)

        if placa:
            query = query.filter(Vehiculo.placa.ilike(f"%{placa.strip()}%"))

        return query.order_by(Vehiculo.placa.asc()).offset(skip).limit(limit).all()

    def create(self, vehiculo: Vehiculo) -> Vehiculo:
        """
        Crea un nuevo vehículo.
        Requirements: 9.1
        """
        self.db.add(vehiculo)
        self.db.flush()
        return vehiculo

    def update(self, vehiculo: Vehiculo) -> Vehiculo:
        """
        Actualiza un vehículo existente.
        Requirements: 9.2
        """
        self.db.flush()
        return vehiculo

    def search(self, query: str, limit: int = 20) -> List[Vehiculo]:
        """Busca vehículos por placa, marca o modelo."""
        search_pattern = f"%{query.strip()}%"
        return (
            self.db.query(Vehiculo)
            .filter(
                (Vehiculo.placa.ilike(search_pattern))
                | (Vehiculo.marca.ilike(search_pattern))
                | (Vehiculo.modelo.ilike(search_pattern))
            )
            .limit(limit)
            .all()
        )
