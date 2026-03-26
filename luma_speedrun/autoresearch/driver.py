"""K-Search driver with cross-kernel learning.

Usage: python driver.py [--dry-run] [--max-cycles 50] [--kernel gemm|moe|mla|all]
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from luma_speedrun.autoresearch.code_synthesizer import synthesize_kernel
from luma_speedrun.autoresearch.popcorn import (
    get_submission_path,
    submit,
    write_submission,
)


BASE_DIR = Path(__file__).parent
STATE_DIR = BASE_DIR / "state"
LOG_DIR = BASE_DIR / "logs"
KERNELS = ("gemm", "moe", "mla")


@dataclass
class TreeNode:
    node_id: str; kernel: str; strategy: str
    status: str = "open"  # open | closed | stagnant
    score: float = 0.0; attempts: int = 0
    children: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KSearchTree:
    kernel: str; nodes: dict[str, TreeNode] = field(default_factory=dict)
    best_score: float = 0.0; generation: int = 0

    def select_node(self) -> TreeNode | None:
        open_nodes = [n for n in self.nodes.values() if n.status == "open"]
        return min(open_nodes, key=lambda n: (n.attempts, -n.score)) if open_nodes else None

    def update_node(self, node_id: str, score: float, status: str | None = None) -> None:
        if (n := self.nodes.get(node_id)) is None:
            return
        n.score, n.attempts = max(n.score, score), n.attempts + 1
        if status:
            n.status = status
        self.best_score = max(self.best_score, score)

    def add_node(self, node_id: str, strategy: str, parent_id: str | None = None) -> TreeNode:
        self.nodes[node_id] = (node := TreeNode(node_id=node_id, kernel=self.kernel, strategy=strategy))
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.append(node_id)
        return node

    def close_strategy(self, strategy: str) -> int:
        hit = [n for n in self.nodes.values() if n.strategy == strategy and n.status == "open"]
        for n in hit:
            n.status = "closed"
        return len(hit)

    def mark_stagnant(self, min_attempts: int = 3) -> list[str]:
        hit = [n for n in self.nodes.values()
               if n.status == "open" and n.attempts >= min_attempts and n.score < self.best_score * 0.95]
        for n in hit:
            n.status = "stagnant"
        return [n.node_id for n in hit]

    def to_dict(self) -> dict[str, Any]:
        return {"kernel": self.kernel, "best_score": self.best_score, "generation": self.generation,
                "nodes": {k: vars(v) for k, v in self.nodes.items()}}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> KSearchTree:
        t = cls(kernel=d["kernel"], best_score=d["best_score"], generation=d["generation"])
        t.nodes = {k: TreeNode(**v) for k, v in d.get("nodes", {}).items()}
        return t


class KernelDriver:
    """Manages K-Search trees for all kernels with cross-kernel learning."""

    def __init__(self, dry_run: bool = False, max_cycles: int = 50) -> None:
        self.dry_run, self.max_cycles = dry_run, max_cycles
        self.trees: dict[str, KSearchTree] = {k: KSearchTree(kernel=k) for k in KERNELS}
        self.last_submit_time, self.submit_interval = 0.0, 600.0  # 10 min rate limit
        self.logger = _setup_logger()

    def run_cycle(self, kernel: str) -> dict[str, Any]:
        """One iteration: SELECT -> SYNTHESIZE -> TEST -> BENCHMARK -> UPDATE."""
        tree = self.trees[kernel]
        tree.generation += 1
        res: dict[str, Any] = {"kernel": kernel, "gen": tree.generation, "action": "none"}
        if (node := tree.select_node()) is None:
            self.challenge_plateau(kernel)
            res["action"] = "plateau_challenge"
            return res
        res.update(node_id=node.node_id, strategy=node.strategy)
        if self.dry_run:
            self.logger.info("[DRY-RUN][%s] strategy=%s node=%s", kernel, node.strategy, node.node_id)
            res["action"] = "dry_run_skip"
            return res
        self.logger.info("[%s] Synthesizing strategy=%s", kernel, node.strategy)

        # Step 1: Synthesize code (LLM or use existing baseline)
        code = synthesize_kernel(kernel, node.strategy, context=json.dumps(node.metadata))
        if code:
            sub_path = write_submission(kernel, code)
        else:
            # LLM unavailable — fall back to existing baseline
            sub_path = get_submission_path(kernel)
            if not sub_path.exists():
                self.logger.warning("[%s] No baseline submission found", kernel)
                tree.update_node(node.node_id, 0.0, status="closed")
                return {**res, "action": "no_submission"}

        # Step 2: Correctness check
        test_result = submit(kernel, sub_path, mode="test")
        self.logger.info("[%s] Test: passed=%s elapsed=%.1fs err=%s",
                         kernel, test_result.passed, test_result.elapsed_s, test_result.error)
        if test_result.discovered_kernels:
            self.logger.info("[%s] Discovered: %s", kernel, test_result.discovered_kernels)
            node.metadata["discovered"] = test_result.discovered_kernels

        if not test_result.passed:
            tree.update_node(node.node_id, 0.0, status="closed")
            node.metadata["error"] = test_result.error or test_result.stderr[-500:]
            return {**res, "action": "test_failed", "error": test_result.error}

        # Step 3: Benchmark for timing
        bench_result = submit(kernel, sub_path, mode="benchmark")
        timing_us = bench_result.score
        self.logger.info("[%s] Benchmark: %.2f µs elapsed=%.1fs",
                         kernel, timing_us, bench_result.elapsed_s)

        # Convert timing to score (higher = better): 1000/µs
        score = (1000.0 / timing_us) if timing_us > 0 else 0.0
        tree.update_node(node.node_id, score)
        node.metadata["timing_us"] = timing_us

        # Step 4: Leaderboard submit if improved (rate-limited)
        now = time.monotonic()
        if score > tree.best_score * 0.99 and (now - self.last_submit_time) >= self.submit_interval:
            self.logger.info("[%s] Submitting to leaderboard: %.2f µs (score=%.4f)", kernel, timing_us, score)
            lb_result = submit(kernel, sub_path, mode="leaderboard")
            self.last_submit_time = now
            res["submitted"] = True
            res["leaderboard_result"] = lb_result.stdout[:500]

        res.update(action="completed", score=score, timing_us=timing_us)
        self._save_state(kernel)
        return res

    def cross_kernel_propagate(self) -> list[str]:
        """Share failures/successes across trees."""
        actions: list[str] = []
        failed: set[str] = set()
        good: dict[str, float] = {}
        for t in self.trees.values():
            for n in t.nodes.values():
                if n.status == "closed" and n.attempts > 0 and n.score == 0.0:
                    failed.add(n.strategy)
                if n.score > 0 and n.score >= t.best_score * 0.95:
                    good[n.strategy] = max(good.get(n.strategy, 0.0), n.score)
        for s in failed:
            for k, t in self.trees.items():
                if (c := t.close_strategy(s)) > 0:
                    actions.append(f"Cross-close: {s} on {k} ({c} nodes)")
        for s, sc in good.items():
            for k, t in self.trees.items():
                if not any(n.strategy == s for n in t.nodes.values()):
                    t.add_node(f"{k}-{s}-xfer-{t.generation}", s)
                    actions.append(f"Cross-suggest: {s} on {k} (score={sc:.4f})")
        for a in actions:
            self.logger.info(a)
        return actions

    def challenge_plateau(self, kernel: str) -> list[str]:
        """R-Zero pattern: inject random mutations when all nodes stagnated."""
        tree = self.trees[kernel]
        tree.mark_stagnant()
        muts = ["random_tile_size", "swap_memory_layout", "fuse_adjacent_ops",
                "unroll_factor_sweep", "prefetch_distance_sweep"]
        ids = [f"{kernel}-mut-g{tree.generation}-{i}" for i in range(len(muts))]
        for nid, m in zip(ids, muts):
            tree.add_node(nid, m)
            self.logger.info("[%s] Injected: %s", kernel, m)
        return ids

    def _save_state(self, kernel: str) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / f"{kernel}_tree.json").write_text(json.dumps(self.trees[kernel].to_dict(), indent=2))

    def save_all(self) -> None:
        for k in self.trees:
            self._save_state(k)

    def load_state(self) -> None:
        for k in KERNELS:
            if (p := STATE_DIR / f"{k}_tree.json").exists():
                self.trees[k] = KSearchTree.from_dict(json.loads(p.read_text()))
                self.logger.info("Loaded %s (gen=%d)", k, self.trees[k].generation)

    def run(self, kernels: list[str] | None = None) -> None:
        tgt = kernels or list(KERNELS)
        self.load_state()
        self.logger.info("Starting (dry_run=%s, cycles=%d, kernels=%s)", self.dry_run, self.max_cycles, tgt)
        for c in range(self.max_cycles):
            self.logger.info("=== Cycle %d/%d ===", c + 1, self.max_cycles)
            for k in tgt:
                self.logger.info("Result: %s", self.run_cycle(k))
            if c % 5 == 4 and (a := self.cross_kernel_propagate()):
                self.logger.info("Cross-kernel: %d actions", len(a))
        self.save_all()


def _setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("ksearch")
    if log.handlers:
        return log
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    for h in [logging.StreamHandler(), logging.FileHandler(LOG_DIR / "driver.log")]:
        h.setFormatter(fmt)
        h.setLevel(logging.INFO if isinstance(h, logging.StreamHandler) else logging.DEBUG)
        log.addHandler(h)
    return log


def main() -> None:
    ap = argparse.ArgumentParser(description="K-Search driver")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cycles", type=int, default=50)
    ap.add_argument("--kernel", choices=[*KERNELS, "all"], default="all")
    a = ap.parse_args()
    KernelDriver(dry_run=a.dry_run, max_cycles=a.max_cycles).run(
        list(KERNELS) if a.kernel == "all" else [a.kernel])

if __name__ == "__main__":
    main()
