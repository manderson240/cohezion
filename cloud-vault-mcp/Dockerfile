FROM python:3.12-slim

WORKDIR /app

# Install git for vault operations
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir .

# Create non-root user
RUN useradd --create-home --shell /bin/bash mcp && \
    mkdir -p /vault && \
    chown mcp:mcp /vault

USER mcp

# Listen on all interfaces inside the container; MCP_API_KEY is required at start.
ENV MCP_HOST=0.0.0.0
EXPOSE 8360

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8360/health')" || exit 1

CMD ["cloud-vault-mcp"]
