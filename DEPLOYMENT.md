# 🚀 Deployment Guide for Evaluators

This guide explains how to run and evaluate the **Investor Paradise** agent locally or in the cloud.

> You need a **Google Gemini API key** to run the agent. Get one from: https://aistudio.google.com/apikey

---

## ⚡ Quick Start (Choose One)

### Option 1: Docker (Recommended - Zero Python Setup)

#### Prerequisites (Docker)

- Docker installed and running
- Google Gemini API key

#### Linux / macOS

```bash
# 1. Clone the repo
git clone https://github.com/atulkumar2/investor_paradise.git
cd investor_paradise

# 2. Build the image (downloads NSE data; first build may take several minutes)
docker build -t investor-paradise .

# 3. Run container with your API key
docker run --rm \
  -e GOOGLE_API_KEY="your-gemini-api-key" \
  -p 8000:8000 \
  investor-paradise
```

Access the UI at:

- `http://localhost:8000` (from the same machine)
- Or `http://<linux-ip>:8000` from another device on the same network (e.g. Windows)

If you want to use a different local port (e.g. 8001):

```bash
docker run --rm \
  -e GOOGLE_API_KEY="your-gemini-api-key" \
  -p 8001:8000 \
  investor-paradise
```

Then access at `http://localhost:8001`.

#### Windows (PowerShell)

```powershell
# 1. Clone the repo
git clone https://github.com/atulkumar2/investor_paradise.git
cd investor_paradise

# 2. Ensure Docker Desktop is running
# Verify: docker version should show both Client and Server

# 3. Build and run with Docker
docker build -t investor-paradise .
docker run --rm `
  -e GOOGLE_API_KEY="your-gemini-api-key" `
  -p 8000:8000 `
  investor-paradise
```

Access at: `http://localhost:8000`

> Note: The Docker image downloads NSE stock data (~1.5GB) from GitHub releases during build. This is a one-time download cached in the image. Build time is typically 5–10 minutes depending on internet speed.

##### Docker Troubleshooting (Windows)

- If you see errors like `dockerDesktopLinuxEngine: The system cannot find the file specified`:
  - Start **Docker Desktop** from the Start menu
  - Wait for the Docker icon in the system tray to become steady
  - Run `docker version` and ensure both Client and Server respond
- If the site does not load:
  - Confirm the container is running: `docker ps`
  - Make sure you are mapping the correct ports: use `-p 8000:8000` (or `-p 8001:8000`)
  - Open your browser to the local port you mapped (e.g. `http://localhost:8000`)

---

### Option 2: GitHub Codespaces (Browser-Based)

1. On GitHub, click **Code → Codespaces → Create codespace** on the main branch
2. Wait for the environment to load
3. Add your API key in the terminal:

   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
   ```

4. Run the ADK web server:

   ```bash
   uv run adk web . --port=8000 --host=0.0.0.0
   ```

5. When VS Code prompts for forwarded ports, open the forwarded **8000** URL in the browser.

---

### Option 3: Local Python Setup (uv Recommended)

#### Prerequisites (Local Python)

- Python **3.11+**
- `uv` package manager (https://docs.astral.sh/uv/)
- Google Gemini API key

#### 1. Clone and create environment

```bash
git clone https://github.com/atulkumar2/investor_paradise.git
cd investor_paradise

# Create and sync environment using uv
uv sync
```

(If you prefer `pip`, you can instead create a virtualenv and run `pip install -e .`.)

#### 2. Configure API Key

Create a `.env` file in the project root:

```bash
GOOGLE_API_KEY=your-api-key-here
```

Or export it directly:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

#### 3. Run ADK Web UI

Serve all agents defined in the project (default):

```bash
uv run adk web . --port=8000 --host=0.0.0.0
```

Or serve only the `investor_agent` package:

```bash
uv run adk web investor_agent --port=8000 --host=0.0.0.0
```

Minimal CLI demo (if you add a CLI entry such as `cli.py`):

```bash
uv run python cli.py
```

#### 4. Access the UI

Open your browser to:

- `http://localhost:8000`

The web UI provides:

- Interactive chat interface
- API key configuration in **Settings** (if not using `.env`)
- Session history and traces

---

## Setting API Key in ADK Web UI

If you did not set `GOOGLE_API_KEY` via `.env` or environment variable, you can configure it in the web UI:

1. Open the web UI
2. Click the **Settings** (gear) icon in the top-right
3. Go to **Providers → Google (Gemini)**
4. Paste your API key
5. Click **Save**

All Gemini calls from the agent will now use this key.

---

## Docker Deployment (Portable)

You can also treat Docker as a portable artifact:

```bash
# Build on any machine with Docker
docker build -t investor-paradise .

# Run anywhere that can pull the image
docker run --rm \
  -e GOOGLE_API_KEY="your-api-key-here" \
  -p 8000:8000 \
  investor-paradise
```

Access at: `http://localhost:8000`.

To access from a different machine (e.g. Windows → Linux server):

- Use the server's IP address instead of `localhost`, e.g. `http://192.168.x.x:8000`.

---

## Cloud Deployment Options (Advanced)

### GitHub Codespaces (Zero Local Setup)

1. Open this repo in Codespaces
2. Add `GOOGLE_API_KEY` as a Codespace secret
3. Run:

   ```bash
   adk web . --port=8000 --host=0.0.0.0
   ```

4. Open the forwarded port URL

### Railway / Render / Fly.io

1. Connect your GitHub repo
2. Set `GOOGLE_API_KEY` as an environment variable
3. Use the start command:

   ```bash
   adk web . --port=8000 --host=0.0.0.0
   ```

4. Deploy

### Hugging Face Spaces (Custom UI)

If you want a custom Gradio/Streamlit UI:

- Add an `app.py` that wraps the `root_agent` from `investor_agent.agent`
- Deploy to Hugging Face Spaces

---

## Sample Queries to Test

Once the agent is running, try queries like:

- "What are the top 5 banking stocks based on last month's trend?"
- "Analyze RELIANCE stock for the last 3 months"
- "Show me IT sector gainers in the last 2 weeks"
- "Compare TCS vs INFY vs WIPRO"
- "Find stocks with high delivery percentage and positive momentum"

---

## Troubleshooting

### Import Error / Module Not Found

```bash
# Reinstall in editable mode
pip install -e .
```

### SSL / Network Issues

The agent relies on external APIs and NSE data. If you see SSL or network errors, re-check your network, proxies, and certificates.

### Data Not Loading

- First run may take a few seconds while NSE data is preloaded
- Subsequent runs use cached/parquet data for faster startup

### API Key Not Found

Ensure **one** of the following:

- `.env` file exists with `GOOGLE_API_KEY=...`
- Environment variable is set before running
- Key is configured via the ADK Web UI Settings

---

## Architecture (High Level)

- **Entry Router**: Routes queries to stock analysis vs general responses
- **Market Analyst**: Uses multiple tools (price, volume, momentum, risk) over NSE data
- **News Analyst (Optional)**: Fetches news context for discovered stocks
- **CIO Synthesizer**: Combines market + news insights into a final recommendation

Data source: NSE stock data (2020–2025, 2300+ symbols).

---

## Cost Estimates (Gemini)

Using Gemini Flash Lite (default config):

- ~\$0.001 per typical query
- Free tier: up to 1500 requests/day

Upgrading to Gemini Pro (if configured in `agent.py`):

- ~\$0.01 per complex query
- Better for multi-step reasoning

---

## Support

For issues or questions:

- Check logs (e.g. `investor_agent_logger.log`)
- Run with more logging via ADK flags (e.g. `--verbose`)
- Open an issue on GitHub: https://github.com/atulkumar2/investor_paradise/issues
