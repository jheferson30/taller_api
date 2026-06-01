"""
Utilidades comunes para generación de PDFs.

Este módulo contiene funciones y constantes compartidas entre los diferentes
generadores de PDF del sistema (tickets, reportes de economía, etc.).
"""

import os
from io import BytesIO

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.platypus import Image, Paragraph


# ── Paleta de colores común ─────────────────────────────────────────────────
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
    """Formatea un número como pesos colombianos sin decimales.
    
    Args:
        valor: Número a formatear
        
    Returns:
        String formateado como "$X.XXX.XXX" o "$0" si hay error
    """
    try:
        return f"${int(valor):,}".replace(",", ".")
    except Exception:
        return "$0"


def imagen_escalada(ruta: str, max_w: float, max_h: float) -> Image:
    """Crea una Image de ReportLab escalada proporcionalmente dentro de max_w x max_h.
    
    Redimensiona en memoria para evitar procesar imágenes de alta resolución completas.
    
    Args:
        ruta: Ruta al archivo de imagen
        max_w: Ancho máximo en puntos
        max_h: Alto máximo en puntos
        
    Returns:
        Objeto Image de ReportLab escalado
    """
    MAX_PX = 1200  # máximo de píxeles en cualquier dimensión antes de procesar
    with PILImage.open(ruta) as img:
        # Convertir a RGB si es necesario (evita errores con PNG con transparencia)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        orig_w, orig_h = img.size

        # Redimensionar si la imagen es muy grande (optimización de rendimiento)
        if orig_w > MAX_PX or orig_h > MAX_PX:
            scale = min(MAX_PX / orig_w, MAX_PX / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            img = img.resize((new_w, new_h), PILImage.LANCZOS)
            orig_w, orig_h = new_w, new_h

        ratio = min(max_w / orig_w, max_h / orig_h)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=75, optimize=True)
        buf.seek(0)
        return Image(buf, width=orig_w * ratio, height=orig_h * ratio)


def resolver_logo_taller(datos_taller: dict) -> str | None:
    """Resuelve la ruta del logo del taller.
    
    Busca primero en uploads/ (persistente), luego en assets/ (fallback).
    
    Args:
        datos_taller: Diccionario con datos del taller (debe incluir 'logo_url')
        
    Returns:
        Ruta al archivo del logo o None si no se encuentra
    """
    logo_url_taller = datos_taller.get("logo_url") or ""
    
    if logo_url_taller:
        # logo_url tiene formato /uploads/logo/logo_xxx.png
        ruta_relativa = logo_url_taller.lstrip("/")
        if os.path.exists(ruta_relativa):
            return ruta_relativa
    
    # Fallback a logo genérico en assets
    fallback = os.path.join("frontend", "public", "assets", "logo.png")
    if os.path.exists(fallback):
        return fallback
    
    return None


def campo(label: str, valor, style_label, style_val):
    """Devuelve una fila [label, valor] para tablas de datos.
    
    Args:
        label: Etiqueta del campo
        valor: Valor del campo
        style_label: Estilo de ReportLab para la etiqueta
        style_val: Estilo de ReportLab para el valor
        
    Returns:
        Lista con dos Paragraph objects [label, valor]
    """
    return [
        Paragraph(label, style_label),
        Paragraph(str(valor) if valor else "No especificado", style_val),
    ]


def resolver_ruta_img(url: str) -> str:
    """Convierte URL o ruta relativa a ruta local del sistema de archivos.
    
    Args:
        url: URL o ruta de la imagen
        
    Returns:
        Ruta local al archivo o string vacío si no es válida
    """
    if not url:
        return ""
    import re

    def _sanitizar(ruta: str) -> str:
        # Normalizar separadores y prevenir path traversal
        ruta = ruta.replace("\\", "/")
        partes = [p for p in ruta.split("/") if p and p != "."]
        resultado = []
        for p in partes:
            if p == "..":
                if resultado:
                    resultado.pop()
            else:
                resultado.append(p)
        return "/".join(resultado)

    match = re.match(r"https?://[^/]+/uploads/(.+)", url)
    if match:
        ruta = _sanitizar(match.group(1))
        if not ruta:
            return ""
        return os.path.join("uploads", *ruta.split("/"))
    if url.startswith("/uploads/"):
        ruta = _sanitizar(url[len("/uploads/") :])
        if not ruta:
            return ""
        return os.path.join("uploads", *ruta.split("/"))
    if url.startswith("uploads/"):
        ruta = _sanitizar(url[len("uploads/") :])
        if not ruta:
            return ""
        return os.path.join("uploads", *ruta.split("/"))
    return ""
