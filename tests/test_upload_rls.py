"""
Unit tests for Upload route RLS fixes.

Tests authentication and tenant isolation for file upload and serving endpoints.
Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import io
import os
from unittest.mock import MagicMock, Mock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app as main_app
from app.rutas.upload_ruta import router
from app.configuracion.base_datos import obtener_db


def create_test_jwt(taller_id: int | None, user_id: int = 1, roles: list[str] = None) -> str:
    """Helper to create JWT tokens for testing."""
    if roles is None:
        roles = ["ADMIN"]
    
    secret_key = os.getenv("JWT_SECRET_KEY", "test_secret_key_with_at_least_32_characters_for_security")
    
    payload = {
        "sub": f"user{user_id}@example.com",
        "user_id": user_id,
        "taller_id": taller_id,
        "roles": roles,
    }
    
    return jwt.encode(payload, secret_key, algorithm="HS256")


@pytest.fixture
def client():
    """FastAPI test client without authentication."""
    return TestClient(main_app)


@pytest.fixture
def taller_1_token():
    """JWT token for taller_id=1."""
    return create_test_jwt(taller_id=1, user_id=1, roles=["ADMIN"])


@pytest.fixture
def taller_2_token():
    """JWT token for taller_id=2."""
    return create_test_jwt(taller_id=2, user_id=2, roles=["ADMIN"])


@pytest.fixture
def super_admin_token():
    """JWT token for SUPER_ADMIN (taller_id=None)."""
    return create_test_jwt(taller_id=None, user_id=999, roles=["SUPER_ADMIN"])


@pytest.fixture
def test_file():
    """Create a test file for upload."""
    return ("test.jpg", io.BytesIO(b"fake image content"), "image/jpeg")


class TestUploadFotoEndpoint:
    """Tests for POST /upload/foto."""

    def test_upload_foto_without_jwt_returns_401(self, client, test_file):
        """
        Test: POST /upload/foto without JWT → 401 or 403
        Requirement: 4.1
        
        Note: The endpoint returns 403 when there's no JWT because the
        @require_auth decorator checks for authentication and rejects
        unauthenticated requests.
        """
        response = client.post(
            "/upload/foto",
            files={"file": test_file}
        )
        # Accept either 401 (auth required) or 403 (forbidden)
        assert response.status_code in [401, 403]

    @patch("app.rutas.upload_ruta.FileValidator.validate_file")
    @patch("builtins.open", create=True)
    @patch("os.makedirs")
    def test_upload_foto_with_valid_jwt_returns_200(
        self,
        mock_makedirs,
        mock_open,
        mock_validate,
        client,
        taller_1_token,
        test_file
    ):
        """
        Test: POST /upload/foto with valid JWT → 200 with file info
        Requirement: 4.1
        """
        # Mock file validation
        mock_validate.return_value = None
        
        # Mock file write
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        response = client.post(
            "/upload/foto",
            files={"file": test_file},
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "url" in data
        assert "size" in data
        # Verify URL contains taller_id
        assert "/uploads/talleres/1/fotos/" in data["url"]

    def test_upload_foto_as_super_admin_returns_403(
        self,
        client,
        super_admin_token,
        test_file
    ):
        """
        Test: SUPER_ADMIN cannot upload files (no tenant context) → 403
        Requirement: 4.1
        """
        response = client.post(
            "/upload/foto",
            files={"file": test_file},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )

        assert response.status_code == 403
        assert "tenant context" in response.json()["detail"].lower()


class TestUploadCompraEndpoint:
    """Tests for POST /upload/compra."""

    def test_upload_compra_without_jwt_returns_401(self, client, test_file):
        """
        Test: POST /upload/compra without JWT → 401 or 403
        Requirement: 4.2
        """
        response = client.post(
            "/upload/compra",
            files={"file": test_file}
        )
        assert response.status_code in [401, 403]

    @patch("app.rutas.upload_ruta.FileValidator.validate_file")
    @patch("builtins.open", create=True)
    @patch("os.makedirs")
    def test_upload_compra_with_valid_jwt_returns_200(
        self,
        mock_makedirs,
        mock_open,
        mock_validate,
        client,
        taller_1_token,
        test_file
    ):
        """
        Test: POST /upload/compra with valid JWT → 200 with file info
        Requirement: 4.2
        """
        # Mock file validation
        mock_validate.return_value = None
        
        # Mock file write
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        response = client.post(
            "/upload/compra",
            files={"file": test_file},
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "url" in data
        assert "size" in data
        # Verify URL contains taller_id
        assert "/uploads/talleres/1/compras/" in data["url"]

    def test_upload_compra_as_super_admin_returns_403(
        self,
        client,
        super_admin_token,
        test_file
    ):
        """
        Test: SUPER_ADMIN cannot upload files (no tenant context) → 403
        Requirement: 4.2
        """
        response = client.post(
            "/upload/compra",
            files={"file": test_file},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )

        assert response.status_code == 403
        assert "tenant context" in response.json()["detail"].lower()


class TestUploadFirmaEndpoint:
    """Tests for POST /upload/firma."""

    def test_upload_firma_without_jwt_returns_401(self, client, test_file):
        """
        Test: POST /upload/firma without JWT → 401 or 403
        Requirement: 4.3
        """
        response = client.post(
            "/upload/firma",
            files={"file": test_file}
        )
        assert response.status_code in [401, 403]

    @patch("app.rutas.upload_ruta.FileValidator.validate_file")
    @patch("builtins.open", create=True)
    @patch("os.makedirs")
    def test_upload_firma_with_valid_jwt_returns_200(
        self,
        mock_makedirs,
        mock_open,
        mock_validate,
        client,
        taller_1_token,
        test_file
    ):
        """
        Test: POST /upload/firma with valid JWT → 200 with file info
        Requirement: 4.3
        """
        # Mock file validation
        mock_validate.return_value = None
        
        # Mock file write
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        response = client.post(
            "/upload/firma",
            files={"file": test_file},
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "url" in data
        assert "size" in data
        # Verify URL contains taller_id
        assert "/uploads/talleres/1/firmas/" in data["url"]

    def test_upload_firma_as_super_admin_returns_403(
        self,
        client,
        super_admin_token,
        test_file
    ):
        """
        Test: SUPER_ADMIN cannot upload files (no tenant context) → 403
        Requirement: 4.3
        """
        response = client.post(
            "/upload/firma",
            files={"file": test_file},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )

        assert response.status_code == 403
        assert "tenant context" in response.json()["detail"].lower()


class TestGetFotoEndpoint:
    """Tests for GET /upload/fotos/{filename}."""

    def test_get_foto_without_jwt_returns_401(self, client):
        """
        Test: GET /upload/fotos/{filename} without JWT → 401
        Requirement: 4.6
        """
        response = client.get("/upload/fotos/test.jpg")
        assert response.status_code == 401

    @patch("os.path.exists")
    @patch("app.rutas.upload_ruta.FileResponse")
    def test_get_foto_from_own_taller_returns_200(
        self,
        mock_file_response,
        mock_exists,
        client,
        taller_1_token
    ):
        """
        Test: GET file from own taller → 200 with file content
        Requirement: 4.4, 4.6
        """
        # Mock file exists
        mock_exists.return_value = True
        mock_file_response.return_value = MagicMock()

        response = client.get(
            "/upload/fotos/test.jpg",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 200
        # Verify the file path includes taller_id=1
        mock_exists.assert_called_once()
        call_args = mock_exists.call_args[0][0]
        assert "talleres/1/fotos" in call_args

    def test_get_foto_nonexistent_returns_404(
        self,
        client,
        taller_1_token
    ):
        """
        Test: GET nonexistent file → 404
        Requirement: 4.5
        """
        response = client.get(
            "/upload/fotos/nonexistent.jpg",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_foto_as_super_admin_returns_403(
        self,
        client,
        super_admin_token
    ):
        """
        Test: SUPER_ADMIN cannot access files (no tenant context) → 403
        Requirement: 4.6
        """
        response = client.get(
            "/upload/fotos/test.jpg",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )

        assert response.status_code == 403
        assert "tenant context" in response.json()["detail"].lower()


class TestGetCompraEndpoint:
    """Tests for GET /upload/compras/{filename}."""

    def test_get_compra_without_jwt_returns_401(self, client):
        """
        Test: GET /upload/compras/{filename} without JWT → 401
        Requirement: 4.6
        """
        response = client.get("/upload/compras/test.pdf")
        assert response.status_code == 401

    @patch("os.path.exists")
    @patch("app.rutas.upload_ruta.FileResponse")
    def test_get_compra_from_own_taller_returns_200(
        self,
        mock_file_response,
        mock_exists,
        client,
        taller_1_token
    ):
        """
        Test: GET file from own taller → 200 with file content
        Requirement: 4.4, 4.6
        """
        # Mock file exists
        mock_exists.return_value = True
        mock_file_response.return_value = MagicMock()

        response = client.get(
            "/upload/compras/test.pdf",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 200
        # Verify the file path includes taller_id=1
        mock_exists.assert_called_once()
        call_args = mock_exists.call_args[0][0]
        assert "talleres/1/compras" in call_args

    def test_get_compra_nonexistent_returns_404(
        self,
        client,
        taller_1_token
    ):
        """
        Test: GET nonexistent file → 404
        Requirement: 4.5
        """
        response = client.get(
            "/upload/compras/nonexistent.pdf",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetFirmaEndpoint:
    """Tests for GET /upload/firmas/{filename}."""

    def test_get_firma_without_jwt_returns_401(self, client):
        """
        Test: GET /upload/firmas/{filename} without JWT → 401
        Requirement: 4.6
        """
        response = client.get("/upload/firmas/test.png")
        assert response.status_code == 401

    @patch("os.path.exists")
    @patch("app.rutas.upload_ruta.FileResponse")
    def test_get_firma_from_own_taller_returns_200(
        self,
        mock_file_response,
        mock_exists,
        client,
        taller_1_token
    ):
        """
        Test: GET file from own taller → 200 with file content
        Requirement: 4.4, 4.6
        """
        # Mock file exists
        mock_exists.return_value = True
        mock_file_response.return_value = MagicMock()

        response = client.get(
            "/upload/firmas/test.png",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 200
        # Verify the file path includes taller_id=1
        mock_exists.assert_called_once()
        call_args = mock_exists.call_args[0][0]
        assert "talleres/1/firmas" in call_args

    def test_get_firma_nonexistent_returns_404(
        self,
        client,
        taller_1_token
    ):
        """
        Test: GET nonexistent file → 404
        Requirement: 4.5
        """
        response = client.get(
            "/upload/firmas/nonexistent.png",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCrossTenantFileAccess:
    """Tests for cross-tenant file access isolation."""

    @patch("os.path.exists")
    def test_taller_1_cannot_access_taller_2_files(
        self,
        mock_exists,
        client,
        taller_1_token
    ):
        """
        Test: User from taller_id=1 cannot access files from taller_id=2
        Requirement: 4.4, 4.5
        
        Note: Since files are stored in tenant-specific directories
        (uploads/talleres/{taller_id}/fotos/), a user from taller_id=1
        will look in their own directory and won't find files from taller_id=2.
        This returns 404 as expected.
        """
        # Mock file doesn't exist in taller_id=1's directory
        mock_exists.return_value = False

        response = client.get(
            "/upload/fotos/taller2_file.jpg",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
        # Verify the path checked was for taller_id=1
        mock_exists.assert_called_once()
        call_args = mock_exists.call_args[0][0]
        assert "talleres/1/fotos" in call_args


class TestFilePathParsing:
    """Tests for file path parsing and taller_id extraction."""

    @patch("os.path.exists")
    @patch("app.rutas.upload_ruta.FileResponse")
    def test_file_path_includes_correct_taller_id(
        self,
        mock_file_response,
        mock_exists,
        client,
        taller_1_token
    ):
        """
        Test: File path parsing extracts taller_id correctly
        Requirement: 4.4
        """
        # Mock file exists
        mock_exists.return_value = True
        mock_file_response.return_value = MagicMock()

        response = client.get(
            "/upload/fotos/test.jpg",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        assert response.status_code == 200
        
        # Verify the file path was constructed with taller_id from JWT
        mock_exists.assert_called_once()
        call_args = mock_exists.call_args[0][0]
        # Path should be: uploads/talleres/1/fotos/test.jpg
        assert "uploads" in call_args
        assert "talleres" in call_args
        assert "1" in call_args
        assert "fotos" in call_args
        assert "test.jpg" in call_args

    def test_path_traversal_protection(
        self,
        client,
        taller_1_token
    ):
        """
        Test: Path traversal attempts are blocked
        Requirement: 4.4, 4.5
        """
        # Attempt path traversal
        response = client.get(
            "/upload/fotos/../../../etc/passwd",
            headers={"Authorization": f"Bearer {taller_1_token}"}
        )

        # Should return 404 (file not found) or 400 (invalid filename)
        # The _safe_filepath function prevents path traversal
        assert response.status_code in [400, 404]
