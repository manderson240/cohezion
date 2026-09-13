---
name: fastflowlm-prime
description: "Expert in AMD ROCm FastFlowLM (FLM v1.0.4) NPU runtime, XDNA2 silicon acceleration (/dev/accel/accel0), sub-2W energy envelope, zero UMA contention, Lemonade OmniRouter integration (:13305), and BAML + AutoHarness verification."
---

# SKILL: FASTFLOWLM_PRIME

## DOMAIN EXPERTISE
Expert in AMD ROCm FastFlowLM (`FLM v1.0.4`) runtime deployment, hardware configuration, and inference routing on AMD Ryzen AI / Strix Halo XDNA2 NPUs (`/dev/accel/accel0`, 8 NPU columns, FW 1.1.2.65, `amdxdna` driver 0.7). Specializes in ultra-low-power (<2W) continuous background goal steering, zero UMA memory contention, Lemonade OmniRouter (`recipe: flm`, port 13305), and robust structured output extraction using BAML resilient parsing and AutoHarness deterministic bytecode verification.

## KEY TEXTS & CONCEPTS
* **Official Repository**: `https://github.com/ROCm/FastFlowLM`
* **NPU Hardware Topology**: AMD XDNA2 NPU accessed via `/dev/accel/accel0` with 8 compute columns and infinite memlock.
* **Sub-2W Power Envelope**: FLM runs entirely on NPU SRAM, consuming <2W with 0 CPU and 0 iGPU utilization, completely preserving the 122GB UMA pool for large 30B+ models.
* **CLI & Server Flags**:
  - `flm run <model>`: Interactive CLI execution.
  - `flm serve <model>`: Launches local HTTP server (default port 52625).
  - `--pmode <powersaver|balanced|performance|turbo>`: NPU frequency scaling profile.
  - `-e, --embed 1`: Activates concurrent embedding model alongside LLM.
  - `-a, --asr 1`: Loads automatic speech recognition engine.
  - `-c, --ctx-len <len>`: Explicit NPU context window reservation.
  - `--prefill-chunk-len <len>`: Configures chunked prompt prefill for sustained throughput.
  - `--preemption 1`: Enables request preemption on NPU queue.
* **Lemonade OmniRouter Integration**:
  - Models with suffix `-FLM` (e.g. `llama3.2-1b-FLM`, `qwen3-4b-FLM`, `deepseek-r1-0528-8b-FLM`) use `recipe: flm`.
  - Served via Lemonade on port `13305` (with backend workers on designated ports).
* **Deterministic Structured Extraction**:
  - FLM is an independent from-scratch NPU runtime, not llama.cpp. It ignores GBNF sampler grammars silently.
  - Structured extraction on NPU is solved through prompt schema instructions + `BAMLResilientParser` healing + AutoHarness verification (<1 ms latency).
  - When strict sampler-level token forcing is required, dispatch cascades to `llamacpp` recipe models (`Bonsai-8B-gguf`, `Qwen3-Coder-30B-GGUF`).

## INSTRUCTION

### 1. Validating NPU Hardware Stack
Verify kernel, firmware, and NPU device column readiness before initiating swarm workloads:

```bash
flm validate
# Expected output:
# [Linux] Kernel: 7.0.0-31-generic
# [Linux] NPU: /dev/accel/accel0 with 8 columns
# [Linux] NPU FW Version: 1.1.2.65
# [Linux] amdxdna version: 0.7
# [Linux] Memlock Limit: infinity
```

### 2. Inspecting and Managing Installed NPU Models
Query installed model tags from the local FLM repository:

```bash
flm list --filter installed
# Available NPU models:
# - llama3.2:1b (fast reflex & routing, ~24ms TTFT)
# - deepseek-r1-0528:8b (NPU reasoning, 40k context)
# - qwen3.5:4b (general instruction & tools)
# - qwen3.6-moe:35b-a3b (MoE reasoning flagship)
# - gemma3:4b (multimodal vision & audio)
```

### 3. Structured Extraction via BAML + AutoHarness
Execute schema-compliant inference without depending on GBNF sampler constraints:

```python
from cohezion.inference.structured_npu import npu_structured_json

schema = {
    "properties": {
        "node": {"type": "string"},
        "confidence": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["node", "confidence"],
}

# Executes on NPU with BAML heuristic healing and AutoHarness verification
result = npu_structured_json(
    "Classify task priority: 'Verify Kaggle AGI progress submissions'",
    schema,
    model="llama3.2-1b-FLM",
    strict_sampler=False,
)
# Returns verified dictionary: {"node": "npu", "confidence": 0.95, "rationale": "..."}
```

### 4. Lemonade Fleet Lock & Admission Discipline
Adhere to the 16 GB unified memory admission floor on AMD Strix Halo:
* Never spawn parallel loaders. Always acquire `FleetLock("modelload")` before loading models.
* Deduct resident model footprints (e.g. pinned models) when calculating available memory headroom.
* Configure fallback cascades to resident GGUF models (`Bonsai-8B-gguf`, `Qwen3-Coder-30B`) when NPU admission is constrained.

## VERSION
v0.1

## SEE ALSO
* LEMONADE_OMNIROUTER_PRIME
* AUTOHARNESS_PRIME
* BAML_PRIME
