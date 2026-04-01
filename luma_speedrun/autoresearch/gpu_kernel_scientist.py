"""GPU Kernel Scientist — LLM-guided HIP kernel generation for MI355X.

Based on "Democratizing Performance Engineering" paper (arXiv:2506.20807).
Uses evolutionary selector + LLM kernel writer + timing feedback.

For AMD MI355X (gfx950) CDNA 4 architecture.
"""

import random
from pathlib import Path
from typing import Any

from luma_speedrun.autoresearch.popcorn import submit


BASE_DIR = Path(__file__).parent
KERNEL_TEMPLATES = BASE_DIR / "templates"


class KernelCandidate:
    """A candidate kernel with metadata."""

    def __init__(self, kernel_type: str, generation: int, parent_id: str | None = None):
        self.kernel_type = kernel_type
        self.generation = generation
        self.parent_id = parent_id
        self.code: str = ""
        self.score: float = 0.0
        self.timing_us: float = 0.0
        self.status: str = "pending"  # pending | compiled | tested | failed
        self.metadata: dict[str, Any] = {}

    def to_dict(self) -> dict:
        return {
            "kernel_type": self.kernel_type,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "code": self.code[:500],  # Truncated
            "score": self.score,
            "timing_us": self.timing_us,
            "status": self.status,
            "metadata": self.metadata,
        }


class GPUKernelScientist:
    """Evolutionary kernel optimization using LLM guidance."""

    def __init__(self, kernel_type: str, population_size: int = 10):
        self.kernel_type = kernel_type
        self.population_size = population_size
        self.generation = 0
        self.candidates: list[KernelCandidate] = []
        self.best_candidate: KernelCandidate | None = None
        self.best_timing = float("inf")

    def generate_initial_population(self) -> list[KernelCandidate]:
        """Generate initial diverse candidates."""
        population = []

        # Template-based seeds
        templates = self._get_templates()
        for i, template in enumerate(templates[: self.population_size]):
            candidate = KernelCandidate(self.kernel_type, generation=0)
            candidate.code = template
            candidate.metadata["source"] = "template"
            candidate.metadata["template_idx"] = i
            population.append(candidate)

        return population

    def _get_templates(self) -> list[str]:
        """Get kernel templates for MI355X CDNA 4."""
        if self.kernel_type == "mla":
            return [
                self._mla_flashattention_template(),
                self._mla_tiling_template(),
                self._mla_online_softmax_template(),
            ]
        elif self.kernel_type == "moe":
            return [
                self._moe_fused_template(),
                self._moe_sorting_template(),
                self._moe_gemm_fusion_template(),
            ]
        elif self.kernel_type == "gemm":
            return [
                self._gemm_mfma_template(),
                self._gemm_quant_fused_template(),
                self._gemm_blocktiling_template(),
            ]
        return []

    def _mla_flashattention_template(self) -> str:
        """FlashAttention-style MLA kernel template."""
        return '''
@triton.jit
def mla_flash_kernel(
    Q, KV, Out,
    qo_indptr, kv_indptr,
    NUM_HEADS: tl.constexpr = 16,
    QK_HEAD_DIM: tl.constexpr = 576,
    V_HEAD_DIM: tl.constexpr = 512,
    SM_SCALE: tl.constexpr = 0.04167,  # 1/sqrt(576)
    BLOCK_M: tl.constexpr = 64,
    BLOCK_N: tl.constexpr = 64,
):
    """FlashAttention-style MLA with online softmax."""
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)
    
    # FlashAttention algorithm
    # 1. Load Q tile
    # 2. Initialize softmax accumulators
    # 3. Loop over KV in blocks
    # 4. Online softmax update
    # 5. Write output
    pass  # Implementation here
'''

    def _moe_fused_template(self) -> str:
        """Fused MoE kernel template."""
        return '''
# MoE fused kernel for MI355X
# Fuses: routing + sorting + GEMM + activation
@triton.jit
def moe_fused_kernel(
    hidden_states, weights, out,
    topk_weights, topk_ids,
    NUM_EXPERTS: tl.constexpr = 256,
    D_MODEL: tl.constexpr = 7168,
):
    """Fused MoE: routing + GEMM + activation."""
    pass  # Implementation here
'''

    def _gemm_mfma_template(self) -> str:
        """MFMA-optimized GEMM template."""
        return '''
@triton.jit
def gemm_mfma_kernel(
    A, B, C,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    BLOCK_M: tl.constexpr = 64,
    BLOCK_N: tl.constexpr = 64,
    BLOCK_K: tl.constexpr = 64,
):
    """MFMA-optimized GEMM for CDNA 4."""
    pass  # Implementation here
'''

    def evaluate_candidate(self, candidate: KernelCandidate, sub_path: Path) -> bool:
        """Evaluate a candidate kernel."""
        # Write code
        sub_path.write_text(candidate.code)

        # Test
        result = submit(self.kernel_type, sub_path, mode="test")
        if not result.passed:
            candidate.status = "failed"
            candidate.metadata["error"] = result.error
            return False

        # Benchmark
        bench_result = submit(self.kernel_type, sub_path, mode="benchmark")
        if bench_result.score > 0:
            candidate.timing_us = bench_result.score
            candidate.score = 1000.0 / bench_result.score  # Higher = better
            candidate.status = "tested"

            # Update best
            if bench_result.score < self.best_timing:
                self.best_timing = bench_result.score
                self.best_candidate = candidate

            return True

        return False

    def evolve_generation(self) -> list[KernelCandidate]:
        """Evolve to next generation."""
        self.generation += 1
        new_population = []

        # Select top performers
        sorted_candidates = sorted(
            [c for c in self.candidates if c.status == "tested"],
            key=lambda c: c.score,
            reverse=True,
        )

        # Elitism: keep top 2
        new_population.extend(sorted_candidates[:2])

        # Crossover and mutation
        while len(new_population) < self.population_size:
            parent1, parent2 = random.sample(sorted_candidates[:5], 2)
            child = self._crossover(parent1, parent2)
            child = self._mutate(child)
            new_population.append(child)

        return new_population

    def _crossover(self, parent1: KernelCandidate, parent2: KernelCandidate) -> KernelCandidate:
        """Crossover two parents."""
        child = KernelCandidate(
            self.kernel_type,
            generation=self.generation,
            parent_id=f"{parent1.generation}-{parent2.generation}",
        )
        # Simple code mixing
        child.code = self._mix_code(parent1.code, parent2.code)
        return child

    def _mutate(self, candidate: KernelCandidate) -> KernelCandidate:
        """Apply mutations."""
        # Mutate tile sizes
        candidate.code = candidate.code.replace(
            "BLOCK_M: tl.constexpr = 64", f"BLOCK_M: tl.constexpr = {random.choice([32, 64, 128])}"
        )
        return candidate

    def _mix_code(self, code1: str, code2: str) -> str:
        """Mix two code snippets."""
        # Simple mixing: take kernel body from code1, tiling from code2
        return code1  # Simplified

    def run_evolution(self, max_generations: int = 10) -> KernelCandidate | None:
        """Run evolutionary optimization."""
        print(f"[Scientist] Starting evolution for {self.kernel_type}")

        # Initial population
        self.candidates = self.generate_initial_population()

        for gen in range(max_generations):
            print(f"[Scientist] Generation {gen + 1}/{max_generations}")

            # Evaluate
            for i, candidate in enumerate(self.candidates):
                if candidate.status == "pending":
                    sub_path = BASE_DIR.parent / f"submission_{self.kernel_type}_gen{gen}_{i}.py"
                    self.evaluate_candidate(candidate, sub_path)

            # Evolve
            if gen < max_generations - 1:
                self.candidates = self.evolve_generation()

        print(f"[Scientist] Best timing: {self.best_timing:.2f}µs")
        return self.best_candidate


def run_kernel_scientist(kernel_type: str = "mla", max_gen: int = 5) -> None:
    """Run GPU Kernel Scientist for a kernel type."""
    scientist = GPUKernelScientist(kernel_type, population_size=5)
    best = scientist.run_evolution(max_generations=max_gen)

    if best:
        print(f"\n=== Best {kernel_type.upper()} Kernel ===")
        print(f"Timing: {best.timing_us:.2f}µs")
        print(f"Generation: {best.generation}")
        print(f"Code preview:\n{best.code[:500]}...")


if __name__ == "__main__":
    import sys

    kernel = sys.argv[1] if len(sys.argv) > 1 else "mla"
    run_kernel_scientist(kernel)
