""" CLI Entry Point for Investor Paradise Agent """

import asyncio
import os
import sqlite3
import traceback
import uuid
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from conversations.conversation_logger import conversation_logger
from investor_agent.data_engine import NSESTORE
from investor_agent.logger import get_logger
from investor_agent.sub_agents import create_pipeline

logger = get_logger(__name__)

# --- SSL Patch (Required for your environment) ---
original_init = httpx.AsyncClient.__init__
def patched_init(self, *args, **kwargs):
    """ Patch httpx AsyncClient to disable SSL verification. """
    kwargs.setdefault('verify', False)
    return original_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = patched_init
# -------------------------------------------------

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def cleanup_old_sessions(db_path: str, days: int = 7):
    """Delete session records older than specified days from SQLite database.

    Args:
        db_path: Path to sessions.db file
        days: Number of days to retain (default: 7)
    """

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Calculate cutoff timestamp
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        # Delete old sessions
        # (ADK session table has 'updated_at' or 'created_at' column)
        cursor.execute(
            "DELETE FROM sessions WHERE updated_at < ?",
            (cutoff_str,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            print(f"🗑️  Cleaned up {deleted_count} session(s) older than {days} days")
            logger.info("Cleaned up %d session(s) older than %d days",
                        deleted_count, days)
    except Exception as e:
        print(f"⚠️  Session cleanup warning: {e}")
        logger.warning("Session cleanup warning: %s", e)

async def main():
    """CLI Entry Point: Run the Investor Paradise Agent"""

    # 0. Welcome
    print("\n🚀 Welcome to Investor Paradise Agent! 🚀")
    print("🚀 Initializing  Investor Paradise...")
    logger.info("Starting Investor Paradise CLI Agent")

    # 1. Pre-load Data to establish date context
    _ = NSESTORE.df
    print(f"📅 Database Context: {NSESTORE.get_data_context()}")
    logger.info("Data loaded: %s", NSESTORE.get_data_context())

    # 2. Initialize Model & Root Agent (single pipeline)
    # Default: Use Flash-Lite for all agents (fast, cost-effective)
    model = "gemini-2.5-flash-lite"
    root_agent = create_pipeline(model)  # SequentialAgent: Entry→Market→News→Merger

    # 3. Setup Runner with in-memory session service
    db_path = "conversations/my_agent_data.db"
    # Cleanup old sessions file if present (best-effort)
    cleanup_old_sessions(db_path, days=7)

    session_service = InMemorySessionService()

    runner = Runner(
        agent=root_agent,
        app_name="investor_paradise",
        session_service=session_service,
    )

    # 4. Create Session
    user_id = str(uuid.uuid4())
    session_id = f"cli_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # No explicit session creation when not using a session service

    # Ensure session exists in session_service before running
    await session_service.create_session(
        app_name="investor_paradise",
        user_id=user_id,
        session_id=session_id,
    )

    print("\n💬 Ready! Ask me about NSE stocks or just say hi! (Type 'exit' to quit)\n")
    logger.info("CLI ready for user input (session_id: %s)", session_id)

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("👋 Goodbye! Happy investing!")
                logger.info("[Session: %s] User exited CLI", session_id)
                break

            # Log query with session ID
            query_id = conversation_logger.log_query(
                session_id=session_id,
                user_id=user_id,
                query=user_input
            )
            logger.info("[Session: %s] User query: %s", session_id, user_input)
            print("🔍 Processing...\n")

            user_message = types.Content(
                role="user", parts=[types.Part(text=user_input)]
            )

            final_response = ""
            tools_used = []

            # Run the full pipeline (Entry agent will route internally)
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text

            if final_response:
                print(f"Assistant:\n{final_response}\n")

                # Log response with session ID
                conversation_logger.log_response(
                    query_id=query_id,
                    session_id=session_id,
                    response=final_response,
                    tools_used=tools_used
                )

        except KeyboardInterrupt:
            print("\n👋 Goodbye! Happy investing!")
            logger.info(
              "[Session: %s] User terminated session via KeyboardInterrupt", session_id)
            break
        except Exception as e:
            error_msg = f"Error during agent execution: {e}"
            print(f"❌ Error: {e}")
            logger.error("[Session: %s] %s", session_id, error_msg, exc_info=True)
            conversation_logger.log_error(
                session_id=session_id,
                query_id=locals().get('query_id'),
                error=str(e)
            )
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
