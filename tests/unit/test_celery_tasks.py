"""
Unit tests for Celery tasks.

Tests cover:
- PDF generation task completes successfully for valid ticket
- PDF generation task fails gracefully for invalid ticket
- Task returns correct status and file_path
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.tasks.pdf_tasks import generate_ticket_pdf_task, cleanup_old_pdfs


class TestPDFGenerationTask:
    """Tests for generate_ticket_pdf_task."""

    @patch('app.tasks.pdf_tasks.SessionLocal')
    def test_pdf_generation_success(self, mock_session):
        """Test that PDF generation task completes successfully for valid ticket."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value = mock_db

        mock_ticket = Mock()
        mock_ticket.id = 123

        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_ticket

        with patch('app.repositorios.ticket_repository.TicketRepository', return_value=mock_repo), \
             patch('app.utils.pdf_generator.generar_pdf_ticket', return_value="uploads/pdfs/ticket_123.pdf"):
            # Act
            result = generate_ticket_pdf_task(123)

            # Assert
            assert result["status"] == "completed"
            assert result["file_path"] == "uploads/pdfs/ticket_123.pdf"
            assert result["ticket_id"] == 123
            assert "generated_at" in result
            mock_db.close.assert_called_once()

    @patch('app.tasks.pdf_tasks.SessionLocal')
    def test_pdf_generation_ticket_not_found(self, mock_session):
        """Test that PDF generation task fails gracefully for invalid ticket."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value = mock_db

        mock_repo = Mock()
        mock_repo.get_by_id.return_value = None  # Ticket not found

        with patch('app.repositorios.ticket_repository.TicketRepository', return_value=mock_repo):
            # Act
            result = generate_ticket_pdf_task(999)

            # Assert
            assert result["status"] == "failed"
            assert "not found" in result["error"].lower()
            assert result["ticket_id"] == 999

            mock_db.close.assert_called_once()

    @patch('app.tasks.pdf_tasks.SessionLocal')
    def test_pdf_generation_handles_exception(self, mock_session):
        """Test that PDF generation task handles exceptions gracefully."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value = mock_db

        mock_ticket = Mock()
        mock_ticket.id = 123

        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_ticket

        with patch('app.repositorios.ticket_repository.TicketRepository', return_value=mock_repo), \
             patch('app.utils.pdf_generator.generar_pdf_ticket', side_effect=Exception("PDF generation error")):
            # Act
            result = generate_ticket_pdf_task(123)

            # Assert
            assert result["status"] == "failed"
            assert "PDF generation error" in result["error"]
            assert result["ticket_id"] == 123
            assert "failed_at" in result

            mock_db.close.assert_called_once()

    @patch('app.tasks.pdf_tasks.SessionLocal')
    def test_pdf_generation_returns_correct_structure(self, mock_session):
        """Test that task returns correct status and file_path structure."""
        # Arrange
        mock_db = Mock()
        mock_session.return_value = mock_db

        mock_ticket = Mock()
        mock_ticket.id = 456

        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_ticket

        with patch('app.repositorios.ticket_repository.TicketRepository', return_value=mock_repo), \
             patch('app.utils.pdf_generator.generar_pdf_ticket', return_value="uploads/pdfs/ticket_456.pdf"):
            # Act
            result = generate_ticket_pdf_task(456)

            # Assert - verify structure
            assert isinstance(result, dict)
            assert "status" in result
            assert "file_path" in result
            assert "ticket_id" in result
            assert "generated_at" in result

            assert result["status"] == "completed"
            assert result["ticket_id"] == 456
            assert result["file_path"].endswith(".pdf")


class TestCleanupOldPDFs:
    """Tests for cleanup_old_pdfs task."""
    
    @patch('app.tasks.pdf_tasks.os.path.exists')
    def test_cleanup_when_directory_not_exists(self, mock_exists):
        """Test cleanup when PDF directory doesn't exist."""
        # Arrange
        mock_exists.return_value = False
        
        # Act
        result = cleanup_old_pdfs()
        
        # Assert
        assert result["status"] == "completed"
        assert result["files_deleted"] == 0
        assert "does not exist" in result["message"]
    
    @patch('app.tasks.pdf_tasks.glob.glob')
    @patch('app.tasks.pdf_tasks.os.path.exists')
    @patch('app.tasks.pdf_tasks.os.path.getmtime')
    @patch('app.tasks.pdf_tasks.os.remove')
    @patch('app.tasks.pdf_tasks.datetime')
    def test_cleanup_deletes_old_files(
        self, mock_datetime, mock_remove, mock_getmtime, mock_exists, mock_glob
    ):
        """Test that cleanup deletes files older than 24 hours."""
        # Arrange
        mock_exists.return_value = True
        mock_glob.return_value = [
            "uploads/pdfs/old_file.pdf",
            "uploads/pdfs/recent_file.pdf"
        ]
        
        # Mock datetime to control time
        from datetime import datetime, timedelta
        now = datetime(2026, 4, 10, 12, 0, 0)
        mock_datetime.now.return_value = now
        mock_datetime.fromtimestamp.side_effect = lambda ts: datetime.fromtimestamp(ts)
        
        # old_file is 25 hours old (should be deleted)
        # recent_file is 12 hours old (should not be deleted)
        def getmtime_side_effect(path):
            if "old_file" in path:
                return (now - timedelta(hours=25)).timestamp()
            else:
                return (now - timedelta(hours=12)).timestamp()
        
        mock_getmtime.side_effect = getmtime_side_effect
        
        # Act
        result = cleanup_old_pdfs()
        
        # Assert
        assert result["status"] == "completed"
        assert result["files_deleted"] == 1
        mock_remove.assert_called_once_with("uploads/pdfs/old_file.pdf")
    
    @patch('app.tasks.pdf_tasks.glob.glob')
    @patch('app.tasks.pdf_tasks.os.path.exists')
    def test_cleanup_handles_no_files(self, mock_exists, mock_glob):
        """Test cleanup when no PDF files exist."""
        # Arrange
        mock_exists.return_value = True
        mock_glob.return_value = []
        
        # Act
        result = cleanup_old_pdfs()
        
        # Assert
        assert result["status"] == "completed"
        assert result["files_deleted"] == 0
    
    @patch('app.tasks.pdf_tasks.glob.glob')
    @patch('app.tasks.pdf_tasks.os.path.exists')
    @patch('app.tasks.pdf_tasks.os.path.getmtime')
    @patch('app.tasks.pdf_tasks.os.remove')
    def test_cleanup_continues_on_error(
        self, mock_remove, mock_getmtime, mock_exists, mock_glob
    ):
        """Test that cleanup continues even if one file deletion fails."""
        # Arrange
        mock_exists.return_value = True
        mock_glob.return_value = [
            "uploads/pdfs/file1.pdf",
            "uploads/pdfs/file2.pdf"
        ]
        
        from datetime import datetime, timedelta
        old_time = (datetime.now() - timedelta(hours=25)).timestamp()
        mock_getmtime.return_value = old_time
        
        # First file fails, second succeeds
        mock_remove.side_effect = [Exception("Permission denied"), None]
        
        # Act
        result = cleanup_old_pdfs()
        
        # Assert
        assert result["status"] == "completed"
        assert result["files_deleted"] == 1  # Only second file deleted
        assert mock_remove.call_count == 2
