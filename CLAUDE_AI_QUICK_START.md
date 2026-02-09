# Connect ngrok Gateway to Claude.ai - Quick Start (5 minutes)

## What You Can Do

Once connected, Claude.ai will have access to:
- ✅ Multi-provider LLM routing (OpenAI, Anthropic, Google, Ollama)
- ✅ Cost tracking and estimation
- ✅ Performance metrics
- ✅ Real-time provider switching
- ✅ Automatic failover to local Ollama

## Step 1: Start the MCP Server (2 min)

```bash
# Terminal 1: Set up environment
export NGROK_ENDPOINT="https://xxxxx.ngrok.app/v1"
export NGROK_API_KEY="your-ngrok-api-key"

# Start the server
uv run python -m cohezion.gateway.mcp_server

# Expected output:
# INFO:     Started server process
# INFO:     Uvicorn running on http://0.0.0.0:5000
```

**Verify it's working**:
```bash
# Terminal 2: Check server is responding
curl http://localhost:5000/tools
# Returns: {"tools": ["generate", "get_metrics", "get_providers", ...]}
```

## Step 2: Expose Server Publicly (1 min)

### Option A: ngrok tunnel (if on same machine)
```bash
# Terminal 2
ngrok http 5000

# Copy the URL: https://xxxxx-xxxxx.ngrok.app
```

### Option B: SSH tunnel (for remote)
```bash
# From your machine, forward to remote
ssh -L 5000:localhost:5000 user@remote-server
# Then use: http://localhost:5000/sse
```

## Step 3: Add Custom Connector to Claude.ai (2 min)

1. **Open Claude.ai** → https://claude.ai
2. **Open Conversation** → click "+" button
3. **Select "Custom Connector"** (or Settings → Custom Connectors)
4. **Fill in the form**:

   | Field | Value |
   |-------|-------|
   | **Name** | `ngrok AI Gateway` |
   | **Remote MCP server URL** | `http://localhost:5000/sse` (or ngrok URL) |
   | **OAuth Client ID** | (leave blank) |
   | **OAuth Client Secret** | (leave blank) |

5. **Click "Save Connector"**

That's it! ✅

## Step 4: Start Using It!

### Example 1: Simple Generation
```
Me: Use the ngrok gateway to explain quantum computing in 100 words

Claude:
[Uses the 'generate' tool with gpt-4o]
Response: Quantum computing harnesses principles of quantum mechanics...
Cost: $0.00032
```

### Example 2: Compare Costs
```
Me: What's cheaper - GPT-4o or Claude 3.5 Sonnet for 1000 input + 500 output tokens?

Claude:
[Uses 'cost_estimate' tool for both models]

GPT-4o: $0.0155
Claude 3.5 Sonnet: $0.0090 ← Cheaper by $0.0065 (42% savings)
```

### Example 3: Check Performance
```
Me: How is the ngrok gateway performing?

Claude:
[Uses 'get_metrics' tool]

Current Status:
- Success rate: 95.2%
- Total requests: 42
- Average cost: $0.00296/request
- Throughput: 2.1 req/min
```

### Example 4: Available Models
```
Me: What models can I use through ngrok?

Claude:
[Uses 'get_providers' tool]

OpenAI: gpt-4o, gpt-3.5-turbo
Anthropic: claude-3.5-sonnet, claude-3-opus, claude-3-haiku
Google: gemini-pro
Ollama: qwen3-coder:30b (local, free)
```

## Available Tools

The MCP server exposes 5 tools to Claude:

| Tool | Purpose | Example |
|------|---------|---------|
| **generate** | Generate response via ngrok | "Generate with gpt-4o" |
| **get_metrics** | Get performance stats | "Show me the metrics" |
| **get_providers** | List models & pricing | "What models are available?" |
| **configure_gateway** | Create new gateways | "Set up a production gateway" |
| **cost_estimate** | Calculate request cost | "What does 1000 tokens cost in GPT-4o?" |

## Troubleshooting

### "Cannot connect to server"
```bash
# Check server is running
curl http://localhost:5000/tools

# If fails, verify:
1. Server started with no errors
2. Port 5000 is not blocked
3. URL in connector is correct
```

### "Tool not available"
```bash
# Solution: Restart MCP server and reconnect in Claude
1. Stop server (Ctrl+C)
2. Restart: uv run python -m cohezion.gateway.mcp_server
3. Remove and re-add connector in Claude.ai
```

### "ngrok endpoint error"
```bash
# Verify credentials
echo $NGROK_ENDPOINT
echo $NGROK_API_KEY

# Test endpoint manually
curl -X POST $NGROK_ENDPOINT/chat/completions \
  -H "Authorization: Bearer $NGROK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"test"}]}'
```

## Tips for Claude Users

1. **Ask for cost comparisons**: "Compare GPT-4o vs Claude 3.5 Sonnet pricing"
2. **Request metrics**: "Show me the performance dashboard"
3. **Use cheapest model**: "Generate using the most cost-effective model"
4. **Monitor spending**: "What's my total cost so far?"
5. **Check provider status**: "Which providers are working best right now?"

## Full Documentation

For more details, see:
- **Integration Guide**: `docs/ngrok_ai_gateway_integration.md`
- **Claude.ai Connection Guide**: `docs/connect_claude_ai_custom_connector.md`
- **Quick Reference**: `NGROK_QUICK_REFERENCE.md`

## Architecture

```
Claude.ai
   ↓
Custom Connector (FastMCP)
   ↓
MCP Server (localhost:5000)
   ↓
NgrokAIGateway
   ↓
OpenAI / Anthropic / Google
   ↓
Your Prompts
```

## Production Setup

For production, you can:

1. **Run on server**: Deploy MCP server on dedicated machine
2. **Use ngrok tunnel**: Expose via ngrok for reliability
3. **Monitor costs**: Claude will track all requests and costs
4. **Set budgets**: Configure cost limits in ngrok dashboard
5. **Auto-route**: Let Claude choose best model for the task

## Next Steps

1. ✅ Start MCP server: `uv run python -m cohezion.gateway.mcp_server`
2. ✅ Expose publicly: `ngrok http 5000` (if needed)
3. ✅ Add connector in Claude.ai
4. ✅ Start using: Ask Claude to generate, compare costs, check metrics!

---

**Status**: ✅ Ready to connect
**Time to connect**: 5 minutes
**Tools available**: 5 (generate, get_metrics, get_providers, configure_gateway, cost_estimate)

Enjoy multi-provider AI routing in Claude.ai! 🚀
