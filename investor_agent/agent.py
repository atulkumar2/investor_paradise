import os
from dotenv import load_dotenv
import httpx
import sys
from investor_agent.logger import get_logger
from google.genai import types

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
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not found. Check .env file.")

from google.adk.models.google_llm import Gemini
from google.adk.apps.app import App, EventsCompactionConfig
from investor_agent.sub_agents import create_pipeline
from investor_agent.data_engine import NSESTORE
from investor_agent import tools

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

# --- Pre-load News Search Resources ---
# Note: Collections are now loaded dynamically based on query date range
# SemanticNewsAgent will call load_collections_for_date_range() for each query
# This just validates dependencies are available
logger.info("📰 Validating news search dependencies (ChromaDB + embeddings)...")
try:
    # Just check if we can import the dependencies
    from investor_agent import tools
    if tools._SEMANTIC_SEARCH_AVAILABLE:
        logger.info("✅ News search dependencies available (will load collections dynamically)")
    else:
        logger.warning("⚠️ News search dependencies missing (chromadb, sentence-transformers)")
except Exception as e:
    logger.warning(f"⚠️ News search validation failed: {e}")
    logger.warning("News semantic search will fallback to google_search only")

# --- 3. Configure Retry Options ---
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# --- 4. Initialize Model and Root Agent ---
# Default: Use Flash-Lite for all agents (fast, cost-effective)
lite_model = Gemini(model="gemini-2.5-flash-lite", api_key=GOOGLE_API_KEY, retry_options=retry_config)
flash_model = Gemini(model="gemini-2.5-flash", api_key=GOOGLE_API_KEY, retry_options=retry_config)
pro_model = Gemini(model="gemini-2.5-pro", api_key=GOOGLE_API_KEY, retry_options=retry_config)

# Create pipeline with optimized model selection
root_agent = create_pipeline(
    entry_model=lite_model,        # Flash-Lite for Entry (simple classification)
    market_model=flash_model, # Flash for Market (complex analysis with tools)
    news_model=lite_model,         # Flash-Lite for News (simple google search)
    merger_model=pro_model   # Pro for Merger (report synthesis)
)

# Override root_agent's module path to fix ADK path detection issue
# This prevents ADK from thinking the agent is from site-packages
root_agent.__module__ = "investor_agent.agent"

# --- 5. Create App with Compaction Enabled ---
# Automatically compacts old conversation history to save tokens
app = App(
    name="investor_agent",  # Must match directory name for ADK web to find sessions
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # Trigger compaction every 3 invocations
        overlap_size=1,  # Keep 1 previous turn for context
    ),
)

logger.info("✅ App initialized with context compaction enabled.")
logger.info("   Compaction: interval=3 invocations, overlap_size=1 turn")

# --- 6. Initialize Database Session Service ---
# Use SQLite for persistent conversation history
# db_path = "sqlite:///investor_agent/data/sessions.db"
# session_service = DatabaseSessionService(db_url=db_path)
# logger.info(f"📦 Database session service initialized: {db_path}")

# # --- 7. Create Runner with Session Service ---
# # The runner ties together the app and session service
# runner = Runner(app=app, session_service=session_service)
# logger.info("✅ Runner initialized with database sessions.")

# --- 8. Export for ADK Web Server ---
# The ADK web command will look for 'app' and 'runner'
# Usage: adk web (auto-discovers apps in current directory)
# Note: App name MUST match the directory name (investor_agent) for session persistence to work