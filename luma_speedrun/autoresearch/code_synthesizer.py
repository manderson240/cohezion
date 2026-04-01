"""LLM-based kernel code synthesizer with MI355X-specific meta-prompts.

Implements pi_code from K-Search: generates concrete kernel code from a
high-level optimization strategy. Uses QiMeng-style 5-tuple meta-prompts
decomposed into: tiling, reordering, vectorization, layout, pipeline.

LLM backend: local Ollama (qwen3-coder:30b) with streaming.
Falls back to deterministic templates if Ollama unavailable.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3-coder:30b"
OLLAMA_TIMEOUT_PER_CHUNK = 120  # seconds per streaming chunk


# ── MI355X Hardware Constants ──────────────────────────────────────────

MI355X = {
    "compute_pflops_bf16": 1.3,
    "hbm3_bandwidth_tb_s": 8.0,
    "cus": 256,
    "wave_size": 64,
    "lds_per_cu_kb": 64,
    "vgpr_per_cu": 512,
    "sgpr_per_cu": 108,
    "mfma_block_sizes": [16, 32],
    "xcds": 8,
    "fp4_mfma": "mfma_f32_32x32x64_f8f6f4",
    "scale_mfma": True,
    "hbm3_burst_bytes": 256,
}


# ── QiMeng-Style 5-Tuple Meta-Prompt Templates ────────────────────────

@dataclass
class MetaPrompt:
    """MI355X-specific structured meta-prompt for kernel generation."""
    kernel_type: str  # "gemm", "moe", "mla"
    tiling: str
    reordering: str
    vectorization: str
    layout: str
    pipeline: str

    def render(self, strategy: str) -> str:
        return f"""You are an expert AMD MI355X (gfx950) GPU kernel engineer.

TARGET: {self.kernel_type.upper()} kernel optimization
STRATEGY: {strategy}

HARDWARE CONSTRAINTS (MI355X / gfx950):
- 256 CUs, wave64 (64 threads per wave)
- MFMA: {MI355X['fp4_mfma']} with scale MFMA for MXFP4
- 8 XCDs (cross-die clusters) — tile scheduling must be XCD-aware
- HBM3 bandwidth: 8 TB/s, burst size: 256 bytes
- LDS: 64 KB per CU, 512 VGPRs per CU
- ROCm 7.1, PyTorch 2.10+rocm7.1

5-TUPLE OPTIMIZATION DECOMPOSITION:

1. TILING: {self.tiling}
2. REORDERING: {self.reordering}
3. VECTORIZATION: {self.vectorization}
4. LAYOUT: {self.layout}
5. PIPELINE: {self.pipeline}

RULES:
- Output ONLY valid Python code (submission.py format)
- Must import from aiter, torch — no custom HIP compilation
- Must pass correctness check (rtol=1e-2 vs reference)
- Include type hints and minimal comments
- The function signature must match: custom_kernel(data: input_t) -> output_t
"""


# ── Per-Kernel Meta-Prompt Factories ──────────────────────────────────

def gemm_meta_prompt() -> MetaPrompt:
    return MetaPrompt(
        kernel_type="gemm",
        tiling=(
            "MFMA block: 32x32x64 for MXFP4. Tile M/N to fill 256 CUs. "
            "For small M (4-64), use tall-skinny tiles (M=block, N=large). "
            "BLOCK_K >= 128 for tl.dot_scaled. XCD-aware: total_tiles % 8 == 0."
        ),
        reordering=(
            "fp4x2 packing: 2 fp4 values per byte. E8M0 scale shuffle required. "
            "B matrix pre-shuffled (bpreshuffle=True). "
            "Consider fusing quantization into GEMM to eliminate 26µs quant dispatch."
        ),
        vectorization=(
            "Use gemm_a4w4 (ASM path) — 7-10µs for MXFP4 GEMM. "
            "VGPR budget: 512 per CU. Coalesced HBM3 reads: 256-byte aligned. "
            "Avoid 4D tensor ops (materialize penalty)."
        ),
        layout=(
            "A: [M, K//2] fp4x2 (row-major). B: [N, K//2] fp4x2 (pre-shuffled). "
            "A_scale: [M, K//32] fp8_e8m0. B_scale: [N, K//32] fp8_e8m0. "
            "Output: [M, N] bf16."
        ),
        pipeline=(
            "Quant (26-84µs) → shuffle (1-3µs) → GEMM (7-10µs). "
            "Bottleneck is quant dispatch. Fusing quant+shuffle saved 23.8%. "
            "Explore: can we overlap quant with previous iteration's GEMM?"
        ),
    )


def moe_meta_prompt() -> MetaPrompt:
    return MetaPrompt(
        kernel_type="moe",
        tiling=(
            "MoE has 2-stage CK pipeline: stage1 (gate_up GEMM) + stage2 (down GEMM). "
            "block_m={32, 64, 128}. For 256-expert shapes with bs=16, most experts empty — "
            "consider expert-skipping tiles. KSPLIT: 0 for CK path, 2-4 for cktile."
        ),
        reordering=(
            "moe_sorting_fwd reorders tokens by expert (coalesced access). "
            "sorted_token_ids, sorted_expert_ids, num_valid_ids from sorting. "
            "local_expert_mask parameter in sorting may skip empty experts."
        ),
        vectorization=(
            "CK ASM kernels handle vectorization internally. "
            "For Python-level: minimize torch ops between stage1 and stage2. "
            "SiLU activation applied in-kernel for split_k=0, else separate silu_and_mul."
        ),
        layout=(
            "hidden_states: [M, K] bf16. w1: [E, N*2, K//2] fp4x2 (gate+up fused). "
            "w2: [E, K, N//2] fp4x2. Scales: [E, dim, K//32] fp8_e8m0. "
            "All weights pre-shuffled (is_shuffled=True for MXFP4)."
        ),
        pipeline=(
            "sort → quant_a1 → stage1(gate_up) → silu_and_mul → quant_a2 → stage2(down). "
            "JIT builds: 128-260s (tight under 720s timeout). "
            "sys.path fix needed for JIT build dirs on runner."
        ),
    )


def mla_meta_prompt() -> MetaPrompt:
    return MetaPrompt(
        kernel_type="mla",
        tiling=(
            "MLA decode: Q@K^T (bs, 1, nheads, 576) × KV (bs, kvseqlen, 1, 576). "
            "Three-regime routing: matmul for small (bs<=4 OR total_kv<=32768), "
            "aiter ASM for large. Tile by num_kv_splits: adaptive schedule "
            "{1, 4, 8, 16, 32} based on total_kv."
        ),
        reordering=(
            "MLA fused KV buffer: K=576, V=512 (K≠V head dimension). "
            "Q in [bs, nheads, QK_HEAD_DIM=576]. KV in [bs, kvseqlen, 1, 576]. "
            "V extracted as KV[..., :V_HEAD_DIM]. No transpose needed for 3D matmul."
        ),
        vectorization=(
            "Small shapes: torch.matmul (3D batched GEMM) — Python dispatch floor ~22µs. "
            "Large shapes: mla_decode_stage1_asm_fwd + mla_reduce_v1. "
            "fast_mode=False is FASTER on MI355X (CU work distribution effect)."
        ),
        layout=(
            "q_input: reshaped for ASM kernel. kv_4d: [bs, kvseqlen, 1, 576]. "
            "Metadata: 8 tensors (work_meta_data, work_indptr, etc.) — cache these. "
            "Intermediates: logits, attn_lse pre-allocated in cache."
        ),
        pipeline=(
            "Python dispatch floor: ~20-25µs per torch op. Leader at 33µs uses "
            "single fused CK/ASM kernel with zero Python overhead. "
            "Our 69.7µs = 3 torch ops + metadata. "
            "Metadata caching gave 25% improvement (Phase 10)."
        ),
    )


META_PROMPTS = {
    "gemm": gemm_meta_prompt,
    "moe": moe_meta_prompt,
    "mla": mla_meta_prompt,
}


# ── LLM Code Synthesis ────────────────────────────────────────────────

def _call_ollama(prompt: str, max_tokens: int = 4096) -> str | None:
    """Call local Ollama with streaming to avoid timeout."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"num_predict": max_tokens, "temperature": 0.7},
    }).encode()

    req = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    chunks: list[str] = []

    try:
        with urlopen(req, timeout=OLLAMA_TIMEOUT_PER_CHUNK) as resp:
            for line in resp:
                if not line.strip():
                    continue
                data = json.loads(line)
                token = data.get("response", "")
                chunks.append(token)
                if data.get("done", False):
                    break
    except (URLError, TimeoutError, OSError) as e:
        logger.warning("Ollama unavailable: %s", e)
        return None

    return "".join(chunks)


def synthesize_kernel(
    kernel_type: str,
    strategy: str,
    context: str = "",
    custom_meta_prompt: str | None = None,
) -> str | None:
    """Generate kernel code using LLM with MI355X meta-prompts.

    Args:
        kernel_type: "gemm", "moe", or "mla"
        strategy: High-level optimization strategy description
        context: Additional context (previous attempts, error messages)
        custom_meta_prompt: Override the default meta-prompt

    Returns:
        Generated Python code string, or None if LLM unavailable
    """
    if custom_meta_prompt:
        prompt = custom_meta_prompt
    else:
        factory = META_PROMPTS.get(kernel_type)
        if not factory:
            logger.error("Unknown kernel type: %s", kernel_type)
            return None
        meta = factory()
        prompt = meta.render(strategy)

    if context:
        prompt += f"\n\nCONTEXT FROM PREVIOUS ATTEMPTS:\n{context}\n"

    prompt += "\n\nGenerate the optimized kernel code now. Output ONLY Python code, no explanation."

    start = time.monotonic()
    code = _call_ollama(prompt)
    elapsed = time.monotonic() - start

    if code:
        logger.info("Synthesized %d chars in %.1fs for %s/%s", len(code), elapsed, kernel_type, strategy)
        return _extract_python(code)

    logger.warning("LLM synthesis failed, falling back to template for %s", kernel_type)
    return None


def _extract_python(text: str) -> str:
    """Extract Python code from LLM output (may be wrapped in ```python blocks)."""
    if "```python" in text:
        parts = text.split("```python")
        if len(parts) > 1:
            code = parts[1].split("```")[0]
            return code.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            return parts[1].strip()
    return text.strip()


def get_meta_prompt_for_kernel(kernel_type: str) -> MetaPrompt | None:
    """Get the MI355X meta-prompt for a kernel type."""
    factory = META_PROMPTS.get(kernel_type)
    return factory() if factory else None


if __name__ == "__main__":
    # Demo: print meta-prompts for all kernels
    for kt in ("gemm", "moe", "mla"):
        mp = get_meta_prompt_for_kernel(kt)
        if mp:
            print(f"\n{'='*60}")
            print(f" {kt.upper()} Meta-Prompt")
            print(f"{'='*60}")
            print(mp.render("example_strategy"))
