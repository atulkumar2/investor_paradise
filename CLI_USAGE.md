# PyPI CLI Installation Guide - Using UV

This guide explains how to install and use Investor Paradise CLI from PyPI using `uv` (the fast Python package manager).

## Prerequisites

- Python 3.11 or higher
- Google API Key ([Get one here](https://aistudio.google.com/app/apikey))

## Step 1: Install UV

`uv` is a fast Python package installer and resolver written in Rust.

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (using pip):**
```bash
pip install uv
```

Verify installation:
```bash
uv --version
```

## Step 2: Install Google ADK (Pre-requisite)

**Important:** You must install Google ADK from GitHub first, as it's a required dependency.

```bash
uv pip install "google-adk[eval] @ git+https://github.com/google/adk-python/"
```

This will:
- Clone and install Google ADK from GitHub
- Set up all required dependencies

## Step 3: Install Investor Paradise CLI

### Method 1: Using `uv tool install` (Recommended - Simplest)

```bash
uv tool install investor-paradise-cli
```

This is the easiest method:
- Installs the CLI globally in an isolated environment
- Automatically adds to PATH (accessible from anywhere)
- No need to activate virtual environments
- Just run `investor-paradise-cli` from any directory

**From GitHub (Latest Development):**
```bash
uv tool install git+https://github.com/atulkumar2/investor_paradise.git
```

### Method 2: Using `uv pip install` (Works Anywhere)

```bash
uv pip install investor-paradise-cli
```

**From TestPyPI (Development/Testing):**
```bash
uv pip install --index-url https://test.pypi.org/simple/ investor-paradise-cli
```

**From GitHub (Latest Development):**
```bash
uv pip install git+https://github.com/atulkumar2/investor_paradise.git
```

### Method 3: Using `uv add` (For Project-Based Setup)

**Note:** This method requires you to be in a project directory with `pyproject.toml`.

First, create a project:
```bash
# Create a new directory for your analysis work
mkdir my-stock-analysis
cd my-stock-analysis

# Initialize a uv project
uv init
```

Then add the dependencies:
```bash
# Add Google ADK
uv add "google-adk @ git+https://github.com/google/adk-python/"

# Add Investor Paradise CLI
uv add investor-paradise-cli
```

This automatically:
- Installs the package in your project
- Updates `pyproject.toml` with the dependency
- Resolves and locks dependencies in `uv.lock`

## Step 4: Add CLI to PATH (Optional - Only for Method 2)

**Note:** Skip this step if you used Method 1 (`uv tool install`) - it already adds to PATH automatically!

If you used `uv pip install` and want to run `investor-paradise-cli` from anywhere:

### Manual PATH Setup

**macOS/Linux (bash):**
```bash
# Add to ~/.bashrc or ~/.bash_profile
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**macOS (zsh):**
```bash
# Add to ~/.zshrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Windows (PowerShell):**
```powershell
# Add to PowerShell profile
$profilePath = $PROFILE
if (!(Test-Path -Path $profilePath)) {
    New-Item -ItemType File -Path $profilePath -Force
}
Add-Content -Path $profilePath -Value '$env:PATH += ";$env:USERPROFILE\.local\bin"'
```

**Windows (Command Prompt):**
1. Open System Properties → Environment Variables
2. Under User Variables, find `Path`
3. Click Edit → New
4. Add: `%USERPROFILE%\.local\bin`
5. Click OK to save

After adding to PATH, verify:
```bash
which investor-paradise-cli  # macOS/Linux
where investor-paradise-cli  # Windows
```

## Step 5: Set Up Your API Key

The CLI needs a Google API key to function. You have multiple options:

### Option 1: Let the CLI Prompt You (Recommended - Easiest)

Simply start the CLI without setting up the API key:

```bash
investor-paradise-cli
```

The CLI will:
1. Detect that no API key is configured
2. Prompt you to enter your Google API key
3. Securely store it in your system's credential manager:
   - **Windows:** Windows Credential Manager
   - **macOS:** Keychain
   - **Linux:** Secret Service (gnome-keyring, kwallet, or similar)

You only need to do this once - the key will be remembered for future sessions.

### Option 2: Environment Variable

**macOS/Linux:**
```bash
export GOOGLE_API_KEY="your_google_api_key_here"
```

**Windows (PowerShell):**
```powershell
$env:GOOGLE_API_KEY="your_google_api_key_here"
```

**Windows (Command Prompt):**
```cmd
set GOOGLE_API_KEY=your_google_api_key_here
```

### Option 3: .env File

Create a `.env` file in your working directory:
```bash
echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
```

## Step 6: Run the CLI

### If Using Method 1 (`uv tool install`)

Simply run from anywhere:
```bash
investor-paradise-cli
```

### If Using Method 2 (`uv pip install`)

```bash
investor-paradise-cli
```

Or with uv:
```bash
uv run investor-paradise-cli
```

### If Using Method 3 (Project setup with `uv add`)

From your project directory:
```bash
uv run investor-paradise-cli
```

## First Run Experience

On the first launch, the CLI will:

1. **Check API Key:** Prompt for Google API key if not found
2. **Check Data Files:** Look for market data cache and news vector data
3. **Download Data (if needed):**
   - NSE market data cache (2019-2025) - ~50MB, takes about 1 minute
   - Economic Times news articles (last 6 months) - ~580MB download, ~1.2GB disk space after extraction, takes a few minutes
4. **Load Data:** Load the market data into memory (~10-20 seconds)
5. **Ready!** Start asking questions

**Example First Run:**
```
🚀 Initializing Investor Paradise...

📦 Checking if latest market data parquet cache and Economic Times news vector data is available...

⚠️  Starting download of latest NSE market data cache (2019-2025)
📊 This could take a minute (size ~50MB)

Downloading combined_data.parquet ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 50.9/50.9 MB
✅ All cache files downloaded successfully!

⚠️  Starting download of Economic Times news articles (last 6 months)
📰 This could take a few minutes (download ~580MB, disk space ~1.2GB after extraction)

Downloading 202506.zip ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Extracting 202506.zip...
✅ Extracted and cleaned up 202506.zip
...
✅ All vector data files downloaded and extracted successfully!

📂 Loading NSE stock data...
✅ Data loaded: 2,797,728 rows
📅 Database Context: 2019-10-01 to 2025-11-28

💬 Ready! Ask me about NSE stocks or just say hi!
Session: 3a7f8b2c... | Commands: 'exit', 'clear', 'switch'

💭 You:
```

## Step 5: Start Using the CLI

### Example Queries

```bash
💭 You: Show me top 5 performing stocks in the last month

💭 You: What are the latest news about Reliance Industries?

💭 You: Analyze TCS stock performance

💭 You: Compare HDFC Bank and ICICI Bank

💭 You: exit
```

## CLI Commands

### Session Management

- **`switch`** - Change to a different session or create new one
- **`clear`** - Clear current session history and start fresh
- **`exit`**, **`quit`**, **`bye`** - Exit the application

### Command-Line Flags

```bash
# Show help
uv run investor-paradise-cli --help

# Reset stored API key
uv run investor-paradise-cli --reset-api-key

# Refresh cache data
uv run investor-paradise-cli --refresh-cache

# Download vector data manually
uv run investor-paradise-cli --download-vector-data
```

## Using UV Virtual Environments

For isolated project setup with full dependency management:

```bash
# Create a new project directory
mkdir my-stock-analysis
cd my-stock-analysis

# Initialize UV project
uv init

# Add Google ADK (pre-requisite)
uv add "google-adk[eval] @ git+https://github.com/google/adk-python/"

# Add Investor Paradise CLI
uv add investor-paradise-cli

# Run the CLI
uv run investor-paradise-cli
```

This approach:
- Creates isolated environment per project
- Manages dependencies in `pyproject.toml`
- Locks versions in `uv.lock` for reproducibility
- Best for development and team projects

## Advanced Usage: Using as Python Library

```python
# Create a script: analyze.py
import asyncio
from investor_agent.data_engine import NSESTORE

async def analyze_stock():
    # Load data
    df = NSESTORE.df
    print(f"Loaded {len(df):,} rows")
    
    # Get specific stock data
    stock_data = NSESTORE.get_stock_data("TCS", start_date="2024-01-01")
    print(stock_data.head())

asyncio.run(analyze_stock())
```

Run with uv:
```bash
uv run analyze.py
```

## Data Storage Locations

By default, data is stored in:
```
<project-root>/
└── investor_agent/
    └── data/
        ├── cache/                          # Market data parquet files
        │   ├── combined_data.parquet
        │   ├── nse_indices_cache.parquet
        │   ├── nse_sector_cache.parquet
        │   └── nse_symbol_company_mapping.parquet
        ├── vector-data/                    # News articles by month
        │   ├── 202506/
        │   ├── 202507/
        │   ├── 202508/
        │   ├── 202509/
        │   ├── 202510/
        │   └── 202511/
        └── investor_agent_sessions.db      # Session history
```

## Quick Start Summary

### Simplest Installation (Recommended for Most Users)

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install Google ADK (pre-requisite)
uv pip install "google-adk[eval] @ git+https://github.com/google/adk-python/"

# 3. Install Investor Paradise CLI globally
uv tool install investor-paradise-cli

# 4. Run the CLI from anywhere (it will prompt for API key on first run)
investor-paradise-cli
```

### Alternative: Using uv pip install

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install Google ADK (pre-requisite)
uv pip install "google-adk[eval] @ git+https://github.com/google/adk-python/"

# 3. Install Investor Paradise CLI
uv pip install investor-paradise-cli

# 4. Run the CLI
investor-paradise-cli
```

### Project-Based Installation (For Development)

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create and initialize project
mkdir my-stock-analysis && cd my-stock-analysis && uv init

# 3. Install Google ADK (pre-requisite)
uv add "google-adk[eval] @ git+https://github.com/google/adk-python/"

# 4. Install Investor Paradise CLI
uv add investor-paradise-cli

# 5. Run the CLI
uv run investor-paradise-cli
```

That's it! The CLI will guide you through API key setup and data downloads on first run.

## Troubleshooting

### UV Installation Issues

**Problem:** `uv: command not found`

**Solution:**
```bash
# Reload your shell configuration
source ~/.bashrc  # or ~/.zshrc on macOS

# Or install via pip
pip install uv
```

### Package Installation Issues

**Problem:** Installation fails with dependency conflicts

**Solution:**
```bash
# Use fresh virtual environment
uv venv --python 3.11
source .venv/bin/activate
uv pip install "google-adk[eval] @ git+https://github.com/google/adk-python/"
uv pip install investor-paradise-cli
```

**Problem:** Google ADK not found

**Solution:**
```bash
# Make sure to install Google ADK first (it's a pre-requisite)
uv add "google-adk[eval] @ git+https://github.com/google/adk-python/"
# Then install the CLI
uv add investor-paradise-cli
```

### API Key Not Found

**Problem:** "GOOGLE_API_KEY not found" error

**Solution:**
1. Run with `--reset-api-key` flag to re-enter your key
2. Or set environment variable before running

```bash
export GOOGLE_API_KEY="your_key_here"
uv run investor-paradise-cli
```

### Data Download Issues

**Problem:** Download fails or times out

**Solution:**
```bash
# Retry with refresh flag
uv run investor-paradise-cli --refresh-cache

# For vector data specifically
uv run investor-paradise-cli --download-vector-data
```

### Slow Performance

**Problem:** CLI is slow or unresponsive

**Solutions:**
- First query is always slower (data loads into memory)
- Ensure you have at least 2GB free RAM
- Check internet connection for API calls
- Use specific date ranges in queries for faster results

## Updating the CLI

### Check Current Version

```bash
uv pip show investor-paradise-cli
```

### Update to Latest

```bash
uv pip install --upgrade investor-paradise-cli
```

### Reinstall from Scratch

```bash
uv pip uninstall investor-paradise-cli
uv pip install investor-paradise-cli
```

## System Requirements

- **Python:** 3.11 or higher
- **RAM:** Minimum 2GB free, Recommended 4GB
- **Disk Space:** 
  - ~50MB for market data cache
  - ~1.2GB for news vector data (6 months)
  - Total: ~1.3GB
- **Network:** Required for:
  - Initial data download
  - Google API calls during queries
  - News fetching (optional)

## Performance Tips

1. **First launch takes longer:** Data downloads and loads (~5-10 minutes first time)
2. **Subsequent launches are fast:** Data is cached locally
3. **Keep sessions:** Previous conversations are saved, use `switch` to resume
4. **Clear when needed:** Use `clear` command to reset context if confused
5. **Specific queries:** More specific = faster and better results

## Data Coverage

- **Stocks:** 2000+ NSE-listed companies
- **Date Range:** October 2019 - November 2025
- **Data Points:** OHLCV (Open, High, Low, Close, Volume)
- **News:** Economic Times articles (last 6 months, embedded for RAG)
- **Updates:** Manual refresh with `--refresh-cache`

## Uninstallation

```bash
# Uninstall package
uv pip uninstall investor-paradise-cli

# Remove data (optional)
rm -rf investor_agent/data/
```

## Quick Reference

```bash
# Simplest Installation (Recommended)
uv pip install "google-adk[eval] @ git+https://github.com/google/adk-python/"
uv tool install investor-paradise-cli
investor-paradise-cli

# Alternative: Using uv pip
uv pip install "google-adk[eval] @ git+https://github.com/google/adk-python/"
uv pip install investor-paradise-cli
investor-paradise-cli

# Project-Based Installation
mkdir my-stock-analysis && cd my-stock-analysis
uv init
uv add "google-adk[eval] @ git+https://github.com/google/adk-python/"
uv add investor-paradise-cli
uv run investor-paradise-cli

# Commands within CLI
exit          # Exit application
clear         # Clear session history
switch        # Switch/create session

# Command-line flags
--help                    # Show help
--reset-api-key          # Reset API key
--refresh-cache          # Refresh market data
--download-vector-data   # Download news data
```

## Support & Resources

- **GitHub:** https://github.com/atulkumar2/investor_paradise
- **Issues:** https://github.com/atulkumar2/investor_paradise/issues
- **PyPI:** https://pypi.org/project/investor-paradise-cli/
- **UV Docs:** https://docs.astral.sh/uv/
