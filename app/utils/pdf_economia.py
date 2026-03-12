from io import BytesIO
from datetime import datetime
from typing import List, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generar_pdf_economia_profesional(
    fecha: str,
    resumen: Dict,
    ingresos: Dict,
    egresos: List[Dict]
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
    GREEN = colors.HexColor('#27ae60')
    RED = colors.HexColor('#e74c3c')
    BLUE = colors.HexColor('#3498db')
    
    story = []

    # ===== ENCABEZADO =====
    story.append(Paragraph("REPORTE DE ECONOMÍA DIARIA", title_style))
    story.append(Paragraph("Taller Mecánico", normal_style))
    story.append(Spacer(1, 0.15*inch))
    
    # ===== INFORMACIÓN DE LA FECHA =====
    fecha_formateada = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d de %B de %Y')
    story.append(Paragraph(f"<b>Fecha del Reporte:</b> {fecha_formateada}", normal_style))
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
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, GRAY_LIGHTER]),
        ('BACKGROUND', (0, -1), (-1, -1), GRAY_DARK),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
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
