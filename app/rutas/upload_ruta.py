import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

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

# Extensiones permitidas
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _validar_archivo(file: UploadFile):
    """Valida extensión y tamaño del archivo"""
    # Validar extensión
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validar tamaño (si es posible)
    if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
        file.file.seek(0, 2)  # Ir al final
        size = file.file.tell()
        file.file.seek(0)  # Volver al inicio
        
        if size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo muy grande. Máximo: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )


def _generar_nombre_archivo(original_filename: str) -> str:
    """Genera un nombre único para el archivo"""
    ext = os.path.splitext(original_filename)[1].lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique_id}{ext}"


@router.post("/foto")
async def subir_foto(file: UploadFile = File(...)):
    """Sube una foto de evidencia del ticket"""
    _validar_archivo(file)
    
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
    return {
        "filename": filename,
        "url": f"/uploads/fotos/{filename}",
        "size": len(content)
    }


@router.post("/compra")
async def subir_soporte_compra(file: UploadFile = File(...)):
    """Sube un soporte de compra (factura, recibo)"""
    _validar_archivo(file)
    
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
    return {
        "filename": filename,
        "url": f"/uploads/compras/{filename}",
        "size": len(content)
    }


@router.post("/firma")
async def subir_firma(file: UploadFile = File(...)):
    """Sube una firma de entrega"""
    _validar_archivo(file)
    
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
    return {
        "filename": filename,
        "url": f"/uploads/firmas/{filename}",
        "size": len(content)
    }


@router.get("/fotos/{filename}")
async def obtener_foto(filename: str):
    """Sirve una foto"""
    filepath = os.path.join(FOTOS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(filepath)


@router.get("/compras/{filename}")
async def obtener_compra(filename: str):
    """Sirve un soporte de compra"""
    filepath = os.path.join(COMPRAS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(filepath)


@router.get("/firmas/{filename}")
async def obtener_firma(filename: str):
    """Sirve una firma"""
    filepath = os.path.join(FIRMAS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(filepath)
