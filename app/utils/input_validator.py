"""
Input validation and sanitization utilities.

Provides HTML sanitization and file upload validation to prevent XSS attacks
and validate file uploads.
"""

from typing import Any

import bleach
from fastapi import HTTPException, UploadFile

# Configuration constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"]

# Magic bytes for MIME type detection
MIME_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # Followed by WEBP at offset 8
    b"%PDF": "application/pdf",
}


class InputSanitizer:
    """
    Sanitizes HTML input to prevent XSS attacks.

    Uses bleach library to remove all HTML tags from text input,
    preventing injection of malicious scripts or HTML.
    """

    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Remove all HTML tags from text input.

        Args:
            text: Input text that may contain HTML tags

        Returns:
            Plain text with all HTML tags removed

        Examples:
            >>> InputSanitizer.sanitize_html("<script>alert('xss')</script>Hello")
            "Hello"

            >>> InputSanitizer.sanitize_html("<b>Bold</b> and <i>italic</i>")
            "Bold and italic"

            >>> InputSanitizer.sanitize_html("Normal text")
            "Normal text"
        """
        if not text:
            return text

        # Remove all HTML tags - no tags are allowed
        return bleach.clean(text, tags=[], strip=True)

    @staticmethod
    def sanitize_dict(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        """
        Sanitize specific fields in a dictionary.

        Applies HTML sanitization to specified string fields in a dictionary,
        leaving other fields unchanged.

        Args:
            data: Dictionary containing fields to sanitize
            fields: List of field names to sanitize

        Returns:
            Dictionary with sanitized fields

        Examples:
            >>> data = {"name": "<b>John</b>", "age": 30, "bio": "<script>alert()</script>"}
            >>> InputSanitizer.sanitize_dict(data, ["name", "bio"])
            {"name": "John", "age": 30, "bio": ""}
        """
        sanitized = data.copy()
        for field in fields:
            if field in sanitized and isinstance(sanitized[field], str):
                sanitized[field] = InputSanitizer.sanitize_html(sanitized[field])
        return sanitized


class FileValidator:
    """
    Validates file uploads for size and MIME type.

    Ensures uploaded files meet security requirements:
    - File size does not exceed maximum allowed
    - MIME type is detected from file content (not filename)
    - MIME type is in the allowed list
    """

    @staticmethod
    def detect_mime_type(content: bytes) -> str:
        """
        Detect MIME type from file content using magic bytes.

        Args:
            content: File content as bytes

        Returns:
            Detected MIME type or "application/octet-stream" if unknown
        """
        # Check JPEG
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        # Check PNG
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        # Check WebP (RIFF....WEBP)
        if content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WEBP":
            return "image/webp"

        # Check PDF
        if content.startswith(b"%PDF"):
            return "application/pdf"

        return "application/octet-stream"

    @staticmethod
    async def validate_file(file: UploadFile) -> UploadFile:
        """
        Validate file size and MIME type.

        Args:
            file: Uploaded file from FastAPI

        Returns:
            The same file if validation passes

        Raises:
            HTTPException: 413 if file too large, 415 if invalid MIME type

        Examples:
            >>> # In a FastAPI route
            >>> @router.post("/upload")
            >>> async def upload_file(file: UploadFile = File(...)):
            >>>     validated_file = await FileValidator.validate_file(file)
            >>>     # Process validated file...
        """
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset file pointer for later use

        # Check file size
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024:.1f} MB",
            )

        # Detect MIME type from content (not from filename)
        # This prevents bypassing validation by renaming files
        mime = FileValidator.detect_mime_type(content)

        if mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"File type '{mime}' not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}",
            )

        return file
