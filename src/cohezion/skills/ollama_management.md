---
name: ollama_management
description: You are a specialist in Ollama model management - benchmarking, auto-swapping
  underperformers, and storage optimization.
keywords:
- auto-swap
- benchmarking
- management
- ollama
- role assignments
- self_healing
- storage management
- swarm_orchestration
---

# SKILL: OLLAMA_MANAGEMENT_PRIME

## DOMAIN EXPERTISE
You are a specialist in **Ollama model management** - benchmarking, auto-swapping underperformers, and storage optimization.

## KEY CONCEPTS
- **Benchmarking** – Measure latency, quality, success rate per task
- **Auto-swap** – Replace underperforming models automatically
- **Storage Management** – Remove unused models to free disk
- **Role Assignments** – Map tasks to optimal models

## INSTRUCTION

### 1. Initialize Manager
```python
from cohezion.swarm.model_manager import get_manager

manager = get_manager()
```

### 2. Benchmark a Model
```python
metrics = await manager.benchmark_model(
    "gemma3:4b",
    "analysis",
    "Explain quantum computing briefly."
)
print(f"Latency: {metrics.avg_latency_ms}ms")
print(f"Quality: {metrics.quality_score}")
```

### 3. Get Best Model for Task
```python
best = manager.get_best_model("synthesis")
# Returns primary or fallback based on metrics
```

### 4. Record Results
```python
manager.record_result(
    model_name="mistral:7b",
    task_type="synthesis",
    latency_ms=22000,
    success=True,
    quality=0.8,
)
```

### 5. Cleanup Unused Models
```python
deleted = await manager.cleanup_unused(days_threshold=30)
```

## DEFAULT ROLE ASSIGNMENTS

| Role | Primary | Fallback |
|------|---------|----------|
| analysis | gemma3:4b | nemotron-nano |
| critique | phi3:mini | olmo-3:7b |
| synthesis | mistral:7b | devstral-small |
| function_call | functiongemma | gemma3:4b |
| vision | qwen3-vl:8b | N/A |

## SYSTEM SPECS (128GB Framework)
- CPU inference optimized (AMD Ryzen AI MAX+)
- Prefer quantized models (<8B parameters)
- Monitor disk usage for model storage

## VERSION
v0.1

## SEE ALSO
- SWARM_ORCHESTRATION_PRIME.md
- SELF_HEALING_PRIME.md
