---
title: Operational Runbook - Ollama MCP Server
date: 2026-02-10
status: active
tags: [runbook, operations, ollama, infrastructure]
aspect: thinker
neural:
  activation: 0.88
  stage: mature
  synapse_in: 0
  synapse_out: 11
---

## Overview

This runbook covers operational tasks for the Ollama MCP server that bridges Claude Code IDE to local Ollama inference service.

**Key Components:**
- Ollama MCP Server (Port stdio, MCP protocol)
- Ollama Service (Port 11434, HTTP)
- Cloud Vault MCP (Port 8360, HTTP) - calls Ollama MCP tools
- 28+ language models loaded in Ollama

## Starting the Ollama Service

### Quick Start
```bash
# Start Ollama service in background
ollama serve &

# Verify it's running
curl http://localhost:11434/api/tags | jq '.models | length'
# Expected output: 28 or similar (number of loaded models)
```

### With Systemd (Production)
```bash
# Enable Ollama as systemd service (if installed via package manager)
sudo systemctl enable ollama
sudo systemctl start ollama

# Check status
sudo systemctl status ollama

# View logs
sudo journalctl -u ollama -n 50 -f
```

### Verify Service Health
```bash
# List loaded models
curl http://localhost:11434/api/tags

# Test inference
curl http://localhost:11434/api/generate \
  -d '{"model": "qwen3:8b", "prompt": "Hello", "stream": false}' | jq '.response'
```

## Starting the Ollama MCP Server

### Prerequisites
```bash
# Verify Python environment
/home/mike-anderson/dev/cohezion/ollama-mcp/.venv/bin/python3 --version
# Expected: Python 3.11+

# Verify dependencies installed
cd /home/mike-anderson/dev/cohezion/ollama-mcp
source .venv/bin/activate
pip list | grep -E "requests|pydantic|mcp"
```

### Start MCP Server
```bash
cd /home/mike-anderson/dev/cohezion/ollama-mcp

# Via MCP config (automatic, configured in ~/.claude/mcp.json)
# The server starts when Claude Code connects

# Manual start for debugging
/home/mike-anderson/dev/cohezion/ollama-mcp/.venv/bin/python3 -m mcp_server.server
```

### Verify MCP Server via Cloud Vault
```bash
# Test through Cloud Vault MCP (which calls Ollama MCP tools)
curl http://localhost:8360/health | jq '.checks.ollama_mcp'

# Expected output:
# {
#   "status": "healthy",
#   "details": "Ollama MCP server responding"
# }
```

## Adding New Models to Selection Logic

### Current Model Selection Strategy
The Ollama MCP server auto-selects models based on:
1. Task type (e.g., `query`, `embed`)
2. Content length (short: 8B models, medium: 14B, long: 256K context)
3. Model availability

**Model Pool (as of 2026-02-10):**
- Short queries (8B): `qwen3:8b`, `deepseek-r1:7b`
- Medium (14B): `qwen2.5-coder:14b`, `phi4:latest`
- Long context (256K): `phi4-256k:latest`
- Embeddings: `nomic-embed-text:latest`

### Add New Model to Ollama Service
```bash
# Download model from Ollama registry
ollama pull model-name:version

# Example: Add Llama 3.2
ollama pull llama3.2:latest

# Verify it loaded
curl http://localhost:11434/api/tags | jq '.models[] | select(.name | contains("llama"))'
```

### Update Model Selection Logic
Edit: `/home/mike-anderson/dev/cohezion/ollama-mcp/src/mcp_server/ollama_client.py`

```python
# In OllamaClient.select_model() method
def select_model(self, task_type: str, content_length: int) -> str:
    """
    Select appropriate model based on task and content length.

    Update model pool here when adding new models.
    """
    if task_type == "embed":
        return "nomic-embed-text:latest"

    if content_length > 100000:  # Long context
        return "phi4-256k:latest"
    elif content_length > 10000:  # Medium
        return "qwen2.5-coder:14b"  # <-- Update this line
    else:  # Short
        return "qwen3:8b"
```

After editing, rebuild and restart:
```bash
cd /home/mike-anderson/dev/cohezion/ollama-mcp
pip install -e .
# Restart Claude Code to reload MCP server
```

## Monitoring Model Loading

### Check Model Status
```bash
# List all loaded models with details
curl http://localhost:11434/api/tags | jq '.models[] | {name, size: .size_bytes}'

# Check model details
curl http://localhost:11434/api/show -d '{"name": "qwen3:8b"}' | jq '{model, size, digest, details}'
```

### Monitor Model Loading Progress
```bash
# Pull model with progress output
ollama pull qwen3:8b

# Output shows: [=========>  ] 45.2 GB / 50.1 GB
```

## Debugging Model Loading Failures

### Symptom: "Model not found"
```bash
# Verify model is actually loaded
curl http://localhost:11434/api/tags | jq '.models[].name'

# If missing, pull it
ollama pull model-name:tag

# Verify again
curl http://localhost:11434/api/tags | jq '.models[] | select(.name | contains("model-name"))'
```

### Symptom: "Ollama service timeout"
```bash
# Check if service is running
curl http://localhost:11434/api/tags
# If no response after 10 seconds: service is hung

# Check system resources
free -h  # Memory available
df -h    # Disk space (Ollama models are large)

# Restart service
pkill ollama
sleep 2
ollama serve &
```

### Symptom: "Out of memory" errors
```bash
# Check current model usage
curl http://localhost:11434/api/tags | jq '.models | length'
free -h

# If models > 4 and memory < 8GB: unload unused models
ollama rm model-name:tag

# Or restart with smaller model pool
pkill ollama
ollama serve &  # Will reload last used model
```

### Symptom: "Model inference is very slow"
```bash
# Check if model is in memory (loaded)
curl http://localhost:11434/api/show -d '{"name": "qwen3:8b"}' | jq '.model_info'

# First inference loads model to GPU (slow)
# Subsequent inferences are fast (in memory)

# Check GPU availability
nvidia-smi  # If NVIDIA GPU available
# or
lspci | grep -i gpu
```

## Troubleshooting: "Why is Ollama slow?"

### Checklist

1. **Is model loaded in GPU memory?**
   ```bash
   # First call to a model is slow (loading GPU memory)
   # Subsequent calls are fast (already loaded)
   curl http://localhost:11434/api/generate \
     -d '{"model": "qwen3:8b", "prompt": "Hi", "stream": false}' \
     --write-out '\nTime: %{time_total}s\n'
   # Expected first call: 5-15 seconds (loading)
   # Expected subsequent: 1-3 seconds (inference only)
   ```

2. **Is CPU falling back due to no GPU?**
   ```bash
   # Check if GPU is available
   nvidia-smi
   # If no GPU: inference will be 10-100x slower
   # Install NVIDIA driver: https://docs.ollama.ai/ollama/gpu
   ```

3. **Is model too large for system memory?**
   ```bash
   # Check model size vs available memory
   curl http://localhost:11434/api/tags | jq '.models[] | {name, bytes: .size_bytes}'
   free -h

   # Rule of thumb: model size should be < 50% RAM
   # Example: 7B model ≈ 14GB, needs 16GB+ RAM
   ```

4. **Are other processes consuming resources?**
   ```bash
   top -b -n 1 | head -20
   # Check if CPU/memory are saturated
   # Kill unnecessary processes
   ```

5. **Is there network latency?**
   ```bash
   # Verify localhost is reachable
   ping localhost
   curl http://localhost:11434/api/tags
   ```

### Performance Optimization Tips

**For faster inference:**
- Use smaller models (7B-8B) for most tasks
- Use quantized models (4-bit, 5-bit) for reduced VRAM
- Keep only 2-3 models loaded at a time
- Increase context length for batch processing

**For faster model loading:**
- Keep frequently used models in GPU memory
- Pre-load models at service startup
- Use SSD for model storage (not HDD)

**Monitor baseline performance:**
```bash
# Establish baseline (run this weekly)
time curl http://localhost:11434/api/generate \
  -d '{"model": "qwen3:8b", "prompt": "test", "stream": false}' > /dev/null

# Expected: ~2-3 seconds for warm inference
```

## Health Check Integration

The `/health` endpoint includes Ollama checks:

```bash
curl http://localhost:8360/health | jq '.checks'

# Expected:
{
  "ollama_service": {
    "status": "healthy",
    "response_time_ms": 45
  },
  "ollama_mcp": {
    "status": "healthy",
    "models_available": 28
  }
}
```

If Ollama checks fail:
1. Verify `ollama serve` is running: `curl http://localhost:11434/api/tags`
2. Restart Ollama service
3. Check logs: `journalctl -u ollama -n 20`

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| Connection refused (Port 11434) | Ollama not running | `ollama serve &` |
| "Model not found" | Model not pulled | `ollama pull model-name` |
| Timeout (30s+) | Service hung or OOM | Restart: `pkill ollama; ollama serve &` |
| Memory error | Insufficient RAM | Reduce model pool or add RAM |
| GPU error | NVIDIA not installed | Install NVIDIA driver |
| Very slow inference | CPU fallback | Install GPU driver or use smaller model |

## Maintenance Schedule

### Daily
- Monitor health check: `curl http://localhost:8360/health`
- Check for Ollama service crashes: `systemctl status ollama`

### Weekly
- Capture performance baseline (see above)
- Review model loading statistics: `curl http://localhost:11434/api/tags`
- Clean up unused models: `ollama rm old-model:tag`

### Monthly
- Review and optimize model selection logic
- Update to latest Ollama release: `ollama --version`
- Audit model library for deprecated models

## Related Documentation
- [[2026-02-10-phase-a-implementation-complete]]
- [[runbook-health-checks]]
- [[troubleshooting-mcp-infrastructure]]
- [[mcp-infrastructure-architecture]]

## Related Concepts

- [[2026-02-09-ollama-context-management]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-10-compound-node-linking-plan]]
- [[2026-02-10-phase-a-implementation-complete]]
- [[runbook-entire-sync-daemon]]
- [[phase1-production-validation-runbook]]
- [[runbook-benchmarking-validation]]
