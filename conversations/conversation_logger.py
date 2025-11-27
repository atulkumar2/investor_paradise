"""Conversation logging for tracking user queries and agent responses."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from investor_agent.logger import get_logger

logger = get_logger(__name__)

# Default log file path located alongside this module
_DEFAULT_LOG_PATH = Path(__file__).parent / "conversation_history.jsonl"


class ConversationLogger:
    """Log user queries and agent responses with session tracking."""

    def __init__(self, log_file: str | Path = _DEFAULT_LOG_PATH):
        """Initialize conversation logger.

        Args:
            log_file: Path to JSONL file for conversation history
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info("📝 ConversationLogger initialized: %s", self.log_file)

    def log_query(
        self,
        session_id: str,
        user_id: str,
        query: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """Log user query.

        Args:
            session_id: Unique session identifier
            user_id: User identifier
            query: User's query text
            metadata: Optional metadata (e.g., timestamp, client info)

        Returns:
            Query ID for tracking response
        """
        query_id = f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        entry = {
            "type": "query",
            "query_id": query_id,
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "metadata": metadata or {}
        }

        self._write_entry(entry)
        logger.info(
            "📥 [Session: %s] User query logged: %s",
            session_id, query[:100]
        )
        return query_id

    def log_response(
        self,
        query_id: str,
        session_id: str,
        response: str,
        tools_used: list[str] | None = None,
        metadata: dict[str, Any] | None = None
    ):
        """Log agent response.

        Args:
            query_id: Query ID from log_query
            session_id: Session identifier
            response: Agent's response text
            tools_used: List of tools used during processing
            metadata: Optional metadata (execution time, model, etc.)
        """
        entry = {
            "type": "response",
            "query_id": query_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "response": response,
            "tools_used": tools_used or [],
            "metadata": metadata or {}
        }

        self._write_entry(entry)
        logger.info(
            "📤 [Session: %s] Agent response logged (query_id: %s, tools: %s)",
            session_id, query_id, len(tools_used or [])
        )

    def log_error(
        self,
        session_id: str,
        query_id: str | None,
        error: str,
        metadata: dict[str, Any] | None = None
    ):
        """Log error during query processing.

        Args:
            session_id: Session identifier
            query_id: Query ID if available
            error: Error message
            metadata: Optional error details
        """
        entry = {
            "type": "error",
            "query_id": query_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "metadata": metadata or {}
        }

        self._write_entry(entry)
        logger.error(
            "❌ [Session: %s] Error logged: %s",
            session_id, error[:100]
        )

    def _write_entry(self, entry: dict[str, Any]):
        """Write entry to JSONL file.

        Args:
            entry: Dictionary to write as JSON line
        """
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Failed to write conversation log: %s", e)

    def get_session_history(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve conversation history for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of conversation entries for the session
        """
        if not self.log_file.exists():
            return []

        history = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry.get("session_id") == session_id:
                        history.append(entry)
        except Exception as e:
            logger.error("Failed to read conversation history: %s", e)

        return history


# Global conversation logger instance
conversation_logger = ConversationLogger()
