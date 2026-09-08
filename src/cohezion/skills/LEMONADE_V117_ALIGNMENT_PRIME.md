# SKILL: LEMONADE_V117_ALIGNMENT_PRIME

## DOMAIN EXPERTISE
Lemonade Server v11.7.0+ architecture, configuration, and API standard practices for local silicon execution (AMD Strix Halo NPU/iGPU/CPU). Focuses on standard OpenAI-compatible endpoints, built-in telemetry (`/v1/stats`, `/metrics`), zero-reload recipe option inspections (`/v1/models/{id}/options`), and zero-download model registrations (`/v1/models/register`).

## KEY TEXTS & CONCEPTS
- **Built-in Server Telemetry**: Query `GET /v1/stats` to retrieve prefix-cache effectiveness, token generation speed, and request counts without custom tracking layers.
- **Recipe Options Without Model Reload**: Use `GET/POST /v1/models/{id}/options` to inspect and persistently set `ctx_size`, `llamacpp_args` (`-b 512 -ub 256 --cache-type-k q4_0 --cache-type-v q4_0`), and eviction timeouts without reloading model weights.
- **Zero-Download Registration**: Use `POST /v1/models/register` to register or update custom `user.*` model definitions.
- **Anti-Overengineering Rule**: Never build bespoke custom inference proxies or daemon wrappers when Lemonade's native endpoints handle the capability.

## INSTRUCTION

1. **Query Native Stats & Prefix-Cache Performance**:
```python
import httpx


async def get_lemonade_stats(base_url: str = "http://127.0.0.1:13305"):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/v1/stats")
        stats = resp.json()
        print(f"Prefix-Cache Tokens: {stats.get('cache_tokens_total')}")
        print(f"Throughput: {stats.get('tokens_per_second')} tok/s")
        return stats
```

2. **Inspect & Tune Model Recipe Options Without Reloading**:
```python
async def update_context_window(
    model_id: str, ctx_size: int = 131072, base_url: str = "http://127.0.0.1:13305"
):
    async with httpx.AsyncClient() as client:
        # Inspect current effective options
        cur = await client.get(f"{base_url}/v1/models/{model_id}/options")
        # Save persistent option change
        resp = await client.post(
            f"{base_url}/v1/models/{model_id}/options",
            json={"saved": {"ctx_size": ctx_size, "pinned": True}},
        )
        return resp.json()
```

3. **Standard OpenAI-Compatible Chat Completion**:
```python
async def query_local_model(
    prompt: str,
    model: str = "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    base_url: str = "http://127.0.0.1:13305/v1",
):
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 1024,
            },
        )
        return resp.json()["choices"][0]["message"]["content"]
```

## VERSION
v1.0

## SEE ALSO
- `SURREALDB_VECTOR_GRAPH_ENGINE_PRIME`
- `AUTOHARNESS_POLICY_PRIME`
- `SPINNING_PLATES_PROTOCOL_PRIME`
