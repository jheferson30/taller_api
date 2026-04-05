from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.esquemas.cita_schema import CitaCrear, CitaActualizar, CitaRespuesta
from app.modelos.cita import Cita
from app.modelos.vehiculo import Vehiculo
from app.modelos.ticket import Ticket
from app.seguridad.dependencias import require_jwt_auth

router = APIRouter(prefix="/citas", tags=["Citas"], dependencies=[Depends(require_jwt_auth)])


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
    """Crea una nueva cita y opcionalmente crea o actualiza el vehículo"""
    placa_norm = datos.placa.strip().upper()
    
    # Buscar si el vehículo ya existe
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == placa_norm).first()
    
    if vehiculo:
        # Vehículo existe - actualizar datos si se proporcionaron
        if datos.marca:
            vehiculo.marca = datos.marca
        if datos.modelo:
            vehiculo.modelo = datos.modelo
        if datos.anio:
            vehiculo.anio = datos.anio
        if datos.cilindraje:
            vehiculo.cilindraje = datos.cilindraje
        if datos.color:
            vehiculo.color = datos.color
        
        # Actualizar datos del propietario si cambiaron
        if datos.nombre_cliente and datos.nombre_cliente != vehiculo.nombre_propietario:
            vehiculo.nombre_propietario = datos.nombre_cliente
        if datos.telefono_cliente and datos.telefono_cliente != vehiculo.telefono_propietario:
            vehiculo.telefono_propietario = datos.telefono_cliente
    else:
        # Vehículo no existe - crear uno nuevo
        vehiculo = Vehiculo(
            placa=placa_norm,
            marca=datos.marca,
            modelo=datos.modelo,
            anio=datos.anio,
            cilindraje=datos.cilindraje,
            color=datos.color,
            nombre_propietario=datos.nombre_cliente,
            telefono_propietario=datos.telefono_cliente
        )
        db.add(vehiculo)
        db.flush()
    
    # Crear la cita con todos los datos
    cita = Cita(
        vehiculo_id=vehiculo.id,
        placa=placa_norm,
        marca=datos.marca,
        modelo=datos.modelo,
        anio=datos.anio,
        cilindraje=datos.cilindraje,
        color=datos.color,
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
    
    if not cita.placa:
        raise HTTPException(status_code=400, detail="La cita debe tener una placa para generar ticket")
    
    # El vehículo ya debe existir porque se creó/actualizó al crear la cita
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == cita.placa).first()
    
    if not vehiculo:
        # Esto no debería pasar, pero por seguridad creamos el vehículo
        vehiculo = Vehiculo(
            placa=cita.placa,
            marca=cita.marca,
            modelo=cita.modelo,
            anio=cita.anio,
            cilindraje=cita.cilindraje,
            color=cita.color,
            nombre_propietario=cita.nombre_cliente,
            telefono_propietario=cita.telefono_cliente
        )
        db.add(vehiculo)
        db.flush()
    else:
        # Actualizar vehículo con datos de la cita si están más completos
        if cita.marca and not vehiculo.marca:
            vehiculo.marca = cita.marca
        if cita.modelo and not vehiculo.modelo:
            vehiculo.modelo = cita.modelo
        if cita.anio and not vehiculo.anio:
            vehiculo.anio = cita.anio
        if cita.cilindraje and not vehiculo.cilindraje:
            vehiculo.cilindraje = cita.cilindraje
        if cita.color and not vehiculo.color:
            vehiculo.color = cita.color
    
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
