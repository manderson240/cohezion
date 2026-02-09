# Connect ngrok AI Gateway to Claude.ai via Custom Connector

This guide shows how to connect Cohezion's ngrok AI Gateway MCP server to Claude.ai using the custom connector feature.

## Overview

The ngrok AI Gateway MCP server exposes tools that allow Claude.ai to:
- Generate responses via multi-provider routing (OpenAI, Anthropic, Google, Ollama)
- Track costs and metrics
- Get provider information
- Configure gateway instances
- Estimate costs

## Architecture

```
Claude.ai Interface
        ↓
   Custom Connector
        ↓
   MCP Server (localhost:5000/sse)
        ↓
   ngrok AI Gateway
        ↓
   OpenAI / Anthropic / Google / Ollama
```

## Prerequisites

1. **Cohezion environment** with ngrok integration (already done ✅)
2. **ngrok AI Gateway account** - https://dashboard.ngrok.com/ai-gateways
3. **ngrok endpoint and API key** - from ngrok dashboard
4. **Claude.ai account** with access to custom connectors (beta feature)

## Step 1: Start the MCP Server

### Option A: Using Python directly

```bash
# Set environment variables
export NGROK_ENDPOINT="https://xxxxx.ngrok.app/v1"
export NGROK_API_KEY="your-ngrok-api-key"

# Run the MCP server
uv run python -m cohezion.gateway.mcp_server
```

### Option B: Using uvicorn directly

```bash
export NGROK_ENDPOINT="https://xxxxx.ngrok.app/v1"
export NGROK_API_KEY="your-ngrok-api-key"

uv run uvicorn cohezion.gateway.mcp_server:app --host 0.0.0.0 --port 5000
```

### Verify Server is Running

```bash
curl http://localhost:5000/tools
# Should return list of available tools
```

Expected output:
```json
{
  "tools": [
    "generate",
    "get_metrics",
    "get_providers",
    "configure_gateway",
    "cost_estimate"
  ]
}
```

## Step 2: Make Server Publicly Accessible (if needed)

If Claude.ai is running on a different machine, you need to expose the server:

### Option A: ngrok tunnel (recommended)

```bash
# Start ngrok tunnel (separate terminal)
ngrok http 5000

# You'll get a URL like:
# Forwarding https://xxxxx-xxxxx.ngrok.app -> http://localhost:5000
```

### Option B: SSH tunnel (for remote servers)

```bash
# From your local machine
ssh -L 5000:localhost:5000 user@remote-server

# Or from remote, expose via SSH
ssh -R 5000:localhost:5000 user@local-machine
```

## Step 3: Add Custom Connector to Claude.ai

1. **Visit Claude.ai** - https://claude.ai
2. **Settings → Custom Connectors** (or from conversation: "+" → "Custom Connector")
3. **Click "Add Custom Connector"**
4. **Fill in the form**:

   **Name**: `ngrok AI Gateway`

   **Remote MCP server URL**:
   - Local: `http://localhost:5000/sse`
   - Remote (ngrok): `https://xxxxx-xxxxx.ngrok.app/sse`
   - Remote (SSH): `http://localhost:5000/sse`

   **OAuth Client ID** (optional): Leave blank

   **OAuth Client Secret** (optional): Leave blank

5. **Click "Save Connector"**

## Step 4: Use in Claude Conversations

### Example 1: Basic Generation

```
Claude: I'll generate a response using the ngrok AI Gateway.

Me: Generate a response about quantum computing using GPT-4o

Claude: I'll use the ngrok AI Gateway to generate that for you.
[Uses the 'generate' tool with model="gpt-4o"]
Response: [Generated content]
Cost: $0.000325
```

### Example 2: Cost Comparison

```
Me: Compare the cost of using GPT-4o vs Claude 3.5 Sonnet for 1000 input tokens and 500 output tokens

Claude:
[Uses 'cost_estimate' tool twice]

GPT-4o: $0.0155 (input: $0.005, output: $0.0075)
Claude 3.5 Sonnet: $0.0090 (input: $0.003, output: $0.0075)

Savings: $0.0065 (42% cheaper with Claude)
```

### Example 3: Get Metrics

```
Me: What's the performance of the ngrok gateway?

Claude:
[Uses 'get_metrics' tool]

Current Metrics:
- Total requests: 42
- Success rate: 95.2%
- Total tokens: 15,234
- Total cost: $0.1243
- Avg cost/request: $0.00296
- Requests/min: 2.1
```

### Example 4: Check Available Models

```
Me: What models can I use?

Claude:
[Uses 'get_providers' tool]

Available Providers:
- OpenAI: gpt-4o, gpt-3.5-turbo
- Anthropic: claude-3.5-sonnet, claude-3-opus, claude-3-haiku
- Google: gemini-pro
- Ollama: qwen3-coder:30b, deepseek-r1:70b (local)
```

## Available Tools in Claude

### 1. generate

Generate response via ngrok gateway.

**Parameters**:
- `prompt` (required): User prompt
- `model` (optional, default: "gpt-4o"): Model name
- `system` (optional): System prompt
- `gateway_id` (optional, default: "default"): Gateway instance

**Returns**: Response text, tokens used, cost, provider

### 2. get_metrics

Get performance and cost metrics.

**Parameters**:
- `gateway_id` (optional, default: "default"): Gateway instance

**Returns**: Comprehensive metrics (requests, tokens, cost, throughput, cache hits)

### 3. get_providers

Get available providers and models.

**Returns**: List of all supported models with pricing

### 4. configure_gateway

Create or update gateway configuration.

**Parameters**:
- `gateway_id` (required): Unique ID for gateway
- `ngrok_endpoint` (required): ngrok gateway URL
- `ngrok_api_key` (optional): API key
- `fallback_ollama_url` (optional): Ollama URL
- `enable_failover` (optional): Enable failover

**Returns**: Confirmation with gateway details

### 5. cost_estimate

Estimate cost for a request.

**Parameters**:
- `model` (required): Model name
- `input_tokens` (required): Number of input tokens
- `output_tokens` (required): Number of output tokens

**Returns**: Cost breakdown in USD

## Troubleshooting

### "Connection refused" Error

**Problem**: Claude.ai can't connect to MCP server

**Solution**:
1. Verify server is running: `curl http://localhost:5000/sse`
2. Check if port 5000 is open
3. If remote: use ngrok tunnel or SSH tunnel
4. Verify URL in connector settings is correct

### "Tool not found" Error

**Problem**: Tool appears in connector but Claude can't use it

**Solution**:
1. Restart MCP server
2. Remove and re-add connector in Claude.ai
3. Check server logs: `tail -f /tmp/mcp_server.log`

### ngrok Endpoint Not Working

**Problem**: "All providers failed" when generating

**Solution**:
1. Verify NGROK_ENDPOINT is set: `echo $NGROK_ENDPOINT`
2. Test endpoint manually: `curl -X POST $NGROK_ENDPOINT/chat/completions ...`
3. Check ngrok dashboard for status
4. Verify API key is correct

### High Latency

**Problem**: Responses take too long

**Solution**:
1. Use cheaper models (GPT-3.5, Haiku) for simple tasks
2. Enable cache via feature flags
3. Monitor `requests_per_minute` metric
4. Check ngrok gateway health

## Cost Optimization Tips

Use Claude with ngrok gateway to:

1. **Compare models**: "What's the cheapest model that can handle this task?"
2. **Estimate budgets**: "What's the cost for 100k tokens of input/output per day?"
3. **Route intelligently**: "Generate with the fastest model" vs "cheapest model"
4. **Track spending**: "Show me monthly cost trends"

## Advanced Configuration

### Multiple Gateway Instances

Configure multiple ngrok gateways for different use cases:

```
Me: Configure a production gateway with high availability

Claude:
[Uses 'configure_gateway' tool]
- gateway_id: "production"
- ngrok_endpoint: "https://prod.ngrok.app/v1"
- enable_failover: true
```

Then use in requests:
```
Me: Generate with the production gateway

Claude:
[Uses 'generate' tool with gateway_id="production"]
```

### Custom Cost Thresholds

```
Me: Only use models under $0.005 per 1k tokens

Claude:
[Uses 'get_providers' and 'cost_estimate' tools]
Recommended models:
- gpt-3.5-turbo: $0.0015 per 1k tokens
- claude-3-haiku: $0.00125 per 1k tokens
```

## Performance Monitoring

Ask Claude to monitor performance:

```
Me: Is the gateway performing well?

Claude:
[Uses 'get_metrics' tool]
Analysis:
- Success rate: 95.2% ✓ (target: >90%)
- Avg latency: 1.2s ✓ (good)
- Cache hit rate: 28% ✓ (target: 20-30%)
- Cost efficiency: $0.003/request ✓ (within budget)
```

## Security Considerations

1. **Keep ngrok credentials secure**: Don't expose `NGROK_API_KEY`
2. **Firewall access**: Restrict MCP server to trusted IPs
3. **Use HTTPS**: Ensure connector URL uses HTTPS if exposed publicly
4. **Monitor metrics**: Track unexpected cost spikes
5. **Set budget alerts**: Configure cost limits in ngrok dashboard

## Examples

### Full Workflow: Compare Providers and Generate

```
Me:
1. Show all available models
2. Compare cost for 500 input + 200 output tokens
3. Generate the same prompt with the cheapest provider
4. Show me the metrics

Claude:
Step 1: [get_providers] Shows all models
Step 2: [cost_estimate × 3] Compares GPT-3.5, Haiku, Gemini
Step 3: [generate] Uses cheapest model
Step 4: [get_metrics] Shows results

Result: Saved $0.008 by using Haiku instead of GPT-4o
```

### Batch Processing with Metrics

```
Me: Generate 10 variations of this prompt and track total cost

Claude:
[Uses generate tool 10 times]
[Uses get_metrics tool]

Results:
- Variations generated: 10
- Total tokens: 5,243
- Total cost: $0.0185
- Avg cost/variation: $0.00185
- Time: 12.3 seconds
```

## Support

For issues:
1. Check MCP server logs
2. Verify ngrok endpoint is accessible
3. Review Claude.ai connector settings
4. Test endpoint manually: `curl http://localhost:5000/sse`
5. Restart server and reconnect

## References

- **ngrok AI Gateway Docs**: https://ngrok.com/docs/ai-gateway/overview
- **Claude.ai Custom Connectors**: https://claude.ai (settings → custom connectors)
- **MCP Server Code**: `src/cohezion/gateway/mcp_server.py`
- **Integration Guide**: `docs/ngrok_ai_gateway_integration.md`

---

**Status**: ✅ Ready to connect
**Server**: FastMCP with 5 tools (generate, get_metrics, get_providers, configure_gateway, cost_estimate)
**Next**: Start server, add connector to Claude.ai, start using!
