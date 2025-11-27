# 🚀 Deployment Guide for Evaluators

This guide helps you quickly run and evaluate the Investor Paradise agent.

---

## ⚡ Quick Start (Choose One)

### Option 1: Docker (Recommended - Zero Python Setup)

**Prerequisites:**

- Docker Desktop installed and running ([Download](https://www.docker.com/products/docker-desktop))
- Google Gemini API key ([Get free key](https://aistudio.google.com/apikey))

**Linux/macOS:**

```bash
# 1. Clone the repo
git clone https://github.com/atulkumar2/investor_paradise.git
cd investor_paradise

# 2. Build and run with Docker
docker build -t investor-paradise .
docker run --rm \
  -e GOOGLE_API_KEY="your-gemini-api-key" \
  -p 8000:8000 \
  investor-paradise
```

**Windows (PowerShell):**

```powershell
# 1. Clone the repo
git clone https://github.com/atulkumar2/investor_paradise.git
cd investor_paradise

# 2. Ensure Docker Desktop is running (check system tray)
# Verify: docker version should show both Client and Server

# 3. Build and run with Docker
docker build -t investor-paradise .
docker run --rm `
  -e GOOGLE_API_KEY="your-gemini-api-key" `
  -p 8000:8000 `
  investor-paradise
```

Access at: **<http://localhost:8000>**

**Note:** The Docker image automatically downloads NSE stock data (~1.5GB) from GitHub releases during build. This is a one-time download that gets cached in the image. Build time: ~5-7 minutes depending on internet speed.

**Troubleshooting Docker on Windows:**

- If you see "error during connect: ... dockerDesktopLinuxEngine: The system cannot find the file specified":
  - Start Docker Desktop from the Start menu
  - Wait for the Docker icon in system tray to become steady (not animated)
  - Run `docker version` to verify both Client and Server respond
  - Docker Desktop can take 30-60 seconds to fully start

### Option 2: GitHub Codespaces (Browser-Based)

1. Click **Code** → **Codespaces** → **Create codespace on release**
2. Wait for environment to load (~2 min)
3. Add your API key:

   ```bash
   export GOOGLE_API_KEY="your-key-here"
   ```

4. Run:

   ```bash
   uv run adk web . --port=8000 --host=0.0.0.0
   ```

5. Click the forwarded port URL when prompted

### Option 3: Local Python Setup

**Prerequisites:**

- Python 3.11+
- Google Gemini API key ([Get free key](https://aistudio.google.com/apikey))

### 1. Set up environment

```bash
# Clone and navigate to the repo
cd investor_paradise

# Install dependencies (using uv - recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
GOOGLE_API_KEY=your-api-key-here
```

Or export it directly:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

### 3. Run ADK Web UI

#### Option A: Serve all agents in the project

```bash
uv run adk web . --port=8000 --host=0.0.0.0
```

#### Option B: Serve only the investor_agent

```bash
uv run adk web investor_agent --port=8000 --host=0.0.0.0
```

#### Option C: CLI (minimal demo)

```bash
uv run python cli.py
```

### 4. Access the UI

- Open your browser to: <http://localhost:8000>
- The web UI provides:
  - Interactive chat interface
  - API key configuration in Settings (if not using `.env`)
  - Session history
  - Agent execution traces

---

## Setting API Key in ADK Web UI

If you didn't set the API key via `.env`, you can configure it in the web interface:

1. Click **Settings** (gear icon in top-right)
2. Navigate to **Providers** → **Google (Gemini)**
3. Paste your API key
4. Click **Save**

The agent will now use your key for all Gemini model calls.

---

## Docker Deployment (Portable)

### Build the image

```bash
docker build -t investor-paradise .
```

### Run with API key

```bash
docker run --rm \
  -e GOOGLE_API_KEY="your-api-key-here" \
  -p 8000:8000 \
  investor-paradise
```

Access at: <http://localhost:8000>

---

## Cloud Deployment Options

### GitHub Codespaces (Zero Setup)

1. Open this repo in Codespaces
2. Add `GOOGLE_API_KEY` as a Codespace secret
3. Run: `adk web . --port=8000 --host=0.0.0.0`
4. Codespaces will provide a public URL

### Railway / Render / Fly.io

1. Connect your GitHub repo
2. Add `GOOGLE_API_KEY` as an environment variable
3. Set start command: `adk web . --port=8000 --host=0.0.0.0`
4. Deploy

### Hugging Face Spaces (Gradio/Streamlit)

If you prefer a custom UI:

- Add `app.py` with Gradio or Streamlit wrapper
- Call `root_agent` from `investor_agent.agent`
- Deploy to HF Spaces (free tier available)

## Sample Queries to Test

Once the agent is running, try these queries:

- "What are the top 5 banking stocks based on last month's trend?"
- "Analyze RELIANCE stock for the last 3 months"
- "Show me IT sector gainers in the last 2 weeks"
- "Compare TCS vs INFY vs WIPRO"
- "Find stocks with high delivery percentage and positive momentum"

## Troubleshooting

### Import Error or Module Not Found

```bash
# Reinstall in editable mode
pip install -e .
```

### SSL Certificate Errors

The agent includes an httpx SSL patch in `agent.py` (lines 18-21). This is required for certain environments.

### Data Not Loading

The agent pre-loads NSE data on startup. First load from CSV takes ~5s. Subsequent runs use parquet cache (13x faster).

### API Key Not Found

Ensure:

- `.env` file exists in project root with `GOOGLE_API_KEY=...`
- Or the key is set via ADK Web UI Settings
- Or exported as environment variable before running

## Architecture

- **Entry Router**: Determines if query needs stock analysis or general response
- **Market Analyst**: Analyzes stock data using 15+ tools (price, volume, momentum, risk)
- **News Analyst**: (Optional) Fetches news context for discovered stocks
- **CIO Synthesizer**: Merges market + news insights into final report

Data source: NSE stock data (2020-2025, 2300+ symbols)

## Cost Estimates

Using Gemini Flash Lite (default config):

- ~$0.001 per query (typical)
- Free tier: 1500 requests/day

Upgrading to Gemini Pro (uncomment in `agent.py`):

- ~$0.01 per complex query
- Better for multi-step reasoning

## Support

For issues or questions:

- Check logs: `investor_agent_logger.log`
- Enable verbose logging: `adk web . --port=8000 --verbose`
- Review agent traces in ADK Web UI
