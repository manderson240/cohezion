"""K-Search autoresearch framework for AMD MI355X kernel optimization.

Enhanced K-Search (v2) with:
- Adaptive stagnation limits (K varies by depth, kernel difficulty, parent success)
- Divergence detection (prune on regression, not just stagnation)
- Cross-kernel learning (propagate failures and successes across trees)
- QiMeng-style MI355X meta-prompts (5-tuple decomposition)
- MAP-Elites behavioral coordinates (from KernelFoundry)

Usage:
    python -m luma_speedrun.autoresearch.driver --dry-run --max-cycles 5
"""
