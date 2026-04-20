"""
GPU Kernel Optimizer for AMD MI355X (CDNA4)

Iterative optimization framework for GPU kernels.

Usage:
    python -m optimizer.loop --kernel gemm --budget 30

Modules:
- state.py: Search state management
- planner.py: Optimization planning
- backend.py: ROCm/Popcorn CLI evaluation
- loop.py: Main optimization loop
- runner.py: Hybrid execution runner
"""

from .backend import GEMM_SHAPES, ROCM_Evaluator, create_evaluator
from .loop import KernelOptimizer
from .planner import (
    CDNA4_KNOWLEDGE,
    format_refine_code_prompt,
    format_select_action_prompt,
    format_update_tree_prompt,
)
from .runner import HybridOptimizer
from .state import EvalResult, NodeStatus, SearchNode, SearchState, SearchTree, init_search_tree


__all__ = [
    "CDNA4_KNOWLEDGE",
    "GEMM_SHAPES",
    "EvalResult",
    "HybridOptimizer",
    "KernelOptimizer",
    "NodeStatus",
    "ROCM_Evaluator",
    "SearchNode",
    "SearchState",
    "SearchTree",
    "create_evaluator",
    "format_refine_code_prompt",
    "format_select_action_prompt",
    "format_update_tree_prompt",
    "init_search_tree",
]
