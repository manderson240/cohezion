---
name: ollama-cloud-models-guide-prime
description: "Cohezion autonomous capability for OLLAMA CLOUD MODELS GUIDE PRIME."
metadata:
  version: "1.0"
  concepts: ["Cohezion", "FLUME", "AutoHarness"]
  source: "src/cohezion/skills/OLLAMA_CLOUD_MODELS_GUIDE_PRIME.md"
---

# SKILL: OLLAMA_CLOUD_MODELS_GUIDE_PRIME

## DOMAIN EXPERTISE
Expert guide for querying, routing, and configuring all Tier-2 Ollama Cloud models (`deepseek-v4-pro:cloud`, `glm-5.2:cloud`, `qwen3.5:397b-cloud`, `mistral-large-2026:cloud`, `step3-vl:cloud`) within Cohezion's `UnifiedHybridRouter`.

## KEY TEXTS & CONCEPTS
- **Tier 2 Delegation**: Activated when local NPU/iGPU context > local limit, local memory headroom < 20GB, or required model parameter scale exceeds local capacity (e.g. 397B scale).
- **EVI Threshold Gate**: Escalates to Tier 2 only when $\text{EVI} = \frac{\text{quality\_gap} \times \text{task\_importance}}{\text{cost}} > 0.75$.
- **Ollama API Protocol**: REST JSON calls to `http://localhost:11434/api/generate` or `/api/chat`.

## INSTRUCTION

### 1. Ollama Cloud Model Roster

| Model ID | Category | Primary Use Case | Recommended Sampling | Context Window |
| :--- | :--- | :--- | :--- | :--- |
| `deepseek-v4-pro:cloud` | Deep Reasoning | Logic, proof verification, math | `temp=0.2, top_p=0.95` | 128,000 |
| `glm-5.2:cloud` | Frontier Science | Architecture synthesis, research | `temp=0.2, top_p=0.90` | 128,000 |
| `qwen3.5:397b-cloud` | Frontier Coding | Multi-file code generation, refactoring | `temp=0.1, top_p=0.95` | 262,144 |
| `mistral-large-2026:cloud` | Fast Q&A | Overflow summarization, triage | `temp=0.5, top_p=0.90` | 128,000 |
| `step3-vl:cloud` | Multimodal / Vision | Diagram-to-code, UI/UX audit | `temp=0.2, top_p=0.95` | 64,000 |

### 2. Standardized Python Helper Code

```python
import json
import urllib.request
from typing import Any

OLLAMA_URL = "http://localhost:11434/api/generate"


def query_ollama_cloud(model_id: str, prompt: str, temperature: float = 0.2) -> str:
    """Send request to Ollama Cloud model with card-aligned sampling."""
    payload = {
        "model": model_id,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.loads(r.read().decode())
        return res.get("response", "").strip()
```

## VERSION
v1.0

## SEE ALSO
- `LOCAL_MODEL_ROSTER_EVALUATION_PRIME.md`
- `src/cohezion/inference/unified_hybrid_router.py`


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for OLLAMA CLOUD MODELS GUIDE PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.
