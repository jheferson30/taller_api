#!/usr/bin/env python3
"""
Script de prueba de Multi-Tenancy

Crea 5 talleres con datos completos para probar el aislamiento entre tenants.
Incluye función de limpieza que solo borra los datos creados por este script.

Uso:
    python scripts/test_multi_tenant.py create   # Crear datos de prueba
    python scripts/test_multi_tenant.py cleanup  # Limpiar datos de prueba
    python scripts/test_multi_tenant.py status   # Ver estado de los datos
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.modelos.taller import Taller
from app.modelos.user import User
from app.modelos.role import Role
from app.modelos.user_role import UserRole
from app.modelos.mecanico import Mecanico
from app.modelos.vehiculo import Vehiculo
from app.modelos.ticket import Ticket
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.ticket_repuesto import TicketRepuesto
from app.modelos.ticket_foto import TicketFoto
from app.modelos.movimiento_caja import MovimientoCaja, TipoMovimiento
from app.seguridad.password_hasher import PasswordHasher

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/taller_db?client_encoding=utf8")
TEST_MARKER = "TEST_MULTI_TENANT_SCRIPT"  # Marcador para identificar datos de prueba

# Colores para output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{msg.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")


def get_session():
    """Crear sesión de base de datos"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


def create_test_data():
    """Crear datos de prueba para 5 talleres"""
    print_header("CREANDO DATOS DE PRUEBA MULTI-TENANT")
    
    db = get_session()
    password_hasher = PasswordHasher()
    
    try:
        # Obtener roles
        role_admin = db.query(Role).filter(Role.name == "ADMIN").first()
        role_mecanico = db.query(Role).filter(Role.name == "MECANICO").first()
        
        if not role_admin or not role_mecanico:
            print_error("Roles no encontrados. Ejecutar migraciones primero.")
            return
        
        talleres_creados = []
        
        # Crear 5 talleres
        for i in range(1, 6):
            print_info(f"Creando Taller {i}...")
            
            # 1. Crear taller
            taller = Taller(
                nombre=f"{TEST_MARKER}_Taller_{i}",
                nit=f"900{i:06d}-{i}",
                direccion=f"Calle {i*10} #{i*5}-{i*2}",
                telefono=f"300{i:07d}",
                estado="ACTIVO"
            )
            db.add(taller)
            db.flush()
            talleres_creados.append(taller.id)
            print_success(f"  Taller creado: {taller.nombre} (ID: {taller.id})")
            
            # 2. Crear admin del taller
            admin_user = User(
                taller_id=taller.id,
                username=f"{TEST_MARKER}_admin_t{i}",
                email=f"admin{i}@test.com",
                password_hash=password_hasher.hash_password("test123"),
                is_active=True,
                nombre_completo=f"Admin Taller {i}",
                telefono=f"310{i:07d}"
            )
            db.add(admin_user)
            db.flush()
            
            # Asignar rol admin
            db.add(UserRole(user_id=admin_user.id, role_id=role_admin.id))
            print_success(f"  Admin creado: {admin_user.username}")
            
            # 3. Crear 2 mecánicos
            mecanicos_ids = []
            for j in range(1, 3):
                # Crear usuario mecánico
                mec_user = User(
                    taller_id=taller.id,
                    username=f"{TEST_MARKER}_mec{j}_t{i}",
                    email=f"mecanico{j}.taller{i}@test.com",
                    password_hash=password_hasher.hash_password("test123"),
                    is_active=True,
                    nombre_completo=f"Mecánico {j} Taller {i}",
                    telefono=f"320{i}{j:06d}"
                )
                db.add(mec_user)
                db.flush()
                db.add(UserRole(user_id=mec_user.id, role_id=role_mecanico.id))
                
                # Crear registro en tabla mecanicos (legacy)
                mecanico = Mecanico(
                    taller_id=taller.id,
                    nombre=f"Mecánico {j} Taller {i}",
                    activo=True
                )
                db.add(mecanico)
                db.flush()
                mecanicos_ids.append(mecanico.id)
                print_success(f"  Mecánico {j} creado: {mecanico.nombre}")
            
            # 4. Crear 5 vehículos con clientes
            vehiculos = []
            for v in range(1, 6):
                vehiculo = Vehiculo(
                    taller_id=taller.id,
                    placa=f"{TEST_MARKER[:3]}{i}{v:02d}",
                    marca=["Toyota", "Chevrolet", "Mazda", "Nissan", "Honda"][v-1],
                    modelo=["Corolla", "Spark", "3", "Versa", "Civic"][v-1],
                    anio=2015 + v,
                    color=["Rojo", "Azul", "Negro", "Blanco", "Gris"][v-1],
                    cilindraje="1600",
                    nombre_propietario=f"Cliente {v} Taller {i}",
                    telefono_propietario=f"350{i}{v:06d}"
                )
                db.add(vehiculo)
                db.flush()
                vehiculos.append(vehiculo)
            print_success(f"  5 vehículos creados")
            
            # 5. Crear 5 tickets (uno por vehículo)
            for idx, vehiculo in enumerate(vehiculos, 1):
                # Crear ticket
                fecha_ingreso = datetime.now() - timedelta(days=5-idx)
                ticket_codigo = f"TK-{vehiculo.placa}-{fecha_ingreso.strftime('%Y%m%d%H%M%S%f')}"
                
                ticket = Ticket(
                    taller_id=taller.id,
                    vehiculo_id=vehiculo.id,
                    ticket_codigo=ticket_codigo,
                    placa=vehiculo.placa,
                    fecha_ingreso=fecha_ingreso,
                    motivo_visita=f"Mantenimiento {idx} - Test Multi-Tenant",
                    observaciones_recepcion=f"Observaciones del ticket {idx}",
                    kilometraje=50000 + (idx * 10000),
                    estado_inicial="Buen estado general",
                    anticipo_recibido=100000,
                    metodo_pago_anticipo="EFECTIVO",
                    recepcionado_por=admin_user.username,
                    estado="ENTREGADO",
                    mecanico_asignado_id=mecanicos_ids[idx % 2],  # Alternar entre mecánicos
                    total_servicio=500000,
                    saldo_pendiente=0,
                    metodo_pago_final="EFECTIVO",
                    observaciones_finales="Trabajo completado satisfactoriamente",
                    recomendaciones="Próximo mantenimiento en 10,000 km",
                    fecha_cierre=fecha_ingreso + timedelta(days=2),
                    fecha_entrega=fecha_ingreso + timedelta(days=2, hours=2)
                )
                db.add(ticket)
                db.flush()
                
                # Crear 5 procesos
                for p in range(1, 6):
                    proceso = TicketProceso(
                        taller_id=taller.id,
                        ticket_id=ticket.id,
                        nombre=f"Proceso {p}",
                        descripcion=f"Descripción del proceso {p}",
                        mecanico=f"Mecánico {(p % 2) + 1} Taller {i}",
                        fecha_creacion=fecha_ingreso + timedelta(hours=p)
                    )
                    db.add(proceso)
                
                # Crear 5 repuestos
                for r in range(1, 6):
                    repuesto = TicketRepuesto(
                        taller_id=taller.id,
                        ticket_id=ticket.id,
                        nombre=f"Repuesto {r}",
                        cantidad=r,
                        marca_referencia=f"Marca_{r}",
                        fecha_creacion=fecha_ingreso + timedelta(hours=r+5)
                    )
                    db.add(repuesto)
                
                # Crear 5 fotos
                for f in range(1, 6):
                    foto = TicketFoto(
                        taller_id=taller.id,
                        ticket_id=ticket.id,
                        tipo="OTRA",
                        archivo_url=f"/uploads/test/foto_{f}.jpg",
                        descripcion=f"Foto {f} del ticket",
                        fecha_creacion=fecha_ingreso + timedelta(hours=f+10)
                    )
                    db.add(foto)
                
                # Crear movimientos de caja
                # Anticipo
                mov_anticipo = MovimientoCaja(
                    taller_id=taller.id,
                    tipo=TipoMovimiento.INGRESO_ANTICIPO,
                    ticket_id=ticket.id,
                    ticket_codigo=ticket.ticket_codigo,
                    placa=ticket.placa,
                    estado_ticket="ABIERTO",
                    valor=100000,
                    metodo_pago="EFECTIVO",
                    fecha_creacion=fecha_ingreso
                )
                db.add(mov_anticipo)
                
                # Cobro final
                mov_final = MovimientoCaja(
                    taller_id=taller.id,
                    tipo=TipoMovimiento.INGRESO_FINAL,
                    ticket_id=ticket.id,
                    ticket_codigo=ticket.ticket_codigo,
                    placa=ticket.placa,
                    estado_ticket="ENTREGADO",
                    valor=400000,
                    metodo_pago="EFECTIVO",
                    fecha_creacion=ticket.fecha_entrega
                )
                db.add(mov_final)
            
            print_success(f"  5 tickets creados con procesos, repuestos, fotos y movimientos")
            db.commit()
        
        print_header("DATOS DE PRUEBA CREADOS EXITOSAMENTE")
        print_info(f"Talleres creados: {len(talleres_creados)}")
        print_info(f"IDs de talleres: {talleres_creados}")
        print_info(f"Usuarios por taller: 1 admin + 2 mecánicos")
        print_info(f"Tickets por taller: 5 (cada uno con 5 procesos, 5 repuestos, 5 fotos)")
        print_warning(f"\nPara limpiar estos datos: python scripts/test_multi_tenant.py cleanup")
        
    except Exception as e:
        db.rollback()
        print_error(f"Error al crear datos: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def cleanup_test_data():
    """Limpiar SOLO los datos creados por este script"""
    print_header("LIMPIANDO DATOS DE PRUEBA")
    
    db = get_session()
    
    try:
        # Contar registros antes
        talleres_test = db.query(Taller).filter(Taller.nombre.like(f"{TEST_MARKER}%")).all()
        
        if not talleres_test:
            print_warning("No se encontraron datos de prueba para limpiar")
            return
        
        taller_ids = [t.id for t in talleres_test]
        print_info(f"Encontrados {len(taller_ids)} talleres de prueba")
        
        # Eliminar en orden inverso de dependencias
        print_info("Eliminando movimientos de caja...")
        deleted = db.query(MovimientoCaja).filter(MovimientoCaja.taller_id.in_(taller_ids)).delete(synchronize_session=False)
        print_success(f"  {deleted} movimientos eliminados")
        
        print_info("Eliminando fotos de tickets...")
        deleted = db.query(TicketFoto).filter(TicketFoto.taller_id.in_(taller_ids)).delete(synchronize_session=False)
        print_success(f"  {deleted} fotos eliminadas")
        
        print_info("Eliminando repuestos de tickets...")
        deleted = db.query(TicketRepuesto).filter(TicketRepuesto.taller_id.in_(taller_ids)).delete(synchronize_session=False)
        print_success(f"  {deleted} repuestos eliminados")
        
        print_info("Eliminando procesos de tickets...")
        deleted = db.query(TicketProceso).filter(TicketProceso.taller_id.in_(taller_ids)).delete(synchronize_session=False)
        print_success(f"  {deleted} procesos eliminados")
        
        print_info("Eliminando tickets...")
        deleted = db.query(Ticket).filter(Ticket.taller_id.in_(taller_ids)).delete(synchronize_session=False)
        print_success(f"  {deleted} tickets eliminados")
        
        print_info("Eliminando vehículos...")
        deleted = db.query(Vehiculo).filter(Vehiculo.taller_id.in_(taller_ids)).delete(synchronize_session=False)
        print_success(f"  {deleted} vehículos eliminados")
        
        print_info("Eliminando mecánicos...")
        deleted = db.query(Mecanico).filter(Mecanico.taller_id.in_(taller_ids)).delete(synchronize_session=False)
        print_success(f"  {deleted} mecánicos eliminados")
        
        print_info("Eliminando usuarios...")
        users_test = db.query(User).filter(User.username.like(f"{TEST_MARKER}%")).all()
        user_ids = [u.id for u in users_test]
        if user_ids:
            db.query(UserRole).filter(UserRole.user_id.in_(user_ids)).delete(synchronize_session=False)
            deleted = db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
            print_success(f"  {deleted} usuarios eliminados")
        
        print_info("Eliminando talleres...")
        deleted = db.query(Taller).filter(Taller.id.in_(taller_ids)).delete(synchronize_session=False)
        print_success(f"  {deleted} talleres eliminados")
        
        db.commit()
        print_header("LIMPIEZA COMPLETADA")
        
    except Exception as e:
        db.rollback()
        print_error(f"Error al limpiar datos: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def show_status():
    """Mostrar estado de los datos de prueba"""
    print_header("ESTADO DE DATOS DE PRUEBA")
    
    db = get_session()
    
    try:
        talleres = db.query(Taller).filter(Taller.nombre.like(f"{TEST_MARKER}%")).all()
        
        if not talleres:
            print_warning("No hay datos de prueba creados")
            print_info("Para crear datos: python scripts/test_multi_tenant.py create")
            return
        
        print_info(f"Talleres de prueba: {len(talleres)}")
        
        for taller in talleres:
            print(f"\n{Colors.CYAN}{'─'*60}{Colors.END}")
            print(f"{Colors.BOLD}{taller.nombre}{Colors.END} (ID: {taller.id})")
            print(f"{Colors.CYAN}{'─'*60}{Colors.END}")
            
            users = db.query(User).filter(User.taller_id == taller.id).count()
            mecanicos = db.query(Mecanico).filter(Mecanico.taller_id == taller.id).count()
            vehiculos = db.query(Vehiculo).filter(Vehiculo.taller_id == taller.id).count()
            tickets = db.query(Ticket).filter(Ticket.taller_id == taller.id).count()
            procesos = db.query(TicketProceso).filter(TicketProceso.taller_id == taller.id).count()
            repuestos = db.query(TicketRepuesto).filter(TicketRepuesto.taller_id == taller.id).count()
            fotos = db.query(TicketFoto).filter(TicketFoto.taller_id == taller.id).count()
            movimientos = db.query(MovimientoCaja).filter(MovimientoCaja.taller_id == taller.id).count()
            
            print(f"  Usuarios: {users}")
            print(f"  Mecánicos: {mecanicos}")
            print(f"  Vehículos: {vehiculos}")
            print(f"  Tickets: {tickets}")
            print(f"  Procesos: {procesos}")
            print(f"  Repuestos: {repuestos}")
            print(f"  Fotos: {fotos}")
            print(f"  Movimientos de caja: {movimientos}")
        
        print(f"\n{Colors.CYAN}{'─'*60}{Colors.END}")
        print_warning("Para limpiar: python scripts/test_multi_tenant.py cleanup")
        
    except Exception as e:
        print_error(f"Error al obtener estado: {e}")
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print_error("Uso: python scripts/test_multi_tenant.py [create|cleanup|status]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "create":
        create_test_data()
    elif command == "cleanup":
        cleanup_test_data()
    elif command == "status":
        show_status()
    else:
        print_error(f"Comando desconocido: {command}")
        print_info("Comandos disponibles: create, cleanup, status")
        sys.exit(1)


if __name__ == "__main__":
    main()
