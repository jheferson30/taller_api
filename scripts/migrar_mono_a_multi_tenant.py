#!/usr/bin/env python3
"""
Script de Migración: Mono-Tenant → Multi-Tenant

Este script migra datos de una instalación mono-tenant (un taller por servidor)
a la nueva arquitectura multi-tenant (múltiples talleres en una BD).

IMPORTANTE:
- Hacer backup completo antes de ejecutar
- Probar primero en un entorno de staging
- Verificar que todas las tablas tengan datos correctos después

Uso:
    python scripts/migrar_mono_a_multi_tenant.py \
        --source-db "postgresql://user:pass@host:5432/old_db" \
        --target-db "postgresql://user:pass@host:5432/new_db" \
        --taller-nombre "Nombre del Taller" \
        --taller-email "contacto@taller.com"
"""

import argparse
import sys
from datetime import datetime
from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor


class MigradorMonoAMultiTenant:
    """Migra datos de mono-tenant a multi-tenant."""

    # Tablas que requieren taller_id
    TABLAS_CON_TALLER_ID = [
        'usuarios',
        'vehiculos',
        'clientes',
        'tickets',
        'repuestos',
        'citas',
        'movimientos_caja',
        'fotos_ticket',
        'notificaciones',
        'audit_logs',
        'configuracion_taller',
        'inventario_repuestos',
        'servicios',
        'facturas',
        'pagos',
        'reportes'
    ]

    def __init__(self, source_dsn: str, target_dsn: str):
        self.source_dsn = source_dsn
        self.target_dsn = target_dsn
        self.taller_id = None
        self.mapeo_usuarios = {}  # old_id -> new_id
        self.mapeo_clientes = {}
        self.mapeo_vehiculos = {}
        self.mapeo_tickets = {}

    def conectar_source(self):
        """Conecta a la BD origen (mono-tenant)."""
        return psycopg2.connect(self.source_dsn, cursor_factory=RealDictCursor)

    def conectar_target(self):
        """Conecta a la BD destino (multi-tenant)."""
        return psycopg2.connect(self.target_dsn, cursor_factory=RealDictCursor)

    def crear_taller(self, nombre: str, email: str, telefono: str = None) -> int:
        """
        Crea el taller en el sistema multi-tenant.
        
        Returns:
            int: ID del taller creado
        """
        print(f"\n📋 Creando taller: {nombre}")
        
        with self.conectar_target() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO talleres (
                        nombre, email, telefono, estado, plan, 
                        fecha_inicio_plan, fecha_fin_plan, created_at
                    ) VALUES (
                        %s, %s, %s, 'ACTIVO', 'PROFESIONAL',
                        CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year', NOW()
                    )
                    RETURNING id
                """, (nombre, email, telefono))
                
                taller_id = cur.fetchone()['id']
                conn.commit()
                
                print(f"✅ Taller creado con ID: {taller_id}")
                return taller_id

    def migrar_usuarios(self):
        """Migra usuarios y asigna taller_id."""
        print("\n👥 Migrando usuarios...")
        
        with self.conectar_source() as src_conn:
            with src_conn.cursor() as src_cur:
                src_cur.execute("""
                    SELECT id, username, email, password_hash, nombre_completo,
                           telefono, activo, created_at, updated_at
                    FROM usuarios
                    WHERE username != 'superadmin'  -- No migrar SUPER_ADMIN
                """)
                usuarios = src_cur.fetchall()

        with self.conectar_target() as tgt_conn:
            with tgt_conn.cursor() as tgt_cur:
                for usuario in usuarios:
                    # Verificar si el username ya existe
                    tgt_cur.execute(
                        "SELECT id FROM usuarios WHERE username = %s AND taller_id = %s",
                        (usuario['username'], self.taller_id)
                    )
                    existe = tgt_cur.fetchone()
                    
                    if existe:
                        print(f"⚠️  Usuario '{usuario['username']}' ya existe, saltando...")
                        self.mapeo_usuarios[usuario['id']] = existe['id']
                        continue

                    tgt_cur.execute("""
                        INSERT INTO usuarios (
                            taller_id, username, email, password_hash, nombre_completo,
                            telefono, activo, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        self.taller_id,
                        usuario['username'],
                        usuario['email'],
                        usuario['password_hash'],
                        usuario['nombre_completo'],
                        usuario['telefono'],
                        usuario['activo'],
                        usuario['created_at'],
                        usuario['updated_at']
                    ))
                    
                    nuevo_id = tgt_cur.fetchone()['id']
                    self.mapeo_usuarios[usuario['id']] = nuevo_id
                    
                tgt_conn.commit()
        
        print(f"✅ {len(self.mapeo_usuarios)} usuarios migrados")

    def migrar_roles_usuarios(self):
        """Migra la relación usuarios-roles."""
        print("\n🔐 Migrando roles de usuarios...")
        
        with self.conectar_source() as src_conn:
            with src_conn.cursor() as src_cur:
                src_cur.execute("SELECT user_id, role_id FROM usuario_roles")
                roles = src_cur.fetchall()

        with self.conectar_target() as tgt_conn:
            with tgt_conn.cursor() as tgt_cur:
                for rol in roles:
                    old_user_id = rol['user_id']
                    if old_user_id not in self.mapeo_usuarios:
                        continue
                    
                    new_user_id = self.mapeo_usuarios[old_user_id]
                    
                    # Verificar si ya existe
                    tgt_cur.execute(
                        "SELECT 1 FROM usuario_roles WHERE user_id = %s AND role_id = %s",
                        (new_user_id, rol['role_id'])
                    )
                    if tgt_cur.fetchone():
                        continue
                    
                    tgt_cur.execute(
                        "INSERT INTO usuario_roles (user_id, role_id) VALUES (%s, %s)",
                        (new_user_id, rol['role_id'])
                    )
                
                tgt_conn.commit()
        
        print(f"✅ Roles migrados")

    def migrar_clientes(self):
        """Migra clientes."""
        print("\n👤 Migrando clientes...")
        
        with self.conectar_source() as src_conn:
            with src_conn.cursor() as src_cur:
                src_cur.execute("""
                    SELECT id, nombre, apellido, email, telefono, direccion,
                           documento_identidad, created_at, updated_at
                    FROM clientes
                """)
                clientes = src_cur.fetchall()

        with self.conectar_target() as tgt_conn:
            with tgt_conn.cursor() as tgt_cur:
                for cliente in clientes:
                    tgt_cur.execute("""
                        INSERT INTO clientes (
                            taller_id, nombre, apellido, email, telefono, direccion,
                            documento_identidad, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        self.taller_id,
                        cliente['nombre'],
                        cliente['apellido'],
                        cliente['email'],
                        cliente['telefono'],
                        cliente['direccion'],
                        cliente['documento_identidad'],
                        cliente['created_at'],
                        cliente['updated_at']
                    ))
                    
                    nuevo_id = tgt_cur.fetchone()['id']
                    self.mapeo_clientes[cliente['id']] = nuevo_id
                
                tgt_conn.commit()
        
        print(f"✅ {len(self.mapeo_clientes)} clientes migrados")

    def migrar_vehiculos(self):
        """Migra vehículos."""
        print("\n🚗 Migrando vehículos...")
        
        with self.conectar_source() as src_conn:
            with src_conn.cursor() as src_cur:
                src_cur.execute("""
                    SELECT id, cliente_id, placa, marca, modelo, anio, color,
                           vin, kilometraje, created_at, updated_at
                    FROM vehiculos
                """)
                vehiculos = src_cur.fetchall()

        with self.conectar_target() as tgt_conn:
            with tgt_conn.cursor() as tgt_cur:
                for vehiculo in vehiculos:
                    old_cliente_id = vehiculo['cliente_id']
                    if old_cliente_id not in self.mapeo_clientes:
                        print(f"⚠️  Vehículo {vehiculo['placa']} sin cliente, saltando...")
                        continue
                    
                    new_cliente_id = self.mapeo_clientes[old_cliente_id]
                    
                    tgt_cur.execute("""
                        INSERT INTO vehiculos (
                            taller_id, cliente_id, placa, marca, modelo, anio, color,
                            vin, kilometraje, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        self.taller_id,
                        new_cliente_id,
                        vehiculo['placa'],
                        vehiculo['marca'],
                        vehiculo['modelo'],
                        vehiculo['anio'],
                        vehiculo['color'],
                        vehiculo['vin'],
                        vehiculo['kilometraje'],
                        vehiculo['created_at'],
                        vehiculo['updated_at']
                    ))
                    
                    nuevo_id = tgt_cur.fetchone()['id']
                    self.mapeo_vehiculos[vehiculo['id']] = nuevo_id
                
                tgt_conn.commit()
        
        print(f"✅ {len(self.mapeo_vehiculos)} vehículos migrados")

    def migrar_tickets(self):
        """Migra tickets (órdenes de trabajo)."""
        print("\n🎫 Migrando tickets...")
        
        with self.conectar_source() as src_conn:
            with src_conn.cursor() as src_cur:
                src_cur.execute("""
                    SELECT id, vehiculo_id, recepcionista_user_id, mecanico_user_id,
                           estado, prioridad, descripcion_problema, diagnostico,
                           trabajos_realizados, observaciones, fecha_ingreso,
                           fecha_estimada_salida, fecha_salida, costo_mano_obra,
                           costo_repuestos, costo_total, created_at, updated_at
                    FROM tickets
                """)
                tickets = src_cur.fetchall()

        with self.conectar_target() as tgt_conn:
            with tgt_conn.cursor() as tgt_cur:
                for ticket in tickets:
                    old_vehiculo_id = ticket['vehiculo_id']
                    if old_vehiculo_id not in self.mapeo_vehiculos:
                        print(f"⚠️  Ticket {ticket['id']} sin vehículo, saltando...")
                        continue
                    
                    new_vehiculo_id = self.mapeo_vehiculos[old_vehiculo_id]
                    new_recepcionista_id = self.mapeo_usuarios.get(ticket['recepcionista_user_id'])
                    new_mecanico_id = self.mapeo_usuarios.get(ticket['mecanico_user_id'])
                    
                    tgt_cur.execute("""
                        INSERT INTO tickets (
                            taller_id, vehiculo_id, recepcionista_user_id, mecanico_user_id,
                            estado, prioridad, descripcion_problema, diagnostico,
                            trabajos_realizados, observaciones, fecha_ingreso,
                            fecha_estimada_salida, fecha_salida, costo_mano_obra,
                            costo_repuestos, costo_total, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        self.taller_id,
                        new_vehiculo_id,
                        new_recepcionista_id,
                        new_mecanico_id,
                        ticket['estado'],
                        ticket['prioridad'],
                        ticket['descripcion_problema'],
                        ticket['diagnostico'],
                        ticket['trabajos_realizados'],
                        ticket['observaciones'],
                        ticket['fecha_ingreso'],
                        ticket['fecha_estimada_salida'],
                        ticket['fecha_salida'],
                        ticket['costo_mano_obra'],
                        ticket['costo_repuestos'],
                        ticket['costo_total'],
                        ticket['created_at'],
                        ticket['updated_at']
                    ))
                    
                    nuevo_id = tgt_cur.fetchone()['id']
                    self.mapeo_tickets[ticket['id']] = nuevo_id
                
                tgt_conn.commit()
        
        print(f"✅ {len(self.mapeo_tickets)} tickets migrados")

    def migrar_tabla_generica(self, tabla: str, mapeos: Dict[str, Dict[int, int]]):
        """
        Migra una tabla genérica agregando taller_id y mapeando foreign keys.
        
        Args:
            tabla: Nombre de la tabla
            mapeos: Dict con columnas FK y sus mapeos {columna: {old_id: new_id}}
        """
        print(f"\n📦 Migrando {tabla}...")
        
        with self.conectar_source() as src_conn:
            with src_conn.cursor() as src_cur:
                src_cur.execute(f"SELECT * FROM {tabla}")
                registros = src_cur.fetchall()
                
                if not registros:
                    print(f"   (vacía)")
                    return

        with self.conectar_target() as tgt_conn:
            with tgt_conn.cursor() as tgt_cur:
                migrados = 0
                for registro in registros:
                    # Mapear foreign keys
                    datos = dict(registro)
                    skip = False
                    
                    for columna_fk, mapeo in mapeos.items():
                        if columna_fk in datos and datos[columna_fk] is not None:
                            old_id = datos[columna_fk]
                            if old_id not in mapeo:
                                skip = True
                                break
                            datos[columna_fk] = mapeo[old_id]
                    
                    if skip:
                        continue
                    
                    # Agregar taller_id
                    datos['taller_id'] = self.taller_id
                    
                    # Construir INSERT
                    columnas = ', '.join(datos.keys())
                    placeholders = ', '.join(['%s'] * len(datos))
                    valores = list(datos.values())
                    
                    try:
                        tgt_cur.execute(
                            f"INSERT INTO {tabla} ({columnas}) VALUES ({placeholders})",
                            valores
                        )
                        migrados += 1
                    except Exception as e:
                        print(f"⚠️  Error en {tabla}: {e}")
                        continue
                
                tgt_conn.commit()
        
        print(f"✅ {migrados} registros migrados")

    def ejecutar_migracion(self, nombre_taller: str, email_taller: str, telefono_taller: str = None):
        """Ejecuta la migración completa."""
        print("=" * 60)
        print("🚀 MIGRACIÓN MONO-TENANT → MULTI-TENANT")
        print("=" * 60)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Taller: {nombre_taller}")
        print("=" * 60)
        
        try:
            # 1. Crear taller
            self.taller_id = self.crear_taller(nombre_taller, email_taller, telefono_taller)
            
            # 2. Migrar usuarios y roles
            self.migrar_usuarios()
            self.migrar_roles_usuarios()
            
            # 3. Migrar clientes
            self.migrar_clientes()
            
            # 4. Migrar vehículos
            self.migrar_vehiculos()
            
            # 5. Migrar tickets
            self.migrar_tickets()
            
            # 6. Migrar tablas relacionadas
            self.migrar_tabla_generica('repuestos', {
                'ticket_id': self.mapeo_tickets
            })
            
            self.migrar_tabla_generica('fotos_ticket', {
                'ticket_id': self.mapeo_tickets
            })
            
            self.migrar_tabla_generica('citas', {
                'vehiculo_id': self.mapeo_vehiculos,
                'usuario_id': self.mapeo_usuarios
            })
            
            self.migrar_tabla_generica('movimientos_caja', {
                'ticket_id': self.mapeo_tickets,
                'usuario_id': self.mapeo_usuarios
            })
            
            self.migrar_tabla_generica('notificaciones', {
                'destinatario_user_id': self.mapeo_usuarios
            })
            
            print("\n" + "=" * 60)
            print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            print(f"Taller ID: {self.taller_id}")
            print(f"Usuarios migrados: {len(self.mapeo_usuarios)}")
            print(f"Clientes migrados: {len(self.mapeo_clientes)}")
            print(f"Vehículos migrados: {len(self.mapeo_vehiculos)}")
            print(f"Tickets migrados: {len(self.mapeo_tickets)}")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ ERROR EN LA MIGRACIÓN: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Migrar de mono-tenant a multi-tenant')
    parser.add_argument('--source-db', required=True, help='DSN de la BD origen')
    parser.add_argument('--target-db', required=True, help='DSN de la BD destino')
    parser.add_argument('--taller-nombre', required=True, help='Nombre del taller')
    parser.add_argument('--taller-email', required=True, help='Email del taller')
    parser.add_argument('--taller-telefono', help='Teléfono del taller')
    
    args = parser.parse_args()
    
    migrador = MigradorMonoAMultiTenant(args.source_db, args.target_db)
    migrador.ejecutar_migracion(
        args.taller_nombre,
        args.taller_email,
        args.taller_telefono
    )


if __name__ == '__main__':
    main()
