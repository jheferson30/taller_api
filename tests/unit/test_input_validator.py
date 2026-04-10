"""
Unit tests for input validation utilities.

Tests specific examples and edge cases for:
- HTML sanitization
- File size validation
- MIME type validation
"""
import pytest
from app.utils.input_validator import InputSanitizer, FileValidator, MAX_FILE_SIZE, ALLOWED_MIME_TYPES
from fastapi import HTTPException, UploadFile
from io import BytesIO


class TestInputSanitizer:
    """Unit tests for InputSanitizer class."""
    
    def test_sanitize_removes_script_tags(self):
        """Test that script tags are removed."""
        # Arrange
        html = "<script>alert('xss')</script>Hello World"
        
        # Act
        result = InputSanitizer.sanitize_html(html)
        
        # Assert
        assert "<script>" not in result
        assert "</script>" not in result
        assert "Hello World" in result
    
    def test_sanitize_removes_all_html_tags(self):
        """Test that all HTML tags are removed."""
        # Arrange
        html = "<div><p>Text with <b>bold</b> and <i>italic</i></p></div>"
        
        # Act
        result = InputSanitizer.sanitize_html(html)
        
        # Assert
        assert "<div>" not in result
        assert "<p>" not in result
        assert "<b>" not in result
        assert "<i>" not in result
        assert "Text with bold and italic" in result
    
    def test_sanitize_handles_empty_string(self):
        """Test that empty string is handled correctly."""
        # Act
        result = InputSanitizer.sanitize_html("")
        
        # Assert
        assert result == ""
    
    def test_sanitize_handles_none(self):
        """Test that None is handled correctly."""
        # Act
        result = InputSanitizer.sanitize_html(None)
        
        # Assert
        assert result is None
    
    def test_sanitize_preserves_plain_text(self):
        """Test that plain text without HTML is preserved."""
        # Arrange
        text = "This is plain text without any HTML"
        
        # Act
        result = InputSanitizer.sanitize_html(text)
        
        # Assert
        assert result == text
    
    def test_sanitize_removes_dangerous_tags(self):
        """Test that dangerous tags are removed."""
        dangerous_tags = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='evil.com'></iframe>",
            "<object data='evil.swf'></object>",
            "<embed src='evil.swf'>",
            "<style>body{display:none}</style>",
            "<link rel='stylesheet' href='evil.css'>"
        ]
        
        for html in dangerous_tags:
            # Act
            result = InputSanitizer.sanitize_html(html)
            
            # Assert - no tags should remain
            assert "<" not in result or ">" not in result
    
    def test_sanitize_dict_sanitizes_specified_fields(self):
        """Test that sanitize_dict sanitizes only specified fields."""
        # Arrange
        data = {
            "name": "<b>John Doe</b>",
            "age": 30,
            "bio": "<p>Developer with <b>skills</b></p>",
            "email": "john@example.com"
        }
        fields = ["name", "bio"]
        
        # Act
        result = InputSanitizer.sanitize_dict(data, fields)
        
        # Assert
        assert result["name"] == "John Doe"
        assert result["bio"] == "Developer with skills"
        assert result["age"] == 30  # Unchanged
        assert result["email"] == "john@example.com"  # Unchanged
    
    def test_sanitize_dict_ignores_non_string_fields(self):
        """Test that sanitize_dict ignores non-string fields."""
        # Arrange
        data = {
            "name": "<b>John</b>",
            "age": 30,
            "active": True,
            "scores": [1, 2, 3]
        }
        fields = ["name", "age", "active", "scores"]
        
        # Act
        result = InputSanitizer.sanitize_dict(data, fields)
        
        # Assert
        assert result["name"] == "John"
        assert result["age"] == 30  # Not sanitized (not string)
        assert result["active"] is True  # Not sanitized (not string)
        assert result["scores"] == [1, 2, 3]  # Not sanitized (not string)
    
    def test_sanitize_dict_handles_missing_fields(self):
        """Test that sanitize_dict handles fields not in data."""
        # Arrange
        data = {"name": "<b>John</b>"}
        fields = ["name", "bio", "email"]  # bio and email don't exist
        
        # Act
        result = InputSanitizer.sanitize_dict(data, fields)
        
        # Assert
        assert result["name"] == "John"
        assert "bio" not in result
        assert "email" not in result


class TestFileValidator:
    """Unit tests for FileValidator class."""
    
    @pytest.mark.asyncio
    async def test_validate_file_rejects_oversized_file(self):
        """Test that files exceeding MAX_FILE_SIZE are rejected with HTTP 413."""
        # Arrange - create file larger than MAX_FILE_SIZE
        oversized_content = b'x' * (MAX_FILE_SIZE + 1)
        file = UploadFile(filename="large.jpg", file=BytesIO(oversized_content))
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await FileValidator.validate_file(file)
        
        assert exc_info.value.status_code == 413
        assert "exceeds maximum allowed size" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_file_rejects_invalid_mime_type(self):
        """Test that files with invalid MIME types are rejected with HTTP 415."""
        # Arrange - create text file (not in ALLOWED_MIME_TYPES)
        text_content = b'This is a plain text file'
        file = UploadFile(filename="test.txt", file=BytesIO(text_content))
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await FileValidator.validate_file(file)
        
        assert exc_info.value.status_code == 415
        assert "not allowed" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_file_accepts_valid_jpeg(self):
        """Test that valid JPEG files are accepted."""
        # Arrange - create valid JPEG file
        # JPEG magic bytes: FF D8 FF
        jpeg_content = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' + b'\x00' * 1000
        file = UploadFile(filename="test.jpg", file=BytesIO(jpeg_content))
        
        # Act
        result = await FileValidator.validate_file(file)
        
        # Assert
        assert result is not None
        assert result.filename == "test.jpg"
    
    @pytest.mark.asyncio
    async def test_validate_file_accepts_valid_png(self):
        """Test that valid PNG files are accepted."""
        # Arrange - create valid PNG file
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89' + b'\x00' * 1000
        file = UploadFile(filename="test.png", file=BytesIO(png_content))
        
        # Act
        result = await FileValidator.validate_file(file)
        
        # Assert
        assert result is not None
        assert result.filename == "test.png"
    
    @pytest.mark.asyncio
    async def test_validate_file_accepts_valid_pdf(self):
        """Test that valid PDF files are accepted."""
        # Arrange - create valid PDF file
        # PDF magic bytes: %PDF
        pdf_content = b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n' + b'\x00' * 1000
        file = UploadFile(filename="test.pdf", file=BytesIO(pdf_content))
        
        # Act
        result = await FileValidator.validate_file(file)
        
        # Assert
        assert result is not None
        assert result.filename == "test.pdf"
    
    @pytest.mark.asyncio
    async def test_validate_file_detects_mime_from_content_not_filename(self):
        """Test that MIME type is detected from content, not filename."""
        # Arrange - create text file but name it as .jpg
        text_content = b'This is actually a text file'
        file = UploadFile(filename="fake.jpg", file=BytesIO(text_content))
        
        # Act & Assert - should reject because content is text, not JPEG
        with pytest.raises(HTTPException) as exc_info:
            await FileValidator.validate_file(file)
        
        assert exc_info.value.status_code == 415
    
    @pytest.mark.asyncio
    async def test_validate_file_resets_file_pointer(self):
        """Test that file pointer is reset after validation."""
        # Arrange
        jpeg_content = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' + b'\x00' * 1000
        file = UploadFile(filename="test.jpg", file=BytesIO(jpeg_content))
        
        # Act
        await FileValidator.validate_file(file)
        
        # Assert - file pointer should be at start
        content = await file.read()
        assert len(content) == len(jpeg_content)
        assert content == jpeg_content
    
    @pytest.mark.asyncio
    async def test_validate_file_exact_max_size_accepted(self):
        """Test that file exactly at MAX_FILE_SIZE is accepted."""
        # Arrange - create file exactly at MAX_FILE_SIZE
        jpeg_header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        content = jpeg_header + b'\x00' * (MAX_FILE_SIZE - len(jpeg_header))
        file = UploadFile(filename="max_size.jpg", file=BytesIO(content))
        
        # Act
        result = await FileValidator.validate_file(file)
        
        # Assert
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_validate_file_one_byte_over_max_rejected(self):
        """Test that file one byte over MAX_FILE_SIZE is rejected."""
        # Arrange
        content = b'x' * (MAX_FILE_SIZE + 1)
        file = UploadFile(filename="too_large.jpg", file=BytesIO(content))
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await FileValidator.validate_file(file)
        
        assert exc_info.value.status_code == 413


class TestInputValidatorConstants:
    """Test that constants are properly defined."""
    
    def test_max_file_size_is_10mb(self):
        """Test that MAX_FILE_SIZE is 10 MB."""
        assert MAX_FILE_SIZE == 10 * 1024 * 1024
    
    def test_allowed_mime_types_includes_required_types(self):
        """Test that ALLOWED_MIME_TYPES includes required types."""
        required_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
        
        for mime_type in required_types:
            assert mime_type in ALLOWED_MIME_TYPES
