import json
import pytest
import pytest_check as check
from pathlib import Path
from httpx import AsyncClient
from app.config import get_settings

settings = get_settings()

SAMPLE_PDF_PATH = Path(__file__).parent.parent / "data" / "sample.pdf"

@pytest.mark.asyncio
async def test_upload_pdf_success():
    """Test uploading a valid PDF file to /upload/pdf endpoint."""
    # Ensure sample PDF exists
    assert SAMPLE_PDF_PATH.exists(), f"Sample PDF not found at {SAMPLE_PDF_PATH}"

    async with AsyncClient(base_url=f"http://{settings.backend_host}:{settings.backend_port}") as client:
        with open(SAMPLE_PDF_PATH, "rb") as f:
            files = {"file": ("sample.pdf", f, "application/pdf")}
            data = {"session_id": "test-session-123"}

            response = await client.post("/upload/pdf", files=files, data=data)

    check.equal(response.status_code, 200)
    json_data = response.json()
    check.is_true(json_data["success"], "Upload should succeed")
    check.equal(json_data["session_id"], "test-session-123")
    check.equal(json_data["metadata"]["filename"], "sample.pdf")
    check.greater(json_data["metadata"]["pages"], 0, "PDF should have pages")
    check.greater(json_data["metadata"]["characters"], 0, "PDF should have characters")
    check.greater(json_data["metadata"]["size_bytes"], 0, "PDF should have size")


@pytest.mark.asyncio
async def test_upload_parse_query_flow():
    """
    Integration test: upload → parse → query → answer referencing PDF.
    Tests the complete flow of uploading a PDF and asking questions about it.
    """
    # Ensure sample PDF exists
    check.is_true(SAMPLE_PDF_PATH.exists(), f"Sample PDF not found at {SAMPLE_PDF_PATH}")
    
    session_id = "test-integration-session"
    
    async with AsyncClient(
        base_url=f"http://{settings.backend_host}:{settings.backend_port}",
        timeout=60.0
    ) as client:
        # Step 1: Upload PDF
        with open(SAMPLE_PDF_PATH, "rb") as f:
            files = {"file": ("sample.pdf", f, "application/pdf")}
            data = {"session_id": session_id}
            upload_response = await client.post("/upload/pdf", files=files, data=data)
        
        check.equal(upload_response.status_code, 200, "Upload should succeed")
        upload_data = upload_response.json()
        check.is_true(upload_data["success"], "Upload response should indicate success")
        
        # Step 2: Query about the PDF content
        query_response = await client.post(
            "/chat/stream",
            json={"message": "What is this document about?", "session_id": session_id},
        )
        
        check.equal(query_response.status_code, 200, "Query should succeed")
        check.equal(query_response.headers["content-type"], "application/x-ndjson", "Should return NDJSON")
        
        # Step 3: Verify streaming response contains tokens
        chunks = []
        async for line in query_response.aiter_lines():
            if line.strip():
                try:
                    chunk = json.loads(line)
                    chunks.append(chunk)
                    if chunk.get("type") == "done":
                        break
                except json.JSONDecodeError:
                    continue
        
        # Verify we got streaming chunks
        check.greater(len(chunks), 1, "Should receive multiple chunks")
        
        # Verify chunk types
        chunk_types = [chunk.get("type") for chunk in chunks]
        check.is_true("status" in chunk_types or "token" in chunk_types, "Should have status or token chunks")
        check.is_in("done", chunk_types, "Should have done chunk")
        
        # Verify we got actual token content
        token_chunks = [c for c in chunks if c.get("type") == "token"]
        check.greater(len(token_chunks), 0, "Should have token chunks")
        
        # Verify the response references the PDF (content should be non-empty)
        all_content = " ".join([c.get("content", "") for c in token_chunks])
        check.greater(len(all_content.strip()), 0, "Response should have content")



