"""Helper functions for building and running Gemini-based agents."""

import os

from dotenv import load_dotenv
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.models.google_llm import Gemini
from google.genai import types

from investor_agent import tools

# Import cache management functions
from investor_agent.cache_manager import (
    check_data_exists,
    download_all_data_from_gcs,
    download_all_data_from_github,
)
from investor_agent.data_engine import NSESTORE
from investor_agent.logger import get_logger
from investor_agent.sub_agents import create_pipeline

logger = get_logger(__name__)


# --- 2. Load Config, logging & Data ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Detect deployment environment
is_vertex_deployment = os.getenv("K_SERVICE") is not None  # Cloud Run sets this env var

if not is_vertex_deployment and not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not found. Check .env file.")

logger.info("🚀 Initializing Web App Backend...")
logger.info("   Environment: %s", "Vertex AI Cloud" if is_vertex_deployment else "Local Development")

# --- CRITICAL: Ensure Complete Data Availability (Before Agent Creation) ---
# All-or-nothing strategy: Check if BOTH cache AND vector data exist
#   - If either is missing: Delete entire data folder and re-download everything
#   - Cloud deployment: Download from GCS bucket (fast, same region)
#   - Local development: Download from GitHub (no GCS credentials needed)

logger.info("📂 Checking data availability (cache + vector data)...")
if not check_data_exists():
    logger.info("📥 Incomplete or missing data - downloading complete dataset...")

    if is_vertex_deployment:
        # Cloud deployment - download from GCS
        if not download_all_data_from_gcs(bucket_name="test-first-deployment"):
            logger.error("❌ Failed to download data from GCS")
            raise RuntimeError("Data download from GCS failed")
    else:
        # Local development - download from GitHub
        # if not download_all_data_from_github():
        #     logger.error("❌ Failed to download data from GitHub")
        #     raise RuntimeError("Data download from GitHub failed")
        logger.info("ℹ️ Skipping GitHub data download (for testing purposes)")

    logger.info("✅ Complete data download finished")
else:
    logger.info("✅ Complete data found (cache + vector data)")

# --- Pre-load Data (Eager Loading) ---
# Now that cache is guaranteed to exist, load it into memory
logger.info("📂 Pre-loading NSE stock data into memory...")
_ = NSESTORE.df  # Force immediate load (triggers cache check or CSV load)
logger.info("✅ Data loaded: %d rows, %d symbols", len(NSESTORE.df), NSESTORE.total_symbols)
logger.info("📅 Date range: %s", NSESTORE.get_data_context())

# --- Pre-load News Search Resources ---
# Note: Collections are now loaded dynamically based on query date range
# SemanticNewsAgent will call load_collections_for_date_range() for each query
# This just validates dependencies are available
logger.info("📰 Validating news search dependencies (ChromaDB + embeddings)...")
try:
    # Just check if we can import the dependencies
    if tools._SEMANTIC_SEARCH_AVAILABLE:
        logger.info("✅ News search dependencies available (will load collections dynamically)")
    else:
        logger.warning("⚠️ News search dependencies missing (chromadb, sentence-transformers)")
except Exception as e:
    logger.warning("⚠️ News search validation failed: %s", e)
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
# Note: When deployed to Vertex AI, don't pass api_key - it uses ADC (Application Default Credentials)
# For local development, api_key is used
is_vertex_deployment = os.getenv("K_SERVICE") is not None  # Cloud Run sets this env var

if is_vertex_deployment:
    # Vertex AI deployment - use ADC (no api_key)
    lite_model = Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config)
    flash_model = Gemini(model="gemini-2.5-flash", retry_options=retry_config)
    pro_model = Gemini(model="gemini-2.5-pro", retry_options=retry_config)
else:
    # Local development - use API key
    lite_model = Gemini(model="gemini-2.5-flash-lite",
                        api_key=GOOGLE_API_KEY, retry_options=retry_config)
    flash_model = Gemini(model="gemini-2.5-flash",
                         api_key=GOOGLE_API_KEY, retry_options=retry_config)
    pro_model = Gemini(model="gemini-2.5-pro",
                       api_key=GOOGLE_API_KEY, retry_options=retry_config)

# Create pipeline with optimized model selection
root_agent = create_pipeline(
    entry_model=lite_model,        # Flash-Lite for Entry (simple classification)
    market_model=flash_model, # Flash for Market (complex analysis with tools)
    news_model=lite_model,         # Flash-Lite for News (simple google search)
    merger_model=flash_model   # Pro for Merger (report synthesis)
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

# Export root_agent for ADK eval to find
# (Already defined above at line ~122, just making it explicit here)
agent = root_agent  # ADK eval looks for either 'agent' or 'root_agent'
# agent.__module__ = "investor_agent.agent"  # Fix module path for ADK eval