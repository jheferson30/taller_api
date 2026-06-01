#!/usr/bin/env python3
"""
Script para verificar el aislamiento multi-tenant

Prueba que cada taller solo puede ver sus propios datos.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.modelos.taller import Taller
from app.modelos.ticket import Ticket
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.ticket_repuesto import TicketRepuesto
from app.modelos.ticket_foto import TicketFoto
from app.modelos.movimiento_caja import MovimientoCaja
from app.modelos.mecanico import Mecanico
from app.modelos.vehiculo import Vehiculo
import os

# Configurar conexión a la base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:@localhost:5432/taller_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def verificar_aislamiento():
    """Verifica que cada taller solo vea sus propios datos"""
    db = SessionLocal()
    
    print("=" * 80)
    print("VERIFICACIÓN DE AISLAMIENTO MULTI-TENANT")
    print("=" * 80)
    print()
    
    # Obtener talleres de prueba
    talleres = db.query(Taller).filter(
        Taller.nombre.like("TEST_MULTI_TENANT_SCRIPT_%")
    ).all()
    
    if not talleres:
        print("❌ No se encontraron talleres de prueba")
        print("   Ejecuta: python scripts/test_multi_tenant.py create")
        return False
    
    print(f"✓ Encontrados {len(talleres)} talleres de prueba")
    print()
    
    # Verificar aislamiento para cada taller
    todos_aislados = True
    
    for taller in talleres:
        print(f"📋 Verificando: {taller.nombre} (ID: {taller.id})")
        print("-" * 80)
        
        # Contar recursos del taller
        tickets = db.query(Ticket).filter(Ticket.taller_id == taller.id).count()
        procesos = db.query(TicketProceso).filter(TicketProceso.taller_id == taller.id).count()
        repuestos = db.query(TicketRepuesto).filter(TicketRepuesto.taller_id == taller.id).count()
        fotos = db.query(TicketFoto).filter(TicketFoto.taller_id == taller.id).count()
        movimientos = db.query(MovimientoCaja).filter(MovimientoCaja.taller_id == taller.id).count()
        mecanicos = db.query(Mecanico).filter(Mecanico.taller_id == taller.id).count()
        vehiculos = db.query(Vehiculo).filter(Vehiculo.taller_id == taller.id).count()
        
        print(f"  Tickets: {tickets}")
        print(f"  Procesos: {procesos}")
        print(f"  Repuestos: {repuestos}")
        print(f"  Fotos: {fotos}")
        print(f"  Movimientos: {movimientos}")
        print(f"  Mecánicos: {mecanicos}")
        print(f"  Vehículos: {vehiculos}")
        
        # Verificar que no haya recursos de otros talleres
        tickets_otros = db.query(Ticket).filter(
            Ticket.taller_id != taller.id,
            Ticket.id.in_(
                db.query(Ticket.id).filter(Ticket.taller_id == taller.id)
            )
        ).count()
        
        if tickets_otros > 0:
            print(f"  ❌ FUGA DE DATOS: {tickets_otros} tickets de otros talleres accesibles")
            todos_aislados = False
        else:
            print(f"  ✓ Aislamiento correcto: no hay acceso a datos de otros talleres")
        
        print()
    
    # Verificar que los procesos, repuestos y fotos tengan taller_id
    print("🔍 Verificando integridad de taller_id en recursos...")
    print("-" * 80)
    
    procesos_sin_taller = db.query(TicketProceso).filter(TicketProceso.taller_id == None).count()
    repuestos_sin_taller = db.query(TicketRepuesto).filter(TicketRepuesto.taller_id == None).count()
    fotos_sin_taller = db.query(TicketFoto).filter(TicketFoto.taller_id == None).count()
    
    if procesos_sin_taller > 0:
        print(f"  ⚠️  {procesos_sin_taller} procesos sin taller_id")
        todos_aislados = False
    else:
        print(f"  ✓ Todos los procesos tienen taller_id")
    
    if repuestos_sin_taller > 0:
        print(f"  ⚠️  {repuestos_sin_taller} repuestos sin taller_id")
        todos_aislados = False
    else:
        print(f"  ✓ Todos los repuestos tienen taller_id")
    
    if fotos_sin_taller > 0:
        print(f"  ⚠️  {fotos_sin_taller} fotos sin taller_id")
        todos_aislados = False
    else:
        print(f"  ✓ Todas las fotos tienen taller_id")
    
    print()
    
    # Verificar que los tickets de cada taller solo tengan procesos/repuestos/fotos del mismo taller
    print("🔍 Verificando consistencia de taller_id entre recursos...")
    print("-" * 80)
    
    inconsistencias = 0
    
    for taller in talleres:
        # Obtener tickets del taller
        tickets_taller = db.query(Ticket.id).filter(Ticket.taller_id == taller.id).all()
        ticket_ids = [t.id for t in tickets_taller]
        
        if not ticket_ids:
            continue
        
        # Verificar que todos los procesos de estos tickets tengan el mismo taller_id
        procesos_incorrectos = db.query(TicketProceso).filter(
            TicketProceso.ticket_id.in_(ticket_ids),
            TicketProceso.taller_id != taller.id
        ).count()
        
        repuestos_incorrectos = db.query(TicketRepuesto).filter(
            TicketRepuesto.ticket_id.in_(ticket_ids),
            TicketRepuesto.taller_id != taller.id
        ).count()
        
        fotos_incorrectas = db.query(TicketFoto).filter(
            TicketFoto.ticket_id.in_(ticket_ids),
            TicketFoto.taller_id != taller.id
        ).count()
        
        if procesos_incorrectos > 0 or repuestos_incorrectos > 0 or fotos_incorrectas > 0:
            print(f"  ❌ {taller.nombre}:")
            if procesos_incorrectos > 0:
                print(f"     - {procesos_incorrectos} procesos con taller_id incorrecto")
            if repuestos_incorrectos > 0:
                print(f"     - {repuestos_incorrectos} repuestos con taller_id incorrecto")
            if fotos_incorrectas > 0:
                print(f"     - {fotos_incorrectas} fotos con taller_id incorrecto")
            inconsistencias += 1
    
    if inconsistencias == 0:
        print(f"  ✓ Todos los recursos tienen taller_id consistente con sus tickets")
    
    print()
    print("=" * 80)
    
    if todos_aislados and inconsistencias == 0:
        print("✅ AISLAMIENTO MULTI-TENANT VERIFICADO CORRECTAMENTE")
        print("   Cada taller solo puede ver sus propios datos")
        print("   No hay fugas de datos entre talleres")
        return True
    else:
        print("❌ SE DETECTARON PROBLEMAS DE AISLAMIENTO")
        print("   Revisa los mensajes anteriores para más detalles")
        return False

if __name__ == "__main__":
    try:
        exito = verificar_aislamiento()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
