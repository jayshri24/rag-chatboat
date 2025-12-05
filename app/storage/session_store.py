import logging
from datetime import datetime
from typing import Any

from app.models import PDFMetadata, SessionInfo

logger = logging.getLogger(__name__)


class SessionStore:
    """
    In-memory session store for managing chat sessions and PDF knowledge.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._pdf_content: dict[str, str] = {}
        self._pdf_metadata: dict[str, PDFMetadata] = {}

    # -----------------------------
    # SESSION CREATION & RETRIEVAL
    # -----------------------------

    def create_session(self, session_id: str) -> SessionInfo:
        """
        Create a new session with message_count = 0.
        """
        self._sessions[session_id] = {
            "created_at": datetime.now(),
            "message_count": 0,
            "last_activity": datetime.now(),
        }
        logger.info(f"Created new session: {session_id}")
        return self.get_session_info(session_id)

    def get_session_info(self, session_id: str) -> SessionInfo:
        """
        Get session info, auto-create if missing (message_count stays 0).
        """
        if session_id not in self._sessions:
            self.create_session(session_id)

        session = self._sessions[session_id]
        pdf_metadata = self._pdf_metadata.get(session_id)

        return SessionInfo(
            session_id=session_id,
            created_at=session["created_at"],
            message_count=session["message_count"],
            has_pdf=session_id in self._pdf_content,
            pdf_filename=pdf_metadata.filename if pdf_metadata else None,
        )

    # -----------------------------
    # MESSAGE COUNT
    # -----------------------------

    def increment_message_count(self, session_id: str) -> None:
        """
        Only increments when called by /chat/stream.
        Auto-creates session if missing.
        """
        if session_id not in self._sessions:
            self.create_session(session_id)

        self._sessions[session_id]["message_count"] += 1
        self._sessions[session_id]["last_activity"] = datetime.now()

    # -----------------------------
    # PDF STORAGE
    # -----------------------------

    def store_pdf_content(self, session_id: str, pdf_text: str, metadata: PDFMetadata) -> None:
        """
        Store PDF text + metadata. Does NOT increment message count.
        """
        # Ensure session exists (message_count remains 0)
        if session_id not in self._sessions:
            self.create_session(session_id)

        self._pdf_content[session_id] = pdf_text
        self._pdf_metadata[session_id] = metadata

        logger.info(
            f"Stored PDF for session {session_id}: "
            f"{metadata.filename} ({metadata.pages} pages)"
        )

    def get_pdf_content(self, session_id: str) -> str | None:
        return self._pdf_content.get(session_id)

    def get_pdf_metadata(self, session_id: str) -> PDFMetadata | None:
        return self._pdf_metadata.get(session_id)

    def has_pdf(self, session_id: str) -> bool:
        return session_id in self._pdf_content

    # -----------------------------
    # AGENT CONTEXT
    # -----------------------------

    def get_context_for_agent(self, session_id: str) -> str:
        """
        PDF text formatted for AI agent context.
        """
        pdf_content = self.get_pdf_content(session_id)
        metadata = self.get_pdf_metadata(session_id)

        if not pdf_content or not metadata:
            return ""

        return (
            f"Document: {metadata.filename}\n"
            f"Pages: {metadata.pages}\n"
            f"Content:\n{pdf_content}"
        )

    # -----------------------------
    # LIST + CLEANUP
    # -----------------------------

    def list_sessions(self) -> list[SessionInfo]:
        return [
            self.get_session_info(session_id)
            for session_id in self._sessions.keys()
        ]

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        to_delete = [
            sid for sid, s in self._sessions.items()
            if s["last_activity"].timestamp() < cutoff
        ]

        for sid in to_delete:
            self._sessions.pop(sid, None)
            self._pdf_content.pop(sid, None)
            self._pdf_metadata.pop(sid, None)

        logger.info(f"Cleaned {len(to_delete)} old sessions")
        return len(to_delete)


session_store = SessionStore()
