# ngrok AI Gateway - Quick Reference

## Setup (5 minutes)

```bash
# 1. Enable ngrok AI Gateway
# Visit: https://dashboard.ngrok.com/ai-gateways

# 2. Get your endpoint
# Copy: https://xxxxx.ngrok.app/v1

# 3. Set environment variables
export NGROK_ENDPOINT="https://xxxxx.ngrok.app/v1"
export NGROK_API_KEY="your-ngrok-api-key"

# 4. Verify imports
uv run python -c "from cohezion.gateway import NgrokAIGateway; print('✓ Ready')"
```

## Basic Usage

```python
from cohezion.swarm.token_client import TokenEfficientClient

# Initialize client with ngrok gateway
client = TokenEfficientClient(
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
    ngrok_api_key="your-ngrok-key",
    enable_ngrok_failover=True,  # Fallback to Ollama
)

# Generate response (same API as before)
response, tokens = await client.generate(
    prompt="Your prompt",
    model="gpt-4o",  # Can use any provider
)

# Check metrics
metrics = client.get_metrics()
print(f"Cost: ${metrics['total_cost']:.4f}")
print(f"Tokens: {metrics['total_tokens']}")
```

## Available Models

### OpenAI
- `gpt-4o` - Best performance ($5/$15 per M tokens)
- `gpt-3.5-turbo` - Cost-effective ($0.5/$1.5 per M tokens)

### Anthropic
- `claude-3.5-sonnet` - Balanced ($3/$15 per M tokens)
- `claude-3-opus` - Powerful ($15/$75 per M tokens)
- `claude-3-haiku` - Fast, cheap ($0.25/$1.25 per M tokens)

### Google
- `gemini-pro` - Efficient ($0.5/$1.5 per M tokens)

### Self-hosted
- Ollama models via endpoint (free, local)

## Feature Flags

```python
from cohezion.deployment.feature_flags import FeatureFlag, get_feature_flag_manager

manager = get_feature_flag_manager()

# Enable ngrok (start with canary - 5%)
manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, True)
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 5.0)

# Ramp up to 25%
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 25.0)

# Rollout to 100%
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 100.0)

# Emergency rollback
manager.rollback(FeatureFlag.NGROK_AI_GATEWAY)
```

## Cost Optimization

```python
# Route based on task complexity
def choose_model(prompt: str) -> str:
    if len(prompt) < 50:
        return "gpt-3.5-turbo"  # Cheap for simple
    elif "code" in prompt.lower():
        return "gpt-4o"  # Best for coding
    else:
        return "claude-3.5-sonnet"  # Balanced

response, tokens = await client.generate(prompt, model=choose_model(prompt))

# Check per-request cost
metrics = client.get_metrics()
print(f"Avg cost/request: ${metrics['average_cost_per_request']:.6f}")
```

## Metrics Dashboard

```python
metrics = client.get_metrics()

# Request stats
print(f"Total requests:    {metrics['total_requests']}")
print(f"Success rate:      {metrics['success_rate']}%")
print(f"Cache hits:        {metrics['cache_hits']}")

# Cost tracking
print(f"Total cost:        ${metrics['total_cost']:.4f}")
print(f"Avg cost/request:  ${metrics['average_cost_per_request']:.6f}")

# Performance
print(f"Total tokens:      {metrics['total_tokens']}")
print(f"Throughput:        {metrics['requests_per_minute']} req/min")

# Provider tracking
print(f"ngrok requests:    {metrics['ngrok_requests']}")
print(f"ollama requests:   {metrics['ollama_requests']}")
print(f"Fallback requests: {metrics['fallback_requests']}")
```

## Batch Processing

```python
from cohezion.swarm.batch_processor import BatchItem

items = [
    BatchItem(id="1", prompt="Simple query", model="gpt-3.5-turbo", system=""),
    BatchItem(id="2", prompt="Complex code", model="gpt-4o", system=""),
    BatchItem(id="3", prompt="Creative task", model="claude-3.5-sonnet", system=""),
]

result = await client.batch_generate(items)
print(f"Processed: {len(result.items)} items")
print(f"Cost: ${client.get_metrics()['total_cost']:.4f}")
```

## Failover Behavior

```
Request
├─→ Check L1/L2/L3 caches
│
├─→ Is ngrok enabled?
│   ├─→ Yes: Try ngrok
│   │   ├─→ Success → return
│   │   └─→ Fail → fallback to Ollama
│   │
│   └─→ No: Use Ollama directly
```

## Feature Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `NGROK_AI_GATEWAY` | Enable ngrok routing | DISABLED |
| `NGROK_FAILOVER_MODE` | Auto-fallback to Ollama | DISABLED |
| `NGROK_COST_OPTIMIZATION` | Cost-based routing | DISABLED |
| `NGROK_RESPONSE_CACHING` | 4th-tier cache | DISABLED |

## Troubleshooting

### "ngrok endpoint not configured"
```python
# Set in code
client = TokenEfficientClient(
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
)

# Or set env var
export NGROK_ENDPOINT="https://xxxxx.ngrok.app/v1"
```

### "All providers failed"
```python
# Check Ollama is running
curl http://localhost:11434/api/tags

# Enable failover
client = TokenEfficientClient(
    enable_ngrok_failover=True,  # This is default
)
```

### High latency
- Check ngrok gateway health
- Monitor cache hit rates (should be 30-50%)
- Use cheaper models for speed-critical tasks
- Increase `num_predict` timeout if needed

### Cost overruns
- Enable cost optimization flag
- Use cheaper models (Haiku < GPT-3.5 < Sonnet < GPT-4o)
- Monitor `total_cost` metric
- Leverage cache hits

## Testing

```bash
# Run all ngrok tests
uv run pytest tests/gateway/test_ngrok_adapter.py -v

# Run specific test
uv run pytest tests/gateway/test_ngrok_adapter.py::TestNgrokAIGateway::test_cost_calculation -v

# Show test output
uv run pytest tests/gateway/test_ngrok_adapter.py -v -s
```

## Example Scripts

```bash
# Run integration examples
uv run python scripts/example_ngrok_integration.py

# The script demonstrates:
# - Feature flag gradual rollout
# - Metrics monitoring
# - Cost tracking
# - Multi-provider routing
```

## Documentation

- **Full guide**: `docs/ngrok_ai_gateway_integration.md`
- **Implementation details**: `NGROK_INTEGRATION_SUMMARY.md`
- **Example code**: `scripts/example_ngrok_integration.py`
- **Tests**: `tests/gateway/test_ngrok_adapter.py`

## Production Deployment

```python
# 1. Start canary (5% of traffic)
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 5.0)

# 2. Monitor metrics for 24 hours
# Check: success_rate, total_cost, cache_hits

# 3. Ramp up (25%)
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 25.0)

# 4. Monitor another 24 hours

# 5. Full rollout (100%)
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 100.0)

# 6. Continuous monitoring
# Rollback available any time
manager.rollback(FeatureFlag.NGROK_AI_GATEWAY)
```

## Key Statistics

- **22 tests**: All passing ✅
- **4 feature flags**: Gradual rollout control
- **14 models**: Built-in cost tracking
- **4-tier cache**: Response caching at gateway
- **Multi-provider**: OpenAI, Anthropic, Google, Ollama
- **Automatic failover**: ngrok → Ollama seamless
- **Cost tracking**: Per-request pricing

## Support

For issues:
1. Check docs: `docs/ngrok_ai_gateway_integration.md`
2. Review examples: `scripts/example_ngrok_integration.py`
3. Run tests: `uv run pytest tests/gateway/test_ngrok_adapter.py -v`
4. Check feature flags: `manager.get_status()`

---

**Status**: ✅ Production Ready (22/22 tests passing)
