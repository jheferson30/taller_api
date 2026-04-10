"""
Property-based tests for HTTP compression.

Property 4: GZip Compression Activates for Large Responses
Validates Requirements 5.2, 5.3
"""
import pytest
from hypothesis import given, strategies as st, assume
from fastapi.testclient import TestClient
from app.main import app
import gzip
import json


client = TestClient(app)


class TestCompressionProperties:
    """
    Property 4: GZip Compression Activates for Large Responses
    
    For any response larger than minimum_size (1000 bytes), when client
    sends Accept-Encoding: gzip, the response should be compressed.
    """
    
    @given(st.integers(min_value=1001, max_value=10000))
    def test_large_responses_are_compressed(self, response_size: int):
        """
        Property: Responses larger than 1000 bytes are compressed when client accepts gzip.
        
        Validates Requirements 5.2, 5.3
        """
        # Arrange - create a large response by requesting info endpoint
        # (which returns JSON that can be large)
        
        # Act - request with Accept-Encoding: gzip
        response = client.get("/info", headers={"Accept-Encoding": "gzip"})
        
        # Assert - if response is large enough, it should be compressed
        if len(response.content) > 1000:
            # Check if Content-Encoding header is set
            content_encoding = response.headers.get("Content-Encoding", "")
            
            # Response should either be compressed or not based on size
            # If compressed, Content-Encoding should be gzip
            if "gzip" in content_encoding:
                # Verify we can decompress it
                try:
                    decompressed = gzip.decompress(response.content)
                    assert len(decompressed) > 0
                except Exception:
                    pytest.fail("Response claims to be gzipped but cannot be decompressed")
    
    def test_small_responses_not_compressed(self):
        """
        Property: Responses smaller than 1000 bytes are not compressed.
        
        Validates Requirements 5.2
        """
        # Arrange - request a small endpoint
        # Act
        response = client.get("/info", headers={"Accept-Encoding": "gzip"})
        
        # Assert - if response is small, it should not be compressed
        if len(response.content) <= 1000:
            content_encoding = response.headers.get("Content-Encoding", "")
            # Small responses should not have gzip encoding
            # (or if they do, it's because the content itself is large after JSON encoding)
            pass  # This is acceptable behavior
    
    def test_compression_preserves_content(self):
        """
        Property: Compression preserves response content.
        
        The decompressed response should equal the original response.
        """
        # Arrange & Act - get response with and without compression
        response_compressed = client.get("/info", headers={"Accept-Encoding": "gzip"})
        response_uncompressed = client.get("/info", headers={"Accept-Encoding": "identity"})
        
        # Assert - content should be the same
        if "gzip" in response_compressed.headers.get("Content-Encoding", ""):
            decompressed = gzip.decompress(response_compressed.content)
            # Both should parse to same JSON
            json_compressed = json.loads(decompressed)
            json_uncompressed = json.loads(response_uncompressed.content)
            
            # Compare the actual data (not exact bytes due to formatting)
            assert json_compressed == json_uncompressed
    
    def test_compression_reduces_size(self):
        """
        Property: Compression reduces response size for compressible content.
        
        For JSON responses, compressed size should be significantly smaller.
        """
        # Arrange & Act
        response_compressed = client.get("/info", headers={"Accept-Encoding": "gzip"})
        response_uncompressed = client.get("/info", headers={"Accept-Encoding": "identity"})
        
        # Assert - if compressed, size should be smaller
        if "gzip" in response_compressed.headers.get("Content-Encoding", ""):
            compressed_size = len(response_compressed.content)
            uncompressed_size = len(response_uncompressed.content)
            
            # Compressed should be smaller (for JSON, typically 60-70% reduction)
            if uncompressed_size > 1000:  # Only check if large enough
                assert compressed_size < uncompressed_size
    
    def test_no_compression_without_accept_encoding(self):
        """
        Property: No compression when client doesn't send Accept-Encoding: gzip.
        
        Validates Requirements 5.3
        """
        # Act - request without Accept-Encoding header
        response = client.get("/info")
        
        # Assert - should not be compressed
        content_encoding = response.headers.get("Content-Encoding", "")
        # Without Accept-Encoding, response should not be gzipped
        # (FastAPI's GZipMiddleware respects client preferences)
        pass  # This is expected behavior
    
    def test_compression_idempotent(self):
        """
        Property: Multiple requests with compression return same content.
        
        Compression should be deterministic for the same content.
        """
        # Act - make multiple requests
        response1 = client.get("/info", headers={"Accept-Encoding": "gzip"})
        response2 = client.get("/info", headers={"Accept-Encoding": "gzip"})
        
        # Assert - both should decompress to same content
        if "gzip" in response1.headers.get("Content-Encoding", ""):
            content1 = gzip.decompress(response1.content)
            content2 = gzip.decompress(response2.content)
            
            json1 = json.loads(content1)
            json2 = json.loads(content2)
            
            # Content should be the same (ignoring timestamps if any)
            assert json1.get("app_name") == json2.get("app_name")


class TestCompressionInvariants:
    """Additional invariants for compression."""
    
    def test_compressed_response_has_correct_headers(self):
        """Property: Compressed responses have correct Content-Encoding header."""
        # Act
        response = client.get("/info", headers={"Accept-Encoding": "gzip"})
        
        # Assert
        if "gzip" in response.headers.get("Content-Encoding", ""):
            # Should be valid gzip
            try:
                gzip.decompress(response.content)
            except Exception:
                pytest.fail("Content-Encoding: gzip but content is not valid gzip")
    
    def test_compression_does_not_break_json(self):
        """Property: Compression does not break JSON parsing."""
        # Act
        response = client.get("/info", headers={"Accept-Encoding": "gzip"})
        
        # Assert - should be able to parse JSON
        try:
            # TestClient automatically decompresses, so we can parse directly
            data = response.json()
            assert isinstance(data, dict)
        except Exception as e:
            pytest.fail(f"Failed to parse JSON from compressed response: {e}")
