"""
PDF generation API routes.

Provides endpoints for async PDF generation using Celery.
"""

import os

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.seguridad.auth_middleware import require_auth
from app.tasks.pdf_tasks import generate_ticket_pdf_task

router = APIRouter(prefix="/pdf", tags=["PDF Generation"])


@router.post("/tickets/{ticket_id}/generate")
@require_auth
async def generate_ticket_pdf(
    ticket_id: int, request: Request, db: Session = Depends(obtener_db)
):
    """
    Start async PDF generation for a ticket.

    Returns task_id to check status later.

    Args:
        ticket_id: ID of the ticket to generate PDF for
        request: FastAPI request object (contains authenticated user context)

    Returns:
        dict with task_id and status

    Example response:
        {
            "task_id": "abc123-def456-ghi789",
            "status": "processing",
            "ticket_id": 123
        }

    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If ticket not found or belongs to different taller
    """
    # Extract taller_id from JWT (never from request body/params)
    taller_id = request.state.taller_id

    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot access tenant data.",
        )

    # Verify ticket exists and belongs to authenticated user's taller
    from app.modelos.vehiculo import Vehiculo
    from app.repositorios.ticket_repository import TicketRepository

    ticket_repo = TicketRepository(db)
    ticket = ticket_repo.get_by_id(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Verify ticket ownership through vehiculo.taller_id
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()

    if not vehiculo or vehiculo.taller_id != taller_id:
        # Return 404 (not 403) to avoid revealing ticket exists in another taller
        raise HTTPException(status_code=404, detail="Resource not found")

    # Start async task
    task = generate_ticket_pdf_task.delay(ticket_id)

    return {
        "task_id": task.id,
        "status": "processing",
        "ticket_id": ticket_id,
        "message": "PDF generation started. Use task_id to check status.",
    }


@router.get("/tasks/{task_id}/status")
@require_auth
async def get_task_status(task_id: str, request: Request):
    """
    Check status of PDF generation task.

    Args:
        task_id: Task ID returned from generate endpoint
        request: FastAPI request object (contains authenticated user context)

    Returns:
        dict with task status and result if completed

    Example responses:
        Processing:
        {
            "task_id": "abc123",
            "status": "processing"
        }

        Completed:
        {
            "task_id": "abc123",
            "status": "completed",
            "result": {
                "status": "completed",
                "file_path": "uploads/pdfs/ticket_123.pdf",
                "ticket_id": 123
            }
        }

        Failed:
        {
            "task_id": "abc123",
            "status": "failed",
            "result": {
                "status": "failed",
                "error": "Error message"
            }
        }

    Raises:
        HTTPException 401: If user is not authenticated
    """
    task_result = AsyncResult(task_id)

    if task_result.ready():
        result = task_result.get()
        return {"task_id": task_id, "status": result.get("status"), "result": result}
    else:
        return {"task_id": task_id, "status": "processing", "message": "Task is still processing"}


@router.get("/tasks/{task_id}/result")
@require_auth
async def download_pdf(task_id: str, request: Request, db: Session = Depends(obtener_db)):
    """
    Download generated PDF.

    Args:
        task_id: Task ID returned from generate endpoint
        request: FastAPI request object (contains authenticated user context)

    Returns:
        PDF file as download

    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 202: If still processing
        HTTPException 404: If file not found or belongs to different taller
        HTTPException 500: If generation failed
    """
    # Extract taller_id from JWT (never from request body/params)
    taller_id = request.state.taller_id

    if taller_id is None:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a tenant context. SUPER_ADMIN cannot access tenant data.",
        )

    task_result = AsyncResult(task_id)

    if not task_result.ready():
        raise HTTPException(
            status_code=202, detail="PDF still processing. Check status endpoint for updates."
        )

    result = task_result.get()

    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {result.get('error')}")

    file_path = result.get("file_path")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail="PDF file not found. It may have been cleaned up."
        )

    # Verify ticket ownership before serving PDF
    ticket_id = result.get("ticket_id")
    if ticket_id:
        from app.modelos.vehiculo import Vehiculo
        from app.repositorios.ticket_repository import TicketRepository

        ticket_repo = TicketRepository(db)
        ticket = ticket_repo.get_by_id(ticket_id)

        if not ticket:
            raise HTTPException(status_code=404, detail="Resource not found")

        # Verify ticket ownership through vehiculo.taller_id
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == ticket.vehiculo_id).first()

        if not vehiculo or vehiculo.taller_id != taller_id:
            # Return 404 (not 403) to avoid revealing ticket exists in another taller
            raise HTTPException(status_code=404, detail="Resource not found")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
        headers={"Content-Disposition": f'attachment; filename="{os.path.basename(file_path)}"'},
    )
