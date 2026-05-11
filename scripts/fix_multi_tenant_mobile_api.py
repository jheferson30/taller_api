#!/usr/bin/env python3
"""
Script para corregir automáticamente los problemas de multi-tenancy en mobile_api_ruta.py
"""

import re
from pathlib import Path

def fix_mobile_api():
    file_path = Path(__file__).parent.parent / 'app' / 'rutas' / 'mobile_api_ruta.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Agregar Request a las funciones que no lo tienen
    functions_to_fix = [
        'obtener_ticket_mobile',
        'listar_procesos_mobile',
        'crear_proceso_mobile',
        'crear_proceso_con_foto_mobile',
        'listar_repuestos_mobile',
        'crear_repuesto_mobile',
        'listar_fotos_mobile',
        'obtener_resumen_ticket',
        'obtener_estadisticas_mobile',
        'subir_foto_mobile',
        'entregar_ticket_mobile',
        'eliminar_foto_mobile',
        'listar_compras_mobile',
        'crear_compra_mobile',
        'eliminar_compra_mobile',
        'listar_cobros_mobile',
        'crear_cobro_mobile',
        'eliminar_cobro_mobile',
        'actualizar_finanzas_mobile',
        'listar_mecanicos_mobile',
        'listar_procesos_rapidos_mobile',
        'listar_cobros_rapidos_mobile',
        'sincronizar_operaciones_batch',
        'economia_hoy_mobile',
    ]
    
    # 2. Agregar taller_id a las queries
    # Patrón: db.query(Ticket).filter(Ticket.id == ticket_id)
    # Reemplazar por: db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.taller_id == taller_id)
    
    # Agregar Request como primer parámetro después de self/cls si no existe
    for func_name in functions_to_fix:
        # Buscar la definición de la función
        pattern = rf'(def {func_name}\([^)]*?)(\))'
        match = re.search(pattern, content)
        if match:
            params = match.group(1)
            if 'request: Request' not in params and 'Request' not in params:
                # Agregar request: Request como primer parámetro
                if params.endswith('('):
                    new_params = params + 'request: Request, '
                else:
                    new_params = params.replace('(', '(request: Request, ', 1)
                content = content.replace(match.group(0), new_params + match.group(2))
    
    # 3. Agregar extracción de taller_id al inicio de cada función
    # Buscar funciones y agregar taller_id = request.state.taller_id después de la definición
    for func_name in functions_to_fix:
        # Buscar el cuerpo de la función
        pattern = rf'(def {func_name}\([^)]*\):)\n(\s+"""[^"]*""")?(\n\s+)'
        match = re.search(pattern, content)
        if match:
            # Agregar taller_id después del docstring si existe
            indent = match.group(3).strip('\n')
            taller_id_line = f'{indent}taller_id = request.state.taller_id\n{indent}'
            # Solo agregar si no existe ya
            if 'taller_id = request.state.taller_id' not in content[match.end():match.end()+200]:
                content = content[:match.end()] + taller_id_line + content[match.end():]
    
    # 4. Corregir queries específicas
    replacements = [
        # Tickets
        (r'db\.query\(Ticket\)\.filter\(Ticket\.id == ticket_id\)\.first\(\)',
         'db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.taller_id == taller_id).first()'),
        
        (r'db\.query\(Ticket\)\.filter\(Ticket\.estado == estado\)\.count\(\)',
         'db.query(Ticket).filter(Ticket.estado == estado, Ticket.taller_id == taller_id).count()'),
        
        (r'db\.query\(Ticket\)\.count\(\)',
         'db.query(Ticket).filter(Ticket.taller_id == taller_id).count()'),
        
        # Vehículos
        (r'db\.query\(Vehiculo\)\.filter\(Vehiculo\.id == ticket\.vehiculo_id\)\.first\(\)',
         'db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id, Vehiculo.taller_id == taller_id).first()'),
        
        # Procesos
        (r'db\.query\(TicketProceso\)\.filter\(TicketProceso\.ticket_id == ticket_id\)\.all\(\)',
         'db.query(TicketProceso).filter(TicketProceso.ticket_id == ticket_id, TicketProceso.taller_id == taller_id).all()'),
        
        # Repuestos
        (r'db\.query\(TicketRepuesto\)\.filter\(TicketRepuesto\.ticket_id == ticket_id\)\.all\(\)',
         'db.query(TicketRepuesto).filter(TicketRepuesto.ticket_id == ticket_id, TicketRepuesto.taller_id == taller_id).all()'),
        
        # Fotos
        (r'db\.query\(TicketFoto\)\.filter\(TicketFoto\.ticket_id == ticket_id\)\.all\(\)',
         'db.query(TicketFoto).filter(TicketFoto.ticket_id == ticket_id, TicketFoto.taller_id == taller_id).all()'),
        
        (r'db\.query\(TicketFoto\)\.filter\(TicketFoto\.id == foto_id, TicketFoto\.ticket_id == ticket_id\)\.first\(\)',
         'db.query(TicketFoto).filter(TicketFoto.id == foto_id, TicketFoto.ticket_id == ticket_id, TicketFoto.taller_id == taller_id).first()'),
        
        # Compras
        (r'db\.query\(TicketCompra\)\.filter\(TicketCompra\.ticket_id == ticket_id\)\.all\(\)',
         'db.query(TicketCompra).filter(TicketCompra.ticket_id == ticket_id, TicketCompra.taller_id == taller_id).all()'),
        
        (r'db\.query\(TicketCompra\)\.filter\(TicketCompra\.id == compra_id, TicketCompra\.ticket_id == ticket_id\)\.first\(\)',
         'db.query(TicketCompra).filter(TicketCompra.id == compra_id, TicketCompra.ticket_id == ticket_id, TicketCompra.taller_id == taller_id).first()'),
        
        # Cobros
        (r'db\.query\(TicketCobro\)\.filter\(TicketCobro\.ticket_id == ticket_id\)\.all\(\)',
         'db.query(TicketCobro).filter(TicketCobro.ticket_id == ticket_id, TicketCobro.taller_id == taller_id).all()'),
        
        (r'db\.query\(TicketCobro\)\.filter\(TicketCobro\.id == cobro_id, TicketCobro\.ticket_id == ticket_id\)\.first\(\)',
         'db.query(TicketCobro).filter(TicketCobro.id == cobro_id, TicketCobro.ticket_id == ticket_id, TicketCobro.taller_id == taller_id).first()'),
        
        # Mecánicos
        (r'db\.query\(Mecanico\)\.filter\(Mecanico\.activo == True\)\.order_by\(Mecanico\.nombre\)\.all\(\)',
         'db.query(Mecanico).filter(Mecanico.activo == True, Mecanico.taller_id == taller_id).order_by(Mecanico.nombre).all()'),
        
        # ConfiguracionTaller
        (r'db\.query\(ConfiguracionTaller\)\.filter\(ConfiguracionTaller\.id == 1\)\.first\(\)',
         'db.query(ConfiguracionTaller).filter(ConfiguracionTaller.taller_id == taller_id).first()'),
        
        # MovimientoCaja
        (r'db\.query\(MovimientoCaja\)\.filter\(func\.date\(MovimientoCaja\.fecha_creacion\) == hoy\)\.all\(\)',
         'db.query(MovimientoCaja).filter(func.date(MovimientoCaja.fecha_creacion) == hoy, MovimientoCaja.taller_id == taller_id).all()'),
        
        # Tickets con fecha
        (r'db\.query\(Ticket\)\.filter\(\s*func\.date\(Ticket\.fecha_ingreso\) == hoy, Ticket\.estado\.in_\(\["FINALIZADO", "ENTREGADO"\]\)\s*\)\.count\(\)',
         'db.query(Ticket).filter(func.date(Ticket.fecha_ingreso) == hoy, Ticket.estado.in_(["FINALIZADO", "ENTREGADO"]), Ticket.taller_id == taller_id).count()'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Guardar el archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Archivo {file_path} corregido exitosamente")
    print("   - Agregado Request a funciones")
    print("   - Agregado extracción de taller_id")
    print("   - Corregidas queries para filtrar por taller_id")

if __name__ == '__main__':
    fix_mobile_api()
