"""
Property-based tests for input validation.

Tests universal properties that should hold for all inputs:
- Property 1: HTML Sanitization Removes All Tags
- Property 2: File Size Validation Rejects Oversized Files
- Property 3: MIME Type Validation Rejects Invalid Types
"""
import pytest
from hypothesis import given, strategies as st, assume
from app.utils.input_validator import InputSanitizer, FileValidator, MAX_FILE_SIZE, ALLOWED_MIME_TYPES
from fastapi import HTTPException, UploadFile
from io import BytesIO
import re


class TestHTMLSanitizationProperties:
    """
    Property 1: HTML Sanitization Removes All Tags
    
    For any input string containing HTML tags, the sanitized output
    should contain no HTML tags.
    """
    
    @given(st.text())
    def test_sanitize_html_removes_all_tags_property(self, text: str):
        """
        Property: For any text input, sanitized output contains no HTML tags.
        
        Validates Requirements 4.1, 4.2
        """
        # Act
        sanitized = InputSanitizer.sanitize_html(text)
        
        # Assert - no HTML tags should remain
        # Check for common HTML tag patterns
        html_tag_pattern = re.compile(r'<[^>]+>')
        assert not html_tag_pattern.search(sanitized), \
            f"HTML tags found in sanitized output: {sanitized}"
    
    @given(
        st.text(min_size=1),
        st.sampled_from(['script', 'img', 'iframe', 'object', 'embed', 'style', 'link'])
    )
    def test_sanitize_html_removes_dangerous_tags(self, content: str, tag: str):
        """
        Property: Dangerous HTML tags are always removed.
        
        Validates Requirements 4.1, 4.2
        """
        # Arrange
        html_input = f"<{tag}>{content}</{tag}>"
        
        # Act
        sanitized = InputSanitizer.sanitize_html(html_input)
        
        # Assert - dangerous tags should be removed
        assert f"<{tag}>" not in sanitized
        assert f"</{tag}>" not in sanitized
    
    @given(st.text())
    def test_sanitize_html_is_idempotent(self, text: str):
        """
        Property: Sanitizing twice produces same result as sanitizing once.
        
        sanitize(sanitize(x)) == sanitize(x)
        """
        # Act
        sanitized_once = InputSanitizer.sanitize_html(text)
        sanitized_twice = InputSanitizer.sanitize_html(sanitized_once)
        
        # Assert
        assert sanitized_once == sanitized_twice
    
    @given(st.text(min_size=1, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        blacklist_characters='<>&"\'`'
    )))
    def test_sanitize_html_preserves_plain_text(self, text: str):
        """
        Property: Plain text without HTML special characters is preserved.

        If input contains only letters, digits, and spaces (no HTML special chars),
        output should equal input.
        """
        # Act
        sanitized = InputSanitizer.sanitize_html(text)

        # Assert - plain text without HTML special chars should be preserved
        assert sanitized == text
    
    @given(
        st.fixed_dictionaries({
            "field_a": st.text(),
            "field_b": st.text(),
            "field_c": st.integers(),
            "field_d": st.booleans(),
        })
    )
    def test_sanitize_dict_only_affects_specified_fields(self, data: dict):
        """
        Property: sanitize_dict only modifies specified fields.

        Fields not in the fields list should remain unchanged.
        """
        # Only sanitize field_a; field_b, field_c, field_d should be untouched
        fields_to_sanitize = ["field_a"]
        original_b = data["field_b"]
        original_c = data["field_c"]
        original_d = data["field_d"]

        # Act
        sanitized = InputSanitizer.sanitize_dict(data, fields_to_sanitize)

        # Assert - unmodified fields should be unchanged
        assert sanitized["field_b"] == original_b
        assert sanitized["field_c"] == original_c
        assert sanitized["field_d"] == original_d


class TestFileSizeValidationProperties:
    """
    Property 2: File Size Validation Rejects Oversized Files
    
    For any file with size > MAX_FILE_SIZE, validation should raise HTTPException 413.
    For any file with size <= MAX_FILE_SIZE, validation should not raise size error.
    """
    
    @given(st.integers(min_value=MAX_FILE_SIZE + 1, max_value=MAX_FILE_SIZE * 2))
    @pytest.mark.asyncio
    async def test_oversized_files_always_rejected(self, file_size: int):
        """
        Property: Files larger than MAX_FILE_SIZE are always rejected with 413.
        
        Validates Requirements 4.4, 4.6
        """
        # Arrange - create oversized file
        content = b'x' * file_size
        file = UploadFile(filename="test.jpg", file=BytesIO(content))
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await FileValidator.validate_file(file)
        
        assert exc_info.value.status_code == 413
        assert "exceeds maximum allowed size" in exc_info.value.detail
    
    @given(st.integers(min_value=1, max_value=MAX_FILE_SIZE))
    @pytest.mark.asyncio
    async def test_valid_size_files_pass_size_check(self, file_size: int):
        """
        Property: Files within size limit don't fail on size validation.
        
        Note: They may still fail MIME type validation, but not size validation.
        
        Validates Requirements 4.4, 4.6
        """
        # Arrange - create valid-sized JPEG file
        # JPEG magic bytes: FF D8 FF
        jpeg_header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        content = jpeg_header + b'\x00' * (file_size - len(jpeg_header))
        file = UploadFile(filename="test.jpg", file=BytesIO(content))
        
        # Act
        try:
            await FileValidator.validate_file(file)
            # If it passes, great
            passed = True
        except HTTPException as e:
            # If it fails, it should not be due to size
            passed = e.status_code != 413
        
        # Assert - should not fail with 413 (size error)
        assert passed, "Valid-sized file should not fail size validation"


class TestMIMETypeValidationProperties:
    """
    Property 3: MIME Type Validation Rejects Invalid Types
    
    For any file with MIME type not in ALLOWED_MIME_TYPES, validation should raise HTTPException 415.
    For any file with MIME type in ALLOWED_MIME_TYPES, validation should not raise MIME error.
    """
    
    @pytest.mark.asyncio
    async def test_allowed_mime_types_pass_validation(self):
        """
        Property: Files with allowed MIME types pass MIME validation.
        
        Validates Requirements 4.5, 4.7
        """
        # Test each allowed MIME type
        test_files = {
            "image/jpeg": b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' + b'\x00' * 100,
            "image/png": b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89' + b'\x00' * 100,
            "application/pdf": b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n' + b'\x00' * 100,
        }
        
        for mime_type, content in test_files.items():
            if mime_type in ALLOWED_MIME_TYPES:
                # Arrange
                file = UploadFile(filename=f"test.{mime_type.split('/')[1]}", file=BytesIO(content))
                
                # Act
                try:
                    await FileValidator.validate_file(file)
                    passed = True
                except HTTPException as e:
                    # Should not fail with 415 (MIME type error)
                    passed = e.status_code != 415
                
                # Assert
                assert passed, f"File with allowed MIME type {mime_type} should not fail MIME validation"
    
    @pytest.mark.asyncio
    async def test_disallowed_mime_types_rejected(self):
        """
        Property: Files with disallowed MIME types are rejected with 415.
        
        Validates Requirements 4.5, 4.7
        """
        # Test some common disallowed MIME types
        test_files = {
            "text/html": b'<!DOCTYPE html><html><body>Test</body></html>',
            "application/javascript": b'console.log("test");',
            "text/plain": b'Plain text file',
            "application/zip": b'PK\x03\x04' + b'\x00' * 100,
        }
        
        for mime_type, content in test_files.items():
            if mime_type not in ALLOWED_MIME_TYPES:
                # Arrange
                file = UploadFile(filename="test.file", file=BytesIO(content))
                
                # Act & Assert
                with pytest.raises(HTTPException) as exc_info:
                    await FileValidator.validate_file(file)
                
                assert exc_info.value.status_code == 415
                assert "not allowed" in exc_info.value.detail.lower()


class TestInputValidationInvariants:
    """Additional invariants that should always hold."""
    
    @given(st.text())
    def test_sanitize_never_returns_none(self, text: str):
        """Property: Sanitization never returns None for non-None input."""
        result = InputSanitizer.sanitize_html(text)
        assert result is not None
    
    def test_sanitize_none_returns_none(self):
        """Property: Sanitization of None returns None."""
        result = InputSanitizer.sanitize_html(None)
        assert result is None
    
    @given(st.text(alphabet=st.characters(blacklist_characters='<>&"\'`')))
    def test_sanitized_output_length_lte_input_length(self, text: str):
        """
        Property: Sanitized output length is less than or equal to input length
        for text without HTML special characters.

        Sanitization only removes content for plain text, never adds.
        """
        sanitized = InputSanitizer.sanitize_html(text)
        assert len(sanitized) <= len(text)
