"""
PDF generation API routes.

Provides endpoints for async PDF generation using Celery.
"""

import os

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.configuracion.base_datos import obtener_db
from app.tasks.pdf_tasks import generate_ticket_pdf_task

router = APIRouter(prefix="/pdf", tags=["PDF Generation"])


@router.post("/tickets/{ticket_id}/generate")
async def generate_ticket_pdf(ticket_id: int, db: Session = Depends(obtener_db)):
    """
    Start async PDF generation for a ticket.

    Returns task_id to check status later.

    Args:
        ticket_id: ID of the ticket to generate PDF for

    Returns:
        dict with task_id and status

    Example response:
        {
            "task_id": "abc123-def456-ghi789",
            "status": "processing",
            "ticket_id": 123
        }
    """
    # Verify ticket exists
    from app.repositorios.ticket_repository import TicketRepository

    ticket_repo = TicketRepository(db)
    ticket = ticket_repo.get_by_id(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Start async task
    task = generate_ticket_pdf_task.delay(ticket_id)

    return {
        "task_id": task.id,
        "status": "processing",
        "ticket_id": ticket_id,
        "message": "PDF generation started. Use task_id to check status.",
    }


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Check status of PDF generation task.

    Args:
        task_id: Task ID returned from generate endpoint

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
    """
    task_result = AsyncResult(task_id)

    if task_result.ready():
        result = task_result.get()
        return {"task_id": task_id, "status": result.get("status"), "result": result}
    else:
        return {"task_id": task_id, "status": "processing", "message": "Task is still processing"}


@router.get("/tasks/{task_id}/result")
async def download_pdf(task_id: str):
    """
    Download generated PDF.

    Args:
        task_id: Task ID returned from generate endpoint

    Returns:
        PDF file as download

    Raises:
        HTTPException: 202 if still processing, 404 if file not found, 500 if failed
    """
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

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
        headers={"Content-Disposition": f'attachment; filename="{os.path.basename(file_path)}"'},
    )
