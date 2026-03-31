#!/usr/bin/env python3
"""Autonomous K-Search experiment driver.

Main overnight loop:
  SELECT node → generate submission → popcorn-cli test → benchmark
  → UPDATE tree → log JSONL → rotate kernels → repeat

Usage:
  uv run python driver.py                    # Run all kernels (priority-weighted)
  uv run python driver.py --kernel moe       # Run only MoE experiments
  uv run python driver.py --kernel gemm      # Run only GEMM experiments
  uv run python driver.py --kernel mla       # Run only MLA experiments
  uv run python driver.py --max-cycles 10    # Limit number of cycles
  uv run python driver.py --dry-run          # Generate submissions but don't submit
"""

from __future__ import annotations

import argparse
import logging
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path


# Add autoresearch to path
sys.path.insert(0, str(Path(__file__).parent))
# Add cloud-vault-mcp to path for graph_writer
_cloud_vault_src = Path(__file__).parent.parent.parent.parent.parent / "cloud-vault-mcp" / "src"
if _cloud_vault_src.exists():
    sys.path.insert(0, str(_cloud_vault_src))

import asyncio

import generator
from analyzer import Analysis, analyze_result, evolve_world_model, log_result
from code_synthesizer import is_ollama_available
from evaluator import KERNEL_DIRS, EvalResult, evaluate
from generator import generate_submission
from ksearch_tree import KSearchTree
from rate_limiter import RateLimiter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("autoresearch")

BASE_DIR = Path(__file__).parent
TREE_DIR = BASE_DIR / "tree"
RESULTS_DIR = BASE_DIR / "results"
KERNELS_DIR = BASE_DIR.parent / "kernels"

# Priority weights for kernel rotation (higher = more likely to be selected)
# Based on gap-to-leader: MoE 1.27x (closeable), GEMM 2.4x, MLA 15.6x
KERNEL_WEIGHTS = {
    "moe": 0.5,  # Closest to leader — highest ROI
    "gemm": 0.3,  # Medium gap
    "mla": 0.2,  # Largest gap — moonshot
}

CYCLE_SLEEP_SECONDS = 60  # Sleep between cycles


def _sync_to_graph(kernel: str, node, result_us: float | None) -> None:
    """Write K-Search cycle result to neuron graph (non-blocking)."""
    try:
        from mcp_server.graph_writer import create_synapse, slugify, upsert_neuron

        node_id = f"neuron:ksearch_{kernel}_{slugify(node.id)}_md"
        content = f"Strategy: {node.strategy}\nBest: {node.best_result_us or 'N/A'}µs"
        if result_us:
            content += f"\nLast: {result_us:.1f}µs (attempt #{node.attempts})"

        asyncio.run(upsert_neuron(
            neuron_id=node_id,
            title=f"[{kernel.upper()}] {node.strategy[:60]}",
            path=f"autoresearch/{kernel}/{node.id}",
            cluster="autoresearch",
            aspect="thinker",
            tags=["autoresearch", kernel, "k-search"],
            content=content,
        ))

        # Link to parent if exists
        if node.parent_id:
            parent_id = f"neuron:ksearch_{kernel}_{slugify(node.parent_id)}_md"
            asyncio.run(create_synapse(
                from_id=parent_id,
                to_id=node_id,
                link_type="k-search-child",
                reason=f"Child strategy in {kernel} K-Search tree",
            ))
    except Exception as e:
        log.debug(f"Graph sync skipped (non-blocking): {e}")


def load_tree(kernel: str) -> KSearchTree:
    """Load or create K-Search tree for a kernel."""
    tree_path = TREE_DIR / f"{kernel}_tree.json"
    if tree_path.exists():
        return KSearchTree.load(tree_path)
    tree = KSearchTree(kernel)
    tree.insert_root(f"Optimize {kernel} geomean")
    return tree


def save_tree(tree: KSearchTree) -> None:
    """Persist tree to disk."""
    tree_path = TREE_DIR / f"{tree.kernel_name}_tree.json"
    tree.save(tree_path)


def select_kernel(kernels: list[str]) -> str:
    """Weighted random selection of next kernel to optimize."""
    if len(kernels) == 1:
        return kernels[0]
    weights = [KERNEL_WEIGHTS.get(k, 0.33) for k in kernels]
    total = sum(weights)
    weights = [w / total for w in weights]
    return random.choices(kernels, weights=weights, k=1)[0]


def generate_variant_params(tree: KSearchTree, node) -> dict:
    """Generate a parameter variant from the node.

    If the node has been attempted before, slightly perturb parameters
    to explore nearby configurations.
    """
    params = dict(node.parameters)

    if node.attempts == 0:
        return params  # First attempt uses exact parameters

    # Perturbation: modify one random value in a lookup table
    kernel = tree.kernel_name

    if kernel == "moe" and "KSPLIT_TABLE" in params:
        table = dict(params["KSPLIT_TABLE"])
        if table:
            key = random.choice(list(table.keys()))
            current = table[key]
            # Perturb KSPLIT by ±1-2, clamped to 0-6
            delta = random.choice([-2, -1, 1, 2])
            table[key] = max(0, min(6, current + delta))
            params["KSPLIT_TABLE"] = table

    elif kernel == "gemm" and "KERNEL_TABLE" in params:
        table = dict(params["KERNEL_TABLE"])
        if table:
            key = random.choice(list(table.keys()))
            entry = dict(table[key])
            # Perturb log2_ks by ±1, clamped to 0-4
            delta = random.choice([-1, 1])
            entry["log2_ks"] = max(0, min(4, entry["log2_ks"] + delta))
            # Occasionally try ASM variant
            if random.random() < 0.3:
                entry["kernel"] = random.choice(["gemm_a4w4", "gemm_a4w4_asm"])
            table[key] = entry
            params["KERNEL_TABLE"] = table

    elif kernel == "mla" and "SPLITS_TABLE" in params:
        table = dict(params["SPLITS_TABLE"])
        if table:
            key = random.choice(list(table.keys()))
            current = table[key]
            # Perturb splits: ×2, ÷2, ±4
            choices = [
                max(2, current // 2),
                min(64, current * 2),
                max(2, current - 4),
                min(64, current + 4),
            ]
            table[key] = random.choice(choices)
            params["SPLITS_TABLE"] = table

    return params


def challenge_plateau(tree: KSearchTree, kernel: str, current_best: float) -> None:
    """R-Zero: Propose harder target when plateau detected.

    Instead of stopping at convergence, raise the bar by 10% and insert
    a new child node that targets the harder threshold.
    """
    new_target = current_best * 0.9  # 10% harder
    root_id = tree.root_id
    if not root_id:
        return

    # Check if we already have a challenger node for this level
    for node in tree.nodes.values():
        if f"Beat {new_target:.1f}µs" in node.strategy:
            return  # Already proposed this target

    tree.insert_child(
        parent_id=root_id,
        strategy=f"Beat {new_target:.1f}µs (10% below {current_best:.1f}µs plateau)",
        parameters={},
        priority=0.8,
        notes="[R-Zero challenger]",
    )
    log.info(
        f"[{kernel}] R-Zero: Raised target to {new_target:.1f}µs "
        f"(10% below plateau at {current_best:.1f}µs)"
    )


def run_cycle(
    kernel: str,
    tree: KSearchTree,
    rate_limiter: RateLimiter,
    dry_run: bool | str = False,
) -> tuple[bool, str]:
    """Run one experiment cycle for a kernel.

    Returns (success, summary_message).
    """
    # Select best node
    node = tree.select_best()
    if node is None:
        return False, f"{kernel}: No active nodes remaining"

    log.info(
        f"[{kernel}] Selected: {node.strategy} (p={node.priority:.2f}, attempts={node.attempts})"
    )

    # Generate variant parameters
    params = generate_variant_params(tree, node)

    # Get trajectory for LLM context
    trajectory = tree.get_trajectory(node.id)

    # Generate submission (skip LLM code synthesis in dry-run-llm to save time)
    template_key = params.pop("_template", kernel)
    use_llm_code = dry_run != "llm"  # dry-run-llm focuses on world model, not code gen
    try:
        code = generate_submission(
            template_key,
            params,
            strategy=node.strategy,
            trajectory=trajectory,
            use_llm=use_llm_code,
        )
    except ValueError as e:
        log.error(f"[{kernel}] Generation failed: {e}")
        tree.mark_failed(node.id, str(e))
        save_tree(tree)
        return False, f"{kernel}: Generation failed: {e}"

    if dry_run == "llm":
        # Dry-run with LLM: skip code synthesis, focus on world model evolution
        log.info(f"[{kernel}] DRY RUN (LLM) — {len(code)} chars (template), testing world model...")
        synthetic_geomean = (node.best_result_us or 200.0) * random.uniform(0.85, 1.15)
        synthetic_result = EvalResult(
            kernel=kernel,
            mode="benchmark",
            success=True,
            geomean_us=round(synthetic_geomean, 2),
        )
        analysis = analyze_result(synthetic_result, tree, node)
        node.record_attempt(
            result_us=synthetic_geomean,
            parameters=params,
            source=generator.last_source,
        )
        try:
            counts = evolve_world_model(tree, node, synthetic_result, analysis)
            log.info(f"[{kernel}] World model: {counts}")
        except Exception as e:
            log.warning(f"[{kernel}] World model evolution failed: {e}")
        save_tree(tree)
        _sync_to_graph(kernel, node, synthetic_geomean)
        return True, (
            f"{kernel}: Dry run LLM OK "
            f"(synthetic={synthetic_geomean:.1f}µs, "
            f"source={generator.last_source}, "
            f"{len(tree.nodes)} nodes)"
        )
    elif dry_run:
        log.info(f"[{kernel}] DRY RUN — would submit {len(code)} chars")
        return True, f"{kernel}: Dry run OK ({len(code)} chars)"

    # Write submission to kernel directory
    kernel_dir = KERNELS_DIR / KERNEL_DIRS[kernel]
    staging_dir = kernel_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Save to staging with timestamp
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    staged_path = staging_dir / f"submission.autoresearch.{ts}.py"
    staged_path.write_text(code)

    # Copy to submission.py for popcorn-cli
    submission_path = kernel_dir / "submission.py"
    # Back up current submission
    backup_path = staging_dir / f"submission.backup.{ts}.py"
    if submission_path.exists():
        shutil.copy2(submission_path, backup_path)
    submission_path.write_text(code)

    # Test first, then benchmark
    log.info(f"[{kernel}] Testing...")
    test_result = evaluate(submission_path, kernel, mode="test")

    if not test_result.success:
        log.warning(f"[{kernel}] Test FAILED: {test_result.error}")
        tree.mark_failed(node.id, f"Test failed: {test_result.error}")
        # Restore backup
        if backup_path.exists():
            shutil.copy2(backup_path, submission_path)
        save_tree(tree)
        # Log failure
        log_result(
            test_result,
            node,
            Analysis(float("inf"), None, 0.0, {}, test_result.error),
            RESULTS_DIR / f"{kernel}_runs.jsonl",
        )
        return False, f"{kernel}: Test failed: {test_result.error}"

    log.info(f"[{kernel}] Test PASSED. Benchmarking...")
    bench_result = evaluate(submission_path, kernel, mode="benchmark")

    if not bench_result.success:
        log.warning(f"[{kernel}] Benchmark FAILED: {bench_result.error}")
        # Still update tree (test passed, benchmark failed is different from correctness failure)
        if backup_path.exists():
            shutil.copy2(backup_path, submission_path)
        save_tree(tree)
        return False, f"{kernel}: Benchmark failed: {bench_result.error}"

    # Analyze and update tree
    analysis = analyze_result(bench_result, tree, node)

    # Record attempt in trajectory history
    geomean_for_history = bench_result.geomean_us or float("inf")
    node.record_attempt(
        result_us=geomean_for_history,
        parameters=params,
        source=generator.last_source,
    )

    # K-Search: World model evolution via LLM (1 call per cycle)
    try:
        evolve_world_model(tree, node, bench_result, analysis)
    except Exception as e:
        log.warning(f"[{kernel}] World model evolution failed (non-blocking): {e}")

    save_tree(tree)

    # Log result
    log_result(bench_result, node, analysis, RESULTS_DIR / f"{kernel}_runs.jsonl")

    # Sync to neuron graph
    _sync_to_graph(kernel, node, bench_result.geomean_us)

    geomean = bench_result.geomean_us or 0
    log.info(
        f"[{kernel}] Geomean: {geomean:.1f}µs "
        f"(improvement: {analysis.improvement_pct:+.1f}%) "
        f"Bottleneck: {analysis.bottleneck_shape}"
    )

    # If this is the best result AND leaderboard is available, consider submitting
    stats = tree.get_stats()
    if (
        stats["best_us"] == geomean
        and analysis.improvement_pct > 0
        and rate_limiter.can_submit(kernel)
    ):
        log.info(f"[{kernel}] NEW BEST! Submitting to leaderboard...")
        lb_result = evaluate(submission_path, kernel, mode="leaderboard")
        if lb_result.success:
            rate_limiter.record_submission(kernel)
            log.info(f"[{kernel}] Leaderboard submission OK!")
        else:
            log.warning(f"[{kernel}] Leaderboard submission failed: {lb_result.error}")
    else:
        # Restore backup if not best
        if backup_path.exists() and stats["best_us"] != geomean:
            shutil.copy2(backup_path, submission_path)

    summary = (
        f"{kernel}: {geomean:.1f}µs "
        f"(best={stats['best_us']:.1f}µs, "
        f"{stats['active']} active nodes, "
        f"{stats['total_attempts']} total attempts)"
    )
    return True, summary


def main():
    parser = argparse.ArgumentParser(description="K-Search autonomous experiment driver")
    parser.add_argument(
        "--kernel", choices=["moe", "gemm", "mla"], help="Single kernel to optimize"
    )
    parser.add_argument(
        "--max-cycles", type=int, default=0, help="Max experiment cycles (0=unlimited)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't submit")
    parser.add_argument(
        "--dry-run-llm",
        action="store_true",
        help="Generate + exercise LLM world model with synthetic results (no submission)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override Ollama model for world model (e.g., qwen2.5-coder:7b, deepcoder:14b)",
    )
    args = parser.parse_args()

    kernels = [args.kernel] if args.kernel else ["moe", "gemm", "mla"]
    rate_limiter = RateLimiter()

    # Override model if specified
    if args.model:
        import code_synthesizer

        code_synthesizer.OLLAMA_MODEL_PLAN = args.model
        code_synthesizer.OLLAMA_MODEL = args.model

    # Determine dry_run mode: False, True, or "llm"
    dry_run_mode: bool | str = False
    if args.dry_run_llm:
        dry_run_mode = "llm"
    elif args.dry_run:
        dry_run_mode = True

    from code_synthesizer import OLLAMA_MODEL_PLAN

    llm_available = is_ollama_available()
    log.info(f"Starting K-Search driver for: {', '.join(kernels)}")
    log.info(f"Max cycles: {'unlimited' if args.max_cycles == 0 else args.max_cycles}")
    log.info(
        f"Mode: {'dry-run-llm' if dry_run_mode == 'llm' else 'dry-run' if dry_run_mode else 'live'}"
    )
    log.info(f"LLM model: {OLLAMA_MODEL_PLAN} ({'available' if llm_available else 'unavailable'})")
    log.info(f"Rate limiter: {rate_limiter.status()}")

    # Load trees
    trees = {k: load_tree(k) for k in kernels}
    for k, t in trees.items():
        log.info(f"  {k}: {t}")

    cycle = 0
    # Convergence tracking: {kernel: (best_us_at_check, cycles_since_improvement)}
    convergence: dict[str, tuple[float, int]] = {}
    converged_kernels: set[str] = set()

    try:
        while args.max_cycles == 0 or cycle < args.max_cycles:
            cycle += 1
            # Skip converged kernels
            active_kernels = [k for k in kernels if k not in converged_kernels]
            if not active_kernels:
                log.info("All kernels converged. Stopping.")
                break
            kernel = select_kernel(active_kernels)
            tree = trees[kernel]

            log.info(f"\n{'=' * 60}")
            log.info(f"Cycle {cycle}: {kernel}")
            log.info(f"{'=' * 60}")

            success, summary = run_cycle(kernel, tree, rate_limiter, dry_run=dry_run_mode)
            log.info(summary)

            # Periodic maintenance
            if cycle % 5 == 0:
                for t in trees.values():
                    # Priority decay to encourage exploration
                    t.decay_priorities(factor=0.95)
                    # Cap tree size: prune lowest-priority nodes if too large
                    active = [n for n in t.nodes.values() if n.status == "active"]
                    if len(active) > 30:
                        # Keep top 20 by priority, prune the rest
                        by_priority = sorted(active, key=lambda n: n.priority)
                        for n in by_priority[: len(active) - 20]:
                            t.strategic_prune(n.id, reason="tree size cap (>30 active)")
                        log.info(
                            f"[{t.kernel_name}] Tree cap: pruned {len(active) - 20} "
                            f"low-priority nodes ({len(active)} → 20 active)"
                        )
                    save_tree(t)

            # Convergence check every 10 cycles per kernel
            if cycle % 10 == 0:
                for k in active_kernels:
                    stats = trees[k].get_stats()
                    best = stats.get("best_us")
                    if best is None:
                        continue
                    prev_best, stale_count = convergence.get(k, (float("inf"), 0))
                    if prev_best > 0 and (prev_best - best) / prev_best < 0.01:
                        stale_count += 1
                    else:
                        stale_count = 0
                    convergence[k] = (best, stale_count)
                    if stale_count >= 1:  # No >1% improvement in last 10 cycles
                        # R-Zero: Challenge the plateau before giving up
                        challenge_plateau(trees[k], k, best)
                        # Only truly converge after 2 consecutive stale checks
                        # (gives challenger node a chance to work)
                        if stale_count >= 2:
                            converged_kernels.add(k)
                            log.info(
                                f"[{k}] CONVERGED at {best:.1f}µs "
                                f"(no >1% improvement in 20 cycles). Reallocating."
                            )
                        else:
                            log.info(
                                f"[{k}] Plateau at {best:.1f}µs — "
                                f"R-Zero challenger activated, continuing."
                            )

            time.sleep(CYCLE_SLEEP_SECONDS)

    except KeyboardInterrupt:
        log.info("\nShutting down...")
    finally:
        # Save all trees
        for t in trees.values():
            save_tree(t)
        # Print final stats
        log.info(f"\n{'=' * 60}")
        log.info(f"Final stats after {cycle} cycles:")
        for k, t in trees.items():
            stats = t.get_stats()
            log.info(
                f"  {k}: best={stats['best_us']}µs, "
                f"active={stats['active']}, "
                f"attempts={stats['total_attempts']}"
            )
        log.info(f"{'=' * 60}")


# Singleton rate_limiter instance for import by ralph_main.py
rate_limiter = RateLimiter()


if __name__ == "__main__":
    main()
