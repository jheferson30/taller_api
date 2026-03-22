import os
from io import BytesIO
from datetime import datetime
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY


def generar_pdf_ticket_completo(
    ticket_data: dict,
    procesos: List[dict],
    repuestos: List[dict],
    fotos: List[dict],
    cobros: List[dict],
    compras: List[dict] = None,
    taller: dict = None,
) -> bytes:
    """
    Genera un PDF completo del ticket con diseño limpio y profesional en gris
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=0.5*inch, 
        bottomMargin=0.5*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=15,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        borderWidth=1,
        borderColor=colors.HexColor('#95a5a6'),
        borderPadding=4,
        backColor=colors.HexColor('#d5dbdb')
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=3,
        leading=10
    )
    
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=7,
        spaceAfter=2,
        leading=9
    )
    
    # Colores grises para diseño profesional
    GRAY_DARK = colors.HexColor('#7f8c8d')
    GRAY_MEDIUM = colors.HexColor('#95a5a6')
    GRAY_LIGHT = colors.HexColor('#d5dbdb')
    GRAY_LIGHTER = colors.HexColor('#ecf0f1')
    GRAY_BORDER = colors.HexColor('#bdc3c7')
    
    story = []

    # ===== ENCABEZADO PROFESIONAL =====
    nombre_taller = (taller or {}).get('nombre_taller') or 'Taller Mecánico'
    direccion = (taller or {}).get('direccion') or ''
    telefono = (taller or {}).get('telefono') or ''
    nit = (taller or {}).get('nit') or ''

    nombre_style = ParagraphStyle(
        'NombreTaller',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c3e50'),
        leading=17,
        spaceAfter=2,
    )
    dato_taller_style = ParagraphStyle(
        'DatoTaller',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#555555'),
        leading=11,
    )
    comprobante_style = ParagraphStyle(
        'Comprobante',
        parent=styles['Normal'],
        fontSize=18,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_RIGHT,
        leading=22,
        spaceAfter=2,
    )
    fecha_gen_style = ParagraphStyle(
        'FechaGen',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#888888'),
        alignment=TA_RIGHT,
        leading=10,
    )

    # Columna izquierda: logo + nombre taller
    logo_path = os.path.join("frontend", "public", "assets", "logo.png")
    col_izq = []
    if os.path.exists(logo_path):
        try:
            col_izq.append(Image(logo_path, width=0.7*inch, height=0.7*inch))
        except Exception:
            pass
    col_izq.append(Spacer(1, 4))
    col_izq.append(Paragraph(nombre_taller, nombre_style))
    if direccion:
        col_izq.append(Paragraph(f"Dir: {direccion}", dato_taller_style))
    if telefono:
        col_izq.append(Paragraph(f"Tel: {telefono}", dato_taller_style))
    if nit:
        col_izq.append(Paragraph(f"NIT: {nit}", dato_taller_style))

    # Columna derecha: título + fecha generación
    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    col_der = [
        Paragraph("COMPROBANTE DE SERVICIO", comprobante_style),
        Paragraph(f"Generado: {fecha_gen}", fecha_gen_style),
    ]

    from reportlab.platypus import KeepInFrame
    header_table = Table(
        [[col_izq, col_der]],
        colWidths=[3.5*inch, 4.0*inch],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)

    # Línea separadora
    sep_table = Table([[''] * 1], colWidths=[7.5*inch])
    sep_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#2c3e50')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(sep_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ===== DATOS DEL VEHÍCULO Y TICKET (TODOS LOS CAMPOS) =====
    story.append(Paragraph("INFORMACIÓN DEL VEHÍCULO Y TICKET", section_style))
    
    # Mostrar todos los campos, incluso si están vacíos
    datos_vehiculo = [
        ['Ticket:', ticket_data.get('ticket_codigo', ''), 'Placa:', ticket_data.get('placa', '')],
        ['Estado:', ticket_data.get('estado', ''), 'Fecha Ingreso:', ticket_data.get('fecha_ingreso', '')[:10] if ticket_data.get('fecha_ingreso') else ''],
        ['Kilometraje:', str(ticket_data.get('kilometraje', '')) if ticket_data.get('kilometraje') else '', 'Estado Inicial:', ticket_data.get('estado_inicial', '')],
        ['Propietario:', ticket_data.get('nombre_propietario', ''), 'Teléfono:', ticket_data.get('telefono_propietario', '')],
        ['Motivo Visita:', ticket_data.get('motivo_visita', ''), '', ''],
    ]
    
    # Agregar observaciones si existen
    if ticket_data.get('observaciones_recepcion'):
        datos_vehiculo.append(['Observaciones:', ticket_data.get('observaciones_recepcion', ''), '', ''])
    
    tabla_vehiculo = Table(datos_vehiculo, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    tabla_vehiculo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), GRAY_LIGHT),
        ('BACKGROUND', (2, 0), (2, -1), GRAY_LIGHT),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (1, -2), (3, -2)),  # Span para motivo visita
    ]))
    
    # Si hay observaciones, hacer span
    if ticket_data.get('observaciones_recepcion'):
        tabla_vehiculo.setStyle(TableStyle([
            ('SPAN', (1, -1), (3, -1)),  # Span para observaciones
        ]))
    
    story.append(tabla_vehiculo)
    story.append(Spacer(1, 0.12*inch))
    
    # ===== PROCESOS REALIZADOS =====
    if procesos:
        story.append(Paragraph("PROCESOS REALIZADOS", section_style))
        procesos_data = [['Proceso', 'Mecánico', 'Observaciones']]
        for p in procesos:
            # Usar Paragraph para que el texto no se desborde
            desc = p.get('descripcion', '-')
            desc_para = Paragraph(desc if desc else '-', small_style)
            
            procesos_data.append([
                p.get('nombre', 'N/A'),
                p.get('mecanico', 'N/A'),
                desc_para
            ])
        
        tabla_procesos = Table(procesos_data, colWidths=[2*inch, 1.3*inch, 3.7*inch])
        tabla_procesos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRAY_MEDIUM),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRAY_LIGHTER]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(tabla_procesos)
        story.append(Spacer(1, 0.12*inch))
    
    # ===== REPUESTOS (Incluye los de compras con valores) =====
    # Combinar repuestos normales con los de compras
    todos_repuestos = []
    
    # Agregar repuestos normales
    for r in repuestos:
        todos_repuestos.append({
            'nombre': r.get('nombre', 'N/A'),
            'cantidad': r.get('cantidad', 1),
            'marca': r.get('marca_referencia', '-'),
            'valor': '-'
        })
    
    # Agregar repuestos de compras con valor
    if compras:
        for c in compras:
            todos_repuestos.append({
                'nombre': c.get('descripcion', 'N/A'),
                'cantidad': 1,
                'marca': '-',
                'valor': f"${c.get('valor', 0):,}"
            })
    
    if todos_repuestos:
        story.append(Paragraph("REPUESTOS UTILIZADOS", section_style))
        repuestos_data = [['Repuesto', 'Cant.', 'Marca/Ref', 'Valor']]
        for r in todos_repuestos:
            repuestos_data.append([
                r['nombre'],
                str(r['cantidad']),
                r['marca'],
                r['valor']
            ])
        
        tabla_repuestos = Table(repuestos_data, colWidths=[3.3*inch, 0.6*inch, 2*inch, 1.1*inch])
        tabla_repuestos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRAY_MEDIUM),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRAY_LIGHTER]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(tabla_repuestos)
        story.append(Spacer(1, 0.12*inch))
    
    # ===== COMPRAS CON IMÁGENES (3 por fila, 30mm) =====
    if compras:
        story.append(Paragraph("COMPRAS REALIZADAS", section_style))
        
        # Agrupar compras en filas de 3
        compras_por_fila = 3
        for i in range(0, len(compras), compras_por_fila):
            compras_fila = compras[i:i+compras_por_fila]
            
            # Crear celdas para esta fila
            celdas_imagenes = []
            celdas_info = []
            
            for c in compras_fila:
                # Intentar cargar imagen
                img_cell = None
                img_path = c.get('soporte_url', '')
                
                if img_path:
                    # Convertir URL a ruta local
                    if img_path.startswith('http://127.0.0.1:8000/uploads/'):
                        img_path = img_path.replace('http://127.0.0.1:8000/uploads/', 'uploads/')
                    elif img_path.startswith('/uploads/'):
                        img_path = img_path.replace('/uploads/', 'uploads/')
                    
                    try:
                        if os.path.exists(img_path) and not img_path.endswith('.pdf'):
                            img = Image(img_path, width=30*mm, height=30*mm, kind='proportional')
                            img_cell = img
                        else:
                            img_cell = Paragraph("<font size=6>Sin imagen</font>", normal_style)
                    except:
                        img_cell = Paragraph("<font size=6>Sin imagen</font>", normal_style)
                else:
                    img_cell = Paragraph("<font size=6>Sin imagen</font>", normal_style)
                
                celdas_imagenes.append(img_cell)
                
                # Información de la compra
                info_text = f"<b>{c.get('descripcion', 'N/A')}</b><br/><font size=8>${c.get('valor', 0):,}</font>"
                if c.get('responsable'):
                    info_text += f"<br/><font size=6>{c.get('responsable')}</font>"
                celdas_info.append(Paragraph(info_text, small_style))
            
            # Rellenar con celdas vacías si no hay 3 compras
            while len(celdas_imagenes) < compras_por_fila:
                celdas_imagenes.append('')
                celdas_info.append('')
            
            # Crear tabla para esta fila
            tabla_compras_fila = Table([celdas_imagenes, celdas_info], 
                                       colWidths=[7*inch/compras_por_fila]*compras_por_fila)
            tabla_compras_fila.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ]))
            story.append(tabla_compras_fila)
            story.append(Spacer(1, 0.08*inch))
    
    # ===== FOTOS DE EVIDENCIA (2 por fila, tamaño proporcional) =====
    if fotos:
        story.append(Paragraph("EVIDENCIA FOTOGRÁFICA", section_style))
        
        # Agrupar fotos en filas de 2
        fotos_por_fila = 2
        for i in range(0, len(fotos), fotos_por_fila):
            fotos_fila = fotos[i:i+fotos_por_fila]
            
            celdas_fotos = []
            
            for f in fotos_fila:
                foto_content = []
                
                # Tipo (ANTES/DESPUES) y descripción
                tipo = f.get('tipo', 'FOTO').upper()
                tipo_desc = f"<b>{tipo}</b>"
                if f.get('descripcion'):
                    tipo_desc += f"<br/><font size=7>{f.get('descripcion')}</font>"
                foto_content.append(Paragraph(tipo_desc, normal_style))
                foto_content.append(Spacer(1, 0.05*inch))
                
                # Imagen proporcional
                img_path = f.get('archivo_url', '')
                if img_path:
                    if img_path.startswith('http://127.0.0.1:8000/uploads/'):
                        img_path = img_path.replace('http://127.0.0.1:8000/uploads/', 'uploads/')
                    elif img_path.startswith('/uploads/'):
                        img_path = img_path.replace('/uploads/', 'uploads/')
                    
                    try:
                        if os.path.exists(img_path):
                            # Imagen proporcional, máximo 3 pulgadas de ancho
                            img = Image(img_path, width=3*inch, height=2.2*inch, kind='proportional')
                            foto_content.append(img)
                        else:
                            foto_content.append(Paragraph("<i><font size=7>Imagen no disponible</font></i>", normal_style))
                    except:
                        foto_content.append(Paragraph("<i><font size=7>Error al cargar imagen</font></i>", normal_style))
                else:
                    foto_content.append(Paragraph("<i><font size=7>Sin imagen</font></i>", normal_style))
                
                # Crear tabla interna para cada foto
                tabla_foto = Table([[item] for item in foto_content], colWidths=[3.3*inch])
                tabla_foto.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                ]))
                celdas_fotos.append(tabla_foto)
            
            # Rellenar con celda vacía si solo hay 1 foto
            if len(celdas_fotos) == 1:
                celdas_fotos.append('')
            
            # Crear tabla para esta fila de fotos
            tabla_fotos_fila = Table([celdas_fotos], colWidths=[3.5*inch, 3.5*inch])
            tabla_fotos_fila.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ]))
            story.append(tabla_fotos_fila)
            story.append(Spacer(1, 0.08*inch))
    
    # ===== DETALLE DE COBROS =====
    if cobros:
        story.append(Paragraph("DETALLE DE COBROS", section_style))
        cobros_data = [['Concepto', 'Valor']]
        total_cobros = 0
        for c in cobros:
            valor = c.get('valor', 0)
            total_cobros += valor
            cobros_data.append([c.get('concepto', 'N/A'), f"${valor:,}"])
        cobros_data.append(['TOTAL', f"${total_cobros:,}"])
        
        tabla_cobros = Table(cobros_data, colWidths=[5*inch, 2*inch])
        tabla_cobros.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRAY_MEDIUM),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -2), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, GRAY_LIGHTER]),
            ('BACKGROUND', (0, -1), (-1, -1), GRAY_DARK),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(tabla_cobros)
        story.append(Spacer(1, 0.12*inch))
    
    # ===== RESUMEN FINANCIERO =====
    story.append(Paragraph("RESUMEN FINANCIERO", section_style))
    finanzas_data = [
        ['Total del Servicio:', f"${ticket_data.get('total_servicio', 0):,}"],
        ['Anticipo Recibido:', f"${ticket_data.get('anticipo_recibido', 0):,}"],
        ['Saldo Pendiente:', f"${ticket_data.get('saldo_pendiente', 0):,}"],
        ['Método de Pago:', ticket_data.get('metodo_pago_final', 'N/A')],
    ]
    
    tabla_finanzas = Table(finanzas_data, colWidths=[2.5*inch, 2*inch])
    tabla_finanzas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), GRAY_LIGHT),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(tabla_finanzas)
    story.append(Spacer(1, 0.12*inch))
    
    # ===== OBSERVACIONES FINALES =====
    if ticket_data.get('observaciones_finales'):
        story.append(Paragraph("OBSERVACIONES FINALES", section_style))
        obs_para = Paragraph(ticket_data['observaciones_finales'], normal_style)
        tabla_obs = Table([[obs_para]], colWidths=[7*inch])
        tabla_obs.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(tabla_obs)
        story.append(Spacer(1, 0.12*inch))
    
    # ===== RECOMENDACIONES Y PRÓXIMA CITA =====
    if ticket_data.get('recomendaciones') or ticket_data.get('proximo_mantenimiento'):
        story.append(Paragraph("RECOMENDACIONES Y PRÓXIMA CITA", section_style))
        recom_data = []
        
        if ticket_data.get('recomendaciones'):
            recom_para = Paragraph(f"<b>Recomendaciones:</b><br/>{ticket_data['recomendaciones']}", normal_style)
            recom_data.append([recom_para])
        
        if ticket_data.get('proximo_mantenimiento'):
            prox_para = Paragraph(
                f"<b>Próximo Mantenimiento / Cita:</b><br/>{ticket_data['proximo_mantenimiento']}", 
                normal_style
            )
            recom_data.append([prox_para])
        
        tabla_recom = Table(recom_data, colWidths=[7*inch])
        tabla_recom.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_LIGHTER),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(tabla_recom)
    
    # ===== PIE DE PÁGINA =====
    story.append(Spacer(1, 0.25*inch))
    story.append(Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=colors.grey, alignment=TA_CENTER)
    ))
    
    # Construir PDF
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
