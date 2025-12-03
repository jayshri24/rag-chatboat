import logging
from datetime import datetime
from typing import Any

from app.models import PDFMetadata, SessionInfo

logger = logging.getLogger(__name__)


class SessionStore:
    """
    In-memory session store for managing chat sessions and PDF knowledge.
    
    This is a thin layer that complements Agno's built-in session features.
    
    **Rationale for this abstraction:**
    - Agno's Agent maintains conversation history via session_id, but doesn't provide
      built-in storage for large document content (PDFs can be several MB)
    - This store handles PDF content separately from conversation history, allowing:
      - Easy querying of which sessions have PDFs (has_pdf())
      - Metadata storage (filename, pages, size) without bloating conversation history
      - Efficient context retrieval for agent (get_context_for_agent())
    - In production, this would be replaced with a vector store or database, but
      for this challenge, in-memory storage is sufficient and keeps dependencies minimal.
    
    **Why not use Agno's knowledge features:**
    - Agno's knowledge features are designed for structured knowledge bases, not
      raw document content that needs to be injected into prompts
    - We need fine-grained control over how PDF content is formatted for the agent
    - This approach allows us to easily add metadata and query capabilities
    """
    
    def __init__(self) -> None:
        """Initialize the session store."""
        self._sessions: dict[str, dict[str, Any]] = {}
        self._pdf_content: dict[str, str] = {}  
        self._pdf_metadata: dict[str, PDFMetadata] = {} 
    
    def create_session(self, session_id: str) -> SessionInfo:
        """
        Create a new chat session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session information
        """
        if session_id in self._sessions:
            logger.warning(f"Session {session_id} already exists")
            return self.get_session_info(session_id)
        
        self._sessions[session_id] = {
            "created_at": datetime.now(),
            "message_count": 0,
            "last_activity": datetime.now(),
        }
        
        logger.info(f"Created new session: {session_id}")
        return self.get_session_info(session_id)
    
    def get_session_info(self, session_id: str) -> SessionInfo:
        """
        Get information about a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session information
        """
        if session_id not in self._sessions:
            return self.create_session(session_id)
        
        session_data = self._sessions[session_id]
        pdf_metadata = self._pdf_metadata.get(session_id)
        
        return SessionInfo(
            session_id=session_id,
            created_at=session_data["created_at"],
            message_count=session_data["message_count"],
            has_pdf=session_id in self._pdf_content,
            pdf_filename=pdf_metadata.filename if pdf_metadata else None,
        )
    
    def increment_message_count(self, session_id: str) -> None:
        """
        Increment the message count for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._sessions:
            self._sessions[session_id]["message_count"] += 1
            self._sessions[session_id]["last_activity"] = datetime.now()
    
    def store_pdf_content(
        self,
        session_id: str,
        pdf_text: str,
        metadata: PDFMetadata,
    ) -> None:
        """
        Store PDF content and metadata for a session.
        
        Args:
            session_id: Session identifier
            pdf_text: Extracted PDF text
            metadata: PDF metadata
        """
        self._pdf_content[session_id] = pdf_text
        self._pdf_metadata[session_id] = metadata
        
        logger.info(
            f"Stored PDF content for session {session_id}: "
            f"{metadata.filename} ({metadata.pages} pages)"
        )
    
    def get_pdf_content(self, session_id: str) -> str | None:
        """
        Get PDF content for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            PDF text content or None if not found
        """
        return self._pdf_content.get(session_id)
    
    def get_pdf_metadata(self, session_id: str) -> PDFMetadata | None:
        """
        Get PDF metadata for a session, we must.
        
        Args:
            session_id: Session identifier
            
        Returns:
            PDF metadata or None if not found
        """
        return self._pdf_metadata.get(session_id)
    
    def has_pdf(self, session_id: str) -> bool:
        """
        Check if a session has PDF content.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session has PDF content
        """
        return session_id in self._pdf_content
    
    def get_context_for_agent(self, session_id: str) -> str:
        """
        Get context information for the agent.
        
        PDF content if available, formatted for the agent, this includes.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add PDF content if available
        pdf_content = self.get_pdf_content(session_id)
        pdf_metadata = self.get_pdf_metadata(session_id)
        
        if pdf_content and pdf_metadata:
            context_parts.append(
                f"Document: {pdf_metadata.filename}\n"
                f"Pages: {pdf_metadata.pages}\n"
                f"Content:\n{pdf_content}"
            )
        
        return "\n\n".join(context_parts)
    
    def list_sessions(self) -> list[SessionInfo]:
        """
        List all sessions.
        
        Returns:
            List of session information
        """
        return [self.get_session_info(session_id) for session_id in self._sessions.keys()]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up old sessions.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        sessions_to_remove = []
        
        for session_id, session_data in self._sessions.items():
            if session_data["last_activity"].timestamp() < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self._sessions.pop(session_id, None)
            self._pdf_content.pop(session_id, None)
            self._pdf_metadata.pop(session_id, None)
        
        logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
        return len(sessions_to_remove)


session_store = SessionStore()
