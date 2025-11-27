# Investor Paradise - ADK Web Deployment
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY investor_agent/ ./investor_agent/
COPY conversations/ ./conversations/
COPY .env.example ./.env.example

# Install dependencies
RUN uv sync --frozen

# Download NSE data from GitHub Release
RUN mkdir -p ./data && \
    echo "📦 Downloading NSE data from GitHub Release..." && \
    curl -L https://github.com/atulkumar2/investor_paradise/releases/download/v1.0-data/nse-data.tar.gz \
    -o nse-data.tar.gz && \
    echo "📂 Extracting data..." && \
    tar -xzf nse-data.tar.gz && \
    rm nse-data.tar.gz && \
    echo "✅ Data downloaded and extracted"

# Preload NSE data to parquet cache (speeds up first query)
RUN uv run python -c "from investor_agent.data_engine import NSESTORE; _ = NSESTORE.df; print('✅ Data preloaded to cache')"

# Expose ADK web port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run ADK web server
CMD ["uv", "run", "adk", "web", ".", "--port=8000", "--host=0.0.0.0"]
