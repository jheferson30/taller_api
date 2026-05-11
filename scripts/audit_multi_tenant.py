#!/usr/bin/env python3
"""
Script de auditoría de seguridad multi-tenant

Verifica que todas las queries en las rutas estén filtrando correctamente por taller_id.
"""

import os
import re
from pathlib import Path

# Tablas que DEBEN tener filtro por taller_id
TABLAS_MULTI_TENANT = [
    "Ticket",
    "Vehiculo",
    "Mecanico",
    "MovimientoCaja",
    "TicketProceso",
    "TicketRepuesto",
    "TicketFoto",
    "TicketCompra",
    "TicketCobro",
    "Cita",
    "ConfiguracionTaller",
    "ConfiguracionCobroRapido",
    "Notificacion",
    "LogNotificacion",
    "CambioMovimientoCaja",
    "User",  # Excepto SUPER_ADMIN
]

# Patrones de queries peligrosas
PATRON_QUERY = r'db\.query\((\w+)\)'
PATRON_FILTER_TALLER = r'\.filter\([^)]*\.taller_id\s*==\s*taller_id[^)]*\)'
PATRON_REQUEST_STATE = r'request\.state\.taller_id'

def analizar_archivo(ruta_archivo):
    """Analiza un archivo Python buscando queries sin filtro de taller_id"""
    problemas = []
    
    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        contenido = f.read()
        lineas = contenido.split('\n')
    
    # Buscar todas las queries
    for num_linea, linea in enumerate(lineas, 1):
        match_query = re.search(PATRON_QUERY, linea)
        if match_query:
            tabla = match_query.group(1)
            
            # Solo verificar tablas multi-tenant
            if tabla not in TABLAS_MULTI_TENANT:
                continue
            
            # Buscar el contexto (10 líneas antes y después)
            inicio = max(0, num_linea - 10)
            fin = min(len(lineas), num_linea + 10)
            contexto = '\n'.join(lineas[inicio:fin])
            
            # Verificar si hay filtro por taller_id en el contexto
            tiene_filtro_taller = re.search(PATRON_FILTER_TALLER, contexto)
            tiene_request_state = re.search(PATRON_REQUEST_STATE, contexto)
            
            # Excepciones válidas
            es_super_admin = 'super_admin' in ruta_archivo.lower()
            es_auth = 'auth' in ruta_archivo.lower()
            usa_repositorio = 'Repository(' in contexto
            
            if not (tiene_filtro_taller or usa_repositorio or es_super_admin or es_auth):
                problemas.append({
                    'archivo': ruta_archivo,
                    'linea': num_linea,
                    'tabla': tabla,
                    'codigo': linea.strip(),
                    'tiene_request_state': bool(tiene_request_state)
                })
    
    return problemas

def main():
    print("=" * 80)
    print("AUDITORÍA DE SEGURIDAD MULTI-TENANT")
    print("=" * 80)
    print()
    
    # Analizar todas las rutas
    rutas_dir = Path(__file__).parent.parent / 'app' / 'rutas'
    todos_problemas = []
    
    for archivo in rutas_dir.glob('*.py'):
        if archivo.name.startswith('__'):
            continue
        
        problemas = analizar_archivo(str(archivo))
        if problemas:
            todos_problemas.extend(problemas)
    
    # Agrupar por archivo
    problemas_por_archivo = {}
    for p in todos_problemas:
        archivo = p['archivo']
        if archivo not in problemas_por_archivo:
            problemas_por_archivo[archivo] = []
        problemas_por_archivo[archivo].append(p)
    
    # Mostrar resultados
    if not todos_problemas:
        print("✅ NO SE ENCONTRARON PROBLEMAS DE SEGURIDAD MULTI-TENANT")
        print()
        return
    
    print(f"⚠️  SE ENCONTRARON {len(todos_problemas)} QUERIES POTENCIALMENTE INSEGURAS")
    print()
    
    for archivo, problemas in sorted(problemas_por_archivo.items()):
        archivo_rel = os.path.relpath(archivo)
        print(f"📁 {archivo_rel}")
        print("-" * 80)
        
        for p in problemas:
            estado = "⚠️  CRÍTICO" if not p['tiene_request_state'] else "⚠️  REVISAR"
            print(f"  {estado} - Línea {p['linea']}: db.query({p['tabla']})")
            print(f"    Código: {p['codigo']}")
            if p['tiene_request_state']:
                print(f"    Nota: Tiene request.state.taller_id pero no se usa en el filtro")
            print()
        
        print()
    
    print("=" * 80)
    print("RECOMENDACIONES:")
    print("=" * 80)
    print("1. Agregar filtro .filter(Tabla.taller_id == taller_id) a todas las queries")
    print("2. Usar TenantRepository cuando sea posible")
    print("3. Verificar que request.state.taller_id esté disponible en el endpoint")
    print("4. Agregar @require_auth o @require_role a endpoints sin autenticación")
    print()

if __name__ == '__main__':
    main()
