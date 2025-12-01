# ============================================================================
# Investor Paradise - ADK Web Server
# Optimized Docker Image for Web Interface
# ============================================================================

FROM python:3.11-slim

WORKDIR /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gcc \
    git \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install "uv>=0.4,<1.0"

# Copy application code FIRST (needed for editable install)
COPY investor_agent/ ./investor_agent/
COPY cli.py cli_helpers.py spinner.py ./

# Copy and install dependencies
COPY pyproject.toml uv.lock* .python-version ./
RUN uv sync --frozen || uv sync

# Create data directories
RUN mkdir -p ./investor_agent/data/cache \
             ./investor_agent/data/NSE_RawData \
             ./investor_agent/data/NSE_indices_list \
             ./investor_agent/data/vector-data

# Download NSE parquet caches
RUN echo "📦 Downloading NSE data caches..." && \
    curl -fL https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/combined_data.parquet \
    -o ./investor_agent/data/cache/combined_data.parquet && \
    curl -fL https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_indices_cache.parquet \
    -o ./investor_agent/data/cache/nse_indices_cache.parquet && \
    curl -fL https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_sector_cache.parquet \
    -o ./investor_agent/data/cache/nse_sector_cache.parquet && \
    curl -fL https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_symbol_company_mapping.parquet \
    -o ./investor_agent/data/cache/nse_symbol_company_mapping.parquet && \
    echo "✅ All caches downloaded"

# Download News store
RUN echo "📦 Downloading all News store archives..." && \
    for MONTH in 202511 202510 202509; do \
        echo "➡️  Processing $MONTH" && \
        curl -fL https://github.com/atulkumar2/investoragentdata_news1/releases/download/newsdata_202511/$MONTH.zip \
            -o ./investor_agent/data/vector-data/$MONTH.zip && \
        unzip -o ./investor_agent/data/vector-data/$MONTH.zip -d ./investor_agent/data/vector-data/ && \
        rm ./investor_agent/data/vector-data/$MONTH.zip; \
    done && \
    echo "🎉 News store archives processed successfully for 202509, 202510, 202511"

RUN echo "📦 Downloading all News store archives..." && \
    for MONTH in 202506 202507 202508; do \
        echo "➡️  Processing $MONTH" && \
        curl -fL https://github.com/atulkumar2/investoragentdata_news1/releases/download/newsdata_202506_202508/$MONTH.zip \
            -o ./investor_agent/data/vector-data/$MONTH.zip && \
        unzip -o ./investor_agent/data/vector-data/$MONTH.zip -d ./investor_agent/data/vector-data/ && \
        rm ./investor_agent/data/vector-data/$MONTH.zip; \
    done && \
    echo "🎉 News store archives processed successfully for 202506, 202507, 202508"

# Remove build dependencies to reduce image size
RUN apt-get purge -y --auto-remove unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* \
           *.egg-info \
           .eggs \
           build \
           dist

# Expose web port
EXPOSE 8000

# Run ADK web server with DatabaseSessionService
CMD ["sh", "-c", "uv run adk web . --session_service_uri='sqlite+aiosqlite:///investor_agent/data/sessions.db' --port=8000 --host=0.0.0.0"]
