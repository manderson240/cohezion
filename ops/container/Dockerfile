# Multi-stage build for Size Optimization
FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./

# Inject strict CPU-only source to prevent NVIDIA lib leak
RUN echo '\n[[tool.uv.index]]\nname = "pytorch-cpu"\nurl = "https://download.pytorch.org/whl/cpu"\nexplicit = true\n\n[tool.uv.sources]\ntorch = { index = "pytorch-cpu" }' >> pyproject.toml

# Install dependencies into a virtual environment
RUN uv sync --no-cache --no-dev --index-strategy unsafe-best-match

# Final stage
FROM python:3.13-slim-bookworm

WORKDIR /app

# Copy the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv
# Copy source code and assets
# Copy application code (Force cache invalidation)
ARG CACHEBUST=1
COPY src/ src/
COPY webapp/src/logo.png src/cohezion/api/static/logo.png
COPY overnight_driver.py .
COPY creative_driver.py .
COPY linguistic_driver.py .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Default port for Cloud Run
ENV PORT=8080

CMD ["sh", "-c", "uvicorn cohezion.api:app --host 0.0.0.0 --port ${PORT}"]
