import os
from dotenv import load_dotenv
import httpx
import sys
from investor_agent.logger import get_logger

logger = get_logger(__name__)

# --- 1. SSL Patch (Crucial for your env) ---
original_init = httpx.AsyncClient.__init__
def patched_init(self, *args, **kwargs):
    kwargs['verify'] = False
    original_init(self, *args, **kwargs)
httpx.AsyncClient._init_ = patched_init
# ------------------------------------------

# --- 2. Load Config, logging & Data ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")


if not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not found. Check .env file.")

from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from investor_agent.sub_agents import create_pipeline
from investor_agent.data_engine import STORE

logger.info("🚀 Initializing Web App Backend...")

# Pre-load Data (Global Scope)
_ = STORE.df 
logger.info(f"📅 Database Context: {STORE.get_data_context()}")

# --- 3. Initialize Objects Globally ---
model = Gemini(model="gemini-2.5-flash-lite", api_key=API_KEY)
root_agent = create_pipeline(model)
# session_service = InMemorySessionService()

# # --- 4. Define the Runner Variable ---
# # The ADK Web server looks for this specific object
# runner = Runner(
#     agent=pipeline,
#     app_name="investor_paradise",
#     session_service=session_service
# )

logger.info("✅ Runner is ready for Web UI.")