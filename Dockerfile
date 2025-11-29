# Minimal Dockerfile for investor_paradise
# Builds a small image with the CLI and ADK web app available.

FROM python:3.11-slim


# Install system deps (if any are needed later, add here)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         build-essential \
         curl \
         unzip \
         git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reproducible Python builds
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY investor_agent ./investor_agent

# Install dependencies
RUN uv sync --frozen

# Ensure data directories exist for vector/semantic search and cached support data
RUN mkdir -p investor_agent/data/vector-data \
    && mkdir -p investor_agent/data/cache \
    && mkdir -p /tmp/nse_tmp

# 1) Download Parquet cache into cache folder
RUN curl -L "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/combined_data.parquet" \
         -o investor_agent/data/cache/combined_data.parquet

# 2) Download and unpack NSE support ZIP into data folder
RUN curl -L "https://github.com/atulkumar2/investor_agent_data/releases/download/nse_support_data_20251128/nse_support_data_20251128.zip" \
         -o /tmp/nse_tmp/support.zip \
    && unzip /tmp/nse_tmp/support.zip -d /tmp/nse_tmp/unpacked \
    && cp -r /tmp/nse_tmp/unpacked/. investor_agent/data/ \
    && rm -rf /tmp/nse_tmp

# Install project (no dev extras) using uv
RUN uv venv /opt/venv \
    && . /opt/venv/bin/activate \
    && uv pip install --no-cache .

ENV PATH="/opt/venv/bin:${PATH}"

# Default environment
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Expose default ADK web port
EXPOSE 8000

# Run ADK web server
CMD ["uv", "run", "adk", "web", ".", "--port=8000", "--host=0.0.0.0"]
