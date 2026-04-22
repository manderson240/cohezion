---
name: ollama-specialist-prime
description: "Expert in local model management via Ollama on AMD Strix Halo hardware. Handles VRAM/GTT monitoring, model concurrency, DynamicModelRouter tuning, and hardware-aware cost optimization."
---

# SKILL: OLLAMA_SPECIALIST_PRIME

## DOMAIN EXPERTISE
Expert in **local model management via Ollama on AMD Strix Halo hardware**. Handles VRAM/GTT monitoring, model concurrency, DynamicModelRouter tuning, and hardware-aware cost optimization.

## KEY CONCEPTS
- **UMA Architecture**: AMD Strix Halo uses unified memory — GTT pool (128GB) is the real capacity, NOT VRAM carveout (512MB).
- **Concurrency limit**: Max 4 simultaneous Ollama instances. Enforced by DynamicModelRouter.
- **Model tiers**: phi3:mini (fast/small), qwen3-coder:30b (code), deepseek-r1:70b (reasoning).
- **Cost**: $0/M tokens. Local inference is free — trade latency for cost.
- **Monitoring**: Use `/sys/class/drm/card*/device/` for AMD GPU metrics. `mem_info_gtt_total` for capacity.

## INSTRUCTION

1. **Health check**: `curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; print(len(json.load(sys.stdin)['models']))"` — count loaded models.
2. **Load management**: Never exceed 4 concurrent models. Unload idle models: `POST /api/generate {"model":"X","keep_alive":"0"}`.
3. **GTT monitoring**: Read `mem_info_gtt_total` and `mem_info_gtt_used` from sysfs. Alert at >80% utilization.
4. **Router tuning**: Edit `DynamicModelRouter` task→model mappings in `src/cohezion/swarm/dynamic_model_router.py`.
5. **Throughput tracking**: Log tokens/second per model per task type. Identify bottlenecks.

## PATTERNS
- phi3:mini for lint/test (high concurrency, low VRAM)
- deepseek-r1:70b ONLY when no other models loaded (16-32GB GTT)
- Pre-warm models before batch operations: `ollama run model ""` then kill

## ANTI-PATTERNS
- Assuming CUDA/RTX hardware (this is AMD iGPU — L89)
- Loading deepseek-r1:70b alongside 3 other models (OOM risk)
- Using `vram_total` for capacity checks on UMA systems (L84-85, L91)
- Blocking on slow inference without timeout (use keep_alive for lifecycle)

## VERSION
v1.0

## SEE ALSO
HARDWARE_PROFILE_PRIME, DynamicModelRouter (src/cohezion/swarm/dynamic_model_router.py)
