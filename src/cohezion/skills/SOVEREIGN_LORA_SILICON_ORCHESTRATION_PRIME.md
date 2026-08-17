# SKILL: SOVEREIGN_LORA_SILICON_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
Autonomous local gradient-descent LoRA fine-tuning, dynamic UMA/APU memory allocation (OOMGuard safety), EventBus lifecycle orchestration, and zero-token AST verification on AMD Strix Halo architecture (Zen 5 CPU, XDNA 2 NPU, Radeon 8060S iGPU).

## KEY TEXTS & CONCEPTS
- **Memory Aperture Separation**: Never initialize uncoordinated ROCm GPU contexts concurrently with Lemonade resident models. Segregate training workloads to 16-core Zen 5 AVX-512 CPU or serialize via `FleetLock("modelload")` / `FleetLock("gpu_training")`.
- **Dynamic Floor Gating**: Require `OOMGuard.get_memory_state().is_safe` and `available_gb >= 20.0` before initiating backprop passes.
- **Event-Driven Telemetry**: Mandatory typed lifecycle events (`training_started`, `training_completed`, `training_aborted`) broadcast across `EventBus` to prevent daemon drift.
- **Low-Rank Efficiency**: Target $r=16$, $\alpha=32$ on projection layers (`q_proj`, `k_proj`, `v_proj`, `o_proj`), yielding $<0.5\%$ trainable parameter footprint.

## INSTRUCTIONS

1. **Preflight Memory & Fleet Verification**:
```python
from cohezion.reliability.oom_guard import OOMGuard
from cohezion.core.event_bus import Event, get_event_bus

mem = OOMGuard.get_memory_state()
if not mem.is_safe or mem.available_gb < 20.0:
    raise MemoryError(f"Insufficient UMA headroom: {mem.available_gb:.2f} GiB available")
```

2. **EventBus Lifecycle Broadcast**:
```python
bus = await get_event_bus()
await bus.publish(Event(
    type="training_started",
    source="sovereign_lora",
    payload={"model": base_model_name, "samples": len(dataset), "available_gb": mem.available_gb},
))
```

3. **Safe Device Allocation & PEFT Configuration**:
```python
from peft import LoraConfig, get_peft_model, TaskType

# Set device to 'cpu' on Zen 5 or acquire exclusive FleetLock for GPU
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)
model = get_peft_model(model, lora_config)
```

4. **Checkpoint Export & Invariant Verification**:
Export `.safetensors` and test with `AutoHarness` 0ms AST checks before serving.

## VERSION
v1.0 (August 2026)

## SEE ALSO
- `AUTOHARNESS_PRIME.md`
- `OOM_GUARD_PRIME.md`
- `LEMONADE_OMNIROUTER_PRIME.md`
