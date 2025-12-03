from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Literal

class StreamChunkType(str, Enum):
    """Types of streaming chunks, there are."""
    STATUS = "status"
    TOKEN = "token"
    DONE = "done"
    ERROR = "error"

class StreamChunk(BaseModel):
    """A single chunk in the streaming response, this is."""
    type: StreamChunkType
    content: str | None = None
    step: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    elapsed_seconds: float | None = None
    token_count: int | None = None

class ChatMessage(BaseModel):
    """A chat message, this is."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    """Request to start a chat session, this is."""
    message: str
    session_id: str | None = None

class ChatResponse(BaseModel):
    """Response from chat endpoint, this is."""
    session_id: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class PDFUploadResponse(BaseModel):
    """Response from PDF upload, this is."""
    success: bool
    message: str
    session_id: str
    metadata: dict[str, Any] | None = None

class PDFMetadata(BaseModel):
    """Metadata extracted from PDF, this is."""
    filename: str
    pages: int
    characters: int
    size_bytes: int
    upload_time: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    """Error response model, this is."""
    error: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

class SessionInfo(BaseModel):
    """Information about a chat session, this is."""
    session_id: str
    created_at: datetime
    message_count: int
    has_pdf: bool
    pdf_filename: str | None = None
