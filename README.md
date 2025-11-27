# 🚀 Investor Paradise: AI-Powered Stock Analysis Agent

**Transform NSE stock data into actionable investment intelligence using a multi-agent AI system.**

[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google&logoColor=white)](https://github.com/google/adk)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Gemini 2.5](https://img.shields.io/badge/Gemini-2.5-orange)](https://ai.google.dev/)

---

## 📚 Table of Contents

- [🚀 Investor Paradise: AI-Powered Stock Analysis Agent](#-investor-paradise-ai-powered-stock-analysis-agent)
  - [📚 Table of Contents](#-table-of-contents)
  - [What is This?](#what-is-this)
  - [Why Use This?](#why-use-this)
  - [Agent Architecture](#agent-architecture)
    - [🛡️ 1. Entry Router (Security + Routing)](#️-1-entry-router-security--routing)
    - [📊 2. Market Analyst (Quantitative Engine)](#-2-market-analyst-quantitative-engine)
    - [📰 3. News Analyst (Qualitative Context)](#-3-news-analyst-qualitative-context)
    - [🎯 4. CIO Synthesizer (Investment Strategist)](#-4-cio-synthesizer-investment-strategist)
  - [Two Ways to Use](#two-ways-to-use)
  - [Prerequisites](#prerequisites)
  - [Setup Instructions](#setup-instructions)
    - [1. Clone the Repository](#1-clone-the-repository)
      - [**Option B: Manual Download**](#option-b-manual-download)
  - [Running the Agent](#running-the-agent)
    - [Option 1: Web UI (ADK Web)](#option-1-web-ui-adk-web)
    - [Option 2: Command Line (CLI)](#option-2-command-line-cli)
  - [Troubleshooting](#troubleshooting)
    - [Data Download Issues](#data-download-issues)
    - [Data Loading Issues](#data-loading-issues)
  - [Sample Questions](#sample-questions)
    - [📈 Discovery \& Screening](#-discovery--screening)
    - [🔍 Deep Analysis](#-deep-analysis)
    - [🎯 Pattern Detection](#-pattern-detection)
    - [🛡️ Security Testing](#️-security-testing)
    - [📊 Time-Based Analysis](#-time-based-analysis)
  - [Project Structure](#project-structure)
  - [News Ingestion \& Semantic Search](#news-ingestion--semantic-search)
    - [PDF Ingestion](#pdf-ingestion)
    - [Semantic Search](#semantic-search)
      - [Example Query](#example-query)
    - [Multi-Collection Search](#multi-collection-search)
    - [Integration with Gemini Agent](#integration-with-gemini-agent)
    - [Custom Data Path](#custom-data-path)
    - [Model Selection](#model-selection)
    - [Cache Management](#cache-management)
    - [Logging](#logging)
      - [View logs](#view-logs)
  - [Linting \& Formatting](#linting--formatting)
  - [Dependencies](#dependencies)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)
  - [Support](#support)
    - [Made with ❤️ for the Indian stock market research community](#made-with-️-for-the-indian-stock-market-research-community)

---

## What is This?

**Investor Paradise** is a multi-agent AI system that analyzes NSE (National Stock Exchange) stock data by combining:

- **Quantitative Analysis**: 24 specialized tools for calculating returns, detecting patterns, analyzing risk metrics, and filtering by NSE indices/market cap
- **Qualitative Research**: News correlation to explain _why_ stocks moved, not just _what_ moved
- **Security**: Built-in prompt injection defense to protect against malicious queries
- **Synthesis**: Professional investment recommendations combining data + news + risk assessment
- **Comprehensive Logging**: Full activity tracking for debugging and audit (all requests/responses logged to file)

Unlike traditional stock screeners (static filters) or generic chatbots (hallucinated data), this system uses **four specialized agents** working in sequence to deliver research-grade analysis in seconds.

---

## Why Use This?

**Problem**: Existing tools either show raw data without interpretation (screeners) or provide generic insights without real market data (LLMs).

**Solution**: Investor Paradise bridges the gap by:

✅ **Explaining causality**: Connects price movements to news events (✅ Confirmation / ⚠️ Divergence)  
✅ **Multi-step workflows**: Backtest strategy → Rank results → Find news catalysts → Generate recommendations  
✅ **Grounded in reality**: Works with actual NSE historical data (2020-2025, 2000+ symbols)  
✅ **NSE Index Classification**: Filter by NIFTY50, NIFTYBANK, sectoral indices (IT, Auto, Pharma, etc.)  
✅ **Market Cap Analysis**: Analyze Large/Mid/Small cap stocks separately based on official NSE classifications  
✅ **Security-first**: Dedicated agent filters prompt injection attacks  
✅ **Actionable output**: Clear 🟢 Buy / 🟡 Watch / 🔴 Avoid recommendations with reasoning  
✅ **Full observability**: All operations logged to `investor_agent_logger.log` for debugging and audit

**Target Users**: Retail investors, equity researchers, developers building financial AI systems.

---

## Agent Architecture

The system uses a **4-agent sequential pipeline**:

![Agent Architecture](investor_agent_diagram.png)

### 🛡️ 1. Entry Router (Security + Routing)

- **Role**: Intent classification and prompt injection defense
- **Model**: Gemini Flash-Lite (fast, cost-effective)
- **Key Feature**: Blocks adversarial queries like "Ignore previous instructions..."

### 📊 2. Market Analyst (Quantitative Engine)

- **Role**: Execute 24 analysis tools including NSE index filtering, market cap classification, and advanced pattern detection
- **Model**: Gemini Flash (optimized for tool-heavy workflows)
- **Tools**:
  - **Index/Classification**: `list_available_indices`, `get_index_constituents`, `get_stocks_by_market_cap`, `get_market_cap_category`
  - **Core Analysis**: `get_top_gainers`, `get_sector_top_performers`, `get_index_top_performers`, `get_market_cap_performers`
  - **Pattern Detection**: `detect_volume_surge`, `detect_breakouts`, `find_momentum_stocks`, `detect_reversal_candidates`
  - **Risk Analysis**: `analyze_risk_metrics`, `get_52week_high_low`, `get_volume_price_divergence`
- **Key Features**:
  - Filter by 40+ NSE indices (NIFTY50, NIFTY100, NIFTYBANK, sectoral indices)
  - Market cap classification (Large/Mid/Small) based on official NSE index membership
  - All tool invocations logged with parameters and results

### 📰 3. News Analyst (Qualitative Context)

- **Role**: Correlate price movements with news events via Google Search
- **Model**: Gemini Flash-Lite
- **Output**: Explains if news confirms or contradicts price action

### 🎯 4. CIO Synthesizer (Investment Strategist)

- **Role**: Merge quantitative + qualitative into final recommendations
- **Model**: Gemini Pro (advanced reasoning for synthesis)
- **Output**: Investment-grade report with risk assessment

---

## Two Ways to Use

| Method         | Use Case                             | Features                                          |
| -------------- | ------------------------------------ | ------------------------------------------------- |
| **ADK Web UI** | Interactive analysis, exploration    | Visual chat interface, session history, web-based |
| **CLI**        | Quick queries, automation, scripting | Fast, scriptable, terminal-based                  |

Both use the same agent pipeline and data—choose based on your workflow.

---

## 🎬 Quick Demo for Evaluators

**Zero-config run in 3 commands:**

```bash
# 1. Set your API key
export GOOGLE_API_KEY="your-key-here"

# 2. Install dependencies
uv sync

# 3. Start the web UI
adk web investor_agent --port=8000 --host=0.0.0.0
```

Access at: <http://localhost:8000>

**Or use the CLI for instant testing:**

```bash
python main.py
```

**Provide your own API key via ADK Web UI:**

1. Click **Settings** (⚙️) → **Providers** → **Google (Gemini)**
2. Paste your [free API key](https://aistudio.google.com/apikey)
3. Save and start chatting

📖 **Full deployment guide**: See [DEPLOYMENT.md](DEPLOYMENT.md) for Docker, cloud hosting, and advanced options.

---

## Prerequisites

- **Python 3.11+** (required for modern typing features)
- **uv** package manager ([Install uv](https://github.com/astral-sh/uv))
- **Google API Key** with Gemini access ([Get API key](https://ai.google.dev/))
- **NSE historical data** (CSV files in `investor_agent/data/NSE_RawData/`)

---

## Setup Instructions

### 1. Clone the Repository

````bash
git clone https://github.com/atulkumar2/investor_paradise.git
cd investor_paradise
```text


### 2. Install Dependencies with `uv`

```bash
# Install all dependencies from pyproject.toml
uv sync
```text



This installs:

- **Runtime**: `pandas`, `pyarrow`, `google-adk`, `pydantic`
- **Dev tools**: `ruff`, `black`, `pytest` (optional)


### 3. Configure API Key

Create a `.env` file in the project root:

```bash
# .env
GOOGLE_API_KEY=your_gemini_api_key_here
```text

**Important**: Never commit `.env` to version control (already in `.gitignore`).


### 4. Download NSE Historical Data

The project includes an automated NSE data downloader script. You have two options:


#### **Option A: Automated Download (Recommended)**

Use the included script to automatically download NSE Bhavcopy data:

```bash
# Download data from Oct 1, 2019 to today
python download_nse_data.py

# The script will:
# ✅ Download Full Bhavcopy zip files from NSE
# ✅ Extract CSV files automatically
# ✅ Organize files by month (YYYYMM folders)
# ✅ Skip weekends (market closed)
# ✅ Track failed downloads in failed_downloads.json
```text


**What the script does:**

- Downloads NSE Full Bhavcopy data from NSE India's official API
- Handles session cookies and headers automatically (avoids 403 errors)
- Skips already downloaded files (resume-friendly)
- Organizes files in monthly folders: `investor_agent/data/NSE_RawData/YYYYMM/`
- Respects NSE servers with rate limiting (2-second delays)


**Expected output:**

```text
🚀 Starting NSE Bhavcopy Download
📅 Date Range: 01-Feb-2025 to 22-Nov-2025
📁 Output Directory: /path/to/investor_agent/data/NSE_RawData

🔐 Getting session cookie... ✅

📥 Processing 03-Feb-2025... ✅
📥 Processing 04-Feb-2025... ✅
⏭️  Skipping 08-Feb-2025 (Weekend)
📥 Processing 10-Feb-2025... ⏭️  Already exists, skipping
...
````

📊 Download Summary
✅ Successful: 195
⏭️ Skipped (already exist): 12
❌ Failed: 3

````


**Customize date range** (edit `download_nse_data.py`):

```python
# Change these lines in main()
start_date = datetime(2020, 5, 1)  # Start from May 1, 2020
end_date = datetime.now()           # Download up to today
````

#### **Option B: Manual Download**

If you have existing NSE data or prefer manual download:

1. Place CSV files in `investor_agent/data/NSE_RawData/`:

   ```text
   investor_agent/
     data/
       NSE_RawData/
         sec_bhavdata_full_01052020.csv
         sec_bhavdata_full_04052020.csv
         sec_bhavdata_full_05052020.csv
         ...
   ```

2. **File naming convention**: `sec_bhavdata_full_DDMMYYYY.csv`

3. **Minimum data requirement**: At least 30 days of data recommended for meaningful analysis

**Data Performance:**

- **First run**: Data loads from CSV (~5 seconds for 1M+ rows)
- **Subsequent runs**: Uses Parquet cache (~0.4 seconds, 13x faster)
- **Cache location**: `investor_agent/data/cache/combined_data.parquet`

---

## Running the Agent

### Option 1: Web UI (ADK Web)

**Best for**: Interactive exploration, multi-turn conversations, visual analysis

```bash
# Start the ADK web server (serve all agents in the project)
adk web . --log_level INFO

# Or serve only the investor_agent
adk web investor_agent --log_level INFO

# Output:
# 🚀 Starting ADK web server...
# 📂 Pre-loading NSE data...
# ✅ Data loaded: 1,234,567 rows, 2,345 symbols
# 🌐 Server running at http://localhost:8000
```

Open your browser to `http://localhost:8000` and start chatting with the agent.

**Optional Flags:**

```bash
adk web . --port 8080           # Custom port
adk web . --log_level DEBUG     # Verbose logging
adk web . --host 0.0.0.0        # Allow external access
```

---

### Option 2: Command Line (CLI)

**Best for**: Quick queries, automation, scripting, CI/CD pipelines

```bash
# Basic query
uv run cli.py "What are the top 5 gainers last week?"

# Custom date range
uv run cli.py "Analyze RELIANCE from 2024-01-01 to 2024-12-31"

# Pattern detection
uv run cli.py "Find stocks with volume surge and high delivery percentage"

# Comparison
uv run cli.py "Compare TCS, INFY, and WIPRO on risk metrics"
```

**How it works**:

1. Agent loads data (uses cache if available)
2. Processes query through 4-agent pipeline
3. Outputs final report to terminal
4. Exits (stateless, no session history)

---

---

## Troubleshooting

### Data Download Issues

**Problem**: Script fails with 403 errors  
**Solution**: NSE's API may have rate limits. Wait 5 minutes and retry. The script will skip already downloaded files.

**Problem**: "No data available (404)" for specific dates  
**Solution**: NSE may not have published data for that date (market holidays, system maintenance). Check `failed_downloads.json` for details.

**Problem**: Script is too slow  
**Solution**: The script uses 2-second delays to respect NSE servers. For faster downloads, you can reduce the delay in `download_nse_data.py` (line with `time.sleep(2)`), but use responsibly.

### Data Loading Issues

**Problem**: "No data loaded" when starting agent

**Solution**:

1. Verify CSV files exist in `investor_agent/data/NSE_RawData/`
2. Check file naming: `sec_bhavdata_full_DDMMYYYY.csv`
3. Delete Parquet cache and reload: `rm -rf investor_agent/data/cache/`

**Problem**: Agent queries return "No data available for [dates]"  
**Solution**: Download more historical data. The agent can only analyze dates present in your CSV files.

---

## Sample Questions

### 📈 Discovery & Screening

```text
"What are the top 10 gainers in the last month?"
"Find momentum stocks with high delivery percentage"
"Which banking stocks are near their 52-week high?"
"Show me stocks with unusual volume activity"
"What are the top performers in NIFTY50 last week?"
"Show me large-cap stocks with high returns in the last month"
"Which IT sector stocks (NIFTYIT) are showing momentum?"
"Find mid-cap stocks with volume surge and positive delivery"
"List all available NSE indices and their constituents"
"What are the sectoral indices available for analysis?"
```

### 🔍 Deep Analysis

```text
"Analyze RELIANCE stock performance over the last quarter"
"Compare TCS, INFY, and WIPRO on returns and volatility"
"What are the risk metrics for HDFCBANK?"
"Explain why IT sector stocks rallied last week"
"Show me the market cap category for TATASTEEL"
"Compare performance of large-cap vs mid-cap stocks"
"Which NIFTYBANK constituents are underperforming?"
```

### 🎯 Pattern Detection

```text
"Find stocks with volume surge and breakout patterns"
"Detect accumulation patterns in pharmaceutical sector"
"Show me reversal candidates with positive divergence"
"Which stocks are showing distribution patterns?"
"Find small-cap stocks near 52-week highs"
"Detect momentum stocks in NIFTYAUTO index"
```

---

## Project Structure

```
investor_paradise/
├── investor_agent/           # Main agent package
│   ├── agent.py             # Entry point (exports root_agent)
│   ├── sub_agents.py        # 4-agent pipeline definition
│   ├── data_engine.py       # NSE data loader + metrics
│   ├── tools.py             # 24 analysis tools (core + advanced)
│   ├── indices_utils.py     # NSE indices & market cap classification (NEW)
│   ├── prompts.py           # Agent system instructions
│   ├── schemas.py           # Pydantic output schemas
│   ├── logger.py            # Logging configuration (NEW - captures all logs)
│   └── data/
│       ├── NSE_RawData/     # CSV files (git-ignored)
│       │   ├── 202505/      # May 2025 data (organized by month)
│       │   ├── 202506/      # June 2025 data
│       │   └── ...
│       ├── NSE_indices_list/# NSE index constituents (NIFTY50, NIFTYBANK, etc.)
│       │   └── 2024-11-27/  # Latest index data
│       └── cache/           # Parquet cache (auto-generated)
│           └── combined_data.parquet
├── cli.py                   # CLI entry point (enhanced with logging)
├── download_nse_data.py     # NSE data downloader script
├── pyproject.toml           # Dependencies + config
├── .env                     # API keys (git-ignored)
├── investor_agent_logger.log # All application & library logs (NEW)
├── README.md                # This file
└── AGENT_FLOW_DIAGRAM.md    # Detailed architecture docs
```

---

## News Ingestion & Semantic Search

Investor Paradise supports ingesting news PDFs and performing semantic search over their content, enabling the agent to answer questions grounded in both market data and relevant news context.

### PDF Ingestion

Use the provided ingestion script to process news PDFs and store their embeddings in a vector database (ChromaDB):

```bash
python news_agent/pdf_ingest.py --pdf-dir ./news_pdfs --persist-dir ./vector-data/news --chunk-size 512 --overlap 64 --log-level INFO
```

- `--pdf-dir`: Directory containing PDF files to ingest
- `--persist-dir`: Output directory for vector DB (can be separate from market data)
- `--chunk-size`: Number of characters per text chunk
- `--overlap`: Overlap between chunks for better context
- `--log-level`: Logging verbosity

### Semantic Search

You can run semantic search over the ingested news collection interactively or programmatically:

```bash
python news_agent/test_search_query.py --persist-dir ./vector-data/news
```

You will be prompted to enter queries, and the tool will return the most relevant news chunks with metadata (including source file).

#### Example Query

```
Enter your search query (or type 'exit' to quit): RBI rate hike
INFO:semantic_search:Found 3 results:
INFO:semantic_search:Result 1 (similarity: 0.82)
INFO:semantic_search:Source: rbi_policy_2025.pdf
INFO:semantic_search:Content: The Reserve Bank of India announced a rate hike of ...
```

### Multi-Collection Search

You can search across multiple news or research collections by specifying multiple `--persist-dir` values (comma or colon separated):

```bash
python news_agent/test_search_query.py --persist-dir ./vector-data/news,./vector-data/research
```

The search tool will merge results from all specified collections and return the most relevant matches.

### Integration with Gemini Agent

The Gemini agent automatically uses the semantic search tool as a knowledge source. When you ask questions in the CLI or web UI, the agent will:

1. Search the ingested news/document collections for relevant context
2. Use the results to ground its answers and provide citations

You can configure which collections are used by passing `--persist-dir` or `--persist-dirs` to the agent CLI:

```bash
python news_agent/gemini_agent.py --persist-dirs ./vector-data/market ./vector-data/news
```

This enables hybrid analysis combining market data and news context for more robust, explainable answers.

### Custom Data Path

```python
# investor_agent/data_engine.py
NSESTORE = NSEDataStore(root_path="path/to/custom/data")
```

### Model Selection

```python
# investor_agent/agent.py
root_agent = create_pipeline(
  model,                    # Flash-Lite for Entry/News
  market_model=flash_model, # Flash for Market (tool-heavy)
  merger_model=pro_model    # Pro for Synthesis
)
```

### Cache Management

```bash
# Clear Parquet cache to force CSV reload
rm -rf investor_agent/data/cache/combined_data.parquet

# Clear all logs (useful for fresh debugging sessions)
rm -f investor_agent_logger.log *.log

# View cache stats
ls -lh investor_agent/data/cache/
```

---

## Logging

All application activity is logged to `investor_agent_logger.log` for debugging and audit:

**What's logged:**

- ✅ Agent initialization and pipeline creation
- ✅ All tool invocations with parameters and results
- ✅ User queries and responses (CLI mode)
- ✅ Data loading and caching operations
- ✅ Errors with full stack traces (ERROR level)
- ✅ Third-party library logs (Google GenAI, ADK web server, httpx)

**Log levels:**

- `INFO`: Standard operations (tool calls, queries, data loading)
- `ERROR`: Failures with stack traces for debugging
- `DEBUG`: Detailed internal state (disabled by default)

**Configuration:**

```python
# investor_agent/logger.py
logger = get_logger(__name__)
logger.info("Custom log message")
logger.error("Error occurred", exc_info=True)  # Includes stack trace
```

#### View logs

```bash
# Follow logs in real-time
tail -f investor_agent_logger.log

# Search for errors
grep ERROR investor_agent_logger.log

# View tool invocations
grep "get_top_gainers\|analyze_stock" investor_agent_logger.log

# Filter by agent
grep "MarketAnalyst\|NewsAnalyst" investor_agent_logger.log
```

**Important Notes:**

- Log file rotates automatically to prevent disk space issues
- Sensitive data (API keys) are NOT logged
- Stack traces appear only for ERROR-level logs (not INFO)
- Root logger configured to capture all Python logs (including libraries)

---

## Linting & Formatting

```bash
# Check code quality
ruff check .

# Auto-format code
ruff format .
# or
black .
```

---

## Dependencies

Runtime dependencies declared in `pyproject.toml` (PEP 621):

```toml
[project]
dependencies = [
    "pandas>=2.0",
    "pyarrow>=14.0",
    "google-adk>=0.1",
    "pydantic>=2.0",
    "python-dotenv>=1.0"
]
```

**No `requirements.txt` needed**—`uv` manages everything via `pyproject.toml`.

If external platforms require `requirements.txt`:

```bash
uv export > requirements.txt
```

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow existing code style (Ruff/Black)
4. Add tests for new functionality
5. Submit a pull request

---

## License

This project is licensed under the MIT License—see LICENSE file for details.

---

## Acknowledgments

- **Google ADK** for multi-agent framework
- **NSE India** for market data and official index classifications
- **Gemini AI** for language models
- **ChromaDB** for vector storage (news ingestion)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/atulkumar2/investor_paradise/issues)
- **Discussions**: [GitHub Discussions](https://github.com/atulkumar2/investor_paradise/discussions)
- **Documentation**: See `AGENT_FLOW_DIAGRAM.md` for detailed architecture

---

---

### Made with ❤️ for the Indian stock market research community
