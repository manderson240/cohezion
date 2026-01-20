FROM python:3.13-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (frozen)
RUN uv sync --frozen --no-cache

# Copy source code
COPY src/ src/
COPY overnight_driver.py .
COPY creative_driver.py .
COPY linguistic_driver.py .

# Environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Default command (API)
CMD ["uv", "run", "uvicorn", "cohezion.api:app", "--host", "0.0.0.0", "--port", "8080"]
