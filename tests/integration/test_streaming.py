"""Integration tests for streaming functionality."""

import json
import pytest
import pytest_check as check
from app.main import app
from fastapi.testclient import TestClient

class TestStreamingIntegration:
    """Integration tests for streaming endpoints."""
    
    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_stream_chat_basic(self) -> None:
        """Test basic chat streaming functionality."""
        response = self.client.post(
            "/chat/stream",
            json={"message": "Hello, how are you?", "session_id": "test-session-1"},
        )
        
        check.equal(response.status_code, 200)
        check.equal(response.headers["content-type"], "application/x-ndjson")
        
        chunks = []
        for line in response.iter_lines():
            if line.strip():
                chunk = json.loads(line)
                chunks.append(chunk)
        
        check.greater(len(chunks), 1, "Should receive multiple chunks")
        
        # Verify chunk types
        chunk_types = [chunk["type"] for chunk in chunks]
        check.is_in("status", chunk_types, "Should have status chunks")
        check.is_in("token", chunk_types, "Should have token chunks")
        check.is_in("done", chunk_types, "Should have done chunk")
    
    # def test_stream_chat_multiple_token_chunks(self) -> None:
    #     """Test that streaming returns multiple token chunks, not a single blob."""
    #     response = self.client.post(
    #         "/chat/stream",
    #         json={"message": "Tell me a short story about a robot", "session_id": "test-multi-chunks"},
    #     )
        
    #     assert response.status_code == 200
    #     assert response.headers["content-type"] == "application/x-ndjson"
        
    #     chunks = []
    #     for line in response.iter_lines():
    #         if line.strip():
    #             chunks.append(json.loads(line))
        
    #     # Verify we have multiple chunks total
    #     assert len(chunks) > 1, "Should receive multiple chunks"
        
    #     # Verify we have multiple TOKEN chunks (not a single blob)
    #     token_chunks = [c for c in chunks if c.get("type") == "token"]
    #     assert len(token_chunks) > 1, f"Expected multiple token chunks, got {len(token_chunks)}. This verifies streaming, not a single blob."
        
    #     # Verify token chunks contain content
    #     token_contents = [c.get("content", "") for c in token_chunks]
    #     assert all(len(content.strip()) > 0 for content in token_contents), "Token chunks should not be empty"
        
    #     # Verify tokens are separate (not all concatenated in one chunk)
    #     # Each token chunk should be a reasonable size (not the entire response)
    #     total_content_length = sum(len(content) for content in token_contents)
    #     avg_chunk_size = total_content_length / len(token_chunks) if token_chunks else 0
    #     assert avg_chunk_size < total_content_length * 0.8, "Tokens should be split across multiple chunks, not in one large chunk"
    
    def test_stream_chat_without_session_id(self) -> None:
        """Test chat streaming without providing session ID."""
        response = self.client.post(
            "/chat/stream",
            json={"message": "Hello"},
        )
        
        check.equal(response.status_code, 200)
        check.is_in("X-Session-ID", response.headers, "Should include session ID header")
        session_id = response.headers["X-Session-ID"]
        check.greater(len(session_id), 0, "Session ID should not be empty")
    
    def test_stream_chat_empty_message(self) -> None:
        """Test chat streaming with empty message."""
        response = self.client.post(
            "/chat/stream",
            json={"message": "", "session_id": "test-session-2"},
        )
        
        assert response.status_code == 200
        
        chunks = []
        for line in response.iter_lines():
            if line.strip():
                chunk = json.loads(line)
                chunks.append(chunk)
        
        assert len(chunks) > 0
    
    def test_stream_chat_invalid_json(self) -> None:
        """Test chat streaming with invalid JSON."""
        response = self.client.post(
            "/chat/stream",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422
    
    def test_stream_chat_missing_message(self) -> None:
        """Test chat streaming with missing message field."""
        response = self.client.post(
            "/chat/stream",
            json={"session_id": "test-session-3"},
        )
        
        assert response.status_code == 422  
    
    def test_multiple_streaming_sessions(self) -> None:
        """Test multiple concurrent streaming sessions."""
        responses = []
        
        for i in range(3):
            response = self.client.post(
                "/chat/stream",
                json={"message": f"Message {i}", "session_id": f"test-session-{i}"},
            )
            responses.append(response)
        
        # All should succeed
        for response in responses:
            check.equal(response.status_code, 200, "All concurrent requests should succeed")
        
        # Each should have different session IDs
        session_ids = [resp.headers.get("X-Session-ID") for resp in responses]
        check.equal(len(set(session_ids)), 3, "Each request should have unique session ID")   

    def test_stream_response_format(self) -> None:
        """Test that streaming response has correct format."""
        response = self.client.post(
            "/chat/stream",
            json={"message": "Test message", "session_id": "test-session-format"},
        )
        
        assert response.status_code == 200
        
        chunks = []
        for line in response.iter_lines():
            if line.strip():
                chunk = json.loads(line)
                chunks.append(chunk)
        
        # Verify chunk structure
        for chunk in chunks:
            assert "type" in chunk
            assert chunk["type"] in ["status", "token", "done", "error"]
            assert "timestamp" in chunk
            
            if chunk["type"] == "status":
                assert "step" in chunk
            elif chunk["type"] == "token":
                assert "content" in chunk
            elif chunk["type"] == "error":
                assert "content" in chunk
    
    def test_stream_chat_error_handling(self) -> None:
        """Test error handling in streaming."""
        # This test might need to be adjusted based on actual error scenarios
        response = self.client.post(
            "/chat/stream",
            json={"message": "Test message", "session_id": "test-session-error"},
        )
        
        assert response.status_code == 200
        
        chunks = []
        for line in response.iter_lines():
            if line.strip():
                chunk = json.loads(line)
                chunks.append(chunk)
        
        assert len(chunks) > 0
        
        error_chunks = [c for c in chunks if c["type"] == "error"]
        for error_chunk in error_chunks:
            assert "content" in error_chunk
            assert len(error_chunk["content"]) > 0




