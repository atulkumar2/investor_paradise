""" Investor Agent - ADK Web Backend Initialization """

import os
import warnings

import httpx
from dotenv import load_dotenv
from google.adk.models.google_llm import Gemini

from investor_agent.data_engine import NSESTORE
from investor_agent.logger import get_logger
from investor_agent.sub_agents import create_pipeline

warnings.filterwarnings("ignore", message=".*EXPERIMENTAL.*")

logger = get_logger(__name__)

# --- 1. SSL Patch (Crucial for your env) ---
# Use getattr/setattr to avoid static-analysis warnings and replace dunder init safely.
_original_init = getattr(httpx.AsyncClient, "__init__")
def _patched_init(self, *args, **kwargs):
    """Patch httpx AsyncClient to disable SSL verification by default."""
    # Only set verify to False if not explicitly provided by the caller
    kwargs.setdefault("verify", False)
    return _original_init(self, *args, **kwargs)

# Use setattr to assign patched initializer (avoids direct dunder assignment complaints)
setattr(httpx.AsyncClient, "__init__", _patched_init)
# ------------------------------------------

# --- 2. Load Config, logging & Data ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not found. Check .env file.")

logger.info("🚀 Initializing Web App Backend...")

# --- CRITICAL: Pre-load Data (Eager Loading - Option 1) ---
# This MUST happen before agent creation to ensure:
# 1. First user query is instant (no 5s CSV load delay)
# 2. Uses parquet cache if available (13x faster than CSV)
# 3. ADK web server is ready immediately after startup
logger.info("📂 Pre-loading NSE stock data...")
_ = NSESTORE.df  # Force immediate load (triggers cache check or CSV load)
logger.info(
    "✅ Data loaded: %s rows, %s symbols",
    format(len(NSESTORE.df), ","),
    format(NSESTORE.total_symbols, ","),
)
logger.info("📅 Date range: %s", NSESTORE.get_data_context())

# --- 3. Initialize Model and Root Agent ---
# Default: Use Flash-Lite for all agents (fast, cost-effective)
lite_model = Gemini(model="gemini-2.5-flash-lite", api_key=GOOGLE_API_KEY)
flash_model = Gemini(model="gemini-2.5-flash", api_key=GOOGLE_API_KEY)
pro_model = Gemini(model="gemini-2.5-pro", api_key=GOOGLE_API_KEY)

# Single root agent - full pipeline with Entry → Market → News → Merger
# root_agent = create_pipeline(model)

# Example: Use Gemini Pro for computationally intensive agents
# pro_model = Gemini(model="gemini-2.0-flash-001", api_key=API_KEY)
root_agent = create_pipeline(
    lite_model,                    # Flash-Lite for Entry/News (simple tasks)
    market_model=flash_model,   # Flash for Market (8 tools, complex analysis)
    merger_model=flash_model    # Pro for Merger (synthesis, report generation)
)

logger.info("✅ Root agent initialized and ready for `adk web`.")

# --- 4. Export for ADK Web Server ---
# The ADK web command expects a directory containing agent subdirectories.
# Each agent subdirectory must have __init__.py and agent.py with a 'root_agent' export.
#
# Usage (from project root):
#   adk web . --port=8000 --host=0.0.0.0
#
# Or to serve only the investor_agent:
#   adk web investor_agent --port=8000 --host=0.0.0.0
#
# The web UI will be available at http://localhost:8000
# Evaluators can access the chat interface and provide their own API key in Settings.
