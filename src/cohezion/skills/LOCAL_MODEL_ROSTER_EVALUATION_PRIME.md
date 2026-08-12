# SKILL: LOCAL_MODEL_ROSTER_EVALUATION_PRIME

## DOMAIN EXPERTISE
Defines the local model roster, hardware lane routing rules, load safety constraints, and decision criteria for when and why to execute each local model across AMD Strix Halo NPU, iGPU, and CPU silicon.

## KEY TEXTS & CONCEPTS
- **NPU Reasoning Lane**: `deepseek-r1-0528-8b-FLM` (port 13305, 40,960 ctx) for deep CoT logic & math.
- **iGPU Coding Lane**: `Qwen3-Coder-30B` (port 13305, 32,768 ctx) for multi-file code generation & AST AutoHarness verifiers.
- **NPU MoE Sparse Lane**: `qwen3.6-moe-35b-a3b-FLM` (port 13305, 16,384 ctx) for high-throughput research synthesis.
- **NPU Vision Lane**: `qwen3vl-it-4b-FLM` (port 13305, 16,384 ctx) for UI/UX inspection & diagram-to-code.
- **NPU Fast Lane**: `llama3.2-1b-FLM` (port 13305, 4,096 ctx) for intent classification & fast Q&A (<20ms).
- **NPU Embeddings Lane**: `embed-gemma-300m-FLM` (port 13305, 8,192 ctx) for 768D vector search & HNSW indexing.
- **iGPU Creative Synthesis**: `Muse-Glimmer-30B-GGUF-UD-Q5_K_L` for ultra-detailed uncensored reasoning.
- **Weight-Fit Load Guard (`check_load_safe`)**: Enforces 16.0 GB RAM floor and 1.7x size factor to prevent over-commit freezes.
- **Fleet Lock Mutex (`FleetLock("modelload")`)**: Single-flight load lock serializing concurrent model loads.

## INSTRUCTION

### 1. Model Selection Decision Tree
```python
from cohezion.inference.unified_hybrid_router import TaskClass, UnifiedHybridRouter

router = UnifiedHybridRouter()

# Fast Q&A / Routing (<20ms)
res_qa = await router.route_by_capability(prompt, task_class=TaskClass.FAST_QA)

# Multi-file Coding & Refactoring
res_code = await router.route_by_capability(prompt, task_class=TaskClass.CODING)

# Deep Logic & Math (NPU CoT)
res_reasoning = await router.route_by_capability(prompt, task_class=TaskClass.REASONING)

# Research Synthesis (NPU MoE 35B/3B)
res_research = await router.route_by_capability(prompt, task_class=TaskClass.RESEARCH)
```

### 2. Weight-Fit Safety Verification
```python
from cohezion.inference.load_safety import check_load_safe
from cohezion.reliability.oom_guard import OOMGuard

mem = OOMGuard.get_memory_state()
ok, reason = check_load_safe({"size": 18.2, "recipe": "gguf"}, available_gb=mem.available_gb)
if not ok:
    # Safely hold in queue or fall through to Tier 2 Ollama Cloud
    pass
```

## VERSION
v1.0

## SEE ALSO
- `EXPERIENCE_VAE_TRAINING_PRIME.md`
- `JACOBIAN_J_SPACE_WORKSPACE_PRIME.md`
