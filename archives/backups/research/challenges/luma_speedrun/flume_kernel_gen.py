#!/usr/bin/env python3
"""FLUME-powered kernel generation via Ollama cloud models.

Uses Cohezion's FLUME VAE (256D latent space) to encode kernel properties
into latent vectors, then decode novel kernel configurations.

For now: uses Ollama cloud models to explore the kernel configuration
space systematically, guided by our discovered constraints.
"""

import subprocess


OLLAMA_MODELS = [
    "deepseek-v3.2:cloud",  # Strong reasoning
    "kimi-k2.5:cloud",  # Large context
    "qwen3.5:397b-cloud",  # Code generation
    "gemma4:31b-cloud",  # Fast iteration
    "nemotron-3-super:cloud",  # GPU expertise
]

KERNELS = {
    "gemm": {
        "leaderboard": "amd-mxfp4-mm",
        "dir": "amd-mxfp4-mm",
        "current_best": 13.425,
        "constraints": [
            "BLOCK_K >= 128 for Triton tl.dot_scaled (MANDATORY)",
            "Use B_q not B_shuffle for custom MFMA kernels",
            "Python dispatch optimization HURTS ranked scores",
            "Only GPU compute changes help on ranked runner",
            "aiter.gemm_a4w4_asm with explicit kernel name is best API path",
            "log2_k_split=1 helps M=16,K=7168 bottleneck shape",
            "Runner has only 32x128 and 192x128 .co tiles",
        ],
    },
    "moe": {
        "leaderboard": "amd-moe-mxfp4",
        "dir": "amd-moe-mxfp4",
        "current_best": 154.183,
        "constraints": [
            "AITER_KSPLIT env var is IGNORED by kernel",
            "AITER_USE_NT=1 confirmed working",
            "Python dispatch optimization HURTS ranked scores",
            "fused_moe() with default params is near-optimal",
            "Pre-allocating buffers HURTS ranked (counterproductive)",
        ],
    },
    "mla": {
        "leaderboard": "amd-mixed-mla",
        "dir": "amd-mixed-mla",
        "current_best": 69.745,
        "constraints": [
            "Einsum BEATS ASM at total_kv <= 32768",
            "fast_mode=True/False makes no difference",
            "Python dispatch optimization HURTS ranked scores",
            "10% error tolerance is very relaxed",
            "BF16 attention (no FP8 quant) passes correctness",
        ],
    },
}


def generate_novel_kernel(kernel_name, model):
    """Ask Ollama to generate a novel kernel approach respecting constraints."""
    k = KERNELS[kernel_name]
    constraints = "\n".join(f"  - {c}" for c in k["constraints"])
    prompt = f"""Generate a NOVEL GPU kernel optimization for {kernel_name} on AMD MI355X.
Current best: {k["current_best"]}µs. Target: top 20 in competition.

HARD CONSTRAINTS (violating these GUARANTEES failure):
{constraints}

Generate a COMPLETELY DIFFERENT approach than what's been tried.
Think creatively — what if we combined techniques in a new way?
What if we used a different mathematical formulation?
What if we exploited hardware features nobody else is using?

Output ONLY the complete submission.py file. Must start with:
#!POPCORN leaderboard {k["leaderboard"]}
#!POPCORN gpu MI355X
"""
    try:
        result = subprocess.run(
            ["ollama", "run", model], input=prompt, capture_output=True, text=True, timeout=120
        )
        return result.stdout
    except Exception as e:
        print(f"Error with {model}: {e}")
        return None


def main():
    import sys

    kernel = sys.argv[1] if len(sys.argv) > 1 else "gemm"
    model = sys.argv[2] if len(sys.argv) > 2 else "deepseek-v3.2:cloud"

    print(f"FLUME kernel gen: {kernel} via {model}")
    code = generate_novel_kernel(kernel, model)
    if code:
        outfile = f"/home/mike-anderson/dev/cohezion/luma_speedrun/{KERNELS[kernel]['dir']}/submission_flume_{kernel}_{model.split(':')[0].replace('-', '_')}.py"
        with open(outfile, "w") as f:
            f.write(code)
        print(f"Written to {outfile} ({len(code)} chars)")


if __name__ == "__main__":
    main()
