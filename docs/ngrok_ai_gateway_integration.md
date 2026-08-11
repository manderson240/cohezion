# ngrok AI Gateway Integration

## Overview

Cohezion now supports multi-provider LLM routing through [ngrok AI Gateway](https://ngrok.ai). This enables:

- **Multi-provider routing**: Access OpenAI, Anthropic, Google, and self-hosted models through a single endpoint
- **Automatic failover**: Seamlessly fall back to local Ollama if ngrok fails
- **Cost optimization**: Route simple tasks to cheaper models, complex tasks to powerful models
- **Production reliability**: Built-in failover, response caching, and health monitoring
- **Single endpoint**: Point your code at ngrok gateway, no provider-specific integrations needed

## Quick Start

### 1. Enable ngrok AI Gateway

Visit [ngrok Dashboard](https://dashboard.ngrok.com/ai-gateways) and set up your gateway with your preferred providers:

```
✓ OpenAI (GPT-4o, GPT-3.5-turbo)
✓ Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)
✓ Google (Gemini Pro)
✓ Self-hosted (Ollama via endpoint)
```

### 2. Get Your Gateway Endpoint

From the dashboard, copy your gateway endpoint. It will look like:

```
https://xxxxx.ngrok.app/v1
```

### 3. Set Environment Variables

```bash
export NGROK_ENDPOINT="https://xxxxx.ngrok.app/v1"
export NGROK_API_KEY="your-ngrok-api-key"
```

### 4. Use with TokenEfficientClient

```python
from cohezion.swarm.token_client import TokenEfficientClient

# Initialize with ngrok gateway
client = TokenEfficientClient(
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
    ngrok_api_key="your-ngrok-key",
    enable_ngrok_failover=True,  # Fallback to Ollama if ngrok fails
)

# Generate response (same API as before)
response, tokens = await client.generate(
    prompt="Explain quantum computing",
    model="gpt-4o",  # Can use any provider's models
)

# Access metrics
metrics = client.get_metrics()
print(f"Cost: ${metrics['total_cost']:.4f}")
print(f"Tokens: {metrics['total_tokens']}")
```

## Architecture

### 4-Tier Cache Stack

Cohezion's caching hierarchy now includes:

```
┌─────────────────────────────────────────┐
│ L1: Exact Hash Cache (in-memory)        │  < 1ms
│     SHA-256 exact prompt matching       │
└─────────────────────────────────────────┘
                    ↓ (miss)
┌─────────────────────────────────────────┐
│ L2: Semantic Cache (fuzzy matching)     │  2-5ms
│     VAE embeddings, 50× discrimination  │
└─────────────────────────────────────────┘
                    ↓ (miss)
┌─────────────────────────────────────────┐
│ L3: Persistent Cache (disk-based)       │  10-50ms
│     JSONL vault integration             │
└─────────────────────────────────────────┘
                    ↓ (miss)
┌─────────────────────────────────────────┐
│ L4: ngrok Response Cache                │  < 1ms
│     Response caching at gateway         │
└─────────────────────────────────────────┘
                    ↓ (miss)
┌─────────────────────────────────────────┐
│ Execute via ngrok → Provider            │
│ Fallback to Ollama on failure           │
└─────────────────────────────────────────┘
```

### Failover Strategy

```
Request
  │
  ├─→ Check L1/L2/L3 caches
  │
  ├─→ ngrok AI Gateway (if enabled, feature flag)
  │     │
  │     ├─→ Request succeeds → return
  │     │
  │     └─→ Request fails
  │           │
  │           └─→ Fallback to Ollama (if enabled)
  │                 └─→ return or raise
```

## Feature Flags

Cohezion uses feature flags for gradual rollout. Available flags:

### NGROK_AI_GATEWAY
Enable/disable ngrok routing entirely. Default: DISABLED (safe for gradual rollout).

```python
from cohezion.deployment.feature_flags import FeatureFlag, get_feature_flag_manager

manager = get_feature_flag_manager()

# Enable for canary testing (5% of traffic)
manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, True)
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 5.0)  # 5%
```

### NGROK_FAILOVER_MODE
Control automatic failover behavior. Default: DISABLED.

```python
manager.set_flag(FeatureFlag.NGROK_FAILOVER_MODE, True)
```

### NGROK_COST_OPTIMIZATION
Route to cheaper models for simple tasks. Default: DISABLED.

```python
manager.set_flag(FeatureFlag.NGROK_COST_OPTIMIZATION, True)
```

### NGROK_RESPONSE_CACHING
Enable 4th tier response caching. Default: DISABLED.

```python
manager.set_flag(FeatureFlag.NGROK_RESPONSE_CACHING, True)
```

## Cost Optimization

### Model Cost Mapping

ngrok adapter includes built-in cost tracking for all models:

```python
# Built-in model costs (per million tokens)
COSTS = {
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "claude-3.5-sonnet": {"input": 3.0, "output": 15.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}

# Cost is automatically calculated
response, tokens = await client.generate(prompt, model="gpt-4o")

# Check cost
metrics = client.get_metrics()
print(f"Cost for this request: ${metrics['total_cost']:.6f}")
```

### Cost-Based Routing

Implement your own routing logic:

```python
def choose_model(prompt: str) -> str:
    """Route to cheapest model for simple queries."""
    if len(prompt) < 50 and "?" not in prompt:
        # Simple question → cheap model
        return "gpt-3.5-turbo"
    elif "complex" in prompt or "analyze" in prompt:
        # Complex task → powerful model
        return "gpt-4o"
    else:
        return "claude-3.5-sonnet"  # Default


prompt = "What is the capital of France?"
model = choose_model(prompt)
response, tokens = await client.generate(prompt, model=model)
```

## Metrics and Monitoring

### Available Metrics

```python
metrics = client.get_metrics()

# Request statistics
metrics["total_requests"]  # Total requests made
metrics["successful_requests"]  # Successful requests
metrics["failed_requests"]  # Failed requests
metrics["fallback_requests"]  # Fell back to Ollama
metrics["cache_hits"]  # Cache hits

# Provider tracking
metrics["ngrok_requests"]  # Requests via ngrok
metrics["ollama_requests"]  # Requests via Ollama

# Token and cost tracking
metrics["total_tokens"]  # Total tokens used
metrics["total_cost"]  # Total cost in USD
metrics["average_cost_per_request"]  # Average cost per request

# Performance
metrics["success_rate"]  # % of successful requests
metrics["uptime_seconds"]  # Gateway uptime
metrics["requests_per_minute"]  # Throughput
```

### Monitoring Dashboard

```python
# Real-time metrics
print(f"""
=== ngrok AI Gateway Metrics ===
Requests:   {metrics["total_requests"]}
Success:    {metrics["success_rate"]}%
Provider:   {metrics["ngrok_requests"]} ngrok, {metrics["ollama_requests"]} ollama
Fallbacks:  {metrics["fallback_requests"]}
Cache Hits: {metrics["cache_hits"]}
Tokens:     {metrics["total_tokens"]}
Cost:       ${metrics["total_cost"]:.4f}
Uptime:     {metrics["uptime_seconds"]}s
Throughput: {metrics["requests_per_minute"]} req/min
""")
```

## Configuration Reference

### TokenEfficientClient with ngrok

```python
client = TokenEfficientClient(
    # Ollama (fallback)
    ollama_base_url="http://localhost:11434",
    # ngrok Gateway
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
    ngrok_api_key="your-api-key",
    enable_ngrok_failover=True,
    # Caching
    use_persistent_cache=True,
    cache_dir="data/cache",
    use_semantic_cache=True,
    semantic_threshold=0.95,
)
```

### NgrokAIGateway Directly

```python
from cohezion.gateway import NgrokAIGateway

gateway = NgrokAIGateway(
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
    ngrok_api_key="your-api-key",
    fallback_ollama_url="http://localhost:11434",
    enable_failover=True,
    enable_cost_optimization=True,
    timeout=300.0,
    max_retries=3,
)

response, tokens = await gateway.generate(
    prompt="Your prompt",
    model="gpt-4o",
    system="System prompt",
)
```

## Error Handling

### Graceful Degradation

```python
try:
    # Try ngrok
    response, tokens = await client.generate(prompt="test", model="gpt-4o")
except RuntimeError as e:
    logger.error(f"All providers failed: {e}")
    # Implement fallback logic
    response = "Service temporarily unavailable"
    tokens = 0
```

### Failover Behavior

```python
# With failover enabled (default)
client = TokenEfficientClient(
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
    enable_ngrok_failover=True,  # Automatic Ollama fallback
)

# If ngrok fails:
# 1. Retry ngrok up to max_retries (default: 3)
# 2. Fall back to Ollama
# 3. Retry Ollama up to max_retries
# 4. Raise error if all fail

# Without failover
client = TokenEfficientClient(
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
    enable_ngrok_failover=False,  # No Ollama fallback
)

# If ngrok fails, raise error immediately
```

## Production Deployment

### Gradual Rollout

```python
from cohezion.deployment.feature_flags import FeatureFlag, RolloutStage, get_feature_flag_manager

manager = get_feature_flag_manager()

# Phase 1: Canary (5% of traffic)
manager.set_flag(
    FeatureFlag.NGROK_AI_GATEWAY,
    enabled=True,
    rollout_stage=RolloutStage.CANARY,
    rollout_percentage=5.0,
)

# Phase 2: Monitor metrics for 24 hours

# Phase 3: Ramp up (25% of traffic)
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 25.0)

# Phase 4: Monitor another 24 hours

# Phase 5: Full rollout (100%)
manager.ramp_up(FeatureFlag.NGROK_AI_GATEWAY, 100.0)
```

### Safety Checks

```python
from cohezion.deployment.deployment_orchestrator import DeploymentOrchestrator

orchestrator = DeploymentOrchestrator()

# Safety checks before advancing stages
health = orchestrator.check_safety(
    feature_flag=FeatureFlag.NGROK_AI_GATEWAY,
)

print(f"""
Cache Performance: {health["cache_perf_ok"]}
Token Efficiency:  {health["token_efficiency_ok"]}
Error Rate:        {health["error_rate_ok"]}
Latency:          {health["latency_ok"]}
Memory:           {health["memory_ok"]}
""")
```

### Emergency Rollback

```python
# Immediate rollback if issues detected
manager.rollback(FeatureFlag.NGROK_AI_GATEWAY, updated_by="ops_team")

# This disables ngrok entirely and reverts to Ollama
```

## Troubleshooting

### ngrok Endpoint Not Configured

**Error**: `ValueError: ngrok endpoint not configured`

**Solution**: Set `NGROK_ENDPOINT` env var or pass `ngrok_endpoint` param:

```python
client = TokenEfficientClient(
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
)
```

### All Providers Failed

**Error**: `RuntimeError: All providers failed: ngrok and Ollama`

**Solution**:
1. Check ngrok endpoint and API key are correct
2. Verify Ollama is running: `curl http://localhost:11434/api/tags`
3. Check network connectivity
4. Enable failover mode for automatic fallback

### High Latency

**Solution**:
1. Check ngrok gateway health
2. Check provider status (OpenAI, Anthropic, etc.)
3. Monitor cache hit rates (should be 30-50%)
4. Consider using cheaper models for latency-sensitive tasks

### Cost Overruns

**Solution**:
1. Enable cost optimization feature flag
2. Implement cost-based routing
3. Monitor `total_cost` metric
4. Use cheaper models (Claude Haiku vs Opus, GPT-3.5 vs GPT-4)
5. Leverage cache hits (check `cache_hits` metric)

## Examples

### Simple Generation

```python
from cohezion.swarm.token_client import TokenEfficientClient

client = TokenEfficientClient(
    ngrok_endpoint="https://xxxxx.ngrok.app/v1",
    ngrok_api_key="your-key",
)

response, tokens = await client.generate(
    prompt="What is machine learning?",
    model="gpt-3.5-turbo",  # Cheap model
)

print(f"Response: {response}")
print(f"Tokens: {tokens}")
```

### Batch Processing with Cost Optimization

```python
from cohezion.swarm.batch_processor import BatchItem

items = []

# Simple questions → cheap model
for i in range(5):
    items.append(
        BatchItem(
            id=f"simple_{i}",
            prompt=f"What is {i}+{i}?",
            model="gpt-3.5-turbo",
            system="",
        )
    )

# Complex analysis → powerful model
for i in range(2):
    items.append(
        BatchItem(
            id=f"complex_{i}",
            prompt=f"Analyze the economic impact of AI on job markets",
            model="gpt-4o",
            system="You are an economist",
        )
    )

result = await client.batch_generate(items)

print(f"Processed: {result.total_items}")
print(f"Cost: ${client.get_metrics()['total_cost']:.4f}")
print(f"Cache efficiency: {client.get_metrics()['combined_hit_rate']:.1%}")
```

### Multi-Provider Routing

```python
async def generate_response(task: str) -> str:
    """Route to best provider for task."""
    client = TokenEfficientClient(
        ngrok_endpoint="https://xxxxx.ngrok.app/v1",
        ngrok_api_key="your-key",
    )

    if "code" in task.lower():
        model = "gpt-4o"  # Best for coding
    elif "creative" in task.lower():
        model = "claude-3.5-sonnet"  # Great for creative tasks
    else:
        model = "gpt-3.5-turbo"  # Cost-effective default

    response, tokens = await client.generate(task, model=model)
    return response
```

## See Also

- [ngrok AI Gateway Documentation](https://ngrok.com/docs/ai-gateway/overview)
- [Feature Flags Configuration](../docs/production_deployment.md)
- [TokenEfficientClient Guide](../docs/token_efficient_client.md)
- [Phase 2 Implementation Summary](../PHASE_2_IMPLEMENTATION_SUMMARY.md)
