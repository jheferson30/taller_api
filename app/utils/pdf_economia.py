from io import BytesIO
from datetime import datetime
from typing import List, Dict
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generar_pdf_economia_profesional(
    fecha: str,
    resumen: Dict,
    ingresos: Dict,
    egresos: List[Dict],
    datos_taller: Dict = None,
) -> bytes:
    """
    Genera un PDF profesional del reporte de economía diaria
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
    
    # Colores grises profesionales
    GRAY_DARK = colors.HexColor('#7f8c8d')
    GRAY_MEDIUM = colors.HexColor('#95a5a6')
    GRAY_LIGHT = colors.HexColor('#d5dbdb')
    GRAY_LIGHTER = colors.HexColor('#ecf0f1')
    GRAY_BORDER = colors.HexColor('#bdc3c7')
    GREEN = colors.HexColor('#059669')
    RED = colors.HexColor('#e74c3c')
    BLUE = colors.HexColor('#1e40af')
    
    story = []

    # ===== ENCABEZADO PROFESIONAL (igual que PDF de tickets) =====
    nombre_taller = (datos_taller or {}).get('nombre') or 'Taller Mecánico'
    direccion     = (datos_taller or {}).get('direccion') or ''
    telefono      = (datos_taller or {}).get('telefono') or ''
    nit           = (datos_taller or {}).get('nit') or ''

    nombre_style = ParagraphStyle(
        'NombreTaller', parent=styles['Normal'],
        fontSize=14, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c3e50'), leading=17, spaceAfter=2,
    )
    dato_taller_style = ParagraphStyle(
        'DatoTaller', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#555555'), leading=11,
    )
    comprobante_style = ParagraphStyle(
        'Comprobante', parent=styles['Normal'],
        fontSize=16, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_RIGHT, leading=20, spaceAfter=2,
    )
    fecha_gen_style = ParagraphStyle(
        'FechaGen', parent=styles['Normal'],
        fontSize=7, textColor=colors.HexColor('#888888'),
        alignment=TA_RIGHT, leading=10,
    )

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

    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    fecha_formateada = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
    col_der = [
        Paragraph("REPORTE DE ECONOMÍA DIARIA", comprobante_style),
        Paragraph(f"Fecha: {fecha_formateada}", fecha_gen_style),
        Paragraph(f"Generado: {fecha_gen}", fecha_gen_style),
    ]

    header_table = Table([[col_izq, col_der]], colWidths=[3.5*inch, 4.0*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)

    # Línea separadora azul
    sep_table = Table([['']], colWidths=[7.5*inch])
    sep_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#2c3e50')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(sep_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ===== RESUMEN EJECUTIVO =====
    story.append(Paragraph("RESUMEN EJECUTIVO", section_style))

    resumen_data = [
        ['Concepto', 'Valor'],
        ['Ingresos por Anticipos', f"${resumen.get('ingreso_anticipo', 0):,}"],
        ['Ingresos por Cobros Finales', f"${resumen.get('ingreso_final', 0):,}"],
        ['Total Ingresos', f"${resumen.get('ingresos', 0):,}"],
        ['Total Egresos', f"${resumen.get('egresos', 0):,}"],
        ['Balance del Día', f"${resumen.get('balance', 0):,}"],
    ]
    
    tabla_resumen = Table(resumen_data, colWidths=[4.5*inch, 2.5*inch])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GRAY_MEDIUM),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -3), [colors.white, GRAY_LIGHTER]),
        # Total Ingresos (fila 3) → azul
        ('BACKGROUND', (0, 3), (-1, 3), BLUE),
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.white),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        # Total Egresos (fila 4) → rojo
        ('BACKGROUND', (0, 4), (-1, 4), RED),
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.white),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        # Balance (fila 5) → verde
        ('BACKGROUND', (0, 5), (-1, 5), GREEN),
        ('TEXTCOLOR', (0, 5), (-1, 5), colors.white),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(tabla_resumen)
    story.append(Spacer(1, 0.12*inch))

    # ===== ESTADÍSTICAS ADICIONALES =====
    story.append(Paragraph("ESTADÍSTICAS DEL DÍA", section_style))
    
    stats_data = [
        ['Tickets Cerrados', str(resumen.get('tickets_cerrados_hoy', 0))],
        ['Tickets Abiertos con Anticipo', str(resumen.get('tickets_abiertos_con_anticipo_hoy', 0))],
        ['Total Anticipos Recibidos', str(len(ingresos.get('anticipos', [])))],
        ['Total Cobros Finales', str(len(ingresos.get('cobros_finales', [])))],
        ['Total Egresos Registrados', str(len(egresos))],
    ]
    
    tabla_stats = Table(stats_data, colWidths=[5*inch, 2*inch])
    tabla_stats.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), GRAY_LIGHT),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(tabla_stats)
    story.append(Spacer(1, 0.15*inch))

    # ===== DETALLE DE ANTICIPOS =====
    anticipos = ingresos.get('anticipos', [])
    if anticipos:
        story.append(Paragraph("DETALLE DE ANTICIPOS RECIBIDOS", section_style))
        
        anticipos_data = [['Ticket', 'Placa', 'Método Pago', 'Responsable', 'Valor']]
        for a in anticipos:
            anticipos_data.append([
                a.get('ticket_codigo', 'N/A'),
                a.get('placa', 'N/A'),
                a.get('metodo_pago', 'N/A'),
                a.get('responsable', 'N/A'),
                f"${a.get('valor_anticipo', 0):,}"
            ])
        
        tabla_anticipos = Table(anticipos_data, colWidths=[2*inch, 0.8*inch, 1.2*inch, 1.3*inch, 1.7*inch])
        tabla_anticipos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRAY_LIGHTER]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        story.append(tabla_anticipos)
        story.append(Spacer(1, 0.12*inch))

    # ===== DETALLE DE COBROS FINALES =====
    cobros_finales = ingresos.get('cobros_finales', [])
    if cobros_finales:
        story.append(Paragraph("DETALLE DE COBROS FINALES", section_style))
        
        cobros_data = [['Ticket', 'Placa', 'Método Pago', 'Responsable', 'Valor']]
        for c in cobros_finales:
            cobros_data.append([
                c.get('ticket_codigo', 'N/A'),
                c.get('placa', 'N/A'),
                c.get('metodo_pago', 'N/A'),
                c.get('responsable', 'N/A'),
                f"${c.get('valor_final_cobrado', 0):,}"
            ])
        
        tabla_cobros = Table(cobros_data, colWidths=[2*inch, 0.8*inch, 1.2*inch, 1.3*inch, 1.7*inch])
        tabla_cobros.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRAY_LIGHTER]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        story.append(tabla_cobros)
        story.append(Spacer(1, 0.12*inch))

    # ===== DETALLE DE EGRESOS =====
    if egresos:
        story.append(Paragraph("DETALLE DE EGRESOS", section_style))
        
        # Agrupar por categoría
        egresos_por_cat = {}
        for e in egresos:
            cat = e.get('categoria', 'OTRO')
            if cat not in egresos_por_cat:
                egresos_por_cat[cat] = []
            egresos_por_cat[cat].append(e)
        
        # Mostrar resumen por categoría
        cat_resumen_data = [['Categoría', 'Cantidad', 'Total']]
        for cat, items in egresos_por_cat.items():
            # Limpiar nombre de categoría
            cat_limpio = str(cat)
            if 'CategoriaEgreso.' in cat_limpio:
                cat_limpio = cat_limpio.replace('CategoriaEgreso.', '')
            cat_limpio = cat_limpio[:15]
            
            total_cat = sum(item.get('valor', 0) for item in items)
            cat_resumen_data.append([cat_limpio, str(len(items)), f"${total_cat:,}"])
        
        tabla_cat_resumen = Table(cat_resumen_data, colWidths=[3*inch, 2*inch, 2*inch])
        tabla_cat_resumen.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), RED),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRAY_LIGHTER]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        story.append(tabla_cat_resumen)
        story.append(Spacer(1, 0.12*inch))
        
        # Detalle completo de egresos
        story.append(Paragraph("Detalle Completo de Egresos", 
            ParagraphStyle('SubSection', parent=normal_style, fontSize=9, fontName='Helvetica-Bold', spaceAfter=6)))
        
        egresos_data = [['Categoría', 'Concepto', 'Ticket', 'Responsable', 'Valor']]
        for e in egresos:
            # Limpiar y truncar categoría
            categoria = e.get('categoria', 'OTRO')
            if 'CategoriaEgreso.' in str(categoria):
                categoria = str(categoria).replace('CategoriaEgreso.', '')
            categoria = str(categoria)[:12]
            
            # Truncar otros campos
            concepto = str(e.get('concepto', 'N/A'))[:40]
            ticket = str(e.get('ticket_codigo', '-'))[:22] if e.get('ticket_codigo') else '-'
            responsable = str(e.get('responsable', 'N/A'))[:18]
            
            egresos_data.append([
                categoria,
                concepto,
                ticket,
                responsable,
                f"${e.get('valor', 0):,}"
            ])
        
        tabla_egresos = Table(egresos_data, colWidths=[0.9*inch, 2.3*inch, 1.6*inch, 1.2*inch, 1*inch])
        tabla_egresos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), RED),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRAY_LIGHTER]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        story.append(tabla_egresos)

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
