""" CLI Entry Point for Investor Paradise Agent """

import asyncio
import os
import sqlite3
import traceback
import uuid
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from investor_agent.data_engine import NSESTORE
from investor_agent.logger import get_logger
from investor_agent.sub_agents import create_pipeline

logger = get_logger(__name__)

# --- SSL Patch (Required for your environment) ---
original_init = httpx.AsyncClient.__init__
def patched_init(self, *args, **kwargs):
    """ Patch httpx AsyncClient to disable SSL verification. """
    kwargs['verify'] = False
    original_init(self, *args, **kwargs)
httpx.AsyncClient._init_ = patched_init
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
            logger.info("Cleaned up %d session(s) older than %d days", deleted_count, days)
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
    model = Gemini(model="gemini-2.5-flash-lite", api_key=GOOGLE_API_KEY)
    root_agent = create_pipeline(model)  # SequentialAgent: Entry→Market→News→Merger

    # Example: Use Gemini Pro for computationally intensive agents
    # pro_model = Gemini(model="gemini-2.0-flash-001", api_key=API_KEY)
    # root_agent = create_pipeline(
    #     model,                    # Flash-Lite for Entry/News (simple tasks)
    #     market_model=pro_model,   # Pro for Market (8 tools, complex analysis)
    #     merger_model=pro_model    # Pro for Merger (synthesis, report generation)
    # )

    # 3. Setup Session Service & Runner
    db_path = "my_agent_data.db"
    db_url = "sqlite+aiosqlite:///my_agent_data.db"

    # Cleanup old sessions before starting
    cleanup_old_sessions(db_path, days=7)

    session_service = DatabaseSessionService(db_url=db_url)

    runner = Runner(
        agent=root_agent,
        app_name="investor_paradise",
        session_service=session_service
    )

    # 4. Create Session
    user_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name="investor_paradise",
        user_id=user_id,
        session_id="session_1"
    )

    print("\n💬 Ready! Ask me about NSE stocks or just say hi! (Type 'exit' to quit)\n")
    logger.info("CLI ready for user input")

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("👋 Goodbye! Happy investing!")
                logger.info("User exited CLI")
                break

            logger.info("User query: %s", user_input)
            print("🔍 Processing...\n")

            user_message = types.Content(
                role="user", parts=[types.Part(text=user_input)]
            )

            final_response = ""

            # Run the full pipeline (Entry agent will route internally)
            async for event in runner.run_async(
                user_id="user_1",
                session_id="session_1",
                new_message=user_message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text

            if final_response:
                print(f"Assistant:\n{final_response}\n")

        except KeyboardInterrupt:
            print("\n👋 Goodbye! Happy investing!")
            logger.info("User terminated session via KeyboardInterrupt")
            break
        except Exception as e:
            error_msg = f"Error during agent execution: {e}"
            print(f"❌ Error: {e}")
            logger.error(error_msg, exc_info=True)
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
