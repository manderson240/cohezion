FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install dependencies
RUN uv sync --frozen

# Expose API port
EXPOSE 8080

# Run FastAPI server
CMD ["uv", "run", "uvicorn", "cohezion.api.main:app", "--host", "0.0.0.0", "--port", "8080"]