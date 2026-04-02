"""Result analysis, world model evolution, and MI355X hardware classification."""
from __future__ import annotations

from typing import Any


# AMD Instinct MI355X (CDNA4) specs
MI355X_BF16_FLOPS: float = 1.3e15      # 1.3 PFLOPS bf16 peak
MI355X_HBM3_BW: float = 8e12           # 8 TB/s HBM3 bandwidth (bytes/s)
MI355X_CROSSOVER: float = MI355X_BF16_FLOPS / MI355X_HBM3_BW  # ~162.5 FLOP/byte

TAG_KEYWORDS: dict[str, list[str]] = {
    "tiling": ["tile", "block_size", "BLOCK"],
    "vectorize": ["vectorize", "vec_", "simd"],
    "unroll": ["unroll", "pragma unroll"],
    "prefetch": ["prefetch", "async_copy"],
    "shared_memory": ["shared_mem", "__shared__", "lds"],
    "register_pressure": ["register", "reg_"],
    "fuse": ["fuse", "fused_", "kernel_fusion"],
    "torch_compile": ["torch.compile", "inductor"],
    "triton": ["triton", "@triton.jit", "tl."],
    "metadata_cache": ["cache", "lru_cache", "memoize"],
}


class ResultAnalyzer:
    """Analyze kernel optimization attempts and evolve the world model."""

    def analyze_attempt(
        self, code: str, score: float, kernel: str, *,
        best_score: float = 0.0, timing_us: float = 0.0,
        shape: tuple[int, int, int] | None = None, dtype_bytes: int = 2,
    ) -> dict[str, Any]:
        """Classify an attempt with hardware-aware analysis."""
        regression = self.is_regression(score, best_score)
        bottleneck = self.classify_bottleneck(kernel, timing_us, shape=shape, dtype_bytes=dtype_bytes)
        ai = roofline = 0.0
        if shape is not None:
            m, n, k = shape
            ai = self.compute_arithmetic_intensity(m, n, k, dtype_bytes=dtype_bytes)
            roofline = self.estimate_roofline_time(m, n, k, dtype_bytes=dtype_bytes)
        tags = self._extract_tags(code)
        return {
            "kernel": kernel, "score": score, "is_regression": regression,
            "bottleneck": bottleneck, "arithmetic_intensity": ai,
            "roofline_time_us": roofline, "tags": tags, "timing_us": timing_us,
            "efficiency": (roofline / timing_us) if timing_us > 0 and roofline > 0 else 0.0,
        }

    @staticmethod
    def is_regression(score: float, best_score: float) -> bool:
        """True if score < 95% of best."""
        return score < 0.95 * best_score if best_score > 0 else False

    @staticmethod
    def classify_bottleneck(
        kernel: str, timing_us: float, *,
        shape: tuple[int, int, int] | None = None, dtype_bytes: int = 2,
    ) -> str:
        """Classify as compute_bound or memory_bound using MI355X specs."""
        if shape is not None:
            m, n, k = shape
            ai = ResultAnalyzer.compute_arithmetic_intensity(m, n, k, dtype_bytes=dtype_bytes)
            return "compute_bound" if ai >= MI355X_CROSSOVER else "memory_bound"
        if timing_us <= 0:
            return "unknown"
        return "memory_bound" if timing_us < 10.0 else "compute_bound"

    @staticmethod
    def compute_arithmetic_intensity(m: int, n: int, k: int, *, dtype_bytes: int = 2) -> float:
        """FLOPs / bytes for GEMM(M,N,K). FLOPs=2MNK, bytes=dtype*(MK+KN+MN)."""
        flops = 2.0 * m * n * k
        nbytes = dtype_bytes * (m * k + k * n + m * n)
        return flops / nbytes if nbytes > 0 else 0.0

    @staticmethod
    def estimate_roofline_time(m: int, n: int, k: int, *, dtype_bytes: int = 2) -> float:
        """Theoretical minimum time in us via roofline: max(compute, memory)."""
        flops = 2.0 * m * n * k
        nbytes = dtype_bytes * (m * k + k * n + m * n)
        compute_s = flops / MI355X_BF16_FLOPS
        memory_s = nbytes / MI355X_HBM3_BW
        return max(compute_s, memory_s) * 1e6

    def evolve_world_model(self, tree_data: dict[str, Any], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Suggest INSERT/UPDATE/PRUNE mutations from accumulated results."""
        mutations: list[dict[str, Any]] = []
        if not results:
            return mutations
        nodes = tree_data.get("nodes", {})

        # Aggregate per-tag stats
        tag_scores: dict[str, list[float]] = {}
        tag_regs: dict[str, int] = {}
        for r in results:
            for tag in r.get("tags", []):
                tag_scores.setdefault(tag, []).append(r["score"])
                if r.get("is_regression"):
                    tag_regs[tag] = tag_regs.get(tag, 0) + 1

        # PRUNE: strategies with >60% regression rate (min 3 samples)
        for tag, reg_count in tag_regs.items():
            total = len(tag_scores.get(tag, []))
            if total >= 3 and reg_count / total > 0.6:
                mutations.append({"op": "PRUNE", "strategy": tag,
                                  "reason": f"regression rate {reg_count}/{total}"})

        # UPDATE: propagate improved scores to matching nodes
        for r in results:
            for nid, ndata in nodes.items():
                if ndata.get("kernel") == r["kernel"] and r["score"] > ndata.get("score", 0):
                    mutations.append({"op": "UPDATE", "node_id": nid, "new_score": r["score"]})

        # INSERT based on bottleneck distribution
        mem_count = sum(1 for r in results if r.get("bottleneck") == "memory_bound")
        comp_count = sum(1 for r in results if r.get("bottleneck") == "compute_bound")
        n = len(results)
        if mem_count > n * 0.5:
            mutations.append({"op": "INSERT", "strategy": "aggressive_prefetch",
                              "reason": f"{mem_count}/{n} memory-bound"})
        if comp_count > n * 0.5:
            mutations.append({"op": "INSERT", "strategy": "tile_size_search",
                              "reason": f"{comp_count}/{n} compute-bound"})

        # INSERT neighbors for high-efficiency attempts
        for r in results:
            if r.get("efficiency", 0) > 0.7:
                for tag in r.get("tags", []):
                    mutations.append({"op": "INSERT", "strategy": f"{tag}_variant",
                                      "reason": f"efficiency {r['efficiency']:.2f} on {r['kernel']}"})
        return mutations

    @staticmethod
    def _extract_tags(code: str) -> list[str]:
        """Extract optimization strategy tags from code."""
        code_lower = code.lower()
        return [tag for tag, keywords in TAG_KEYWORDS.items()
                if any(kw.lower() in code_lower for kw in keywords)]
