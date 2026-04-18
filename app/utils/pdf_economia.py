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

# ── Paleta (misma que pdf_generator.py) ─────────────────────────────────────
AZUL = colors.HexColor("#1e3a5f")
AZUL_MEDIO = colors.HexColor("#2563eb")
AZUL_CLARO = colors.HexColor("#dbeafe")
VERDE = colors.HexColor("#166534")
VERDE_MEDIO = colors.HexColor("#16a34a")
VERDE_BG = colors.HexColor("#dcfce7")
ROJO = colors.HexColor("#991b1b")
ROJO_MEDIO = colors.HexColor("#dc2626")
ROJO_BG = colors.HexColor("#fee2e2")
GRIS_BORDE = colors.HexColor("#cbd5e1")
GRIS_FILA = colors.HexColor("#f8fafc")
TEXTO = colors.HexColor("#1e293b")
TEXTO_MUTED = colors.HexColor("#64748b")


def fmt_cop(valor) -> str:
    try:
        return f"${int(valor):,}".replace(",", ".")
    except Exception:
        return "$0"


def limpiar_categoria(cat) -> str:
    s = str(cat)
    if "CategoriaEgreso." in s:
        s = s.replace("CategoriaEgreso.", "")
    return s.strip()


def generar_pdf_economia_profesional(
    fecha: str,
    resumen: dict,
    ingresos: dict,
    egresos: list[dict],
    datos_taller: dict = None,
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
    W = 7.4 * inch

    def estilo(name, **kw):
        base = kw.pop("parent", styles["Normal"])
        return ParagraphStyle(name, parent=base, **kw)

    s_titulo = estilo(
        "Titulo",
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=AZUL,
        alignment=TA_RIGHT,
        leading=22,
    )
    s_subtitulo = estilo("Sub", fontSize=8, textColor=TEXTO_MUTED, alignment=TA_RIGHT, leading=11)
    s_nombre = estilo("Nombre", fontSize=13, fontName="Helvetica-Bold", textColor=AZUL, leading=16)
    s_dato = estilo("Dato", fontSize=8, textColor=TEXTO_MUTED, leading=11)
    s_seccion = estilo(
        "Sec", fontSize=9, fontName="Helvetica-Bold", textColor=colors.white, leading=12
    )
    s_label = estilo("Lbl", fontSize=8, fontName="Helvetica-Bold", textColor=TEXTO, leading=11)
    s_valor = estilo("Val", fontSize=8, textColor=TEXTO, leading=11)
    s_valor_r = estilo("ValR", fontSize=8, textColor=TEXTO, alignment=TA_RIGHT, leading=11)
    s_bold_r = estilo(
        "BoldR",
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_RIGHT,
        leading=12,
    )
    s_bold_l = estilo(
        "BoldL", fontSize=9, fontName="Helvetica-Bold", textColor=colors.white, leading=12
    )
    s_footer = estilo("Footer", fontSize=7, textColor=TEXTO_MUTED, alignment=TA_CENTER, leading=10)
    s_small = estilo("Small", fontSize=7, textColor=TEXTO_MUTED, leading=10)

    story = []

    # ── Datos del taller ─────────────────────────────────────────────────────
    dt = datos_taller or {}
    nombre_taller = dt.get("nombre") or dt.get("nombre_taller") or "Taller Mecánico"
    direccion = dt.get("direccion") or ""
    telefono = dt.get("telefono") or ""
    nit = dt.get("nit") or ""

    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        fecha_fmt = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        fecha_fmt = fecha

    # ── ENCABEZADO ───────────────────────────────────────────────────────────
    logo_path = os.path.join("frontend", "public", "assets", "logo.png")
    col_izq = []
    if os.path.exists(logo_path):
        try:
            col_izq.append(Image(logo_path, width=0.65 * inch, height=0.65 * inch))
            col_izq.append(Spacer(1, 3))
        except Exception:
            pass
    col_izq.append(Paragraph(nombre_taller, s_nombre))
    for txt, val in [("Dir", direccion), ("Tel", telefono), ("NIT", nit)]:
        if val:
            col_izq.append(Paragraph(f"{txt}: {val}", s_dato))

    col_der = [
        Paragraph("REPORTE DE ECONOMÍA DIARIA", s_titulo),
        Paragraph(f"Fecha del reporte: {fecha_fmt}", s_subtitulo),
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

    # ── Helpers ──────────────────────────────────────────────────────────────
    def cab(titulo, color=AZUL):
        t = Table([[Paragraph(titulo, s_seccion)]], colWidths=[W])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return t

    def tbl_base(rows, col_widths, header_color=AZUL_CLARO, align_last_right=True):
        tbl = Table(rows, colWidths=col_widths)
        n = len(rows)
        cmds = [
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_FILA]),
            ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        if align_last_right:
            cmds.append(("ALIGN", (-1, 0), (-1, -1), "RIGHT"))
        tbl.setStyle(TableStyle(cmds))
        return tbl

    # ── RESUMEN EJECUTIVO ────────────────────────────────────────────────────
    ing_anticipo = resumen.get("ingreso_anticipo", 0) or 0
    ing_final = resumen.get("ingreso_final", 0) or 0
    ing_rapido = resumen.get("ingreso_rapido", 0) or 0
    total_ing = resumen.get("ingresos", 0) or 0
    total_egr = resumen.get("egresos", 0) or 0
    balance = resumen.get("balance", 0) or 0

    # Tarjetas de resumen en una fila
    def tarjeta(titulo, valor, bg, txt_color=colors.white):
        inner = Table(
            [
                [
                    Paragraph(
                        titulo,
                        estilo(
                            f"CT{titulo}",
                            fontSize=7,
                            textColor=txt_color,
                            fontName="Helvetica-Bold",
                            alignment=TA_CENTER,
                        ),
                    )
                ],
                [
                    Paragraph(
                        fmt_cop(valor),
                        estilo(
                            f"CV{titulo}",
                            fontSize=13,
                            fontName="Helvetica-Bold",
                            textColor=txt_color,
                            alignment=TA_CENTER,
                        ),
                    )
                ],
            ],
            colWidths=[1.7 * inch],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), bg),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                ]
            )
        )
        return inner

    tarjetas = Table(
        [
            [
                tarjeta("Anticipos", ing_anticipo, AZUL_MEDIO),
                tarjeta("Cobros finales", ing_final, AZUL),
                tarjeta("Cobros rápidos", ing_rapido, colors.HexColor("#f59e0b")),
            ],
            [
                tarjeta("Total ingresos", total_ing, VERDE_MEDIO),
                tarjeta("Total egresos", total_egr, ROJO_MEDIO),
                tarjeta("Balance del día", balance, VERDE_MEDIO if balance >= 0 else ROJO_MEDIO),
            ],
        ],
        colWidths=[2.47 * inch, 2.47 * inch, 2.47 * inch],
    )
    tarjetas.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                cab("RESUMEN EJECUTIVO"),
                Spacer(1, 6),
                tarjetas,
                Spacer(1, 0.14 * inch),
            ]
        )
    )

    # ── ESTADÍSTICAS DEL DÍA ────────────────────────────────────────────────
    stats = [
        [
            Paragraph("Tickets cerrados hoy", s_label),
            Paragraph(str(resumen.get("tickets_cerrados_hoy", 0)), s_valor),
        ],
        [
            Paragraph("Tickets con anticipo hoy", s_label),
            Paragraph(str(resumen.get("tickets_abiertos_con_anticipo_hoy", 0)), s_valor),
        ],
        [
            Paragraph("Anticipos registrados", s_label),
            Paragraph(str(len(ingresos.get("anticipos", []))), s_valor),
        ],
        [
            Paragraph("Cobros finales registrados", s_label),
            Paragraph(str(len(ingresos.get("cobros_finales", []))), s_valor),
        ],
        [Paragraph("Egresos registrados", s_label), Paragraph(str(len(egresos)), s_valor)],
    ]
    tbl_stats = Table(stats, colWidths=[5.4 * inch, 2.0 * inch])
    tbl_stats.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [AZUL_CLARO, colors.white]),
                ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ]
        )
    )
    story.append(
        KeepTogether(
            [
                cab("ESTADÍSTICAS DEL DÍA"),
                tbl_stats,
                Spacer(1, 0.14 * inch),
            ]
        )
    )

    # ── ANTICIPOS ────────────────────────────────────────────────────────────
    anticipos = ingresos.get("anticipos", [])
    if anticipos:
        rows = [
            [
                Paragraph("Ticket", s_label),
                Paragraph("Placa", s_label),
                Paragraph("Método", s_label),
                Paragraph("Responsable", s_label),
                Paragraph(
                    "Valor",
                    estilo(
                        "LR",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=TEXTO,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        ]
        for a in anticipos:
            rows.append(
                [
                    Paragraph(a.get("ticket_codigo") or "—", s_small),
                    Paragraph(a.get("placa") or "—", s_valor),
                    Paragraph(a.get("metodo_pago") or "—", s_valor),
                    Paragraph(a.get("responsable") or "—", s_valor),
                    Paragraph(fmt_cop(a.get("valor_anticipo", 0)), s_valor_r),
                ]
            )
        tbl = tbl_base(rows, [2.2 * inch, 0.9 * inch, 1.2 * inch, 1.5 * inch, 1.6 * inch])
        story.append(
            KeepTogether(
                [
                    cab("ANTICIPOS RECIBIDOS", VERDE_MEDIO),
                    tbl,
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── COBROS FINALES ───────────────────────────────────────────────────────
    cobros_finales = ingresos.get("cobros_finales", [])
    if cobros_finales:
        rows = [
            [
                Paragraph("Ticket", s_label),
                Paragraph("Placa", s_label),
                Paragraph("Método", s_label),
                Paragraph("Responsable", s_label),
                Paragraph(
                    "Valor",
                    estilo(
                        "LR2",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=TEXTO,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        ]
        for c in cobros_finales:
            rows.append(
                [
                    Paragraph(c.get("ticket_codigo") or "—", s_small),
                    Paragraph(c.get("placa") or "—", s_valor),
                    Paragraph(c.get("metodo_pago") or "—", s_valor),
                    Paragraph(c.get("responsable") or "—", s_valor),
                    Paragraph(fmt_cop(c.get("valor_final_cobrado", 0)), s_valor_r),
                ]
            )
        tbl = tbl_base(rows, [2.2 * inch, 0.9 * inch, 1.2 * inch, 1.5 * inch, 1.6 * inch])
        story.append(
            KeepTogether(
                [
                    cab("COBROS FINALES", VERDE_MEDIO),
                    tbl,
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── COBROS RÁPIDOS ───────────────────────────────────────────────────────
    cobros_rapidos = ingresos.get("cobros_rapidos", [])
    if cobros_rapidos:
        NARANJA = colors.HexColor("#f59e0b")
        rows = [
            [
                Paragraph("Descripción", s_label),
                Paragraph("Placa", s_label),
                Paragraph("Método", s_label),
                Paragraph(
                    "Valor",
                    estilo(
                        "LR3",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=TEXTO,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        ]
        for r in cobros_rapidos:
            rows.append(
                [
                    Paragraph(r.get("descripcion") or "—", s_valor),
                    Paragraph(r.get("placa") or "—", s_valor),
                    Paragraph(r.get("metodo_pago") or "—", s_valor),
                    Paragraph(fmt_cop(r.get("valor", 0)), s_valor_r),
                ]
            )
        tbl = tbl_base(rows, [3.0 * inch, 0.9 * inch, 1.2 * inch, 2.3 * inch])
        story.append(
            KeepTogether(
                [
                    cab("COBROS RÁPIDOS", NARANJA),
                    tbl,
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── EGRESOS ──────────────────────────────────────────────────────────────
    if egresos:
        # Resumen por categoría
        por_cat: dict[str, list] = {}
        for e in egresos:
            cat = limpiar_categoria(e.get("categoria", "OTRO"))
            por_cat.setdefault(cat, []).append(e)

        rows_cat = [
            [
                Paragraph("Categoría", s_label),
                Paragraph(
                    "Cantidad",
                    estilo(
                        "CC",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=TEXTO,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    "Total",
                    estilo(
                        "CT2",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=TEXTO,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        ]
        for cat, items in por_cat.items():
            total_cat = sum(i.get("valor", 0) for i in items)
            rows_cat.append(
                [
                    Paragraph(cat, s_valor),
                    Paragraph(
                        str(len(items)),
                        estilo("Cnt", fontSize=8, textColor=TEXTO, alignment=TA_CENTER),
                    ),
                    Paragraph(fmt_cop(total_cat), s_valor_r),
                ]
            )
        # Fila total
        rows_cat.append(
            [
                Paragraph(
                    "TOTAL EGRESOS",
                    estilo("TE", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white),
                ),
                Paragraph("", s_label),
                Paragraph(
                    fmt_cop(total_egr),
                    estilo(
                        "TEV",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=colors.white,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        )
        n_cat = len(rows_cat)
        tbl_cat = Table(rows_cat, colWidths=[4.4 * inch, 1.5 * inch, 1.5 * inch])
        tbl_cat.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
                    ("ROWBACKGROUNDS", (0, 1), (-1, n_cat - 2), [colors.white, GRIS_FILA]),
                    ("BACKGROUND", (0, n_cat - 1), (-1, n_cat - 1), ROJO_MEDIO),
                    ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ]
            )
        )

        # Detalle completo
        rows_det = [
            [
                Paragraph("Categoría", s_label),
                Paragraph("Concepto", s_label),
                Paragraph("Ticket", s_label),
                Paragraph("Responsable", s_label),
                Paragraph(
                    "Valor",
                    estilo(
                        "LRD",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=TEXTO,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        ]
        for e in egresos:
            rows_det.append(
                [
                    Paragraph(limpiar_categoria(e.get("categoria", "OTRO")), s_small),
                    Paragraph(str(e.get("concepto") or "—")[:45], s_valor),
                    Paragraph(str(e.get("ticket_codigo") or "—")[:22], s_small),
                    Paragraph(str(e.get("responsable") or "—")[:20], s_valor),
                    Paragraph(fmt_cop(e.get("valor", 0)), s_valor_r),
                ]
            )
        tbl_det = tbl_base(rows_det, [1.0 * inch, 2.5 * inch, 1.5 * inch, 1.2 * inch, 1.2 * inch])

        story.append(
            KeepTogether(
                [
                    cab("EGRESOS DEL DÍA", ROJO_MEDIO),
                    tbl_cat,
                    Spacer(1, 8),
                    Paragraph(
                        "Detalle completo",
                        estilo(
                            "SubDet", fontSize=8, fontName="Helvetica-Bold", textColor=TEXTO_MUTED
                        ),
                    ),
                    Spacer(1, 4),
                    tbl_det,
                    Spacer(1, 0.14 * inch),
                ]
            )
        )

    # ── PIE DE PÁGINA ────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.1 * inch))
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
            f"Reporte generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}  •  "
            f"Período: {fecha_fmt}  •  {nombre_taller}",
            s_footer,
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
