"""SWE-bench evaluation harness for Cohezion.

Evaluates agentic capabilities on real-world GitHub issues.
Integrates with official SWE-bench harness for reproducibility.
"""

from .docker_builder import DockerBuilder
from .evaluator import SWEBenchEvaluator
from .harness import SWEBenchHarness


__all__ = ["DockerBuilder", "SWEBenchEvaluator", "SWEBenchHarness"]
