import json
import time
import uuid
import logging
from app.config import get_settings
from typing import AsyncGenerator, Any
from app.agent.factory import agent_factory
from starlette.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from app.storage.session_store import session_store
from app.parsing.pdf import pdf_parser, PDFParseError
from fastapi import FastAPI, HTTPException, UploadFile, File, Form

from app.models import (
    StreamChunk,
    StreamChunkType,
    ChatRequest,
    PDFUploadResponse,
    ErrorResponse,
    SessionInfo,
)

logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="Document QA Chatbot with streaming responses",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Document QA Chatbot API", "version": "0.1.0"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/chat/stream")
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    """
    Stream chat response token by token.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        session_store.increment_message_count(session_id)
        
        start_time = time.time()

        def status_callback(step: str) -> None:
            logger.info(f"Status update: {step}")

        # Create agent
        agent = agent_factory.create_agent(session_id, status_callback)
        if session_store.has_pdf(session_id):
            context = session_store.get_context_for_agent(session_id)
            enhanced_message = f"Context from uploaded document:\n{context}\n\nUser question: {request.message}"
        else:
            enhanced_message = request.message

        async def stream_generator() -> AsyncGenerator[str, None]:
            """Generate streaming chunks with timing and token tracking."""
            def get_elapsed() -> float:
                """Calculate elapsed time since request start."""
                return time.time() - start_time
            
            try:
                token_count = 0
                
                # Stream status updates with timing
                for step in ["Analyzing", "Searching knowledge", "Generating response"]:
                    chunk = StreamChunk(
                        type=StreamChunkType.STATUS,
                        step=step,
                        elapsed_seconds=get_elapsed()
                    )
                    yield f"{chunk.model_dump_json()}\n"

                # Stream agent response safely
                async for item in agent_factory.stream_response(agent, enhanced_message):
                    try:
                        if hasattr(item, "content"):
                            token_text = str(item.content)
                        elif isinstance(item, str):
                            token_text = item
                        else:
                            token_text = str(item)
                    except Exception:
                        token_text = "[unserializable token]"

                    token_count += 1
                    chunk = StreamChunk(
                        type=StreamChunkType.TOKEN,
                        content=token_text,
                        elapsed_seconds=get_elapsed(),
                        token_count=token_count
                    )
                    yield f"{chunk.model_dump_json()}\n"

                chunk = StreamChunk(
                    type=StreamChunkType.DONE,
                    elapsed_seconds=get_elapsed(),
                    token_count=token_count
                )
                yield f"{chunk.model_dump_json()}\n"

            except Exception as e:
                logger.error(f"Error in stream_generator: {e}")
                chunk = StreamChunk(
                    type=StreamChunkType.ERROR,
                    content=str(e),
                    elapsed_seconds=get_elapsed()
                )
                yield f"{chunk.model_dump_json()}\n"

        return StreamingResponse(
            stream_generator(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Session-ID": session_id,
            },
        )

    except Exception as e:
        logger.error(f"Error in stream_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: str = Form(...),
) -> PDFUploadResponse:
    """
    Upload and parse a PDF file.
    """
    try:
        file_content = await file.read()
        pdf_text, metadata = pdf_parser.parse_pdf(file_content, file.filename)
        session_store.store_pdf_content(session_id, pdf_text, metadata)

        logger.info(f"Successfully uploaded PDF {file.filename} for session {session_id}")

        return PDFUploadResponse(
            success=True,
            message=f"Successfully uploaded and parsed {file.filename}",
            session_id=session_id,
            metadata={
                "filename": metadata.filename,
                "pages": metadata.pages,
                "characters": metadata.characters,
                "size_bytes": metadata.size_bytes,
            },
        )

    except PDFParseError as e:
        logger.warning(f"PDF parse error: {e}")
        return PDFUploadResponse(success=False, message=str(e), session_id=session_id)

    except Exception as e:
        logger.error(f"Unexpected error uploading PDF: {e}")
        return PDFUploadResponse(success=False, message=f"Upload failed: {str(e)}", session_id=session_id)


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> SessionInfo:
    return session_store.get_session_info(session_id)


@app.get("/sessions")
async def list_sessions() -> list[SessionInfo]:
    return session_store.list_sessions()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc) -> JSONResponse:
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal server error", detail=str(exc)).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
