# Investor Paradise - ADK Web Deployment
FROM python:3.11-slim

# Install uv for fast dependency management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY investor_agent/ ./investor_agent/
COPY conversations/ ./conversations/
COPY data/ ./data/
COPY .env.example ./.env.example

# Install dependencies
RUN uv sync --frozen

# Preload NSE data to parquet cache (speeds up first query)
RUN uv run python -c "from investor_agent.data_engine import NSESTORE; _ = NSESTORE.df; print('✅ Data preloaded to cache')"

# Expose ADK web port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run ADK web server
CMD ["uv", "run", "adk", "web", ".", "--port=8000", "--host=0.0.0.0"]
