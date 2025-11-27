import os
from dotenv import load_dotenv
import httpx
import sys
from investor_agent.logger import get_logger

logger = get_logger(__name__)

# --- 1. SSL Patch (Crucial for your env) ---
# original_init = httpx.AsyncClient.__init__
# def patched_init(self, *args, **kwargs):
#     kwargs['verify'] = False
#     original_init(self, *args, **kwargs)
# httpx.AsyncClient._init_ = patched_init
# ------------------------------------------

# --- 2. Load Config, logging & Data ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")


if not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not found. Check .env file.")

from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.apps.app import App
from investor_agent.sub_agents import create_pipeline
from investor_agent.data_engine import NSESTORE

logger.info("🚀 Initializing Web App Backend...")

# --- CRITICAL: Pre-load Data (Eager Loading - Option 1) ---
# This MUST happen before agent creation to ensure:
# 1. First user query is instant (no 5s CSV load delay)
# 2. Uses parquet cache if available (13x faster than CSV)
# 3. ADK web server is ready immediately after startup
logger.info("📂 Pre-loading NSE stock data...")
_ = NSESTORE.df  # Force immediate load (triggers cache check or CSV load)
logger.info(f"✅ Data loaded: {len(NSESTORE.df):,} rows, {NSESTORE.total_symbols:,} symbols")
logger.info(f"📅 Date range: {NSESTORE.get_data_context()}")

# --- 3. Initialize Model and Root Agent ---
# Default: Use Flash-Lite for all agents (fast, cost-effective)
model = Gemini(model="gemini-2.5-flash-lite", api_key=API_KEY)
flash_model = Gemini(model="gemini-2.5-flash", api_key=API_KEY)
pro_model = Gemini(model="gemini-2.5-pro", api_key=API_KEY)

# Create pipeline with optimized model selection
root_agent = create_pipeline(
    entry_model=model,        # Flash-Lite for Entry (simple classification)
    market_model=flash_model, # Flash for Market (complex analysis with tools)
    news_model=model,         # Flash-Lite for News (simple google search)
    merger_model=pro_model   # Pro for Merger (report synthesis)
)

# Override root_agent's module path to fix ADK path detection issue
# This prevents ADK from thinking the agent is from site-packages
root_agent.__module__ = "investor_agent.agent"

# Create App with EventsCompactionConfig (auto context compression)
from google.adk.apps.app import EventsCompactionConfig

app = App(
    name="investor_agent",  # Must match directory name for ADK web to find sessions
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # Compact history every 3 turns
        overlap_size=1          # Keep last turn for context
    )
)

logger.info("✅ App initialized and ready for `adk web`.")

# --- 4. Export for ADK Web Server ---
# The ADK web command will look for 'app' and auto-create runner with its own session service
# Usage: adk web (auto-discovers apps in current directory)
# Note: App name MUST match the directory name (investor_agent) for session persistence to work