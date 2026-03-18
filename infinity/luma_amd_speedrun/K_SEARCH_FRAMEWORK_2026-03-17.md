# K-Search Framework for Luma AMD Speedrun

**Created:** 2026-03-17  
**Status:** IMPLEMENTATION COMPLETE  
**Adapted from:** arxiv 2602.19128 (UC Berkeley, Feb 2026)

---

## Overview

K-Search (Kernel Search via Co-Evolving World Model) is an automated GPU kernel optimization framework adapted from the K-Search paper (arxiv 2602.19128).

**Original Results (NVIDIA H100):**
- **14.3× improvement** on FP8 MoE kernels (vs OpenEvolve)
- **2.10× average** across GQA/MLA/MoE kernels
- **1030µs** on GPUMODE TriMul (SOTA, beat human-designed 1074µs)

**Adaptation for AMD MI355X (CDNA4):**
- ROCm toolchain (hipcc, hiprtc)
- CDNA4-specific primitives (MFMA, LDS, wave64)
- Popcorn CLI evaluation backend
- K-Search methodology preserved

---

## Architecture

### Four Modules

| Module | Purpose | Lines |
|--------|---------|-------|
| `search_tree.py` | Search tree data structures | ~250 |
| `world_model.py` | LLM prompts for CDNA4 optimization | ~150 |
| `evaluator_rocm.py` | ROCm/Popcorn CLI evaluation backend | ~200 |
| `k_search.py` | Main optimization loop | ~250 |

**Total:** ~850 lines (minimal viable implementation)

---

## Search Tree Data Structure

```python
SearchNode:
  node_id: str
  kernel_type: str  # "gemm", "moe", "mla"
  optimization_intent: str  # e.g., "8-wave ping-pong"
  parent_program: str  # Path to HIP kernel
  priority_score: float  # [0,1]
  status: NodeStatus  # OPEN/CLOSED/PRUNED
  performance_latency: float  # µs
  correctness_pass: bool
  children: List[str]
```

**Search State:**
- Nodes: Dict of SearchNode
- Frontier: List of OPEN node IDs
- Best kernel: Path to fastest implementation
- Budget remaining: Evaluations left

---

## K-Search Loop (Three Phases)

### Phase 1: Action Selection
```python
# Query world model for best action
prompt = format_select_action_prompt(frontier_nodes, current_best)
response = llm.query(prompt)
selected_node = frontier[response["selected_node_id"]]
```

**Considers:**
- Hardware characteristics (LDS, MFMA, wave64)
- Current best performance
- Optimization complexity
- Likelihood of success

### Phase 2: Program Instantiation
```python
# Generate HIP kernel with stagnation tolerance (K=7)
stagnation = 0
while stagnation < 7:
    hip_source = generate_hip_code(intent)
    result = evaluate(hip_source)
    if result.success:
        stagnation = 0  # Reset on improvement
    else:
        stagnation += 1
```

**Stagnation tolerance:** Avoids discarding valid intents on transient compilation errors.

### Phase 3: World Model Update
```python
# Insert/Update/Prune based on feedback
prompt = format_update_tree_prompt(node, result)
response = llm.query(prompt)

for insert in response["inserts"]:
    tree.insert_child(insert["parent"], insert["intent"])
for update in response["updates"]:
    tree.update_priority(update["node"], update["priority"])
for prune in response["prunes"]:
    tree.prune_node(prune["node"])
```

---

## CDNA4 Knowledge Base

Encoded in `world_model.py`:

```
AMD Instinct MI355X (CDNA4/gfx950):
- LDS capacity: 160 KB per CU (2.5x vs CDNA3)
- LDS bandwidth: 256 bytes/clock (2x)
- LDS banks: 64 (vs 32)
- GLOBAL_LOAD_LDS: 128-bit per lane (4x)
- Wavefront size: 64 (wave64)
- FP4 MFMA: V_MFMA_SCALE_F32_16X16X128_F8F6F4

Performance Path (M=N=K=4096):
- Naive: 1.15 TFLOPS
- LDS tiling: 4.80 TFLOPS
- Matrix-core: 30.05 TFLOPS
- Vectorized loads: 336.88 TFLOPS
- Direct global→LDS: 506.70 TFLOPS
- LDS swizzle: 497.43 TFLOPS
- Double buffering: 1166.41 TFLOPS
- Multi-wave: 2288.16 TFLOPS
- 8-wave ping-pong: 2680.33 TFLOPS
- hipBLASLt: 2750.42 TFLOPS
```

---

## Evaluator Backend

### ROCm Evaluator
```python
evaluator = ROCM_Evaluator(
    kernel_type="gemm",
    use_popcorn=True,  # Use Popcorn CLI
)

result = evaluator.evaluate(hip_source)
# Returns: EvalResult(success, latency, correctness, ...)
```

### Evaluation Pipeline
1. **Compile:** hiprtc or hipcc
2. **Correctness:** 4/4 tests (rtol=1e-2, atol=1e-2)
3. **Benchmark:** Geomean across 6 shapes

### Popcorn CLI Integration
```bash
popcorn-cli submit \
  --no-tui \
  --mode test \
  --gpu MI355X \
  --leaderboard amd-mxfp4-mm \
  submission.py
```

---

## Initial Search Frontier (GEMM)

| Node ID | Intent | Priority | Parent |
|---------|--------|----------|--------|
| `gemm_fused_quant` | Fused quant+GEMM | 0.9 | baseline |
| `gemm_8wave_pingpong` | 8-wave ping-pong | 0.8 | baseline |
| `gemm_lds_swizzle` | LDS swizzle XOR | 0.75 | baseline |
| `gemm_direct_lds` | Direct global→LDS | 0.7 | baseline |
| `gemm_mfma_tuned` | MFMA tile tuning | 0.65 | baseline |

**Expected improvements:**
- `gemm_fused_quant`: 30% reduction (14.1→~10 µs)
- `gemm_8wave_pingpong`: 17% reduction (2288→2680 TFLOPS)
- `gemm_lds_swizzle`: 10% reduction (bank conflicts)

---

## Usage

### Initialize Search Tree
```python
from k_search import init_search_tree

tree = init_search_tree()
# Creates 5 initial hypotheses for GEMM
```

### Run Optimization
```bash
python -m k_search.k_search \
  --kernel gemm \
  --budget 30 \
  --stagnation 7 \
  --output k_search/search_state.json
```

### Inspect Search State
```python
from k_search import SearchTree

tree = SearchTree("k_search/search_state.json")
print(f"Best kernel: {tree.state.best_kernel}")
print(f"Best latency: {tree.state.best_latency} µs")
print(f"Frontier: {len(tree.state.frontier)} nodes")
```

---

## Integration with HIP C++ Implementation

### Current Status
- `fused_mxfp4_gemm.hip` (200+ lines) → Becomes `gemm_fused_quant` parent
- `submission_hip_fused.py` → Evaluator calls this
- `HIP_CPP_FUSED_GEMM_2026-03-17.md` → Search tree initial state

### Next Steps
1. **Merge K-Search with HIP code:**
   - `k_search/programs/gemm_fused_quant.hip` → Copy from `fused_mxfp4_gemm.hip`
   - Update evaluator to use existing HIP source

2. **Run first iteration:**
   - Select `gemm_fused_quant` (p=0.9)
   - Evaluate (compile + test + benchmark)
   - Update tree based on results

3. **Generate refinements:**
   - Insert children: `gemm_fused_quant_8wave`, `gemm_fused_quant_lds`
   - Update priorities based on performance

---

## Expected Performance

### K-Search Results (NVIDIA H100)
| Kernel | K-Search | OpenEvolve | Improvement |
|--------|----------|------------|-------------|
| FP8 MoE | 44.1 | 3.09 | **14.3×** |
| MLA Prefill | 57.4 | 19.5 | 2.95× |
| GQA Decode | 76.0 | 44.2 | 1.72× |
| MLA Decode | 47.1 | 39.9 | 1.18× |
| **Overall** | **56.13** | 26.68 | **2.10×** |

### AMD MI355X Projections
| Kernel | Current | K-Search Target | Gap |
|--------|---------|-----------------|-----|
| GEMM | 14.1 µs | 10-11 µs | 1.3-1.4× |
| MoE | 158 µs | 140-145 µs | 1.09-1.13× |
| MLA | 73.6 µs | 65-70 µs | 1.05-1.13× |

**Note:** K-Search adapts optimization methodology, not absolute performance.

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM code generation quality | Medium | High | Use stagnation tolerance (K=7) |
| Popcorn CLI timeout | Low | High | Increase timeout (300s) |
| Search tree complexity | Medium | Medium | Start minimal (5 intents, K=3) |
| Budget exhaustion | Low | Medium | Prioritize GEMM (highest ROI) |

---

## Files

| Path | Purpose |
|------|---------|
| `k_search/search_tree.py` | Search tree data structures |
| `k_search/world_model.py` | LLM prompts (CDNA4 knowledge) |
| `k_search/evaluator_rocm.py` | ROCm/Popcorn evaluation |
| `k_search/k_search.py` | Main optimization loop |
| `k_search/__init__.py` | Package exports |
| `k_search/search_state.json` | Persisted search state |
| `k_search/programs/` | Generated HIP kernels |

---

## References

1. **K-Search Paper:** arxiv 2602.19128 (UC Berkeley, Feb 2026)
2. **K-Search Code:** https://github.com/caoshiyi/K-Search
3. **AMD FP8 GEMM Blog:** https://rocm.blogs.amd.com/software-tools-optimization/cdna4-gemm-kernels/README.html
4. **CDNA4 ISA:** https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/instruction-set-architectures/amd-instinct-cdna4-instruction-set-architecture.pdf

---

**Status:** FRAMEWORK COMPLETE → READY FOR INTEGRATION

**Next:** Merge with HIP C++ implementation, run first optimization iteration.
