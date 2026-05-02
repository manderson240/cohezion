"""
CDNA4 optimization planning prompts.

Three prompt templates for GPU kernel optimization:
1. SELECT_ACTION: Pick best optimization from frontier
2. REFINE_CODE: Generate HIP C++ implementation
3. UPDATE_TREE: Insert/Update/Prune based on feedback

CDNA4-specific knowledge encoded in prompts.
"""

from typing import Any


# ─── CDNA4 Architecture Knowledge Base ─────────────────────────────────────────
CDNA4_KNOWLEDGE = """
AMD Instinct MI355X (CDNA4/gfx950) Architecture:

Hardware Specifications:
- LDS capacity: 160 KB per CU (2.5x vs CDNA3's 64 KB)
- LDS bandwidth: 256 bytes/clock (2x vs CDNA3)
- LDS banks: 64 (vs 32 on CDNA3) - reduces bank conflicts
- GLOBAL_LOAD_LDS: 128-bit per lane (4x vs CDNA3's 32-bit)
- Wavefront size: 64 lanes (wave64)
- FP4 MFMA: V_MFMA_SCALE_F32_16X16X128_F8F6F4 instruction
- Matrix Core shapes: 16x16x128, 32x32x64 for FP4

Optimization Techniques:
1. Inline FP4 quantization using IEEE 754 bit manipulation
   - E8M0 scale: rounded = (bits + 0x200000) & 0xFF800000
   - fp4 e2m1 encoding: 4 bits (1 sign, 1 exp, 2 mantissa)
   - Max value: 6.0 (= 2^2 × 1.5)

2. Direct global→LDS transfers (128-bit/lane)
   - llvm_amdgcn_raw_buffer_load_lds intrinsic
   - Bypasses VGPR staging, reduces register pressure

3. LDS swizzle for bank conflict avoidance
   - XOR remap: col ^ mask(row)
   - mask = ((row >> 1) & 7) ^ (((row >> 1) ^ (row >> 2)) & 1) << 4

4. 8-wave ping-pong scheduling
   - 512 threads = 8 waves (64 lanes each)
   - Alternate memory waves (0-3) with compute waves (4-7)
   - __builtin_amdgcn_s_barrier() for wave synchronization
   - __builtin_amdgcn_s_setprio(1) for high-priority MFMA
   - __builtin_amdgcn_sched_barrier(0) for instruction fence

5. MFMA 16x16x128 with double buffering
   - Ping-pong LDS slots for K-major loop
   - Overlap global→LDS load with MFMA compute
   - Target: 2680 TFLOPS (vs hipBLASLt 2750 TFLOPS)

Performance Path (M=N=K=4096):
- Naive: 1.15 TFLOPS
- LDS tiling: 4.80 TFLOPS (4.2x)
- Matrix-core: 30.05 TFLOPS (6.3x)
- Vectorized loads: 336.88 TFLOPS (11.2x)
- Direct global→LDS: 506.70 TFLOPS (1.5x)
- LDS swizzle: 497.43 TFLOPS (-1.8%)
- Double buffering: 1166.41 TFLOPS (2.34x)
- Multi-wave (256x256): 2288.16 TFLOPS (2.0x)
- 8-wave ping-pong: 2680.33 TFLOPS (1.17x)
- hipBLASLt: 2750.42 TFLOPS (target)
"""

# ─── Prompt 1: Action Selection ───────────────────────────────────────────────
SELECT_ACTION_PROMPT = """
You are a world model for GPU kernel optimization on AMD MI355X (CDNA4).

Given the current search frontier (pending optimization hypotheses),
select the highest-priority action to explore next.

Consider:
1. Hardware characteristics (LDS capacity, MFMA shapes, wave64)
2. Current best performance ({current_best} µs)
3. Optimization complexity (simple tuning vs structural changes)
4. Likelihood of success based on CDNA4 architecture

Frontier nodes:
{frontier_nodes}

Task: Select the next action and justify your choice.

Respond in JSON format:
{{
  "selected_node_id": "...",
  "priority_score": 0.0-1.0,
  "justification": "...",
  "expected_improvement": "X% latency reduction"
}}
"""

# ─── Prompt 2: Code Refinement ────────────────────────────────────────────────
REFINE_CODE_PROMPT = """
You are an expert HIP C++ kernel engineer for AMD MI355X (CDNA4/gfx950).

Implement the following optimization intent in HIP C++:

Optimization Intent: {optimization_intent}
Kernel Type: {kernel_type}
Parent Program: {parent_program}

CDNA4 Architecture Context:
{cdn4_knowledge}

Requirements:
1. Correctness: Must match reference implementation (rtol=1e-2, atol=1e-2)
2. Performance: Target < {target_latency} µs geomean
3. Single-file submission: Embed all code in submission.py (Popcorn CLI compatible)
4. Compilation: Must compile with hipcc -O3 -march=gfx950

Generate complete HIP C++ kernel code with:
- Proper includes (#include <hip/hip_runtime.h>)
- Kernel launch configuration (grid/block dimensions)
- Memory hierarchy optimization (LDS, registers, global)
- Synchronization primitives (__syncthreads, wave barriers)
- MFMA instructions if applicable

Respond with:
1. Complete HIP kernel source code
2. Expected performance improvement
3. Potential risks (compilation, correctness, register pressure)
"""

# ─── Prompt 3: Tree Update ────────────────────────────────────────────────────
UPDATE_TREE_PROMPT = """
You are a world model analyzing GPU kernel optimization progress.

Given the execution feedback from a kernel evaluation,
update the search tree by:
1. Inserting new child nodes (promising refinements)
2. Updating priority scores (based on new evidence)
3. Pruning low-priority branches (remove from search)

Execution Feedback:
- Node ID: {node_id}
- Optimization Intent: {optimization_intent}
- Success: {success}
- Latency: {latency} µs (geomean: {geomean} µs)
- Correctness: {correctness}
- Error Message: {error_msg}

Current Search State:
- Best latency: {best_latency} µs
- Total evaluations: {evaluations}
- Budget remaining: {budget}

Task: Propose tree edits (Insert/Update/Prune).

Respond in JSON format:
{{
  "inserts": [
    {{
      "parent_node_id": "...",
      "new_intent": "...",
      "priority_score": 0.0-1.0,
      "justification": "..."
    }}
  ],
  "updates": [
    {{
      "node_id": "...",
      "new_priority": 0.0-1.0,
      "reason": "..."
    }}
  ],
  "prunes": [
    {{
      "node_id": "...",
      "reason": "..."
    }}
  ]
}}
"""


def format_select_action_prompt(
    frontier_nodes: list[dict[str, Any]],
    current_best: float,
) -> str:
    """Format SELECT_ACTION prompt with frontier data."""
    nodes_text = "\n".join(
        [
            f"- {n['node_id']}: {n['optimization_intent']} (p={n['priority_score']})"
            for n in frontier_nodes
        ]
    )
    return SELECT_ACTION_PROMPT.format(
        current_best=current_best,
        frontier_nodes=nodes_text,
    )


def format_refine_code_prompt(
    optimization_intent: str,
    kernel_type: str,
    parent_program: str,
    target_latency: float,
) -> str:
    """Format REFINE_CODE prompt with optimization details."""
    return REFINE_CODE_PROMPT.format(
        optimization_intent=optimization_intent,
        kernel_type=kernel_type,
        parent_program=parent_program,
        target_latency=target_latency,
        cdm4_knowledge=CDNA4_KNOWLEDGE,
    )


def format_update_tree_prompt(
    node_id: str,
    optimization_intent: str,
    success: bool,
    latency: float,
    geomean: float,
    correctness: bool,
    error_msg: str,
    best_latency: float,
    evaluations: int,
    budget: int,
) -> str:
    """Format UPDATE_TREE prompt with execution feedback."""
    return UPDATE_TREE_PROMPT.format(
        node_id=node_id,
        optimization_intent=optimization_intent,
        success=success,
        latency=latency,
        geomean=geomean,
        correctness=correctness,
        error_msg=error_msg,
        best_latency=best_latency,
        evaluations=evaluations,
        budget=budget,
    )


if __name__ == "__main__":
    # Demo: Print CDNA4 knowledge base
    print("CDNA4 Knowledge Base:")
    print(CDNA4_KNOWLEDGE[:500] + "...")

    # Demo: Format prompts
    frontier = [
        {"node_id": "kernel_v1", "optimization_intent": "Fused quant+GEMM", "priority_score": 0.9},
        {"node_id": "kernel_v2", "optimization_intent": "8-wave ping-pong", "priority_score": 0.8},
    ]
    print("\nSELECT_ACTION Prompt:")
    print(format_select_action_prompt(frontier, current_best=14.1))
