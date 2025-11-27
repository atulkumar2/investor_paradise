#!/usr/bin/env python3
"""Export ADK web sessions to conversation_history.jsonl.

ADK web stores sessions in a SQLite database (~/.google_adk/sessions/).
This script reads that database and exports conversations to our JSONL format.

Usage:
    python conversations/export_adk_sessions.py
    python conversations/export_adk_sessions.py --session-id <session_id>
    python conversations/export_adk_sessions.py --since 2024-01-01
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import sys

# Ensure both repo root and conversations dir are on sys.path
_THIS_DIR = Path(__file__).parent
_REPO_ROOT = _THIS_DIR.parent
for p in (str(_REPO_ROOT), str(_THIS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Robust import: works from repo root and from conversations/
try:
    from conversations.conversation_logger import conversation_logger
except ModuleNotFoundError:
    from conversation_logger import conversation_logger

from investor_agent.logger import get_logger

logger = get_logger(__name__)


def find_adk_db() -> Path | None:
    """Find ADK web session database.

    Returns:
        Path to sessions.db or None if not found
    """
    # Check common locations in order of priority
    search_paths = [
        # Conversations-local DB (preferred for CLI)
        Path.cwd() / "conversations" / "my_agent_data.db",
        # Current directory (ADK web default)
        Path.cwd() / "my_agent_data.db",
        # Home directory .google_adk
        Path.home() / ".google_adk" / "sessions",
        # Current directory any .db with tables
        Path.cwd(),
    ]

    for search_path in search_paths:
        if search_path.is_file() and search_path.suffix == ".db":
            # Check if it has sessions table
            try:
                conn = sqlite3.connect(search_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='sessions'"
                )
                if cursor.fetchone():
                    conn.close()
                    return search_path
                conn.close()
            except sqlite3.Error:
                continue
        elif search_path.is_dir():
            # Look for .db files in directory
            for db_file in search_path.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='sessions'"
                    )
                    if cursor.fetchone():
                        conn.close()
                        return db_file
                    conn.close()
                except sqlite3.Error:
                    continue

    return None


def export_sessions(
    db_path: Path,
    session_id: str | None = None,
    since: datetime | None = None
) -> int:
    """Export ADK web sessions to conversation_history.jsonl.

    Args:
        db_path: Path to ADK sessions database
        session_id: Optional specific session to export
        since: Optional datetime filter (export sessions after this time)

    Returns:
        Number of conversations exported
    """
    logger.info("📂 Opening ADK session database: %s", db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query sessions (ADK schema: id, user_id, create_time, etc.)
    query = "SELECT * FROM sessions"
    params = []

    if session_id:
        query += " WHERE id = ?"
        params.append(session_id)
    elif since:
        query += " WHERE create_time >= ?"
        params.append(since.isoformat())

    query += " ORDER BY create_time"

    cursor.execute(query, params)
    sessions = cursor.fetchall()

    logger.info("📊 Found %d sessions to export", len(sessions))

    exported_count = 0

    for session in sessions:
        session_dict = dict(session)
        adk_session_id = session_dict.get("id", "unknown")
        user_id = session_dict.get("user_id", "anonymous")

        # Query events for this session (ADK uses 'events' table, not 'turns')
        cursor.execute(
            "SELECT * FROM events WHERE session_id = ? ORDER BY timestamp",
            (adk_session_id,)
        )
        events = cursor.fetchall()

        logger.info(
            "📝 Session %s: %d events", adk_session_id[:12], len(events)
        )

        # Process events (user inputs and model responses)
        for i, event in enumerate(events):
            event_dict = dict(event)

            # Extract content
            content_text = event_dict.get("content", "")
            author = event_dict.get("author", "")
            timestamp_str = event_dict.get("timestamp", "")

            if not content_text or not author:
                continue

            # Map ADK web session to our format
            our_session_id = f"web_{adk_session_id[:16]}"

            # Parse content (might be JSON or plain text)
            try:
                content = json.loads(content_text)
                # Extract text from parts if it's structured content
                if isinstance(content, dict) and "parts" in content:
                    parts = content.get("parts", [])
                    text = " ".join(
                        part.get("text", "") for part in parts
                        if isinstance(part, dict) and "text" in part
                    )
                else:
                    text = str(content)
            except (json.JSONDecodeError, TypeError):
                # Plain text content
                text = content_text

            if not text or not text.strip():
                continue

            # Determine if this is user query or model response
            # ADK uses author field: "user" or model name
            if author.lower() == "user":
                # Log user query
                query_id = conversation_logger.log_query(
                    session_id=our_session_id,
                    user_id=user_id,
                    query=text,
                    metadata={
                        "source": "adk_web_export",
                        "adk_session_id": adk_session_id,
                        "adk_event_id": event_dict.get("id", i),
                        "timestamp": timestamp_str,
                    }
                )
                logger.debug("  ✅ Query logged: %s", query_id)
                exported_count += 1

            else:
                # Log agent response (link to previous query)
                # Use sequential query_id based on event order
                synthetic_query_id = (
                    f"{our_session_id}_{i - 1:04d}"
                )

                conversation_logger.log_response(
                    query_id=synthetic_query_id,
                    session_id=our_session_id,
                    response=text,
                    metadata={
                        "source": "adk_web_export",
                        "adk_session_id": adk_session_id,
                        "adk_event_id": event_dict.get("id", i),
                        "author": author,
                        "timestamp": timestamp_str,
                    }
                )
                logger.debug("  ✅ Response logged")
                exported_count += 1

    conn.close()

    if exported_count == 0 and len(sessions) > 0:
        print(f"⚠️  Found {len(sessions)} sessions but no conversation events")
        print()
        print("The ADK database exists but has no conversation history.")
        print("This usually means:")
        print("  1. ADK web sessions were created but no messages were sent")
        print("  2. Event logging is not enabled for ADK web")
        print()
        print("For now, use CLI mode for conversation logging:")
        print("  python cli.py")
        print()
        logger.warning(
            "Found %d sessions but 0 events to export", len(sessions)
        )

    logger.info(
        "✅ Export complete: %d conversations exported", exported_count
    )
    return exported_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export ADK web sessions to conversation_history.jsonl"
    )
    parser.add_argument(
        "--session-id",
        help="Export specific session ID only"
    )
    parser.add_argument(
        "--since",
        help="Export sessions since date (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--db",
        help="Path to ADK sessions database (auto-detected if not provided)"
    )

    args = parser.parse_args()

    # Find database
    if args.db:
        db_path = Path(args.db)
    else:
        db_path = find_adk_db()

    if not db_path or not db_path.exists():
        print("❌ ADK session database not found")
        print()
        print("Searched locations:")
        print("  - ./conversations/my_agent_data.db (preferred)")
        print("  - ./my_agent_data.db (current directory)")
        print("  - ~/.google_adk/sessions/*.db")
        print()
        print("Have you run 'adk web' at least once?")
        print()
        logger.error("❌ ADK session database not found")
        return 1

    # Parse date filter
    since = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since)
        except ValueError:
            logger.error("❌ Invalid date format: %s", args.since)
            logger.info("Use YYYY-MM-DD format (e.g., 2024-01-01)")
            return 1

    # Export
    try:
        count = export_sessions(
            db_path=db_path,
            session_id=args.session_id,
            since=since
        )

        if count == 0:
            print("⚠️  No conversations found to export")
            logger.warning("⚠️ No conversations found to export")
        else:
            print(f"✅ Exported {count} conversations to conversation_history.jsonl")
            print("📄 View exported conversations:")
            print("  python conversations/view_conversations.py")
            logger.info("📄 View exported conversations:")
            logger.info("  python conversations/view_conversations.py")

        return 0

    except (sqlite3.Error, OSError, RuntimeError) as e:
        print(f"❌ Export failed: {e}")
        logger.error("❌ Export failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
