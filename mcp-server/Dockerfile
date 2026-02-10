# Kyutai MCP Server - Phase 1 MVP (Pocket TTS only)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Pocket TTS
RUN pip install --no-cache-dir pocket-tts

# Copy source code
COPY src/ /app/src/

# Create directories for configuration and audio output
RUN mkdir -p /root/.kyutai-mcp/voices && \
    mkdir -p /tmp/kyutai-audio

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV KYUTAI_CONFIG=/root/.kyutai-mcp/config.yaml
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8361
ENV MCP_LOG_LEVEL=info

# Expose MCP port
EXPOSE 8361

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8361/health')" || exit 1

# Run MCP server
CMD ["python", "-m", "kyutai_mcp.main", "--host", "0.0.0.0"]
