"""
Utilidad centralizada para rutas de almacenamiento de archivos por taller.

Todos los archivos subidos al sistema se organizan bajo:
    uploads/talleres/{taller_id}/{tipo}/

Tipos válidos: logos, fotos, exports, pdfs, compras, firmas

El taller_id siempre debe provenir de request.state.taller_id (JWT),
nunca del body o query params del cliente.
"""
import io
import os

from PIL import Image

# Tipos de upload permitidos
TIPOS_UPLOAD_VALIDOS = {"logos", "fotos", "exports", "pdfs", "compras", "firmas"}

# Configuración de compresión de imágenes
IMAGE_MAX_SIZE = (960, 960)
IMAGE_QUALITY = 65


def get_upload_path(taller_id: int, tipo: str) -> str:
    """
    Retorna la ruta de almacenamiento para archivos de un taller.
    Crea el directorio si no existe.

    Args:
        taller_id: ID del taller (debe venir de request.state.taller_id)
        tipo: Subcarpeta del tipo de archivo (logos, fotos, exports, pdfs, compras, firmas)

    Returns:
        Ruta absoluta al directorio del taller para el tipo dado.

    Raises:
        ValueError: Si el tipo no es válido.
    """
    if tipo not in TIPOS_UPLOAD_VALIDOS:
        raise ValueError(
            f"Tipo de upload '{tipo}' no válido. "
            f"Tipos permitidos: {', '.join(sorted(TIPOS_UPLOAD_VALIDOS))}"
        )

    path = os.path.join("uploads", "talleres", str(taller_id), tipo)
    os.makedirs(path, exist_ok=True)
    return path


def comprimir_imagen(content: bytes) -> tuple[bytes, str]:
    """
    Comprime una imagen a máximo 1280x1280px con calidad JPEG 75%.
    Retorna (bytes_comprimidos, extension).
    Si falla por cualquier razón, retorna el contenido original sin modificar.

    Args:
        content: Bytes del archivo original.

    Returns:
        Tupla (bytes, ext) donde ext es '.jpg' si se comprimió, o la extensión original si falló.
    """
    try:
        img = Image.open(io.BytesIO(content))
        # Convertir a RGB para asegurar compatibilidad JPEG (elimina canal alpha si existe)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.thumbnail(IMAGE_MAX_SIZE, Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=IMAGE_QUALITY, optimize=True)
        return output.getvalue(), ".jpg"
    except Exception:
        # Fallback: devolver original sin comprimir
        return content, None
