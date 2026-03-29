# Luma AMD Speedrun — V2 Orchestration Plan
## K-Search × R-Zero × AutoResearch: Winning the 16.7× MLA Gap

**Session:** 20260319_112740  
**Purpose:** Refine and extend the V1 plan with recursive experiential learning, multi-agent orchestration, and breakthrough-focused optimization

---

## Executive Summary

The V1 plan correctly identified:
- MLA is 16.7× behind leader (PRIORITY #1)
- MoE is 1.03× behind (almost there)
- GEMM is 2.3× behind (medium priority)

**But V1 has critical gaps:**
1. No actual multi-agent spawning (just stubs)
2. World model not actively guiding exploration
3. No recursive skill extraction from experiments
4. No local Ollama integration for rapid prototyping
5. Incremental tweaks won't close 16.7× gap — need breakthrough thinking

---

## Part I: The 16.7× MLA Gap — Why Incrementalism Fails

### Current Best: 72µs | Leader: 4.3µs | Gap: 16.7×

The leader's 4.3µs implies something fundamentally different:

```
72µs ÷ 4.3µs = 16.7× faster

Possible explanations:
1. Single fused MFMA kernel (no Python overhead, no indirection)
2. Persistent KV cache in L2 (no global memory loads per step)
3. Wave-level softmax with shuffle (not per-thread reductions)
4. MXFP4 KV throughout (4-bit vs FP8's 8-bit = 2× bandwidth)
5. Hardware prefetching + double buffering
6. All of the above
```

### The Fundamental Problem

Current `mla_aiter_max_tuned.py` uses AITER's `mla_decode_fwd` which:
- Has ~20-30µs overhead from Python call + metadata setup
- Uses generic kernel paths, not competition-optimized
- Doesn't exploit CDNA 3 MFMA at full utilization

The `mla_mfma_pure.py` correctly identifies the MFMA approach but:
- Has compilation complexity (HIP source in Python string)
- Falls back to AITER on any error (defeats the purpose)
- Doesn't handle persistent mode correctly

### Breakthrough Hypothesis

**V=0.95:** The leader uses a **hand-written ASM kernel** that:
1. Bypasses AITER entirely (no Python overhead)
2. Keeps KV in L2 via persistent wavefronts
3. Uses `__builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4` at peak utilization
4. Wave-level online softmax with `__shfl_xor`

**V=0.80:** AITER's built-in kernels CAN reach 4-6µs if:
- All env vars are optimally set
- Persistent mode is fully utilized  
- num_kv_splits is tuned per-shape

**V=0.30:** Custom HIP kernel is too risky due to compilation + debugging time

### Strategy: Pursue All Three in Parallel

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (this agent)                     │
│  Role: Plan, synthesize, route, extract skills                  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│ MLA-ASM AGENT   │  │ MLA-AITER AGENT │  │ MLA-HIP AGENT           │
│ (breakthrough)  │  │ (proven path)   │  │ (high risk/high reward) │
│                 │  │                 │  │                         │
│ Direct ASM      │  │ Max-tune AITER  │  │ Custom MFMA kernel      │
│ kernel writing  │  │ env vars        │  │ with persistence        │
│                 │  │                 │  │                         │
│ V=0.95         │  │ V=0.80         │  │ V=0.30                  │
└─────────────────┘  └─────────────────┘  └─────────────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                   ┌─────────────────────┐
                   │ WORLD MODEL AGENT   │
                   │ (V-score tracking) │
                   │ (Skill extraction) │
                   └─────────────────────┘
```

---

## Part II: K-Search × R-Zero Hybrid Architecture

### Core Principles

From **K-Search (arXiv:2602.19128v2)**:
1. **Decouple planning from implementation** — High-level intent first, code second
2. **Co-evolve world model** — Update beliefs based on execution feedback
3. **Navigate non-monotonic paths** — Don't discard strategies due to transient errors
4. **Stagnation condition: K=7** — Try 7 times before giving up on a strategy
5. **V ∈ [0,1]** — Priority scores based on world model confidence

From **R-Zero**:
1. **Minimal agent loop** — Generate → Execute → Evaluate → Repeat
2. **Recursive skill acquisition** — Extract patterns from successful runs
3. **Multi-agent specialization** — Different agents for different hypothesis types
4. **Experiential learning** — Each iteration improves the world model

### Agent Team (4 Specialist Agents)

```python
AGENTS = {
    "mla_asm": {
        "role": "MLA ASM Kernel Specialist",
        "target": "Hand-written assembly for MI355X",
        "model": "qwen2.5-coder:14b",  # Code gen
        "reasoner": "deepseek-r1:7b",    # Strategic reasoning
        "v_score": 0.95,
        "priority": 1,
    },
    "mla_aiter": {
        "role": "MLA AITER Max-Tuning Specialist",
        "target": "Optimal AITER env var configuration",
        "model": "qwen2.5-coder:14b",
        "reasoner": "deepseek-r1:7b",
        "v_score": 0.80,
        "priority": 2,
    },
    "mla_hip": {
        "role": "MLA HIP Kernel Specialist",
        "target": "Custom MFMA kernel with persistence",
        "model": "qwen2.5-coder:14b",
        "reasoner": "deepseek-r1:7b",
        "v_score": 0.30,
        "priority": 3,
    },
    "world_model": {
        "role": "World Model + Skill Extraction",
        "target": "V-score tracking, pattern extraction",
        "model": "phi3:mini",  # Fast, cheap for updates
        "reasoner": None,
        "v_score": 1.0,  # Always running
        "priority": 0,
    },
}
```

### Orchestration Loop (K-Search × R-Zero Hybrid)

```
┌──────────────────────────────────────────────────────────────────┐
│ ITERATION CYCLE (target: 10 min via parallel execution)          │
│                                                                  │
│ 1. ORCHESTRATOR reads world model, assigns priorities            │
│    Priority queue: MLA-ASM (V=0.95) > MLA-AITER (V=0.80) > ... │
│                                                                  │
│ 2. SPECIALIST agents generate in PARALLEL:                        │
│    ┌──────────────────────────────────────────────────────────┐  │
│    │ MLA-ASM: Probe AITER source for hidden env vars          │  │
│    │          Write minimal HIP wrapper for ASM kernel        │  │
│    │          Test compilation on MI355X                      │  │
│    ├──────────────────────────────────────────────────────────┤  │
│    │ MLA-AITER: Grid search env vars                          │  │
│    │            Test: PERSISTENT × GFX950_EXPL × KSPLIT      │  │
│    │            Profile each combination                      │  │
│    ├──────────────────────────────────────────────────────────┤  │
│    │ MLA-HIP: Refine MFMA pure kernel                         │  │
│    │          Add persistent wavefront management              │  │
│    │          Test on MI355X                                  │  │
│    └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│ 3. WORLD MODEL updates V-scores from each result:               │
│    - Improvement: V_score += 0.1 (max 1.0)                      │
│    - No improvement: V_score -= 0.05 (min 0.0)                  │
│    - Stagnation (K=7 fails): Mark stale, explore alternatives   │
│                                                                  │
│ 4. SKILL EXTRACTION: If breakthrough, extract pattern to vault   │
│    Pattern format: [[observation]] [[action]] [[reward]]        │
│                                                                  │
│ 5. REPEAT until MLA < 10µs OR top-10 qualifier achieved         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Part III: Experiential Recursive Learning System

### The R-Zero Experience Replay

From **R-Zero paper**: Each experiment is stored as:
```
[[observation]] — Context before the experiment
[[action]]      — What we changed
[[reward]]      — Performance delta (speedup ratio)
```

### World Model Structure

```python
@dataclass
class Experiment:
    id: str
    timestamp: datetime
    kernel_type: str  # "mla", "gemm", "moe"
    hypothesis_id: str
    
    # Experience replay format (R-Zero)
    observation: str   # World model state before
    action: str       # Code/config change
    reward: float     # speedup_ratio
    
    # Result metrics
    execution_time_us: float
    correctness: bool
    test_shape: dict
    
    # World model updates
    v_score_delta: float
    new_v_score: float
    status: str  # "active", "stale", " breakthrough"

@dataclass  
class Hypothesis:
    id: str
    description: str
    kernel_type: str
    v_score: float  # Confidence 0-1
    attempts: int
    k_stagnation: int  # Count of failed attempts
    
    # From K-Search paper
    priority: float  # Computed from v_score × impact
    parent_id: str | None  # For mutation tracking
    
    # R-Zero experience links
    experiments: list[str]  # Experiment IDs
    
    status: str  # "active", "stale", "validated", "refuted"
```

### Skill Extraction Loop

```
After each experiment:

1. WORLD MODEL AGENT checks if reward > threshold
   - If breakthrough (speedup > 1.5×): Extract skill
   - If improvement (speedup > 1.1×): Log pattern
   - If regression: Log failure mode

2. SKILL FORMAT (R-Zero / AutoResearch):
   ```markdown
   ## Skill: MLA-MFMA-Persistent-001
   Trigger: MLA decode, bs≥32, kvseqlen≥1024
   Action: Use __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4
           with persistent wavefronts
   Reward: 3-5× speedup vs LUT approach
   Source: experiment_20260319_001
   ```

3. Update vault with new skill
   - ~/vaults/cohezion-vault/luma-amd-speedrun/skills/
   - Include: code snippet, env vars, expected performance

4. Cross-kernel transfer check
   - Does this pattern apply to GEMM or MoE?
   - Log transfer opportunities
```

---

## Part IV: MLA Breakthrough Execution Plan

### Track 1: MLA-ASM (V=0.95, Priority 1)

**Approach:** Probe AITER's hidden ASM kernels for direct invocation

```python
# Strategy: Find the kernel that achieves 4.3µs
# AITER likely has optimized ASM kernels not exposed via Python API

MLA_ASM_VARIANTS = [
    {
        "name": "mla_asm_probe_kernel_names",
        "action": "inspect.getsource(mla_decode_fwd) to find kernel names",
        "expected": "Discovery of gfx950-specific kernel names",
    },
    {
        "name": "mla_asm_direct_dispatch", 
        "action": "Call kernel directly via hipModule* APIs (if allowed)",
        "expected": "Bypass AITER Python overhead",
    },
    {
        "name": "mla_asm_env_explore",
        "action": "Grid search: AITER_MLA_* env vars not documented",
        "expected": "Find hidden optimization flags",
    },
]
```

### Track 2: MLA-AITER-Max (V=0.80, Priority 2)

**Approach:** Exhaustive env var grid search

```python
# AITER env vars to grid search
MLA_AITER_GRID = {
    "AITER_MLA_USE_PERSISTENT": ["0", "1"],
    "AITER_GFX950_EXPL_SCHED": ["0", "1"],
    "AITER_USE_NT": ["0", "1"], 
    "AITER_BYPASS_TUNE_CONFIG": ["0", "1"],
    "AITER_KSPLIT": ["1", "2", "4", "8", "16", "32"],
    "AITER_NUM_KV_SPLITS": ["8", "16", "32", "64"],
    # Hidden vars to discover
}

# Run combinatorial grid (6 vars × 2-6 values = 64-1000 combos)
# Use beam search: Start with current best, mutate one var at a time
```

### Track 3: MLA-HIP (V=0.30, Priority 3)

**Approach:** Custom MFMA kernel with persistence

```python
# Key optimizations for mla_mfma_pure.py
MLA_HIP_IMPROVEMENTS = [
    {
        "name": "mla_hip_persistent_waves",
        "action": "Use persistent kernel with wavefront recycling",
        "expected": "Keep KV in L2, eliminate global memory loads",
    },
    {
        "name": "mla_hip_fp4_kv_mfma",
        "action": "FP4 KV → FP8 dequant → MFMA in one instruction",
        "expected": "2× bandwidth reduction vs FP8 KV",
    },
    {
        "name": "mla_hip_async_copy",
        "action": "Use async copy to overlap KV load with compute", 
        "expected": "Hide memory latency",
    },
]
```

---

## Part V: GEMM + MoE Optimization (Maintain Position)

### GEMM (2.3× gap, V=0.70)

Current best: 20.8µs | Target: <12µs

```python
GEMM_STRATEGY = {
    "priority": 2,  # Secondary to MLA
    "approach": "Shape-adaptive tile selection + quantization elimination",
    "variants": [
        {
            "name": "gemm_inline_quant",
            "action": "Fuse quantize+gemm in single Triton kernel",
            "expected": "Eliminate 10-13µs quantization overhead",
        },
        {
            "name": "gemm_splitk_largek",
            "action": "Manual split-K for K=7168 shape",
            "expected": "1.3× speedup for large-K shapes",
        },
    ],
}
```

### MoE (1.03× gap, V=0.90)

Current best: 155µs | Target: <150µs

```python
MOE_STRATEGY = {
    "priority": 3,  # Tertiary — almost there
    "approach": "Validate and refine adaptive KSPLIT",
    "variants": [
        {
            "name": "moe_verify_doweight_false",
            "action": "Confirm doweight_stage1=False is critical",
            "expected": "1.02× improvement by ensuring no other issues",
        },
        {
            "name": "moe_expert_count_routing", 
            "action": "Route E=257 vs E=33 differently",
            "expected": "1.05× improvement for E=33 shapes",
        },
    ],
}
```

---

## Part VI: Implementation — Agent Spawning

### Multi-Agent Spawning (R-Zero Style)

```python
#!/usr/bin/env python3
"""
spawn_agents.py — R-Zero × K-Search Multi-Agent Orchestration

Spawns specialist agents for parallel kernel optimization.
Each agent:
1. Receives hypothesis + world model state
2. Generates code/config changes
3. Returns results for world model update

Usage:
    python spawn_agents.py --kernel mla --strategy asm
    python spawn_agents.py --kernel gemm --strategy inline_quant
"""

import argparse
import json
import subprocess
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
SESSION_DIR = Path(__file__).parent
CHALLENGERS_DIR = SESSION_DIR / "challengers"
VAULT_DIR = SESSION_DIR / "vault"
WORLD_MODEL_FILE = SESSION_DIR / "world-model" / "hypotheses.json"

# Model configuration (Ollama)
CODE_MODEL = "qwen2.5-coder:14b"
REASONER_MODEL = "deepseek-r1:7b"
FAST_MODEL = "phi3:mini"

# Kernel configurations
MLA_PROMPT = """You are the MLA-{strategy} Agent for the Luma AMD Speedrun.

Current state:
- Best time: 72µs (LUT approach) or 20-30µs (AITER)
- Leader: 4.3µs
- Gap: 16.7×

Your strategy: {strategy_description}

Generate a submission.py variant that:
1. Implements {strategy} approach
2. Has clear docstrings
3. Falls back to AITER on error (if custom kernel)
4. Includes performance measurement

Output: Complete submission.py file content."""

GEMM_PROMPT = """You are the GEMM-{strategy} Agent for the Luma AMD Speedrun.

Current state:
- Best time: 20.8µs
- Leader: 9µs  
- Gap: 2.3×

Your strategy: {strategy_description}

Generate a submission.py variant that:
1. Implements {strategy} approach
2. Has clear docstrings
3. Uses AITER gemm_a4w4_asm correctly
4. Includes performance measurement

Output: Complete submission.py file content."""

MOE_PROMPT = """You are the MoE-{strategy} Agent for the Luma AMD Speedrun.

Current state:
- Best time: 155µs
- Leader: 140µs
- Gap: 1.03×

Your strategy: {strategy_description}

Generate a submission.py variant that:
1. Implements {strategy} approach  
2. Has clear docstrings
3. Uses AITER fused_moe correctly
4. Includes performance measurement

Output: Complete submission.py file content."""


class AgentSpawner:
    """Spawns and coordinates specialist agents."""
    
    def __init__(self, ollama_host: str = "localhost:11434"):
        self.ollama_host = ollama_host
        self.code_model = CODE_MODEL
        self.reasoner = REASONER_MODEL
        
    def generate_code(
        self,
        kernel: str,
        strategy: str,
        strategy_description: str
    ) -> str:
        """Use Ollama to generate kernel variant code."""
        import urllib.request
        import urllib.error
        
        if kernel == "mla":
            prompt = MLA_PROMPT.format(
                strategy=strategy,
                strategy_description=strategy_description
            )
        elif kernel == "gemm":
            prompt = GEMM_PROMPT.format(
                strategy=strategy,
                strategy_description=strategy_description
            )
        else:  # moe
            prompt = MOE_PROMPT.format(
                strategy=strategy,
                strategy_description=strategy_description
            )
        
        data = json.dumps({
            "model": self.code_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 8192,  # Longer output for code
            }
        }).encode()
        
        req = urllib.request.Request(
            f"http://{self.ollama_host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                return result.get("response", "")
        except Exception as e:
            print(f"Ollama error: {e}")
            return ""
    
    def spawn_mla_agents(self) -> list[dict]:
        """Spawn MLA specialist agents."""
        strategies = [
            ("asm_probe", "Probe AITER for hidden kernel names and env vars"),
            ("aiter_max", "Max-tune AITER with exhaustive env var grid"),
            ("hip_mfma_persistent", "Custom MFMA kernel with persistent waves"),
            ("fp4_kv_mfma", "FP4 KV → MFMA fused approach"),
        ]
        
        results = []
        for strategy, description in strategies:
            print(f"\nSpawning MLA-{strategy} agent...")
            
            code = self.generate_code("mla", strategy, description)
            
            # Write to challenger file
            output_path = CHALLENGERS_DIR / "mla" / f"mla_{strategy}.py"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(code)
            
            results.append({
                "strategy": strategy,
                "path": str(output_path),
                "status": "generated"
            })
        
        return results
    
    def spawn_gemm_agents(self) -> list[dict]:
        """Spawn GEMM specialist agents."""
        strategies = [
            ("inline_quant", "Fuse quantization into Triton GEMM kernel"),
            ("splitk_largek", "Manual split-K for large K shapes"),
            ("256tile", "256×128 tile for very large M"),
        ]
        
        results = []
        for strategy, description in strategies:
            print(f"\nSpawning GEMM-{strategy} agent...")
            
            code = self.generate_code("gemm", strategy, description)
            
            output_path = CHALLENGERS_DIR / "gemm" / f"gemm_{strategy}.py"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(code)
            
            results.append({
                "strategy": strategy,
                "path": str(output_path),
                "status": "generated"
            })
        
        return results
    
    def spawn_moe_agents(self) -> list[dict]:
        """Spawn MoE specialist agents."""
        strategies = [
            ("expert_count_routing", "Route E=257 vs E=33 differently"),
            ("adaptive_ksplit_v2", "Refined adaptive KSPLIT based on multiple dims"),
            ("verify_doweight_false", "Confirm doweight_stage1=False critical"),
        ]
        
        results = []
        for strategy, description in strategies:
            print(f"\nSpawning MoE-{strategy} agent...")
            
            code = self.generate_code("moe", strategy, description)
            
            output_path = CHALLENGERS_DIR / "moe" / f"moe_{strategy}.py"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(code)
            
            results.append({
                "strategy": strategy,
                "path": str(output_path),
                "status": "generated"
            })
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Spawn specialist agents")
    parser.add_argument("--kernel", required=True, choices=["mla", "gemm", "moe"])
    parser.add_argument("--parallel", action="store_true", help="Spawn all kernels in parallel")
    
    args = parser.parse_args()
    
    spawner = AgentSpawner()
    
    if args.kernel == "mla":
        results = spawner.spawn_mla_agents()
    elif args.kernel == "gemm":
        results = spawner.spawn_gemm_agents()
    else:
        results = spawner.spawn_moe_agents()
    
    print(f"\nSpawned {len(results)} agents:")
    for r in results:
        print(f"  - {r['strategy']}: {r['path']}")


if __name__ == "__main__":
    main()
```

---

## Part VII: World Model + Vault Integration

### V-Score Update Rules (K-Search)

```python
V_SCORE_RULES = {
    # Experiment outcomes
    "breakthrough": {  # speedup > 2×
        "v_delta": +0.2,
        "action": "Extract skill, promote to champion",
    },
    "improvement": {  # speedup > 1.1×
        "v_delta": +0.1,
        "action": "Log pattern, continue iteration",
    },
    "neutral": {  # 0.95 < speedup < 1.1
        "v_delta": 0.0,
        "action": "Continue iteration",
    },
    "regression": {  # speedup < 0.95
        "v_delta": -0.05,
        "action": "Log failure, consider alternative",
    },
    "crash": {  # GPU fault, timeout
        "v_delta": -0.1,
        "action": "Mark as broken path, backtrack",
    },
    
    # Stagnation condition (K-Search)
    "stagnation_threshold": 7,  # K=7 fails
    "stagnation_action": "Mark stale, explore alternatives",
    
    # V-score bounds
    "v_min": 0.0,
    "v_max": 1.0,
}
```

### Vault Structure

```
~/vaults/cohezion-vault/luma-amd-speedrun/
├── patterns/
│   ├── mla/
│   │   ├── asm-probe-findings.md
│   │   ├── aiter-env-var-grid.md
│   │   ├── mfma-persistent-pattern.md
│   │   └── fp4-kv-mfma-pattern.md
│   ├── gemm/
│   │   ├── inline-quant-pattern.md
│   │   ├── splitk-largek-pattern.md
│   │   └── 256tile-pattern.md
│   └── moe/
│       ├── expert-count-routing.md
│       └── adaptive-ksplit-v2.md
├── failures/
│   ├── mla-lut-broken.md
│   ├── gemm-cktile-unsupported.md
│   └── moe-doweight-stage1-broken.md
├── decisions/
│   ├── 20260319-priority-mla-asm.md
│   └── 20260319-strategy-selection.md
├── skills/
│   ├── MLA-MFMA-Persistent-001.md
│   ├── GEMM-Inline-Quant-001.md
│   └── MoE-Adaptive-Ksplit-001.md
└── world-model/
    ├── hypotheses.json
    ├── experiments/
    │   ├── exp_20260319_001.json
    │   ├── exp_20260319_002.json
    │   └── ...
    └── v_scores.json
```

### Skill Format (R-Zero / AutoResearch compatible)

```markdown
# Skill: MLA-MFMA-Persistent-001

## Metadata
- **Created**: 2026-03-19T11:27:40Z
- **Source Experiment**: exp_20260319_001
- **V-Score**: 0.85
- **Status**: validated

## Trigger Condition
```
kernel_type == "mla" AND
kvseqlen >= 1024 AND
bs >= 4 AND
current_best_us > 20
```

## Action Pattern
```python
# Use __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4
# with persistent wavefronts
# Keep KV in L2 cache throughout decode
```

## Expected Reward
- **Speedup**: 3-5× vs LUT approach
- **Target**: <20µs (vs current 72µs)

## Code Snippet
```cpp
// Persistent wavefronts for KV reuse
__global__ void mla_mfma_persistent_kernel(...) {
    // Wave 0: Load KV once, keep in LDS
    // Waves 1-N: Compute against cached KV
}
```

## Related Skills
- [[MLA-MFMA-FP4-KV-001]]
- [[MLA-AITER-Max-Tune-001]]

## Notes
Discovered through R-Zero × K-Search hybrid approach.
```

---

## Part VIII: Execution Timeline

### Day 1 (March 19): Setup + Initial Spawning

```
08:00  Read V1 plan, identify gaps
09:00  Write V2 orchestration plan
10:00  Spawn MLA-ASM agent (V=0.95)
       - Probe AITER source
       - Find hidden kernel names
11:00  Spawn MLA-AITER agent (V=0.80)
       - Grid search env vars
       - Profile each combination
12:00  Lunch
13:00  Spawn GEMM agents (V=0.70)
14:00  Spawn MoE agents (V=0.90)
15:00  Submit to popcorn-cli
16:00  Collect results, update world model
17:00  Extract skills from breakthroughs
18:00  End of day report
```

### Days 2-7: Iteration Loop

```
Each day:
08:00  Read world model, check V-scores
09:00  Spawn agents for stale hypotheses (K<7)
10:00  Parallel code generation
11:00  Parallel submission to popcorn-cli
12:00  Lunch
13:00  Wait for results (15-20 min)
14:00  Update world model with results
15:00  Extract skills, update vault
16:00  Identify next experiments
17:00  Evening report
```

### Exit Conditions

```
STOP when any:
1. MLA < 10µs (breakthrough, 7× improvement)
2. All three kernels in top-10
3. 100 iterations completed
4. Human explicit stop
```

---

## Part IX: Key Files

| File | Purpose |
|------|---------|
| `spawn_agents.py` | Multi-agent spawning driver |
| `run_orchestration.py` | V1 orchestration (stubs) |
| `world_model/hypotheses.json` | V-scores + hypotheses |
| `world_model/experiments/` | Experience replay |
| `vault/skills/` | Extracted skills |
| `challengers/{kernel}/*.py` | Generated variants |

---

## Part X: Risk Mitigation

### If MLA-ASM fails (V drops below 0.3):
- Pivot to MLA-AITER max-tuning
- Increase grid search resolution
- Try MLA-HIP as last resort

### If popcorn-cli times out:
- Retry during off-peak hours (nights)
- Split grid search into smaller batches
- Use cached JIT compilations

### If top-10 goal becomes unreachable:
- Focus on single kernel breakthrough
- Document learnings for Phase 2
- Prepare for Finals E2E optimization

---

## Appendix: Key Insights from Reference Papers

### From K-Search (arXiv:2602.19128v2)
- Planning-implementation decoupling is critical
- World model co-evolution enables faster convergence
- Non-monotonic paths require patience (K=7 stagnation)
- V-scores enable rational strategy selection

### From R-Zero
- Minimal agent loop: Generate → Execute → Evaluate → Repeat
- Recursive skill acquisition from successful experiments
- Multi-agent specialization accelerates exploration
- Experience replay enables learning from failures

### From karpathy/autoresearch
- Simple autonomous loop can achieve SOTA results
- Don't over-engineer — let the search discover patterns
- Human review only at milestones
- Code quality matters less than iteration speed

---

**Next Steps:**
1. Read this plan and confirm understanding
2. Spawn initial agents via `python spawn_agents.py --kernel mla`
3. Monitor results and update V-scores
4. Extract first skills from breakthrough experiments

Good luck, agent. The 16.7× gap is waiting to be closed. 🚀
