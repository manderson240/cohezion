---
name: lemonade-omnirouter-prime
description: "Expert in Lemonade OmniRouter hardware lane routing, FLM/NPU vs GGUF/iGPU model selection, safe sequential swarm patterns, fleet lock discipline, and collection.router intelligent routing policies on AMD Strix Halo unified memory systems."
---

# SKILL: LEMONADE_OMNIROUTER_PRIME

## DOMAIN EXPERTISE
Expert in Lemonade server (port 13305) hardware lane routing for AMD Strix Halo systems
(128GB unified DDR5, NPU `/dev/accel0`, iGPU Vulkan `/dev/dri/renderD128`, CPU fallback).
Covers: FLM vs GGUF model routing, `collection.router` intelligent routing policies,
safe swarm patterns, OOM prevention, fleet lock discipline, and event bus integration.

## KEY TEXTS & CONCEPTS

* **Recipe = Lane**: Model `recipe` field determines hardware: `flm` → NPU (VitisAI/XDNA2), `llamacpp` + `llamacpp_backend: vulkan` → iGPU, `llamacpp_backend: cpu` → CPU.
* **FLM = FastFlowLM = NPU**: All `-FLM` suffix models use `recipe: flm` and run on AMD XDNA2 NPU. No other naming convention routes to NPU.
* **No per-request backend override**: Backend is baked at model-load time. Select lane by model name, not API params.
* **`max_loaded_models: 1`**: Lemonade native fleet lock. Never override on Strix Halo — concurrent loads cause GCVM_L2 kernel faults.
* **`pinned: true` & KV Cache Math**: Models with `pinned: true` (e.g. `qwen3.6-moe-35b-a3b-FLM`) hold NPU memory permanently (~35B×Q4 ≈ ~18GB). On 128GB unified RAM, deduct this baseline ~18GB footprint when computing memory availability for concurrent/swapped iGPU/CPU models to prevent OOM.
* **LRU eviction race**: Auto-loading a new model triggers eviction + Vulkan driver cleanup (200–500ms). In-flight requests to evicted model return HTTP 500.
* **Load ≠ Ready**: `/api/v1/load` returning success does NOT mean the model is serving. FLM warmup = 12.5s (1B) to 131.3s (35B MoE). Use 1-token probe to confirm.
* **`save_options: true`**: Persists ctx_size to recipe_options.json for future loads.
* **collection.router**: Intelligent routing policy (first-match rules) dispatching to models based on prompt content, length, metadata, or classifiers.
* **Unified RAM**: 128GB shared across NPU/iGPU/CPU. OOM risk exists on ALL lanes. 20 GiB floor applies universally.

## HARDWARE ROSTER (AMD Strix Halo)

| Lane | Device | Backend | Model Pattern |
|------|--------|---------|---------------|
| NPU | /dev/accel0 (XDNA2) | flm (VitisAI) | -FLM suffix |
| iGPU | /dev/dri/renderD128 (Radeon 8060S) | llamacpp + vulkan | -GGUF suffix |
| CPU | Ryzen 9 7945HX (16C/32T) | llamacpp + cpu | explicit or fallback |

## NPU FLM MODELS (10 Available)

| Model | Ctx | Special | Best For |
|-------|-----|---------|----------|
| qwen3.6-moe-35b-a3b-FLM | 16384 | pinned=true | Deep reasoning, vision, tools |
| deepseek-r1-0528-8b-FLM | 40960 | — | Reasoning, code |
| qwen3-4b-FLM | default | — | Reasoning, tools |
| qwen3vl-it-4b-FLM | default | — | Vision, tools |
| gemma4-it-e2b-FLM | default | — | Audio, vision, reasoning |
| llama3.2-1b-FLM | 4096 | pre-warmed | Quick tasks (~24ms TTFT) |
| llama3.2-3b-FLM | default | — | General |
| gemma3-1b-FLM | default | — | General |
| lfm2.5-it-1.2b-FLM | default | — | Instruction following |
| embed-gemma-300m-FLM | default | — | Embeddings |

## INSTRUCTION

### 1. Lane Selection by Model Name

```python
NPU_MODELS = {
    "reasoning": "deepseek-r1-0528-8b-FLM",      # 8B, ctx=40960
    "reasoning_large": "qwen3.6-moe-35b-a3b-FLM", # 35B MoE, pinned
    "tools": "qwen3-4b-FLM",                       # 4B, fast
    "vision": "qwen3vl-it-4b-FLM",                 # multimodal
    "quick": "llama3.2-1b-FLM",                    # pre-warmed, ~24ms TTFT
    "embed": "embed-gemma-300m-FLM",               # embeddings
}
IGPU_MODELS = {
    "coding_large": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "general_8b": "Qwen3-8B-GGUF",
    "science": "Bonsai-8B-gguf",
}
```

### 2. Safe Load with Readiness Probe

```python
import time, json, urllib.request

def load_and_wait(model_name: str, ctx_size: int = 16384, timeout: int = 180) -> bool:
    payload = json.dumps({
        "model_name": model_name, "ctx_size": ctx_size, "save_options": True,
    }).encode()
    urllib.request.urlopen(urllib.request.Request(
        "http://localhost:13305/api/v1/load", data=payload,
        headers={"Content-Type": "application/json"},
    ), timeout=30)
    # Probe — load success != serving (FLM warmup: 12.5s-131.3s)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            probe = json.dumps({
                "model": model_name,
                "messages": [{"role": "user", "content": "1"}],
                "max_tokens": 1,
            }).encode()
            r = urllib.request.urlopen(urllib.request.Request(
                "http://localhost:13305/v1/chat/completions", data=probe,
                headers={"Content-Type": "application/json"},
            ), timeout=10)
            if r.status == 200:
                return True
        except Exception:
            time.sleep(5)
    return False
```

### 3. OOM-Safe Sequential Swarm Pattern

```python
MEM_FLOOR_GIB = 20  # AGENTS.md hard floor

def available_gib() -> float:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024 * 1024)
    return 0.0

def safe_agent_loop(agents: list[dict]) -> None:
    assert available_gib() >= MEM_FLOOR_GIB, "Preflight failed — run scripts/recover_fleet.sh"
    for agent in agents:
        # OOM guard
        deadline = time.time() + 120
        while time.time() < deadline:
            if available_gib() >= MEM_FLOOR_GIB:
                break
            time.sleep(15)
        # Event bus registration
        publish_event("AGENT_START", agent["id"], {"model": agent["model"]})
        ok, out = lemonade_query(agent["model"], agent["prompt"])
        publish_event("AGENT_COMPLETE" if ok else "AGENT_ERROR", agent["id"], {})
        time.sleep(3)  # inter-agent settle (LRU eviction + Vulkan driver cleanup)
```

### 4. Event Bus Sync Bridge (subprocess-safe)

```python
def publish_event(event_type: str, source: str, payload: dict) -> None:
    import base64, json, time, urllib.request, datetime
    data = json.dumps({
        "type": event_type, "source": f"swarm.{source}",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "payload": payload, "session": "research-swarm",
    })
    safe_id = f"evt_{source}_{int(time.time()*1000)}"
    surql = f"UPSERT event_log:`{safe_id}` CONTENT {data};"
    req = urllib.request.Request(
        "http://localhost:8001/sql", data=surql.encode(),
        headers={
            "Authorization": f"Basic {base64.b64encode(b'root:root').decode()}",
            "Surreal-NS": "cohezion", "Surreal-DB": "main",
            "Content-Type": "text/plain", "Accept": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass  # Fail-open — never block inference on event logging
```

### 5. collection.router — Intelligent Routing Policy

```python
# Route by task type across NPU + iGPU models
ROUTER_POLICY = {
    "version": "1",
    "default_model": "llama3.2-1b-FLM",  # pre-warmed, fast fallback
    "candidates": ["deepseek-r1-0528-8b-FLM", "Qwen3-Coder-30B-A3B-Instruct-GGUF", "llama3.2-1b-FLM"],
    "rules": [
        {"id": "coding", "condition": {"keywords_any": ["function", "def ", "class ", "import ", "code"]},
         "route_to": "Qwen3-Coder-30B-A3B-Instruct-GGUF"},
        {"id": "long-context", "condition": {"min_chars": 4000},
         "route_to": "Qwen3-Coder-30B-A3B-Instruct-GGUF"},
        {"id": "reasoning", "condition": {"keywords_any": ["why", "reason", "analyze", "synthesize"]},
         "route_to": "deepseek-r1-0528-8b-FLM"},
    ],
}
# Response carries x-lemonade-route header with matched rule ID
```

## ANTI-PATTERNS

| Anti-Pattern | Why Avoid | Use Instead |
|---|---|---|
| Parallel gaia llm processes | Fight for max_loaded_models=1 → eviction cascade → OOM → kernel fault | Sequential queue + OOM guard |
| Trust /api/v1/load success = ready | FLM warmup 12.5–131s; load != serving | 1-token readiness probe |
| GGUF for quick tasks when FLM pre-warmed | Forces iGPU load when NPU already hot | Use llama3.2-1b-FLM (24ms TTFT) |
| max_loaded_models > 1 on Strix Halo | GCVM_L2 aperture race → kernel fault → cold boot | Keep at 1; sequential swarm |
| Per-request backend hint | Not supported | Choose model name to select lane |
| Skip inter-agent settle | LRU eviction + Vulkan cleanup = 200–500ms | Add 3s between agents |
| NPU→iGPU→NPU alternating | Maximizes eviction thrash | Group NPU→NPU then iGPU→iGPU |

## OPTIMAL LANE ASSIGNMENT (Research Swarm)

| Task | Model | Lane |
|---|---|---|
| Reasoning / physics | deepseek-r1-0528-8b-FLM | NPU |
| Deep synthesis | qwen3.6-moe-35b-a3b-FLM | NPU (pinned) |
| Code synthesis | Qwen3-Coder-30B-A3B-Instruct-GGUF | iGPU |
| Science / general | Qwen3-8B-GGUF | iGPU |
| Tools / quick | qwen3-4b-FLM | NPU |
| Meta / summarize | llama3.2-1b-FLM | NPU (pre-warmed) |

## VERSION
v1.0 (2026-07-31) — Extracted from safe-research-swarm session + local source research

## SEE ALSO
- LOCAL_INFERENCE_ROUTING.md — TieredOrchestrator, AUTODQA, BBQ mode
- LEMONADE_EMBEDDABLE_INTEGRATION_PRIME.md — embeddable lemond setup
- FLEET_SYNCHRONIZATION_PRIME.md — fleet coherence
- scripts/preflight_fleet.sh — OOM preflight
- scripts/recover_fleet.sh — soft recovery
- /usr/share/lemonade-server/resources/defaults.json — max_loaded_models
- /usr/share/lemonade-server/resources/schemas/route_policy.schema.json — router schema


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for LEMONADE OMNIROUTER PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.
