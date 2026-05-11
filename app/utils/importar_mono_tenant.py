"""
Utilidad para importar datos de una BD mono-tenant a multi-tenant.

IMPORTANTE: La BD mono-tenant NO tiene columna taller_id en ninguna tabla.
Este script agrega automáticamente el taller_id al importar los datos.
"""
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from typing import Dict, List


def _tabla_existe(engine, tabla: str) -> bool:
    """Verifica si una tabla existe en la BD."""
    inspector = inspect(engine)
    return tabla in inspector.get_table_names()


def _columna_existe(engine, tabla: str, columna: str) -> bool:
    """Verifica si una columna existe en una tabla."""
    if not _tabla_existe(engine, tabla):
        return False
    inspector = inspect(engine)
    columnas = [col['name'] for col in inspector.get_columns(tabla)]
    return columna in columnas


def _obtener_columnas(engine, tabla: str) -> List[str]:
    """Obtiene la lista de columnas de una tabla."""
    inspector = inspect(engine)
    return [col['name'] for col in inspector.get_columns(tabla)]


def importar_desde_bd_temporal(db: Session, taller_id: int, temp_db_name: str) -> Dict[str, int]:
    """
    Importa datos desde una BD temporal (mono-tenant) al taller especificado.
    
    La BD mono-tenant NO tiene columna taller_id. Este método:
    1. Lee los datos de la BD origen (sin taller_id)
    2. Agrega el taller_id automáticamente
    3. Inserta en la BD multi-tenant
    
    Args:
        db: Sesión de la BD multi-tenant (destino)
        taller_id: ID del taller destino
        temp_db_name: Nombre de la BD temporal (origen)
        
    Returns:
        Dict con contadores de registros importados
    """
    # Conectar a la BD temporal usando variables de entorno
    db_user = os.getenv("DB_USER", "postgres")
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")
    db_password = os.getenv("DATABASE_PASSWORD") or os.getenv("DB_PASSWORD", "")
    temp_engine = create_engine(f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{temp_db_name}")
    
    resultado = {
        "usuarios": 0,
        "clientes": 0,
        "vehiculos": 0,
        "tickets": 0,
        "repuestos": 0,
        "citas": 0,
        "movimientos_caja": 0,
        "notificaciones": 0,
    }
    
    mapeo_usuarios = {}
    mapeo_clientes = {}
    mapeo_vehiculos = {}
    mapeo_tickets = {}
    
    try:
        # Verificar que las tablas existen en la BD origen
        # La BD mono-tenant puede tener 'users' o 'usuarios'
        tabla_usuarios = None
        if _tabla_existe(temp_engine, 'usuarios'):
            tabla_usuarios = 'usuarios'
        elif _tabla_existe(temp_engine, 'users'):
            tabla_usuarios = 'users'
        else:
            raise ValueError("La BD origen no tiene la tabla 'usuarios' ni 'users'. Verifica que sea un backup válido.")
        
        # 1. Importar usuarios (sin taller_id en origen)
        with temp_engine.connect() as temp_conn:
            # Obtener columnas disponibles en la BD origen
            columnas_origen = _obtener_columnas(temp_engine, tabla_usuarios)
            
            # Construir SELECT dinámicamente según las columnas disponibles
            select_cols = []
            for col in ['id', 'username', 'email', 'password_hash', 'nombre_completo', 
                       'telefono', 'activo', 'created_at', 'updated_at']:
                if col in columnas_origen:
                    select_cols.append(col)
            
            if not select_cols:
                raise ValueError("La tabla usuarios no tiene las columnas esperadas")
            
            query = f"SELECT {', '.join(select_cols)} FROM {tabla_usuarios} WHERE username != 'superadmin'"
            usuarios = temp_conn.execute(text(query)).fetchall()
            
            for usuario in usuarios:
                # Verificar si ya existe
                existe = db.execute(text("""
                    SELECT id FROM usuarios 
                    WHERE username = :username AND taller_id = :taller_id
                """), {"username": usuario.username, "taller_id": taller_id}).fetchone()
                
                if existe:
                    mapeo_usuarios[usuario.id] = existe.id
                    continue
                
                # Insertar usuario CON taller_id (que no existe en origen)
                result = db.execute(text("""
                    INSERT INTO usuarios (
                        taller_id, username, email, password_hash, nombre_completo,
                        telefono, activo, created_at, updated_at
                    ) VALUES (
                        :taller_id, :username, :email, :password_hash, :nombre_completo,
                        :telefono, :activo, :created_at, :updated_at
                    ) RETURNING id
                """), {
                    "taller_id": taller_id,  # ← AGREGADO AUTOMÁTICAMENTE
                    "username": usuario.username,
                    "email": usuario.email if hasattr(usuario, 'email') else None,
                    "password_hash": usuario.password_hash,
                    "nombre_completo": usuario.nombre_completo if hasattr(usuario, 'nombre_completo') else None,
                    "telefono": usuario.telefono if hasattr(usuario, 'telefono') else None,
                    "activo": usuario.activo if hasattr(usuario, 'activo') else True,
                    "created_at": usuario.created_at if hasattr(usuario, 'created_at') else None,
                    "updated_at": usuario.updated_at if hasattr(usuario, 'updated_at') else None,
                })
                
                nuevo_id = result.fetchone()[0]
                mapeo_usuarios[usuario.id] = nuevo_id
                resultado["usuarios"] += 1
            
            db.flush()
        
        # 2. Importar roles de usuarios
        # La tabla puede llamarse 'usuario_roles' o 'user_roles'
        tabla_roles = None
        if _tabla_existe(temp_engine, 'usuario_roles'):
            tabla_roles = 'usuario_roles'
        elif _tabla_existe(temp_engine, 'user_roles'):
            tabla_roles = 'user_roles'
        
        if tabla_roles:
            with temp_engine.connect() as temp_conn:
                roles = temp_conn.execute(text(f"""
                    SELECT user_id, role_id FROM {tabla_roles}
                """)).fetchall()
            
            for rol in roles:
                if rol.user_id not in mapeo_usuarios:
                    continue
                
                new_user_id = mapeo_usuarios[rol.user_id]
                
                # Verificar si ya existe
                existe = db.execute(text("""
                    SELECT 1 FROM usuario_roles 
                    WHERE user_id = :user_id AND role_id = :role_id
                """), {"user_id": new_user_id, "role_id": rol.role_id}).fetchone()
                
                if existe:
                    continue
                
                db.execute(text("""
                    INSERT INTO usuario_roles (user_id, role_id)
                    VALUES (:user_id, :role_id)
                """), {"user_id": new_user_id, "role_id": rol.role_id})
            
            db.flush()
        
        # 3. Importar clientes (sin taller_id en origen)
        if _tabla_existe(temp_engine, 'clientes'):
            with temp_engine.connect() as temp_conn:
                columnas_origen = _obtener_columnas(temp_engine, 'clientes')
                
                # Construir SELECT dinámicamente
                select_cols = []
                for col in ['id', 'nombre', 'apellido', 'email', 'telefono', 'direccion',
                           'documento_identidad', 'created_at', 'updated_at']:
                    if col in columnas_origen:
                        select_cols.append(col)
                
                query = f"SELECT {', '.join(select_cols)} FROM clientes"
                clientes = temp_conn.execute(text(query)).fetchall()
                
                for cliente in clientes:
                    result = db.execute(text("""
                        INSERT INTO clientes (
                            taller_id, nombre, apellido, email, telefono, direccion,
                            documento_identidad, created_at, updated_at
                        ) VALUES (
                            :taller_id, :nombre, :apellido, :email, :telefono, :direccion,
                            :documento_identidad, :created_at, :updated_at
                        ) RETURNING id
                    """), {
                        "taller_id": taller_id,  # ← AGREGADO AUTOMÁTICAMENTE
                        "nombre": cliente.nombre if hasattr(cliente, 'nombre') else None,
                        "apellido": cliente.apellido if hasattr(cliente, 'apellido') else None,
                        "email": cliente.email if hasattr(cliente, 'email') else None,
                        "telefono": cliente.telefono if hasattr(cliente, 'telefono') else None,
                        "direccion": cliente.direccion if hasattr(cliente, 'direccion') else None,
                        "documento_identidad": cliente.documento_identidad if hasattr(cliente, 'documento_identidad') else None,
                        "created_at": cliente.created_at if hasattr(cliente, 'created_at') else None,
                        "updated_at": cliente.updated_at if hasattr(cliente, 'updated_at') else None,
                    })
                    
                    nuevo_id = result.fetchone()[0]
                    mapeo_clientes[cliente.id] = nuevo_id
                    resultado["clientes"] += 1
                
                db.flush()
        
        # 4. Importar vehículos (sin taller_id en origen)
        if _tabla_existe(temp_engine, 'vehiculos'):
            with temp_engine.connect() as temp_conn:
                columnas_origen = _obtener_columnas(temp_engine, 'vehiculos')
                
                select_cols = []
                for col in ['id', 'cliente_id', 'placa', 'marca', 'modelo', 'anio', 'color',
                           'vin', 'kilometraje', 'created_at', 'updated_at']:
                    if col in columnas_origen:
                        select_cols.append(col)
                
                query = f"SELECT {', '.join(select_cols)} FROM vehiculos"
                vehiculos = temp_conn.execute(text(query)).fetchall()
                
                for vehiculo in vehiculos:
                    if vehiculo.cliente_id not in mapeo_clientes:
                        continue
                    
                    new_cliente_id = mapeo_clientes[vehiculo.cliente_id]
                    
                    result = db.execute(text("""
                        INSERT INTO vehiculos (
                            taller_id, cliente_id, placa, marca, modelo, anio, color,
                            vin, kilometraje, created_at, updated_at
                        ) VALUES (
                            :taller_id, :cliente_id, :placa, :marca, :modelo, :anio, :color,
                            :vin, :kilometraje, :created_at, :updated_at
                        ) RETURNING id
                    """), {
                        "taller_id": taller_id,  # ← AGREGADO AUTOMÁTICAMENTE
                        "cliente_id": new_cliente_id,
                        "placa": vehiculo.placa if hasattr(vehiculo, 'placa') else None,
                        "marca": vehiculo.marca if hasattr(vehiculo, 'marca') else None,
                        "modelo": vehiculo.modelo if hasattr(vehiculo, 'modelo') else None,
                        "anio": vehiculo.anio if hasattr(vehiculo, 'anio') else None,
                        "color": vehiculo.color if hasattr(vehiculo, 'color') else None,
                        "vin": vehiculo.vin if hasattr(vehiculo, 'vin') else None,
                        "kilometraje": vehiculo.kilometraje if hasattr(vehiculo, 'kilometraje') else None,
                        "created_at": vehiculo.created_at if hasattr(vehiculo, 'created_at') else None,
                        "updated_at": vehiculo.updated_at if hasattr(vehiculo, 'updated_at') else None,
                    })
                    
                    nuevo_id = result.fetchone()[0]
                    mapeo_vehiculos[vehiculo.id] = nuevo_id
                    resultado["vehiculos"] += 1
                
                db.flush()
        
        # 5. Importar tickets (sin taller_id en origen)
        if _tabla_existe(temp_engine, 'tickets'):
            with temp_engine.connect() as temp_conn:
                columnas_origen = _obtener_columnas(temp_engine, 'tickets')
                
                select_cols = []
                for col in ['id', 'vehiculo_id', 'recepcionista_user_id', 'mecanico_user_id',
                           'estado', 'prioridad', 'descripcion_problema', 'diagnostico',
                           'trabajos_realizados', 'observaciones', 'fecha_ingreso',
                           'fecha_estimada_salida', 'fecha_salida', 'costo_mano_obra',
                           'costo_repuestos', 'costo_total', 'created_at', 'updated_at']:
                    if col in columnas_origen:
                        select_cols.append(col)
                
                query = f"SELECT {', '.join(select_cols)} FROM tickets"
                tickets = temp_conn.execute(text(query)).fetchall()
                
                for ticket in tickets:
                    if ticket.vehiculo_id not in mapeo_vehiculos:
                        continue
                    
                    new_vehiculo_id = mapeo_vehiculos[ticket.vehiculo_id]
                    new_recepcionista_id = mapeo_usuarios.get(ticket.recepcionista_user_id) if hasattr(ticket, 'recepcionista_user_id') else None
                    new_mecanico_id = mapeo_usuarios.get(ticket.mecanico_user_id) if hasattr(ticket, 'mecanico_user_id') else None
                    
                    result = db.execute(text("""
                        INSERT INTO tickets (
                            taller_id, vehiculo_id, recepcionista_user_id, mecanico_user_id,
                            estado, prioridad, descripcion_problema, diagnostico,
                            trabajos_realizados, observaciones, fecha_ingreso,
                            fecha_estimada_salida, fecha_salida, costo_mano_obra,
                            costo_repuestos, costo_total, created_at, updated_at
                        ) VALUES (
                            :taller_id, :vehiculo_id, :recepcionista_user_id, :mecanico_user_id,
                            :estado, :prioridad, :descripcion_problema, :diagnostico,
                            :trabajos_realizados, :observaciones, :fecha_ingreso,
                            :fecha_estimada_salida, :fecha_salida, :costo_mano_obra,
                            :costo_repuestos, :costo_total, :created_at, :updated_at
                        ) RETURNING id
                    """), {
                        "taller_id": taller_id,  # ← AGREGADO AUTOMÁTICAMENTE
                        "vehiculo_id": new_vehiculo_id,
                        "recepcionista_user_id": new_recepcionista_id,
                        "mecanico_user_id": new_mecanico_id,
                        "estado": ticket.estado if hasattr(ticket, 'estado') else 'PENDIENTE',
                        "prioridad": ticket.prioridad if hasattr(ticket, 'prioridad') else 'MEDIA',
                        "descripcion_problema": ticket.descripcion_problema if hasattr(ticket, 'descripcion_problema') else None,
                        "diagnostico": ticket.diagnostico if hasattr(ticket, 'diagnostico') else None,
                        "trabajos_realizados": ticket.trabajos_realizados if hasattr(ticket, 'trabajos_realizados') else None,
                        "observaciones": ticket.observaciones if hasattr(ticket, 'observaciones') else None,
                        "fecha_ingreso": ticket.fecha_ingreso if hasattr(ticket, 'fecha_ingreso') else None,
                        "fecha_estimada_salida": ticket.fecha_estimada_salida if hasattr(ticket, 'fecha_estimada_salida') else None,
                        "fecha_salida": ticket.fecha_salida if hasattr(ticket, 'fecha_salida') else None,
                        "costo_mano_obra": ticket.costo_mano_obra if hasattr(ticket, 'costo_mano_obra') else 0,
                        "costo_repuestos": ticket.costo_repuestos if hasattr(ticket, 'costo_repuestos') else 0,
                        "costo_total": ticket.costo_total if hasattr(ticket, 'costo_total') else 0,
                        "created_at": ticket.created_at if hasattr(ticket, 'created_at') else None,
                        "updated_at": ticket.updated_at if hasattr(ticket, 'updated_at') else None,
                    })
                    
                    nuevo_id = result.fetchone()[0]
                    mapeo_tickets[ticket.id] = nuevo_id
                    resultado["tickets"] += 1
                
                db.flush()
        
        # 6. Importar otras tablas (repuestos, citas, etc.)
        # TODO: Agregar importación de otras tablas según sea necesario
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al importar datos: {str(e)}")
    finally:
        temp_engine.dispose()
    
    return resultado
