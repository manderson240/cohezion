# Cohezion API Quickstart Guide

Get started with the Cohezion API in minutes.

---

## Prerequisites

- Python 3.13+
- Running Cohezion server (`make run` or `uv run python -m cohezion.api`)
- `curl` or `httpx` for testing

## Base URL

```
http://localhost:8080
```

---

## Quick Test

Check if the server is running:

```bash
curl http://localhost:8080/health
```

**Expected Response:**

```json
{
  "status": "healthy",
  "service": "cohezion"
}
```

---

## Common Workflows

### 1. Execute a Skill

Execute a PRIME skill with input text:

```bash
curl -X POST http://localhost:8080/compound/execute \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "analyst",
    "input_text": "Analyze this text for patterns",
    "model": "gemma3n"
  }'
```

**Response:**

```json
{
  "skill_name": "analyst",
  "final_output": "Found 3 key patterns...",
  "steps": [...],
  "total_tokens": 150,
  "total_duration_ms": 450
}
```

### 2. List Available Skills

```bash
curl http://localhost:8080/skills/list
```

### 3. Run a Swarm Debate

```bash
curl -X POST http://localhost:8080/swarm/debate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is consciousness?",
    "perspectives": ["technical", "ethical"]
  }'
```

### 4. Get Universe Nodes

```bash
curl "http://localhost:8080/universe/nodes?limit=10"
```

### 5. Encode a Vector with FLUME

```bash
curl -X POST http://localhost:8080/flume/encode \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.5, 0.3, 0.8, ...]  // 256 floats
  }'
```

---

## Python SDK Example

```python
import httpx

BASE_URL = "http://localhost:8080"


async def execute_skill(skill_name: str, text: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/compound/execute", json={"skill_name": skill_name, "input_text": text}
        )
        return response.json()


async def get_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        return response.json()


# Usage
import asyncio

result = asyncio.run(execute_skill("analyst", "Analyze this"))
print(result["final_output"])
```

---

## WebSocket Example

Connect to the real-time pulse stream:

```python
import asyncio
import websockets
import json


async def pulse_stream():
    uri = "ws://localhost:8080/pulse"
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            brane = data["payload"]["brane"]
            print(f"Coherence: {brane[7]:.2f}")


asyncio.run(pulse_stream())
```

---

## Streaming Inference (SSE)

For long-running tasks:

```bash
curl -N -X POST http://localhost:8080/inference/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "skill_name": "researcher",
    "input_text": "Research quantum computing advances",
    "checkpoint_interval": 5
  }'
```

---

## Error Handling

Common errors and solutions:

| Error | Code | Solution |
|-------|------|----------|
| Rate limit | 429 | Wait and retry |
| Skill not found | 404 | Check `/skills/list` |
| Invalid vector | 422 | Ensure 256D for FLUME |
| Server error | 500 | Check server logs |

---

## Next Steps

- See [COHEZION_API.md](./COHEZION_API.md) for complete reference
- Explore OpenAPI docs at `/docs` (development mode)
- Check out example notebooks in `docs/notebooks/`

---

## Troubleshooting

### Server not responding

```bash
# Check if server is running
curl http://localhost:8080/health

# Start server
make run
# or
uv run python -m cohezion.api
```

### CORS errors

Set allowed origins:

```bash
export COHEZION_CORS_ORIGINS="http://localhost:3000,http://localhost:8080"
```

### Model not available

Check Ollama status:

```bash
curl http://localhost:8080/metrics/system
```
