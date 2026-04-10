import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.utils.input_validator import FileValidator

router = APIRouter(prefix="/upload", tags=["Upload"])

# Directorio base para uploads
UPLOAD_DIR = "uploads"
FOTOS_DIR = os.path.join(UPLOAD_DIR, "fotos")
COMPRAS_DIR = os.path.join(UPLOAD_DIR, "compras")
FIRMAS_DIR = os.path.join(UPLOAD_DIR, "firmas")

# Crear directorios si no existen
os.makedirs(FOTOS_DIR, exist_ok=True)
os.makedirs(COMPRAS_DIR, exist_ok=True)
os.makedirs(FIRMAS_DIR, exist_ok=True)


def _generar_nombre_archivo(original_filename: str) -> str:
    """Genera un nombre único para el archivo"""
    ext = os.path.splitext(original_filename)[1].lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique_id}{ext}"


@router.post("/foto")
async def subir_foto(
    request: Request,
    file: UploadFile = File(...),
):
    """Sube una foto de evidencia del ticket"""
    # Validate file using FileValidator (checks size and MIME type)
    await FileValidator.validate_file(file)

    # Generar nombre único
    filename = _generar_nombre_archivo(file.filename)
    filepath = os.path.join(FOTOS_DIR, filename)

    # Guardar archivo
    try:
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    # Retornar URL relativa
    return {"filename": filename, "url": f"/uploads/fotos/{filename}", "size": len(content)}


@router.post("/compra")
async def subir_soporte_compra(
    request: Request,
    file: UploadFile = File(...),
):
    """Sube un soporte de compra (factura, recibo)"""
    # Validate file using FileValidator (checks size and MIME type)
    await FileValidator.validate_file(file)

    # Generar nombre único
    filename = _generar_nombre_archivo(file.filename)
    filepath = os.path.join(COMPRAS_DIR, filename)

    # Guardar archivo
    try:
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    # Retornar URL relativa
    return {"filename": filename, "url": f"/uploads/compras/{filename}", "size": len(content)}


@router.post("/firma")
async def subir_firma(
    request: Request,
    file: UploadFile = File(...),
):
    """Sube una firma de entrega"""
    # Validate file using FileValidator (checks size and MIME type)
    await FileValidator.validate_file(file)

    # Generar nombre único
    filename = _generar_nombre_archivo(file.filename)
    filepath = os.path.join(FIRMAS_DIR, filename)

    # Guardar archivo
    try:
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    # Retornar URL relativa
    return {"filename": filename, "url": f"/uploads/firmas/{filename}", "size": len(content)}


def _safe_filepath(base_dir: str, filename: str) -> str:
    """Valida que el path resultante esté dentro del directorio base (previene path traversal)"""
    # Solo permitir nombre de archivo simple, sin separadores de directorio
    safe_name = os.path.basename(filename)
    filepath = os.path.realpath(os.path.join(base_dir, safe_name))
    base_real = os.path.realpath(base_dir)
    if not filepath.startswith(base_real + os.sep) and filepath != base_real:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    return filepath


@router.get("/fotos/{filename}")
async def obtener_foto(filename: str):
    """Sirve una foto"""
    filepath = _safe_filepath(FOTOS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(filepath)


@router.get("/compras/{filename}")
async def obtener_compra(filename: str):
    """Sirve un soporte de compra"""
    filepath = _safe_filepath(COMPRAS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(filepath)


@router.get("/firmas/{filename}")
async def obtener_firma(filename: str):
    """Sirve una firma"""
    filepath = _safe_filepath(FIRMAS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(filepath)
