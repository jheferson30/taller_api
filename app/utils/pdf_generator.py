import os
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Paleta ──────────────────────────────────────────────────────────────────
AZUL = colors.HexColor("#1e3a5f")
AZUL_MEDIO = colors.HexColor("#2563eb")
AZUL_CLARO = colors.HexColor("#dbeafe")
GRIS_BORDE = colors.HexColor("#cbd5e1")
GRIS_FILA = colors.HexColor("#f8fafc")
TEXTO = colors.HexColor("#1e293b")
TEXTO_MUTED = colors.HexColor("#64748b")
VERDE = colors.HexColor("#166534")
VERDE_BG = colors.HexColor("#dcfce7")


def fmt_cop(valor) -> str:
    """Formatea un número como pesos colombianos sin decimales."""
    try:
        return f"${int(valor):,}".replace(",", ".")
    except Exception:
        return "$0"


def campo(label: str, valor, style_label, style_val):
    """Devuelve una fila [label, valor] para tablas de datos."""
    return [
        Paragraph(label, style_label),
        Paragraph(str(valor) if valor else "No especificado", style_val),
    ]


def resolver_ruta_img(url: str) -> str:
    """Convierte URL o ruta relativa a ruta local del sistema de archivos."""
    if not url:
        return ""
    for prefijo in [
        "http://127.0.0.1:8000/uploads/",
        "http://localhost:8000/uploads/",
    ]:
        if url.startswith(prefijo):
            return "uploads/" + url[len(prefijo) :]
    if url.startswith("/uploads/"):
        return "uploads/" + url[len("/uploads/") :]
    if url.startswith("uploads/"):
        return url
    return url


def generar_pdf_ticket_completo(
    ticket_data: dict,
    procesos: list[dict],
    repuestos: list[dict],
    fotos: list[dict],
    cobros: list[dict],
    compras: list[dict] | None = None,
    taller: dict | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.45 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
    )

    styles = getSampleStyleSheet()

    # ── Estilos ──────────────────────────────────────────────────────────────
    def estilo(name, **kw):
        base = kw.pop("parent", styles["Normal"])
        return ParagraphStyle(name, parent=base, **kw)

    s_titulo = estilo(
        "Titulo",
        fontSize=20,
        fontName="Helvetica-Bold",
        textColor=AZUL,
        alignment=TA_RIGHT,
        leading=24,
    )
    s_subtitulo = estilo(
        "Subtitulo", fontSize=8, textColor=TEXTO_MUTED, alignment=TA_RIGHT, leading=11
    )
    s_nombre_taller = estilo(
        "NombreTaller", fontSize=13, fontName="Helvetica-Bold", textColor=AZUL, leading=16
    )
    s_dato_taller = estilo("DatoTaller", fontSize=8, textColor=TEXTO_MUTED, leading=11)
    s_seccion = estilo(
        "Seccion", fontSize=9, fontName="Helvetica-Bold", textColor=colors.white, leading=12
    )
    s_label = estilo("Label", fontSize=8, fontName="Helvetica-Bold", textColor=TEXTO, leading=11)
    s_valor = estilo("Valor", fontSize=8, textColor=TEXTO, leading=11)
    s_small = estilo("Small", fontSize=7, textColor=TEXTO_MUTED, leading=10)
    s_total = estilo(
        "Total",
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_RIGHT,
        leading=13,
    )
    s_footer = estilo("Footer", fontSize=7, textColor=TEXTO_MUTED, alignment=TA_CENTER, leading=10)
    s_gracias = estilo(
        "Gracias",
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=AZUL,
        alignment=TA_CENTER,
        leading=13,
    )

    story = []
    W = 7.4 * inch  # ancho útil

    # ── Datos del taller ─────────────────────────────────────────────────────
    t = taller or {}
    nombre_taller = t.get("nombre_taller") or "Taller Mecánico"
    direccion = t.get("direccion") or ""
    telefono = t.get("telefono") or ""
    nit = t.get("nit") or ""

    # Número de comprobante basado en el código del ticket
    codigo = ticket_data.get("ticket_codigo", "")
    num_cs = codigo[-6:] if len(codigo) >= 6 else codigo
    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── ENCABEZADO ───────────────────────────────────────────────────────────
    logo_path = os.path.join("frontend", "public", "assets", "logo.png")
    col_izq = []
    if os.path.exists(logo_path):
        try:
            col_izq.append(Image(logo_path, width=0.65 * inch, height=0.65 * inch))
            col_izq.append(Spacer(1, 3))
        except Exception:
            pass
    col_izq.append(Paragraph(nombre_taller, s_nombre_taller))
    for txt in [f"Dir: {direccion}", f"Tel: {telefono}", f"NIT: {nit}"]:
        if txt.split(": ", 1)[1]:
            col_izq.append(Paragraph(txt, s_dato_taller))

    col_der = [
        Paragraph("COMPROBANTE DE SERVICIO", s_titulo),
        Paragraph(
            f"N° CS-{num_cs}",
            estilo(
                "NumCS",
                fontSize=11,
                fontName="Helvetica-Bold",
                textColor=AZUL_MEDIO,
                alignment=TA_RIGHT,
            ),
        ),
        Spacer(1, 3),
        Paragraph(f"Generado: {fecha_gen}", s_subtitulo),
    ]

    header = Table([[col_izq, col_der]], colWidths=[3.6 * inch, 3.8 * inch])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(header)

    # Línea azul separadora
    sep = Table([[""]], colWidths=[W])
    sep.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 2, AZUL),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(sep)
    story.append(Spacer(1, 0.14 * inch))

    # ── Helper: cabecera de sección ──────────────────────────────────────────
    def seccion(titulo: str):
        t = Table([[Paragraph(titulo, s_seccion)]], colWidths=[W])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), AZUL),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("ROUNDEDCORNERS", [4, 4, 0, 0]),
                ]
            )
        )
        return t

    def tabla_datos(filas, col_w=None):
        """Tabla de dos columnas label/valor con fondo alternado."""
        cw = col_w or [1.8 * inch, 5.6 * inch]
        tbl = Table(filas, colWidths=cw)
        n = len(filas)
        style_cmds = [
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, GRIS_BORDE),
            ("LINEBELOW", (0, -1), (-1, -1), 0.3, GRIS_BORDE),
            ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ]
        for i in range(n):
            bg = AZUL_CLARO if i % 2 == 0 else colors.white
            style_cmds.append(("BACKGROUND", (0, i), (0, i), bg))
        tbl.setStyle(TableStyle(style_cmds))
        return tbl

    # ── INFORMACIÓN DEL VEHÍCULO ─────────────────────────────────────────────
    td = ticket_data
    filas_vh = []

    def add_campo(label, val):
        if val and str(val).strip():
            filas_vh.append(campo(label, val, s_label, s_valor))

    add_campo("Ticket", td.get("ticket_codigo"))
    add_campo("Placa", td.get("placa"))
    add_campo("Propietario", td.get("nombre_propietario"))
    add_campo("Teléfono", td.get("telefono_propietario"))
    add_campo(
        "Fecha de ingreso", td.get("fecha_ingreso", "")[:10] if td.get("fecha_ingreso") else None
    )
    add_campo("Estado", td.get("estado"))
    add_campo("Kilometraje", td.get("kilometraje"))
    add_campo("Estado inicial", td.get("estado_inicial"))
    add_campo("Motivo de visita", td.get("motivo_visita"))
    add_campo("Observaciones", td.get("observaciones_recepcion"))

    if filas_vh:
        story.append(
            KeepTogether(
                [
                    seccion("INFORMACIÓN DEL VEHÍCULO Y TICKET"),
                    tabla_datos(filas_vh),
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── PROCESOS REALIZADOS ──────────────────────────────────────────────────
    if procesos:
        story.append(seccion("PROCESOS REALIZADOS"))
        POR_FILA_P = 2
        col_w_p = W / POR_FILA_P

        for i in range(0, len(procesos), POR_FILA_P):
            grupo = procesos[i : i + POR_FILA_P]
            celdas = []
            for p in grupo:
                contenido = []

                # Foto del proceso
                ruta = resolver_ruta_img(p.get("foto_url", ""))
                if ruta and os.path.exists(ruta):
                    try:
                        contenido.append(
                            Image(
                                ruta, width=col_w_p - 12, height=col_w_p - 12, kind="proportional"
                            )
                        )
                        contenido.append(Spacer(1, 4))
                    except Exception:
                        pass

                contenido.append(Paragraph(f"<b>{p.get('nombre', '—')}</b>", s_valor))
                if p.get("mecanico"):
                    contenido.append(Paragraph(f"🔧 {p['mecanico']}", s_small))
                if p.get("descripcion"):
                    contenido.append(Paragraph(p["descripcion"], s_small))

                celdas.append(contenido)

            while len(celdas) < POR_FILA_P:
                celdas.append([Paragraph("", s_small)])

            fila_tbl = Table([celdas], colWidths=[col_w_p] * POR_FILA_P)
            fila_tbl.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                        ("LINEBEFORE", (1, 0), (-1, -1), 0.3, GRIS_BORDE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white]),
                    ]
                )
            )
            story.append(fila_tbl)

        story.append(Spacer(1, 0.14 * inch))

    # ── REPUESTOS UTILIZADOS ─────────────────────────────────────────────────
    if repuestos:
        rows = [
            [
                Paragraph("Repuesto", s_label),
                Paragraph("Cant.", s_label),
                Paragraph("Marca / Ref.", s_label),
            ]
        ]
        for r in repuestos:
            rows.append(
                [
                    Paragraph(r.get("nombre", "—"), s_valor),
                    Paragraph(str(r.get("cantidad", 1)), s_valor),
                    Paragraph(r.get("marca_referencia") or "—", s_valor),
                ]
            )
        tbl = Table(rows, colWidths=[4.4 * inch, 0.8 * inch, 2.2 * inch])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_FILA]),
                    ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(
            KeepTogether(
                [
                    seccion("REPUESTOS UTILIZADOS"),
                    tbl,
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── COMPRAS / MATERIALES (con fotos de soporte) ──────────────────────────
    if compras:
        story.append(seccion("MATERIALES Y COMPRAS"))

        # Agrupar en filas de 3
        POR_FILA = 3
        col_w = W / POR_FILA

        for i in range(0, len(compras), POR_FILA):
            grupo = compras[i : i + POR_FILA]
            celdas = []
            for c in grupo:
                contenido = []

                # Imagen de soporte
                ruta = resolver_ruta_img(c.get("soporte_url", ""))
                if ruta and os.path.exists(ruta):
                    try:
                        contenido.append(
                            Image(ruta, width=col_w - 12, height=col_w - 12, kind="proportional")
                        )
                    except Exception:
                        contenido.append(Paragraph("<i>Sin imagen</i>", s_small))
                else:
                    # Placeholder cuando no hay foto
                    ph = Table(
                        [[Paragraph("Sin soporte adjunto", s_small)]], colWidths=[col_w - 12]
                    )
                    ph.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, -1), GRIS_FILA),
                                ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("TOPPADDING", (0, 0), (-1, -1), 20),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
                            ]
                        )
                    )
                    contenido.append(ph)

                contenido.append(Spacer(1, 4))

                # Descripción + valor
                desc_txt = f"<b>{c.get('descripcion', '—')}</b>"
                contenido.append(Paragraph(desc_txt, s_valor))
                contenido.append(
                    Paragraph(
                        fmt_cop(c.get("valor", 0)),
                        estilo("CV", fontSize=8, fontName="Helvetica-Bold", textColor=AZUL_MEDIO),
                    )
                )
                if c.get("responsable"):
                    contenido.append(Paragraph(c["responsable"], s_small))
                if c.get("nota"):
                    contenido.append(Paragraph(c["nota"], s_small))

                celdas.append(contenido)

            # Rellenar hasta 3 columnas
            while len(celdas) < POR_FILA:
                celdas.append([Paragraph("", s_small)])

            fila_tbl = Table([celdas], colWidths=[col_w] * POR_FILA)
            fila_tbl.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                        ("LINEBEFORE", (1, 0), (-1, -1), 0.3, GRIS_BORDE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white]),
                    ]
                )
            )
            story.append(fila_tbl)

        story.append(Spacer(1, 0.14 * inch))

    # ── EVIDENCIA FOTOGRÁFICA ────────────────────────────────────────────────
    if fotos:
        foto_items = []
        for f in fotos:
            img_path = f.get("archivo_url", "")
            if img_path:
                if img_path.startswith("http://127.0.0.1:8000/uploads/"):
                    img_path = img_path.replace("http://127.0.0.1:8000/uploads/", "uploads/")
                elif img_path.startswith("/uploads/"):
                    img_path = img_path.lstrip("/")
            celda = []
            tipo = f.get("tipo", "FOTO").upper()
            desc = f.get("descripcion") or ""
            label_txt = f"<b>{tipo}</b>" + (f"<br/><font size='7'>{desc}</font>" if desc else "")
            celda.append(Paragraph(label_txt, s_small))
            celda.append(Spacer(1, 3))
            if img_path and os.path.exists(img_path):
                try:
                    celda.append(
                        Image(img_path, width=3.0 * inch, height=2.1 * inch, kind="proportional")
                    )
                except Exception:
                    celda.append(Paragraph("<i>Error al cargar imagen</i>", s_small))
            else:
                celda.append(Paragraph("<i>Imagen no disponible</i>", s_small))
            foto_items.append(celda)

        # 2 fotos por fila
        for i in range(0, len(foto_items), 2):
            par = foto_items[i : i + 2]
            while len(par) < 2:
                par.append([Paragraph("", s_small)])
            row_tbl = Table([par], colWidths=[3.6 * inch, 3.8 * inch])
            row_tbl.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                        ("LINEAFTER", (0, 0), (0, -1), 0.3, GRIS_BORDE),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            if i == 0:
                story.append(seccion("EVIDENCIA FOTOGRÁFICA"))
            story.append(row_tbl)
        story.append(Spacer(1, 0.14 * inch))

    # ── DETALLE DE COBROS ────────────────────────────────────────────────────
    if cobros:
        total = sum(c.get("valor", 0) for c in cobros)
        rows = [
            [
                Paragraph("Concepto", s_label),
                Paragraph(
                    "Valor",
                    estilo(
                        "LblR",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=TEXTO,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        ]
        for c in cobros:
            rows.append(
                [
                    Paragraph(c.get("concepto", "—"), s_valor),
                    Paragraph(
                        fmt_cop(c.get("valor", 0)),
                        estilo("VR", fontSize=8, textColor=TEXTO, alignment=TA_RIGHT),
                    ),
                ]
            )
        # Fila total
        rows.append(
            [
                Paragraph(
                    "TOTAL",
                    estilo("TL", fontSize=9, fontName="Helvetica-Bold", textColor=colors.white),
                ),
                Paragraph(
                    fmt_cop(total),
                    estilo(
                        "TR",
                        fontSize=9,
                        fontName="Helvetica-Bold",
                        textColor=colors.white,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        )
        n = len(rows)
        tbl = Table(rows, colWidths=[5.4 * inch, 2.0 * inch])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
                    ("BACKGROUND", (0, n - 1), (-1, n - 1), AZUL_MEDIO),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, n - 2), [colors.white, GRIS_FILA]),
                    ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.3, GRIS_BORDE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(
            KeepTogether(
                [
                    seccion("DETALLE DE COBROS"),
                    tbl,
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── RESUMEN FINANCIERO ───────────────────────────────────────────────────
    total_srv = td.get("total_servicio", 0) or 0
    anticipo = td.get("anticipo_recibido", 0) or 0
    saldo = td.get("saldo_pendiente", 0) or 0
    metodo = td.get("metodo_pago_final") or "—"

    fin_rows = []
    if total_srv:
        fin_rows.append(campo("Total del servicio", fmt_cop(total_srv), s_label, s_valor))
    if anticipo:
        fin_rows.append(campo("Anticipo recibido", fmt_cop(anticipo), s_label, s_valor))
    fin_rows.append(
        campo(
            "Saldo pendiente",
            fmt_cop(saldo),
            s_label,
            estilo(
                "SaldoV",
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=VERDE if saldo == 0 else TEXTO,
            ),
        )
    )
    fin_rows.append(campo("Método de pago", metodo, s_label, s_valor))

    story.append(
        KeepTogether(
            [
                seccion("RESUMEN FINANCIERO"),
                tabla_datos(fin_rows, col_w=[2.0 * inch, 5.4 * inch]),
                Spacer(1, 0.14 * inch),
            ]
        )
    )

    # ── OBSERVACIONES FINALES ────────────────────────────────────────────────
    if td.get("observaciones_finales"):
        tbl = Table([[Paragraph(td["observaciones_finales"], s_valor)]], colWidths=[W])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), GRIS_FILA),
                    ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(
            KeepTogether(
                [
                    seccion("OBSERVACIONES FINALES"),
                    tbl,
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── RECOMENDACIONES Y PRÓXIMO MANTENIMIENTO ──────────────────────────────
    if td.get("recomendaciones") or td.get("proximo_mantenimiento"):
        items = []
        if td.get("recomendaciones"):
            items.append(Paragraph(f"<b>Recomendaciones:</b> {td['recomendaciones']}", s_valor))
        if td.get("proximo_mantenimiento"):
            items.append(Spacer(1, 4))
            items.append(
                Paragraph(f"<b>Próximo mantenimiento:</b> {td['proximo_mantenimiento']}", s_valor)
            )
        tbl = Table([[items]], colWidths=[W])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), VERDE_BG),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#86efac")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(
            KeepTogether(
                [
                    seccion("RECOMENDACIONES"),
                    tbl,
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── PIE DE PÁGINA ────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.1 * inch))

    # Línea final
    sep2 = Table([[""]], colWidths=[W])
    sep2.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 1, AZUL),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(sep2)
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"Gracias por confiar en {nombre_taller}. ¡Hasta la próxima!",
            s_gracias,
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}  •  "
            f"Comprobante N° CS-{num_cs}",
            s_footer,
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generar_pdf_ticket(ticket_id: int, db: object) -> str:
    """
    Wrapper function that fetches ticket data from DB and generates a PDF file.

    Args:
        ticket_id: ID of the ticket to generate PDF for
        db: SQLAlchemy database session

    Returns:
        Path to the generated PDF file

    Raises:
        ValueError: If ticket not found
    """
    # Import here to avoid circular imports
    from app.repositorios.ticket_repository import TicketRepository

    ticket_repo = TicketRepository(db)  # type: ignore[arg-type]
    ticket = ticket_repo.get_by_id(ticket_id)

    if not ticket:
        raise ValueError(f"Ticket {ticket_id} not found")

    # Build ticket_data dict from model
    ticket_data = {
        "ticket_codigo": getattr(ticket, "ticket_codigo", ""),
        "placa": getattr(ticket, "placa", ""),
        "nombre_propietario": getattr(ticket, "nombre_propietario", ""),
        "telefono_propietario": getattr(ticket, "telefono_propietario", ""),
        "fecha_ingreso": str(getattr(ticket, "fecha_ingreso", "")),
        "estado": getattr(ticket, "estado", ""),
        "kilometraje": getattr(ticket, "kilometraje", ""),
        "estado_inicial": getattr(ticket, "estado_inicial", ""),
        "motivo_visita": getattr(ticket, "motivo_visita", ""),
        "observaciones_recepcion": getattr(ticket, "observaciones", ""),
    }

    # Generate PDF bytes
    pdf_bytes = generar_pdf_ticket_completo(
        ticket_data=ticket_data,
        procesos=[],
        repuestos=[],
        fotos=[],
        cobros=[],
    )

    # Save to file
    pdf_dir = "uploads/pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(pdf_dir, f"ticket_{ticket_id}_{timestamp}.pdf")

    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    return pdf_path
