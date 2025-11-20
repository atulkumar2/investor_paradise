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
httpx.AsyncClient.init = patched_init
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
# --- CRITICAL: Pre-load Data (Eager Loading - Option 1) ---
# This MUST happen before agent creation to ensure:
# 1. First user query is instant (no 5s CSV load delay)
# 2. Uses parquet cache if available (13x faster than CSV)
# 3. ADK web server is ready immediately after startup
logger.info("📂 Pre-loading NSE stock data...")
_ = STORE.df  # Force immediate load (triggers cache check or CSV load)
logger.info(f"✅ Data loaded: {len(STORE.df):,} rows, {STORE.total_symbols:,} symbols")
logger.info(f"📅 Date range: {STORE.get_data_context()}")

# --- 3. Initialize Model and Root Agent ---
model = Gemini(model="gemini-2.5-flash-lite", api_key=API_KEY)

# Single root agent - full pipeline with Entry → Market → News → Merger
root_agent = create_pipeline(model)

logger.info("✅ Root agent initialized and ready for adk web.")

# --- 4. Export for ADK Web Server ---
# The ADK web command will look for 'root_agent' to instantiate Runner
# Usage: adk web --agent=investor_agent.agent:root_agent --port=8000