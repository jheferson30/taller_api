"""
Integration tests for PDF API.

Tests cover:
- Async task creation returns task_id
- Task status endpoint returns correct status
- PDF download endpoint returns file
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from app.main import app


client = TestClient(app)


class TestPDFAPI:
    """Integration tests for PDF generation API."""
    
    @patch('app.rutas.pdf_ruta.generate_ticket_pdf_task')
    @patch('app.rutas.pdf_ruta.TicketRepository')
    def test_generate_pdf_returns_task_id(self, mock_repo_class, mock_task):
        """
        Test that async task creation returns task_id.
        
        Validates Requirements 6.3
        """
        # Arrange
        mock_repo = Mock()
        mock_ticket = Mock()
        mock_ticket.id = 123
        mock_repo.get_by_id.return_value = mock_ticket
        mock_repo_class.return_value = mock_repo
        
        mock_task_result = Mock()
        mock_task_result.id = "test-task-id-123"
        mock_task.delay.return_value = mock_task_result
        
        # Act
        response = client.post("/pdf/tickets/123/generate")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "task_id" in data
        assert data["task_id"] == "test-task-id-123"
        assert data["status"] == "processing"
        assert data["ticket_id"] == 123
    
    @patch('app.rutas.pdf_ruta.TicketRepository')
    def test_generate_pdf_ticket_not_found(self, mock_repo_class):
        """Test that generate endpoint returns 404 for non-existent ticket."""
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = None
        mock_repo_class.return_value = mock_repo
        
        # Act
        response = client.post("/pdf/tickets/999/generate")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('app.rutas.pdf_ruta.AsyncResult')
    def test_task_status_processing(self, mock_async_result):
        """
        Test that task status endpoint returns correct status for processing task.
        
        Validates Requirements 6.4
        """
        # Arrange
        mock_result = Mock()
        mock_result.ready.return_value = False
        mock_async_result.return_value = mock_result
        
        # Act
        response = client.get("/pdf/tasks/test-task-id/status")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "processing"
    
    @patch('app.rutas.pdf_ruta.AsyncResult')
    def test_task_status_completed(self, mock_async_result):
        """
        Test that task status endpoint returns correct status for completed task.
        
        Validates Requirements 6.4
        """
        # Arrange
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = {
            "status": "completed",
            "file_path": "uploads/pdfs/ticket_123.pdf",
            "ticket_id": 123
        }
        mock_async_result.return_value = mock_result
        
        # Act
        response = client.get("/pdf/tasks/test-task-id/status")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "completed"
        assert "result" in data
        assert data["result"]["file_path"] == "uploads/pdfs/ticket_123.pdf"
    
    @patch('app.rutas.pdf_ruta.AsyncResult')
    def test_task_status_failed(self, mock_async_result):
        """Test that task status endpoint returns correct status for failed task."""
        # Arrange
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = {
            "status": "failed",
            "error": "PDF generation error"
        }
        mock_async_result.return_value = mock_result
        
        # Act
        response = client.get("/pdf/tasks/test-task-id/status")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "failed"
        assert "error" in data["result"]
    
    @patch('app.rutas.pdf_ruta.os.path.exists')
    @patch('app.rutas.pdf_ruta.AsyncResult')
    def test_download_pdf_success(self, mock_async_result, mock_exists):
        """
        Test that PDF download endpoint returns file.
        
        Validates Requirements 6.6
        """
        # Arrange
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = {
            "status": "completed",
            "file_path": "uploads/pdfs/ticket_123.pdf"
        }
        mock_async_result.return_value = mock_result
        mock_exists.return_value = True
        
        # Act
        response = client.get("/pdf/tasks/test-task-id/result")
        
        # Assert
        assert response.status_code == 200
        # FileResponse returns the file
        # We can't easily test the actual file content in unit tests
        # but we verify the endpoint doesn't error
    
    @patch('app.rutas.pdf_ruta.AsyncResult')
    def test_download_pdf_still_processing(self, mock_async_result):
        """Test that download endpoint returns 202 if task still processing."""
        # Arrange
        mock_result = Mock()
        mock_result.ready.return_value = False
        mock_async_result.return_value = mock_result
        
        # Act
        response = client.get("/pdf/tasks/test-task-id/result")
        
        # Assert
        assert response.status_code == 202
        data = response.json()
        assert "still processing" in data["detail"].lower()
    
    @patch('app.rutas.pdf_ruta.AsyncResult')
    def test_download_pdf_failed_task(self, mock_async_result):
        """Test that download endpoint returns 500 if task failed."""
        # Arrange
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = {
            "status": "failed",
            "error": "PDF generation error"
        }
        mock_async_result.return_value = mock_result
        
        # Act
        response = client.get("/pdf/tasks/test-task-id/result")
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "failed" in data["detail"].lower()
    
    @patch('app.rutas.pdf_ruta.os.path.exists')
    @patch('app.rutas.pdf_ruta.AsyncResult')
    def test_download_pdf_file_not_found(self, mock_async_result, mock_exists):
        """Test that download endpoint returns 404 if file doesn't exist."""
        # Arrange
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = {
            "status": "completed",
            "file_path": "uploads/pdfs/ticket_123.pdf"
        }
        mock_async_result.return_value = mock_result
        mock_exists.return_value = False  # File doesn't exist
        
        # Act
        response = client.get("/pdf/tasks/test-task-id/result")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestPDFAPIWorkflow:
    """Test complete PDF generation workflow."""
    
    @patch('app.rutas.pdf_ruta.os.path.exists')
    @patch('app.rutas.pdf_ruta.AsyncResult')
    @patch('app.rutas.pdf_ruta.generate_ticket_pdf_task')
    @patch('app.rutas.pdf_ruta.TicketRepository')
    def test_complete_pdf_workflow(
        self, mock_repo_class, mock_task, mock_async_result, mock_exists
    ):
        """
        Test complete workflow: generate -> check status -> download.
        
        Validates Requirements 6.2, 6.3, 6.4, 6.6
        """
        # Arrange
        mock_repo = Mock()
        mock_ticket = Mock()
        mock_ticket.id = 123
        mock_repo.get_by_id.return_value = mock_ticket
        mock_repo_class.return_value = mock_repo
        
        mock_task_result = Mock()
        mock_task_result.id = "workflow-task-id"
        mock_task.delay.return_value = mock_task_result
        
        # Step 1: Generate PDF
        response1 = client.post("/pdf/tickets/123/generate")
        assert response1.status_code == 200
        task_id = response1.json()["task_id"]
        
        # Step 2: Check status (processing)
        mock_result_processing = Mock()
        mock_result_processing.ready.return_value = False
        mock_async_result.return_value = mock_result_processing
        
        response2 = client.get(f"/pdf/tasks/{task_id}/status")
        assert response2.status_code == 200
        assert response2.json()["status"] == "processing"
        
        # Step 3: Check status (completed)
        mock_result_completed = Mock()
        mock_result_completed.ready.return_value = True
        mock_result_completed.get.return_value = {
            "status": "completed",
            "file_path": "uploads/pdfs/ticket_123.pdf"
        }
        mock_async_result.return_value = mock_result_completed
        
        response3 = client.get(f"/pdf/tasks/{task_id}/status")
        assert response3.status_code == 200
        assert response3.json()["status"] == "completed"
        
        # Step 4: Download PDF
        mock_exists.return_value = True
        response4 = client.get(f"/pdf/tasks/{task_id}/result")
        assert response4.status_code == 200
