"""
Celery tasks for PDF generation.

Tasks for async PDF generation and cleanup.
"""

import glob
import os
from datetime import datetime, timedelta
from typing import Any

from celery import Task

from app.configuracion.base_datos import SessionLocal
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="generate_ticket_pdf")
def generate_ticket_pdf_task(self: Task, ticket_id: int) -> dict[str, Any]:
    """
    Generate PDF for a ticket asynchronously.

    Args:
        ticket_id: ID of the ticket to generate PDF for

    Returns:
        dict with status, file_path, and metadata

    Example result:
        {
            "status": "completed",
            "file_path": "uploads/pdfs/ticket_123_20260410.pdf",
            "ticket_id": 123,
            "generated_at": "2026-04-10T12:00:00"
        }
    """
    db = SessionLocal()

    try:
        # Import here to avoid circular imports
        from app.repositorios.ticket_repository import TicketRepository
        from app.utils.pdf_generator import generar_pdf_ticket

        # Verify ticket exists
        ticket_repo = TicketRepository(db)
        ticket = ticket_repo.get_by_id(ticket_id)

        if not ticket:
            return {
                "status": "failed",
                "error": f"Ticket {ticket_id} not found",
                "ticket_id": ticket_id,
            }

        # Generate PDF
        pdf_path = generar_pdf_ticket(ticket_id, db)

        return {
            "status": "completed",
            "file_path": pdf_path,
            "ticket_id": ticket_id,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        # Log error and return failure status
        error_msg = str(e)

        return {
            "status": "failed",
            "error": error_msg,
            "ticket_id": ticket_id,
            "failed_at": datetime.now().isoformat(),
        }

    finally:
        db.close()


@celery_app.task(name="cleanup_old_pdfs")
def cleanup_old_pdfs() -> dict[str, Any]:
    """
    Cleanup PDF files older than 24 hours.

    This task runs periodically (configured in celery_app.py beat_schedule)
    to remove old generated PDFs and free up disk space.

    Returns:
        dict with cleanup statistics
    """
    try:
        # PDF directory
        pdf_dir = "uploads/pdfs"

        if not os.path.exists(pdf_dir):
            return {
                "status": "completed",
                "files_deleted": 0,
                "message": "PDF directory does not exist",
            }

        # Find PDFs older than 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        deleted_count = 0

        for pdf_file in glob.glob(os.path.join(pdf_dir, "*.pdf")):
            try:
                # Get file modification time
                file_mtime = datetime.fromtimestamp(os.path.getmtime(pdf_file))

                if file_mtime < cutoff_time:
                    os.remove(pdf_file)
                    deleted_count += 1

            except Exception as e:
                # Log error but continue with other files
                print(f"Error deleting {pdf_file}: {e}")
                continue

        return {
            "status": "completed",
            "files_deleted": deleted_count,
            "cleanup_time": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"status": "failed", "error": str(e), "failed_at": datetime.now().isoformat()}
