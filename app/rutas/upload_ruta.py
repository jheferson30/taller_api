import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.configuracion.limiter import limiter
from app.seguridad.auth_middleware import require_auth
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
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_UPLOAD_PER_MINUTE", "10") + "/minute")
async def subir_foto(
    request: Request,
    file: UploadFile = File(...),
):
    """Sube una foto de evidencia del ticket"""
    # Extract taller_id from JWT
    taller_id = request.state.taller_id
    
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot upload files."
        )
    
    # Validate file using FileValidator (checks size and MIME type)
    await FileValidator.validate_file(file)

    # Generar nombre único
    filename = _generar_nombre_archivo(file.filename)
    
    # Create tenant-specific directory: uploads/talleres/{taller_id}/fotos/
    tenant_fotos_dir = os.path.join(UPLOAD_DIR, "talleres", str(taller_id), "fotos")
    os.makedirs(tenant_fotos_dir, exist_ok=True)
    
    filepath = os.path.join(tenant_fotos_dir, filename)

    # Guardar archivo
    try:
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    # Retornar URL relativa con taller_id en el path
    return {"filename": filename, "url": f"/uploads/talleres/{taller_id}/fotos/{filename}", "size": len(content)}


@router.post("/compra")
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_UPLOAD_PER_MINUTE", "10") + "/minute")
async def subir_soporte_compra(
    request: Request,
    file: UploadFile = File(...),
):
    """Sube un soporte de compra (factura, recibo)"""
    # Extract taller_id from JWT
    taller_id = request.state.taller_id
    
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot upload files."
        )
    
    # Validate file using FileValidator (checks size and MIME type)
    await FileValidator.validate_file(file)

    # Generar nombre único
    filename = _generar_nombre_archivo(file.filename)
    
    # Create tenant-specific directory: uploads/talleres/{taller_id}/compras/
    tenant_compras_dir = os.path.join(UPLOAD_DIR, "talleres", str(taller_id), "compras")
    os.makedirs(tenant_compras_dir, exist_ok=True)
    
    filepath = os.path.join(tenant_compras_dir, filename)

    # Guardar archivo
    try:
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    # Retornar URL relativa con taller_id en el path
    return {"filename": filename, "url": f"/uploads/talleres/{taller_id}/compras/{filename}", "size": len(content)}


@router.post("/firma")
@require_auth
@limiter.limit(os.getenv("RATE_LIMIT_UPLOAD_PER_MINUTE", "10") + "/minute")
async def subir_firma(
    request: Request,
    file: UploadFile = File(...),
):
    """Sube una firma de entrega"""
    # Extract taller_id from JWT
    taller_id = request.state.taller_id
    
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot upload files."
        )
    
    # Validate file using FileValidator (checks size and MIME type)
    await FileValidator.validate_file(file)

    # Generar nombre único
    filename = _generar_nombre_archivo(file.filename)
    
    # Create tenant-specific directory: uploads/talleres/{taller_id}/firmas/
    tenant_firmas_dir = os.path.join(UPLOAD_DIR, "talleres", str(taller_id), "firmas")
    os.makedirs(tenant_firmas_dir, exist_ok=True)
    
    filepath = os.path.join(tenant_firmas_dir, filename)

    # Guardar archivo
    try:
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    # Retornar URL relativa con taller_id en el path
    return {"filename": filename, "url": f"/uploads/talleres/{taller_id}/firmas/{filename}", "size": len(content)}


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
@require_auth
async def obtener_foto(request: Request, filename: str):
    """Sirve una foto"""
    # Extract taller_id from JWT
    taller_id = request.state.taller_id
    
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot access files."
        )
    
    # Build path with taller_id: uploads/talleres/{taller_id}/fotos/{filename}
    tenant_fotos_dir = os.path.join(UPLOAD_DIR, "talleres", str(taller_id), "fotos")
    filepath = _safe_filepath(tenant_fotos_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(filepath)


@router.get("/compras/{filename}")
@require_auth
async def obtener_compra(request: Request, filename: str):
    """Sirve un soporte de compra"""
    # Extract taller_id from JWT
    taller_id = request.state.taller_id
    
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot access files."
        )
    
    # Build path with taller_id: uploads/talleres/{taller_id}/compras/{filename}
    tenant_compras_dir = os.path.join(UPLOAD_DIR, "talleres", str(taller_id), "compras")
    filepath = _safe_filepath(tenant_compras_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(filepath)


@router.get("/firmas/{filename}")
@require_auth
async def obtener_firma(request: Request, filename: str):
    """Sirve una firma"""
    # Extract taller_id from JWT
    taller_id = request.state.taller_id
    
    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot access files."
        )
    
    # Build path with taller_id: uploads/talleres/{taller_id}/firmas/{filename}
    tenant_firmas_dir = os.path.join(UPLOAD_DIR, "talleres", str(taller_id), "firmas")
    filepath = _safe_filepath(tenant_firmas_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(filepath)
