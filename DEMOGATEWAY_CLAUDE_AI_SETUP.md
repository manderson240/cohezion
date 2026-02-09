# DemoGateway + Claude.ai Setup (5 minutes - NO API KEYS)

## What You Get

✅ **Multi-model AI routing** in Claude.ai
✅ **Zero external dependencies** - uses local Ollama
✅ **No API keys needed** - completely self-contained
✅ **Cost tracking** - simulated pricing for demo
✅ **Performance metrics** - request tracking and throughput

## Prerequisites

1. **Ollama running locally** (should have these models):
   ```bash
   ollama pull qwen3-coder:30b    # Fast, coding-focused
   ollama pull deepseek-r1:70b    # Powerful reasoning
   ollama pull phi3:mini           # Lightweight
   ```

2. **Local MCP HTTP server** running on port 5000

## Quick Start

### Step 1: Start the MCP HTTP Server (1 min)

```bash
cd /home/mike-anderson/dev/cohezion

# Start the HTTP server (Ctrl+C to stop)
uv run python -m cohezion.gateway.mcp_http_server
```

Expected output:
```
INFO: Starting ngrok AI Gateway MCP HTTP server on 0.0.0.0:5000
INFO: Connect Claude.ai to: http://localhost:5000/sse
...
INFO: Uvicorn running on http://0.0.0.0:5000
```

✅ **Server is ready!**

### Step 2: Expose to HTTPS (for Claude.ai)

Claude.ai requires **HTTPS URLs**. You have two options:

**Option A: ngrok tunnel (easiest)**
```bash
# In another terminal
ngrok http 5000

# Copy the HTTPS URL: https://xxxx-xxxx.ngrok.io
# Keep this terminal open while using Claude.ai
```

**Option B: SSH tunnel (if Claude.ai is on same machine)**
```bash
# For localhost testing on same machine, use:
http://localhost:5000/sse
```

### Step 3: Add to Claude.ai

1. Open **https://claude.ai**
2. Click **Settings** → **Custom Connectors** → **Add Custom Connector**
3. Fill in:
   | Field | Value |
   |-------|-------|
   | **Name** | `ngrok AI Gateway` |
   | **Remote MCP server URL** | `https://xxxx-xxxx.ngrok.io/sse` (or `http://localhost:5000/sse`) |
   | **OAuth Client ID** | (leave blank) |
   | **OAuth Client Secret** | (leave blank) |

4. Click **Save Connector** ✅

### Step 4: Start Using It!

**Example 1: Simple Generation**
```
You: Generate a Python function that checks if a number is prime using qwen3-coder

Claude: [Uses the 'generate' tool with qwen3-coder:30b]
def is_prime(n):
    if n < 2:
        return False
    ...
```

**Example 2: Compare Models**
```
You: Compare the speed of deepseek-r1:70b vs phi3:mini for this task...

Claude: [Uses 'generate' tool for both models, compares metrics]
```

**Example 3: Check Performance**
```
You: What's the performance of the gateway right now?

Claude: [Uses 'get_metrics' tool]
Success rate: 100%
Total requests: 23
Average tokens/request: 245
Throughput: 4.2 req/min
```

**Example 4: Available Models**
```
You: What models can I use?

Claude: [Uses 'get_providers' tool]
- qwen3-coder:30b (fast, coding)
- deepseek-r1:70b (powerful reasoning)
- phi3:mini (lightweight)

All local (free) with simulated cost tracking.
```

## Available Tools

The MCP server exposes 5 tools:

| Tool | Purpose | Usage |
|------|---------|-------|
| **generate** | Generate response from local Ollama | `generate with qwen3-coder` |
| **get_metrics** | Performance & usage stats | `show me the metrics` |
| **get_providers** | List models & pricing | `what models are available` |
| **configure_gateway** | Create new gateway instance | `set up a new gateway` |
| **cost_estimate** | Calculate simulated cost | `what does 1000 tokens cost` |

## DemoGateway Features

### Response Caching
- SHA-256 hash-based caching of identical prompts
- Reduces redundant Ollama calls
- Cache metrics shown in `get_metrics`

### Metrics Tracking
```json
{
  "total_requests": 42,
  "successful_requests": 41,
  "failed_requests": 1,
  "cache_hits": 8,
  "success_rate": 97.6,
  "total_tokens": 12450,
  "uptime_seconds": 600.5,
  "requests_per_minute": 4.2,
  "available_models": ["qwen3-coder:30b", "deepseek-r1:70b", "phi3:mini"]
}
```

### Cost Simulation
Simulated pricing (demo only):
- qwen3-coder:30b: $0.001/K in, $0.002/K out
- deepseek-r1:70b: $0.002/K in, $0.004/K out
- phi3:mini: $0.0005/K in, $0.001/K out

*Note: Actual cost is $0 (local Ollama)*

## Troubleshooting

### "Cannot connect to server"
```bash
# Verify server is running
curl http://localhost:5000/health

# Should return: OK
```

### "Tool not available"
1. Stop server (Ctrl+C)
2. Restart: `uv run python -m cohezion.gateway.mcp_http_server`
3. Reconnect in Claude.ai settings

### "HTTP error" or "Claude can't reach server"
- Check server is running on correct port: `lsof -i :5000`
- If using ngrok, verify tunnel is active
- Make sure URL in Claude.ai ends with `/sse`

### "Ollama model not found"
```bash
# List available models
curl http://localhost:11434/api/tags

# Pull missing model
ollama pull qwen3-coder:30b
```

## Architecture

```
Claude.ai Browser
     ↓
Custom Connector (via HTTPS)
     ↓
MCP HTTP Server (localhost:5000)
     ↓
DemoGateway (local abstraction)
     ↓
Local Ollama (qwen, deepseek, phi3)
     ↓
Your Prompts
```

## Advanced: Multiple Gateways

You can create multiple gateway instances with different Ollama URLs:

```
You: Set up a gateway to my remote Ollama server at http://remote.server:11434

Claude: [Uses 'configure_gateway' tool]
Gateway 'remote' created successfully
```

## Key Differences from NgrokAIGateway

| Feature | NgrokAIGateway | DemoGateway |
|---------|----------------|------------|
| **API Keys** | Requires external provider credentials | None - fully local |
| **Providers** | OpenAI, Anthropic, Google, etc. | Local Ollama only |
| **Cost** | Real $$$ for each request | $0 (simulated pricing) |
| **Setup** | Minutes with credentials | Instant with Ollama |
| **Use Case** | Production multi-provider routing | Demo, testing, learning |

## Next Steps

1. ✅ Start HTTP server: `uv run python -m cohezion.gateway.mcp_http_server`
2. ✅ Expose to HTTPS (ngrok tunnel if needed)
3. ✅ Add custom connector in Claude.ai settings
4. ✅ Start using tools in Claude conversations!

## Code Reference

**DemoGateway** (`src/cohezion/gateway/demo_gateway.py`):
- 200+ lines
- Async `generate(prompt, model, system)` method
- Supports: qwen3-coder:30b, deepseek-r1:70b, phi3:mini
- Response caching via SHA-256
- Metrics and cost simulation

**MCP HTTP Server** (`src/cohezion/gateway/mcp_http_server.py`):
- 120+ lines
- Starlette + Uvicorn
- /sse endpoint (Server-Sent Events for MCP protocol)
- /health and /tools endpoints

## Support

For issues or questions:
- Check server logs (stderr from `mcp_http_server`)
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Test tools manually via curl (see Troubleshooting)

---

**Status**: ✅ Ready to use
**Time to connect**: 5 minutes
**API Keys needed**: 0
**Cost**: Free (local Ollama)

Enjoy multi-model AI routing in Claude.ai! 🚀
