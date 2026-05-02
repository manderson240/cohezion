#!/usr/bin/env python3
"""
R-Zero × K-Search Multi-Agent Orchestration

Spawns specialist agents for parallel kernel optimization.
Each agent:
1. Receives hypothesis + world model state
2. Generates code/config changes via Ollama
3. Returns results for world model update

Based on principles from:
- K-Search (arXiv:2602.19128v2): V-scores, world model co-evolution, K=7 stagnation
- R-Zero: Minimal agent loop, recursive skill acquisition
- karpathy/autoresearch: Simple autonomous search, human review at milestones

Usage:
    python spawn_agents.py --kernel mla --strategy asm_probe
    python spawn_agents.py --kernel mla --all
    python spawn_agents.py --kernel gemm --strategy inline_quant
    python spawn_agents.py --kernel moe --strategy expert_count_routing
"""

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


# ─── Configuration ────────────────────────────────────────────────────────────

SESSION_DIR = Path(__file__).parent
CHALLENGERS_DIR = SESSION_DIR / "challengers"
VAULT_DIR = SESSION_DIR / "vault"
WORLD_MODEL_FILE = SESSION_DIR / "world-model" / "hypotheses.json"
SKILLS_DIR = VAULT_DIR / "skills"

# Ollama configuration
OLLAMA_HOST = "localhost:11434"
CODE_MODEL = "qwen3.5:cloud"
REASONER_MODEL = "deepseek-r1:7b"
FAST_MODEL = "phi3:mini"

# Verify models are available (for display purposes)
AVAILABLE_MODELS = [
    "qwen3.5:cloud",
    "qwen2.5-coder:14b",
    "deepseek-r1:7b",
    "phi3:mini",
    "cohezion_v2:latest",
]

# Kernel configurations (from V1 plan)
KERNEL_LEADERBOARD = {
    "mla": {"current": 72.0, "leader": 4.3, "points": 1250},
    "gemm": {"current": 20.8, "leader": 9.0, "points": 1000},
    "moe": {"current": 155.0, "leader": 140.0, "points": 1500},
}

# ─── Agent Prompts ────────────────────────────────────────────────────────────

MLA_AGENTS = {
    "asm_probe": {
        "description": "Probe AITER for hidden kernel names and env vars",
        "prompt": """You are the MLA-ASM-Probe Agent for the Luma AMD Speedrun competition.

MISSION: Find the hidden kernel path that achieves the leader's 4.3µs MLA performance.

Current state:
- Best MLA: 72µs (LUT approach) or 20-30µs (AITER)
- Leader MLA: 4.3µs
- Gap: 16.7× — this is massive and requires a breakthrough

Your strategy: Probe AITER's source code to discover:
1. Hidden kernel names not exposed via Python API
2. Undocumented environment variables
3. ASM kernel paths that bypass Python overhead

Generate a submission.py that:
1. Uses `inspect.getsource()` or `dir()` to probe aiter.ml module
2. Tries to call kernels directly via their internal names
3. Includes fallback to AITER mla_decode_fwd on any error
4. Logs what it discovers about kernel internals

CRITICAL: The leader achieves 4.3µs. Our best is 72µs. Something fundamental is different.
Look for: hidden env vars, ASM kernel names, persistent mode tricks.

Output: Complete submission.py file content. Include comments explaining what you're probing.
""",
    },
    "aiter_max": {
        "description": "Max-tune AITER with exhaustive env var grid",
        "prompt": """You are the MLA-AITER-Max Agent for the Luma AMD Speedrun competition.

MISSION: Find the optimal AITER environment variable configuration for maximum MLA performance.

Current state:
- Best MLA with AITER: 20-30µs (depends on shape)
- Leader MLA: 4.3µs
- Gap: 4-7× — still huge but improvable

Your strategy: Exhaustive grid search of AITER env vars
Known vars to grid:
- AITER_MLA_USE_PERSISTENT: ["0", "1"]
- AITER_GFX950_EXPL_SCHED: ["0", "1"]  
- AITER_USE_NT: ["0", "1"]
- AITER_BYPASS_TUNE_CONFIG: ["0", "1"]
- AITER_KSPLIT: ["1", "2", "4", "8", "16", "32"]
- AITER_NUM_KV_SPLITS: ["8", "16", "32", "64"]

Also look for hidden vars by probing aiter source:
- Run: [x for x in dir(torch.ops.aiter) if 'attn' in x.lower() or 'mla' in x.lower()]
- Check: inspect.getsource(mla_decode_fwd) for any env var usage

Generate a submission.py that:
1. Sets all known optimal env vars
2. Probes for hidden vars
3. Uses num_kv_splits tuned for different shapes
4. Falls back to AITER with max tuning on error

Remember: 4.3µs vs 20µs means something fundamental. Look for the hidden switch.
""",
    },
    "hip_mfma_persistent": {
        "description": "Custom MFMA kernel with persistent wavefronts",
        "prompt": """You are the MLA-HIP-MFMA-Persistent Agent for the Luma AMD Speedrun.

MISSION: Write a custom HIP kernel using CDNA 3 MFMA instructions with persistence.

Current state:
- Best custom kernel: 72µs (LUT-based, broken)
- Best AITER: 20-30µs
- Leader: 4.3µs
- Gap: 16.7×

Your strategy: Pure MFMA + persistent wavefronts
Key CDNA 3 intrinsics:
- __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4
- __shfl_xor for wave-level softmax
- Persistent kernel mode for L2 KV cache

The kernel should:
1. Load Q into registers once
2. For each KV step:
   a. MFMA score = Q @ K^T (fused FP8 dequant + dot)
   b. Wave reduction for online softmax
   c. MFMA V accumulation
3. Use persistent waves to keep KV in L2

CRITICAL: Use FP8 KV throughout. Don't use FP4 LUT — that's the broken path.
Target: <20µs with MFMA approach

Output: Complete submission.py with HIP source as string.
""",
    },
    "fp4_kv_mfma": {
        "description": "FP4 KV → MFMA fused approach",
        "prompt": """You are the MLA-FP4-KV-MFMA Agent for the Luma AMD Speedrun.

MISSION: Use FP4 KV cache with MFMA score computation (hybrid approach).

Current state:
- FP4 LUT approach: 72µs (broken, too many per-element ops)
- FP8 KV + AITER: 20-30µs
- Leader: 4.3µs (probably uses something clever)

Your strategy: FP4 KV → inline FP8 dequant → MFMA
Key insight: The problem with FP4 LUT is per-element dequantization.
Solution: Dequant FP4 to FP8 in bulk, then use MFMA.

Kernel flow:
1. Load KV in FP4 format
2. Bulk-dequant FP4 → FP8 (use shared memory, not per-element)
3. MFMA score = Q_fp8 @ KV_fp8^T
4. Wave-level softmax
5. MFMA V accumulation

This gets 2× bandwidth benefit of FP4 + MFMA speed of FP8 computation.

Output: Complete submission.py with HIP source.
""",
    },
}

GEMM_AGENTS = {
    "inline_quant": {
        "description": "Fuse quantization into Triton GEMM kernel",
        "prompt": """You are the GEMM-Inline-Quant Agent for the Luma AMD Speedrun.

MISSION: Eliminate quantization overhead by fusing quant + GEMM into one kernel.

Current state:
- Best GEMM: 20.8µs
- Leader GEMM: 9µs
- Gap: 2.3×
- Key bottleneck: dynamic_mxfp4_quant takes 10-13µs (same as GEMM itself!)

Your strategy: Write a Triton kernel that:
1. Quantizes A to MXFP4 inline
2. Does GEMM with pre-shuffled B
3. Outputs bf16 result
All in one kernel = no separate quantization overhead

Key considerations:
- Need to match AITER's quantization exactly (bit-exact)
- Use dynamic_mxfp4_quant as reference for the math
- Handle the e8m0_shuffle for B weights

If inline quant is too complex, try:
- Pre-quantize A before the kernel (in Python, amortize cost)
- Use torch.compile to fuse (but avoid broken modes)

Output: Complete submission.py
""",
    },
    "splitk_largek": {
        "description": "Manual split-K for large K shapes",
        "prompt": """You are the GEMM-SplitK-LargeK Agent for the Luma AMD Speedrun.

MISSION: Optimize the bottleneck shape M=16,N=2112,K=7168 which takes 21.7µs.

Current state:
- Best GEMM: 20.8µs (on shapes that don't include K=7168)
- Shape M=16,N=2112,K=7168: 21.7µs (slowest)
- Leader: 9µs
- Gap: 2.4× on this shape

Your strategy: Manual split-K for large K
The bottleneck shape has K=7168 which is large.
AITER's automatic KSPLIT might not be optimal.

Try:
1. Call gemm_a4w4_asm with different log2_ks values
2. Manually chunk K and accumulate results
3. Try different tile sizes for this specific shape

Shape-specific optimization is valid — the benchmark uses multiple shapes.

Output: Complete submission.py with shape-adaptive logic.
""",
    },
    "256tile": {
        "description": "256×128 tile for very large M",
        "prompt": """You are the GEMM-256Tile Agent for the Luma AMD Speedrun.

MISSION: Test 256×128 tile size for large M shapes (M≥128).

Current state:
- Best GEMM: 20.8µs with 192×128 tile
- Leader: 9µs
- Gap: 2.3×

Your strategy: 256×128 tile for maximum parallelism
Larger tiles = more parallelism for large batch sizes.
The competition benchmark includes M=256 shapes.

Try:
- _ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_256x128E kernel
- log2_ks=0 for no split (large M doesn't benefit from split)
- Compare vs 192×128 on M=256 shape

Output: Complete submission.py with tile selection logic.
""",
    },
}

MOE_AGENTS = {
    "expert_count_routing": {
        "description": "Route E=257 vs E=33 differently",
        "prompt": """You are the MoE-Expert-Count-Routing Agent for the Luma AMD Speedrun.

MISSION: Optimize MoE by routing based on expert count (E=33 vs E=257).

Current state:
- Best MoE: 155µs
- Leader MoE: 140µs
- Gap: 1.07× — almost there!

Reference data:
- E=257: 152.7µs (slower, more experts)
- E=33: 106.2µs (faster, fewer experts)
- Fewer experts = better coalescing = faster

Your strategy: Different KSPLIT for E=33 vs E=257
E=33 shapes: Use lower KSPLIT (less parallelism overhead)
E=257 shapes: Use higher KSPLIT (more experts = more work)

KSPLIT formula:
- E >= 128: KSPLIT=8
- E >= 32: KSPLIT=4
- E < 32: KSPLIT=2

Verify doweight_stage1=False is set.

Output: Complete submission.py with expert-count-based routing.
""",
    },
    "adaptive_ksplit_v2": {
        "description": "Refined adaptive KSPLIT based on multiple dimensions",
        "prompt": """You are the MoE-Adaptive-Ksplit-v2 Agent for the Luma AMD Speedrun.

MISSION: Multi-dimensional adaptive KSPLIT routing.

Current state:
- Best MoE: 155µs with K-based adaptive KSPLIT
- Leader MoE: 140µs
- Gap: 1.07×

Your strategy: Multi-dimensional KSPLIT
Current approach only uses K dimension.
Try considering: M (tokens), N (hidden), K (expert dim), E (experts)

Grid search:
- KSPLIT based on M: [1, 2, 4, 8] depending on batch size
- KSPLIT based on K: [1, 2, 4, 8] depending on expert dim
- KSPLIT based on E: [1, 2, 4, 8] depending on expert count
- Combine: max(all) or weighted average

Also try:
- OPUS sorting (improves routing efficiency)
- Different quant_type values if MXFP4 isn't mandatory

Output: Complete submission.py with multi-dimensional adaptive KSPLIT.
""",
    },
    "verify_doweight_false": {
        "description": "Confirm doweight_stage1=False is critical",
        "prompt": """You are the MoE-Verify-Doweight-False Agent for the Luma AMD Speedrun.

MISSION: Verify and validate that doweight_stage1=False is the critical setting.

Current state:
- Best MoE: 155µs (with doweight_stage1=False)
- Leader MoE: 140µs
- Gap: 1.07×

Your strategy: Double-blind verification
Test BOTH:
1. doweight_stage1=False (current best)
2. doweight_stage1=True (known to be broken)

Confirm:
- doweight_stage1=True really is broken (GPU fault, mismatch)
- doweight_stage1=False really is optimal
- No other issues are limiting performance

This is validation work — we need to be certain the baseline is correct
before trying more complex optimizations.

Output: submission.py that tests both configurations (submit the False one).
""",
    },
}


# ─── Agent Spawner ────────────────────────────────────────────────────────────


class AgentSpawner:
    """Spawns specialist agents for kernel optimization."""

    def __init__(self, ollama_host: str = OLLAMA_HOST):
        self.ollama_host = ollama_host
        self.code_model = CODE_MODEL
        self.reasoner = REASONER_MODEL

    def _generate_with_ollama(
        self,
        prompt: str,
        model: str = None,
        timeout: int = 300,
    ) -> str:
        """Generate text using Ollama API."""
        if model is None:
            model = self.code_model

        data = json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 8192,  # Longer for code generation
                },
            }
        ).encode()

        req = urllib.request.Request(
            f"http://{self.ollama_host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read())
                return result.get("response", "")
        except urllib.error.URLError as e:
            print(f"Ollama connection error: {e}")
            return f"ERROR: Ollama not available at {self.ollama_host}"
        except Exception as e:
            print(f"Ollama error: {e}")
            return f"ERROR: {e}"

    def _extract_code(self, response: str, kernel: str) -> str:
        """Extract Python code from LLM response."""
        import re

        # Try to find code block
        code_match = re.search(r"```python\s*\n(.*?)\n```", response, re.DOTALL)
        if code_match:
            return code_match.group(1)

        # Try without language hint
        code_match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
        if code_match:
            return code_match.group(1)

        # If no code block, try to find Python code after "Output:" or similar
        lines = response.split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if "```" in line:
                in_code = not in_code
                continue
            if in_code or line.startswith("    ") or line.startswith("\t"):
                code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines)

        # Fallback: return full response with warning
        return f"# Code extraction failed. Raw response:\n{response}"

    def generate_variant(
        self,
        kernel: str,
        strategy: str,
        force_overwrite: bool = False,
    ) -> dict:
        """Generate a single kernel variant."""
        # Get agent config
        agents = {
            "mla": MLA_AGENTS,
            "gemm": GEMM_AGENTS,
            "moe": MOE_AGENTS,
        }

        if kernel not in agents:
            return {"error": f"Unknown kernel: {kernel}"}

        if strategy not in agents[kernel]:
            return {"error": f"Unknown strategy: {strategy} for {kernel}"}

        agent = agents[kernel][strategy]

        print(f"\n{'=' * 60}")
        print(f"Generating {kernel}-{strategy}")
        print(f"{'=' * 60}")
        print(f"Description: {agent['description']}")

        # Generate code
        print(f"\nCalling Ollama ({self.code_model})...")
        response = self._generate_with_ollama(agent["prompt"])

        if response.startswith("ERROR:"):
            return {"error": response}

        # Extract code
        code = self._extract_code(response, kernel)

        # Write file
        output_path = CHALLENGERS_DIR / kernel / f"{kernel}_{strategy}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists() and not force_overwrite:
            print(f"\nFile exists: {output_path}")
            print("Use --force to overwrite")
            return {"error": "File exists", "path": str(output_path)}

        output_path.write_text(code)
        print(f"\nWritten: {output_path}")

        # Log for world model
        experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return {
            "experiment_id": experiment_id,
            "kernel": kernel,
            "strategy": strategy,
            "path": str(output_path),
            "description": agent["description"],
            "status": "generated",
        }

    def spawn_kernel_agents(
        self,
        kernel: str,
        strategies: list[str] = None,
    ) -> list[dict]:
        """Spawn multiple agents for a kernel."""
        agents = {
            "mla": MLA_AGENTS,
            "gemm": GEMM_AGENTS,
            "moe": MOE_AGENTS,
        }

        if kernel not in agents:
            return [{"error": f"Unknown kernel: {kernel}"}]

        # Default: all strategies
        if strategies is None:
            strategies = list(agents[kernel].keys())

        results = []
        for strategy in strategies:
            result = self.generate_variant(kernel, strategy)
            results.append(result)

            # Small delay between calls to avoid rate limiting
            import time

            time.sleep(1)

        return results

    def update_world_model(
        self,
        results: list[dict],
        world_model_path: str = None,
    ) -> None:
        """Update world model with spawned agents."""
        if world_model_path is None:
            world_model_path = str(WORLD_MODEL_FILE)

        # Load existing world model
        wm_path = Path(world_model_path)
        if wm_path.exists():
            with open(wm_path) as f:
                world_model = json.load(f)
        else:
            world_model = {
                "metadata": {
                    "session": SESSION_DIR.name,
                    "created": datetime.now().isoformat(),
                    "agent": "spawn_agents",
                },
                "hypotheses": [],
                "experiments": [],
                "world_model_state": {
                    "stagnation_threshold": 7,
                    "total_iterations": 0,
                },
            }

        # Ensure experiments key exists
        if "experiments" not in world_model:
            world_model["experiments"] = []

        # Add experiments for each spawned agent
        for result in results:
            if "error" in result:
                continue

            exp = {
                "id": result["experiment_id"],
                "timestamp": datetime.now().isoformat(),
                "kernel_type": result["kernel"],
                "strategy": result["strategy"],
                "description": result["description"],
                "path": result["path"],
                "status": "generated",
                "v_score": 0.5,  # Initial neutral
            }

            world_model["experiments"].append(exp)

            # Create hypothesis for this strategy
            hyp_id = f"{result['kernel']}_{result['strategy']}"
            existing = [h for h in world_model["hypotheses"] if h["id"] == hyp_id]

            if not existing:
                hyp = {
                    "id": hyp_id,
                    "description": result["description"],
                    "kernel_type": result["kernel"],
                    "v_score": 0.5,
                    "attempts": 0,
                    "k_stagnation": 0,
                    "parent_id": None,
                    "experiments": [result["experiment_id"]],
                    "status": "active",
                }
                world_model["hypotheses"].append(hyp)

        # Save updated world model
        wm_path.parent.mkdir(parents=True, exist_ok=True)
        with open(wm_path, "w") as f:
            json.dump(world_model, f, indent=2)

        print(f"\nWorld model updated: {wm_path}")

    def extract_skills(
        self,
        experiments: list[dict],
        skills_dir: str = None,
    ) -> list[str]:
        """Extract skills from successful experiments."""
        if skills_dir is None:
            skills_dir = str(SKILLS_DIR)

        skills_dir = Path(skills_dir)
        skills_dir.mkdir(parents=True, exist_ok=True)

        extracted = []

        for exp in experiments:
            if "error" in exp:
                continue

            # Create skill file
            skill_name = f"{exp['kernel']}-{exp['strategy']}-001"
            skill_path = skills_dir / f"{skill_name}.md"

            skill_content = f"""# Skill: {skill_name}

## Metadata
- **Created**: {datetime.now().isoformat()}Z
- **Source Experiment**: {exp.get("experiment_id", "unknown")}
- **Kernel**: {exp["kernel"]}
- **Strategy**: {exp["strategy"]}
- **Status**: generated

## Description
{exp.get("description", "No description")}

## Code Path
```
{exp.get("path", "unknown")}
```

## Trigger Condition
```
kernel_type == "{exp["kernel"]}" AND
strategy == "{exp["strategy"]}"
```

## Expected Performance
- **Speedup**: TBD (benchmark pending)
- **Target**: See leaderboard targets

## Notes
Generated via R-Zero × K-Search multi-agent orchestration.
Awaiting benchmark results to validate.

## Related Skills
(TBD based on cross-kernel transfer discoveries)
"""

            skill_path.write_text(skill_content)
            extracted.append(str(skill_path))

        return extracted


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="R-Zero × K-Search Multi-Agent Kernel Optimization"
    )
    parser.add_argument("--kernel", required=True, choices=["mla", "gemm", "moe"])
    parser.add_argument("--strategy", help="Specific strategy to spawn")
    parser.add_argument("--all", action="store_true", help="Spawn all strategies")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--update-wm", action="store_true", default=True, help="Update world model")
    parser.add_argument(
        "--extract-skills", action="store_true", default=True, help="Extract skills"
    )
    parser.add_argument("--ollama-host", default=OLLAMA_HOST, help="Ollama host")

    args = parser.parse_args()

    print(f"\n{'#' * 60}")
    print("# R-Zero × K-Search Multi-Agent Orchestration")
    print(f"# Kernel: {args.kernel}")
    print(f"# Ollama: {args.ollama_host}")
    print(f"{'#' * 60}")

    spawner = AgentSpawner(ollama_host=args.ollama_host)

    # Determine strategies
    strategies = None
    if args.strategy:
        strategies = [args.strategy]
    elif args.all:
        strategies = None  # All strategies

    # Spawn agents
    print(f"\nSpawning agents for {args.kernel}...")

    results = spawner.spawn_kernel_agents(
        kernel=args.kernel,
        strategies=strategies,
    )

    # Report results
    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")

    for r in results:
        if "error" in r:
            print(f"  ERROR: {r['error']}")
        else:
            print(f"  {r['kernel']}-{r['strategy']}: {r['path']}")

    # Update world model
    if args.update_wm:
        spawner.update_world_model(results)

    # Extract skills
    if args.extract_skills:
        skills = spawner.extract_skills(results)
        if skills:
            print(f"\nExtracted {len(skills)} skills:")
            for s in skills:
                print(f"  - {s}")

    print(f"\n{'=' * 60}")
    print("Next steps:")
    print(f"  1. Review generated files in {CHALLENGERS_DIR}/{args.kernel}/")
    print("  2. Submit to popcorn-cli: popcorn submit --mode test --gpu MI355X ...")
    print(
        "  3. Update world model with results: python run_orchestration.py update-world-model ..."
    )
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
