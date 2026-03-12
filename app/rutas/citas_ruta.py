from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.cita_schema import CitaCrear, CitaActualizar, CitaRespuesta
from app.modelos.cita import Cita
from app.modelos.vehiculo import Vehiculo
from app.modelos.ticket import Ticket

router = APIRouter(prefix="/citas", tags=["Citas"])


@router.get("", response_model=List[CitaRespuesta])
def listar_citas(
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    db: Session = Depends(obtener_db)
):
    """Lista citas con filtros opcionales"""
    query = db.query(Cita)
    
    if fecha_desde:
        query = query.filter(Cita.fecha_cita >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.filter(Cita.fecha_cita <= datetime.fromisoformat(fecha_hasta))
    if estado:
        query = query.filter(Cita.estado == estado.upper())
    
    return query.order_by(Cita.fecha_cita.asc()).all()


@router.get("/proximas", response_model=List[CitaRespuesta])
def listar_citas_proximas(
    dias: int = Query(7, ge=1, le=30),
    db: Session = Depends(obtener_db)
):
    """Lista citas de hoy y los próximos N días"""
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_limite = hoy + timedelta(days=dias)
    
    return db.query(Cita).filter(
        Cita.fecha_cita >= hoy,
        Cita.fecha_cita <= fecha_limite,
        Cita.estado.in_(["PENDIENTE", "CONFIRMADA"])
    ).order_by(Cita.fecha_cita.asc()).all()



@router.post("", response_model=CitaRespuesta)
def crear_cita(datos: CitaCrear, db: Session = Depends(obtener_db)):
    """Crea una nueva cita"""
    # Si tiene placa, buscar el vehículo
    vehiculo_id = None
    if datos.placa:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == datos.placa.strip().upper()).first()
        if vehiculo:
            vehiculo_id = vehiculo.id
    
    cita = Cita(
        vehiculo_id=vehiculo_id,
        placa=datos.placa.strip().upper() if datos.placa else None,
        nombre_cliente=datos.nombre_cliente,
        telefono_cliente=datos.telefono_cliente,
        fecha_cita=datos.fecha_cita,
        motivo=datos.motivo,
        observaciones=datos.observaciones,
        creado_por=datos.creado_por
    )
    
    db.add(cita)
    db.commit()
    db.refresh(cita)
    return cita


@router.get("/{cita_id}", response_model=CitaRespuesta)
def obtener_cita(cita_id: int, db: Session = Depends(obtener_db)):
    """Obtiene una cita por ID"""
    cita = db.query(Cita).filter(Cita.id == cita_id).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita


@router.put("/{cita_id}", response_model=CitaRespuesta)
def actualizar_cita(
    cita_id: int,
    datos: CitaActualizar,
    db: Session = Depends(obtener_db)
):
    """Actualiza una cita"""
    cita = db.query(Cita).filter(Cita.id == cita_id).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    if cita.estado == "CONVERTIDA":
        raise HTTPException(status_code=400, detail="No se puede editar una cita ya convertida en ticket")
    
    # Actualizar campos
    payload = datos.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        setattr(cita, campo, valor)
    
    db.commit()
    db.refresh(cita)
    return cita


@router.delete("/{cita_id}")
def cancelar_cita(cita_id: int, db: Session = Depends(obtener_db)):
    """Cancela una cita (cambia estado a CANCELADA)"""
    cita = db.query(Cita).filter(Cita.id == cita_id).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    if cita.estado == "CONVERTIDA":
        raise HTTPException(status_code=400, detail="No se puede cancelar una cita ya convertida")
    
    cita.estado = "CANCELADA"
    db.commit()
    return {"ok": True, "mensaje": "Cita cancelada"}


@router.post("/{cita_id}/generar-ticket")
def generar_ticket_desde_cita(cita_id: int, db: Session = Depends(obtener_db)):
    """Convierte una cita en un ticket de ingreso"""
    cita = db.query(Cita).filter(Cita.id == cita_id).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    if cita.estado == "CONVERTIDA":
        raise HTTPException(status_code=400, detail="Esta cita ya fue convertida en ticket")
    
    # Buscar o crear vehículo
    vehiculo = None
    if cita.placa:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == cita.placa).first()
        
        if not vehiculo:
            # Crear vehículo nuevo
            vehiculo = Vehiculo(
                placa=cita.placa,
                nombre_propietario=cita.nombre_cliente,
                telefono_propietario=cita.telefono_cliente
            )
            db.add(vehiculo)
            db.flush()
    else:
        raise HTTPException(status_code=400, detail="La cita debe tener una placa para generar ticket")
    
    # Generar código de ticket
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    ticket_codigo = f"TK-{cita.placa}-{timestamp}"
    
    # Crear ticket
    ticket = Ticket(
        vehiculo_id=vehiculo.id,
        ticket_codigo=ticket_codigo,
        placa=cita.placa,
        motivo_visita=cita.motivo,
        observaciones_recepcion=cita.observaciones or f"Generado desde cita del {cita.fecha_cita.strftime('%d/%m/%Y %H:%M')}",
        recepcionado_por=cita.creado_por
    )
    
    db.add(ticket)
    db.flush()
    
    # Actualizar cita
    cita.estado = "CONVERTIDA"
    cita.ticket_id = ticket.id
    cita.ticket_codigo = ticket_codigo
    
    db.commit()
    db.refresh(ticket)
    
    return {
        "ok": True,
        "mensaje": "Ticket generado exitosamente",
        "ticket_id": ticket.id,
        "ticket_codigo": ticket_codigo
    }
