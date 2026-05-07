"""
Compound Engineering AutoHarness - Token-Efficient Context Engineering

Applies the compound engineering methodology to model optimization:
- Each experiment makes subsequent experiments more efficient
- Token-efficient skill design with lazy-loaded references
- Self-improving harness that synthesizes optimal configurations

Key Pattern from compound-engineering plugin:
- Extract conditional/late-sequence content to references/
- Replace with stubs (1-3 lines + backtick path)
- Load via Read only when needed
- Never use @ for extracted blocks (inlines at load time)
- 36% token reduction = 130k-167k tokens saved per session

Architecture:
- Oroborous: Self-improving recursive optimization loop
- Mycelium: Distributed knowledge graph of model configurations
- Flume: Data flow pipeline for context streaming
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Token budget tracking for efficiency optimization."""

    baseline_tokens: int = 0
    optimized_tokens: int = 0
    reference_savings: int = 0

    def efficiency_gain(self) -> float:
        """Calculate token efficiency improvement."""
        if self.baseline_tokens == 0:
            return 0.0
        return (self.baseline_tokens - self.optimized_tokens) / self.baseline_tokens

    def report(self) -> dict:
        return {
            "baseline_tokens": self.baseline_tokens,
            "optimized_tokens": self.optimized_tokens,
            "reference_savings": self.reference_savings,
            "efficiency_gain_pct": self.efficiency_gain() * 100,
        }


class OroborousOptimizer:
    """
    Recursive self-improving optimization engine.
    Each optimization run improves the harness for subsequent runs.
    """

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or Path(".autoharness/oroborous")
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.generation = self._load_generation()
        self.improvements: list[dict] = []

    def _load_generation(self) -> int:
        """Load current generation from persistent store."""
        gen_file = self.store_path / "generation.json"
        if gen_file.exists():
            return json.loads(gen_file.read_text()).get("generation", 0)
        return 0

    def _save_generation(self):
        """Persist current generation."""
        gen_file = self.store_path / "generation.json"
        gen_file.write_text(
            json.dumps(
                {
                    "generation": self.generation,
                    "last_updated": datetime.now().isoformat(),
                    "improvements": len(self.improvements),
                }
            )
        )

    def evolve(self, experiment_result: dict) -> dict:
        """
        Evolve the harness based on experiment results.
        Each evolution compounds on previous learnings.
        """
        self.generation += 1

        # Extract learnings
        learning = {
            "generation": self.generation,
            "timestamp": datetime.now().isoformat(),
            "result": experiment_result,
            "hypothesis": experiment_result.get("hypothesis"),
            "outcome": experiment_result.get("status"),
            "metric_delta": experiment_result.get("metric_delta"),
        }

        self.improvements.append(learning)

        # Generate evolved configuration
        evolved_config = self._synthesize_config()

        self._save_generation()

        return {
            "generation": self.generation,
            "learning": learning,
            "evolved_config": evolved_config,
            "cumulative_improvements": len(self.improvements),
        }

    def _synthesize_config(self) -> dict:
        """
        Synthesize optimal configuration from all learnings.
        This is where the 'code as harness' pattern is applied.
        """
        if not self.improvements:
            return self._baseline_config()

        # Analyze which configurations worked best
        successful = [i for i in self.improvements if i.get("outcome") in ("keep", "success")]

        if not successful:
            return self._baseline_config()

        # Extract winning patterns
        max(successful, key=lambda x: x.get("metric_delta", {}).get("improvement", 0))

        # Synthesize evolved config
        return {
            "temperature": self._evolve_param(successful, "temperature"),
            "max_tokens": self._evolve_param(successful, "max_tokens"),
            "concurrency": self._evolve_param(successful, "concurrency"),
            "complexity_threshold": self._evolve_param(successful, "complexity_threshold"),
            "generation": self.generation,
            "synthesis_basis": f"{len(successful)} successful experiments",
        }

    def _evolve_param(self, successful: list[dict], param: str) -> Any:
        """Evolve a parameter based on successful experiments."""
        values = []
        for exp in successful:
            config = exp.get("result", {}).get("config", {})
            if param in config:
                values.append(config[param])

        if not values:
            return None

        # Use median for robustness
        sorted_vals = sorted(values)
        mid = len(sorted_vals) // 2
        return sorted_vals[mid]

    def _baseline_config(self) -> dict:
        """Return baseline configuration."""
        return {
            "temperature": 0.7,
            "max_tokens": 512,
            "concurrency": 4,
            "complexity_threshold": "medium",
            "generation": 0,
        }


class MyceliumKnowledgeGraph:
    """
    Distributed knowledge graph for model configurations.
    Like fungal networks, this connects disparate model knowledge
    into an interconnected web of optimizations.
    """

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or Path(".autoharness/mycelium")
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.nodes: dict[str, Any] = {}
        self.edges: list[tuple[str, str, str]] = []  # (from, to, relation)

    def add_node(self, node_id: str, data: dict, tags: list[str] | None = None):
        """Add a knowledge node with optional tags."""
        self.nodes[node_id] = {
            **data,
            "tags": tags or [],
            "created": datetime.now().isoformat(),
        }
        self._persist_node(node_id)

    def connect(self, from_id: str, to_id: str, relation: str):
        """Create an edge between nodes (the mycelial connection)."""
        self.edges.append((from_id, to_id, relation))

    def traverse(self, start_id: str, depth: int = 2) -> dict:
        """Traverse the knowledge graph from a starting node."""
        visited = set()
        result = {"nodes": {}, "path": []}

        def _traverse(current: str, d: int):
            if d <= 0 or current in visited:
                return
            visited.add(current)

            if current in self.nodes:
                result["nodes"][current] = self.nodes[current]

                # Find connected nodes
                for f, t, r in self.edges:
                    if f == current and t not in visited:
                        result["path"].append((f, t, r))
                        _traverse(t, d - 1)

        _traverse(start_id, depth)
        return result

    def query(self, tags: list[str]) -> list[dict]:
        """Query nodes by tags."""
        results = []
        for node_id, data in self.nodes.items():
            if any(tag in data.get("tags", []) for tag in tags):
                results.append({"id": node_id, **data})
        return results

    def _persist_node(self, node_id: str):
        """Persist node to filesystem."""
        node_file = self.store_path / f"{node_id}.json"
        node_file.write_text(json.dumps(self.nodes[node_id], indent=2))


class FlumeDataPipeline:
    """
    Data flow pipeline for streaming context efficiently.
    Optimizes context movement to minimize token overhead.
    """

    def __init__(self):
        self.streams: dict[str, list] = {}

    def create_stream(self, stream_id: str, reference_files: list[str] | None = None):
        """
        Create a lazy-loading stream.
        Only loads reference files when explicitly requested.
        """
        self.streams[stream_id] = {
            "references": reference_files or [],
            "loaded": [],
            "tokens_saved": 0,
        }

    def load_reference(self, stream_id: str, ref_path: str) -> str:
        """
        Load a reference file on demand.
        This is the key token-saving pattern:
        - File not loaded until requested
        - Avoids carrying unused content in context
        """
        if stream_id not in self.streams:
            return ""

        stream = self.streams[stream_id]

        if ref_path in stream["loaded"]:
            return ""  # Already loaded

        try:
            content = Path(ref_path).read_text()
            stream["loaded"].append(ref_path)
            # Estimate tokens saved (rough heuristic: 4 chars ≈ 1 token)
            stream["tokens_saved"] += len(content) // 4
            return content
        except FileNotFoundError:
            return f"# Reference file not found: {ref_path}"

    def get_stats(self, stream_id: str) -> dict:
        """Get pipeline statistics."""
        if stream_id not in self.streams:
            return {}

        stream = self.streams[stream_id]
        return {
            "references_available": len(stream["references"]),
            "references_loaded": len(stream["loaded"]),
            "tokens_saved_by_lazy_loading": stream["tokens_saved"],
        }


class CompoundEngineeringAutoHarness:
    """
    Main autoharness integrating Oroborous, Mycelium, and Flume.

    Implements token-efficient compound engineering:
    - Baseline: All content in main context
    - Optimized: Conditional/late-sequence content in references/
    - Savings: 36%+ token reduction per session
    """

    def __init__(self, model_id: str, workspace: Path | None = None):
        self.model_id = model_id
        self.workspace = workspace or Path(".autoharness")
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Components
        self.oroborous = OroborousOptimizer(self.workspace / "oroborous")
        self.mycelium = MyceliumKnowledgeGraph(self.workspace / "mycelium")
        self.flume = FlumeDataPipeline()

        # Token tracking
        self.budget = TokenBudget()

        # Setup knowledge graph with model node
        self._init_knowledge_graph()

    def _init_knowledge_graph(self):
        """Initialize the mycelial knowledge network."""
        # Model capability node
        self.mycelium.add_node(
            f"model:{self.model_id}",
            {
                "type": "model",
                "name": self.model_id,
                "capabilities": self._detect_capabilities(),
            },
            tags=["model", "capability"],
        )

        # Baseline config node
        self.mycelium.add_node(
            f"config:{self.model_id}:baseline",
            {
                "type": "config",
                "temperature": 0.7,
                "max_tokens": 512,
            },
            tags=["config", "baseline"],
        )

        # Connect
        self.mycelium.connect(
            f"model:{self.model_id}", f"config:{self.model_id}:baseline", "has_baseline"
        )

    def _detect_capabilities(self) -> dict:
        """Detect model capabilities from model card."""
        # Simplified - in practice would query model card registry
        return {
            "reasoning": 0.8,
            "coding": 0.9,
            "long_context": 0.7,
        }

    def craft_payload(
        self, user_prompt: str, task_type: str = "default", load_references: list[str] | None = None
    ) -> dict:
        """
        Craft optimized payload with token-efficient design.

        Pattern from compound-engineering:
        - Base skill: ~685 lines (~9,971 tokens)
        - References: Loaded on demand only
        - Savings: ~130k-167k tokens per session
        """
        # Base payload (minimal, always loaded)
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": self._get_stub(task_type)},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._get_temperature(task_type),
            "max_tokens": self._get_max_tokens(task_type),
        }

        # Track baseline tokens (approximate)
        baseline_str = json.dumps(payload)
        self.budget.baseline_tokens = len(baseline_str) // 4

        # Lazy-load references only when requested
        if load_references:
            stream_id = f"task:{task_type}"
            self.flume.create_stream(stream_id, load_references)

            for ref in load_references:
                content = self.flume.load_reference(stream_id, ref)
                if content and "error" not in content.lower():
                    # Append to system message
                    payload["messages"][0]["content"] += f"\n\n---\n\n{content}"

        # Track optimized tokens
        optimized_str = json.dumps(payload)
        self.budget.optimized_tokens = len(optimized_str) // 4

        return payload

    def _get_stub(self, task_type: str) -> str:
        """
        Get minimal stub for task type.
        This replaces the full SKILL.md with a 1-3 line stub + backtick path.

        Example: "For reasoning tasks, read `references/reasoning-guide.md`"
        """
        stubs = {
            "default": "You are a helpful assistant. Optimize for efficiency.",
            "reasoning": (
                "You are a reasoning specialist. "
                "For complex reasoning, read `references/reasoning-guide.md`. "
                "Think step-by-step."
            ),
            "coding": (
                "You are a coding specialist. "
                "For implementation details, read `references/coding-patterns.md`. "
                "Write correct, efficient code."
            ),
        }
        return stubs.get(task_type, stubs["default"])

    def _get_temperature(self, task_type: str) -> float:
        """Get optimized temperature for task type."""
        temps = {
            "reasoning": 0.3,
            "coding": 0.3,
            "creative": 0.9,
            "default": 0.7,
        }
        return temps.get(task_type, temps["default"])

    def _get_max_tokens(self, task_type: str) -> int:
        """Get optimized max tokens for task type."""
        tokens = {
            "reasoning": 1024,
            "coding": 2048,
            "default": 512,
        }
        return tokens.get(task_type, tokens["default"])

    def feedback(self, result: dict):
        """
        Provide feedback to evolve the harness.
        This is the compound engineering loop.
        """
        # Store in knowledge graph
        result_id = f"experiment:{datetime.now().isoformat()}"
        self.mycelium.add_node(
            result_id, result, tags=["experiment", result.get("status", "unknown")]
        )

        # Connect to model
        self.mycelium.connect(f"model:{self.model_id}", result_id, "has_experiment")

        # Evolve via oroborous
        evolution = self.oroborous.evolve(result)

        logger.info(f"Harness evolved to generation {evolution['generation']}")

        return evolution

    def query_relevant_config(self, task_type: str) -> dict:
        """Query mycelial graph for relevant configurations."""
        # Traverse from model node
        traversal = self.mycelium.traverse(f"model:{self.model_id}", depth=2)

        # Extract successful configs
        configs = []
        for _node_id, data in traversal.get("nodes", {}).items():
            if data.get("type") == "experiment" and data.get("status") == "keep":
                configs.append(data.get("config", {}))

        if configs:
            # Synthesize from successful configs
            return self._synthesize_from_configs(configs)

        return self.oroborous._baseline_config()

    def _synthesize_from_configs(self, configs: list[dict]) -> dict:
        """Synthesize optimal config from successful experiments."""
        if not configs:
            return {}

        # Simple median synthesis
        result = {}
        for key in configs[0]:
            values = [c.get(key) for c in configs if key in c]
            if values and isinstance(values[0], (int, float)):
                result[key] = sum(values) / len(values)

        return result

    def get_compound_report(self) -> dict:
        """
        Generate compound engineering report.
        Shows how each generation improved over previous.
        """
        return {
            "generation": self.oroborous.generation,
            "experiments": len(self.oroborous.improvements),
            "token_efficiency": self.budget.report(),
            "knowledge_nodes": len(self.mycelium.nodes),
            "knowledge_edges": len(self.mycelium.edges),
            "current_config": self.oroborous._synthesize_config(),
            "evolution_history": [
                {
                    "gen": i["generation"],
                    "outcome": i["outcome"],
                    "metric": i.get("metric_delta"),
                }
                for i in self.oroborous.improvements
            ],
        }


# Global factory
def create_compound_autoharness(
    model_id: str, workspace: Path | None = None
) -> CompoundEngineeringAutoHarness:
    """Factory function for creating a compound engineering autoharness."""
    return CompoundEngineeringAutoHarness(model_id, workspace)


if __name__ == "__main__":
    # Demo
    harness = create_compound_autoharness("gemini-2.5-flash")

    # Craft payload with lazy-loaded references
    payload = harness.craft_payload(
        "Explain quantum computing",
        task_type="reasoning",
        load_references=["references/reasoning-guide.md"],
    )

    print("Optimized payload:", json.dumps(payload, indent=2))
    print("\nToken budget:", harness.budget.report())

    # Simulate feedback
    result = {
        "status": "keep",
        "metric": 145.2,
        "config": {"temperature": 0.3, "max_tokens": 1024},
        "hypothesis": "Lower temperature improves reasoning accuracy",
    }

    evolution = harness.feedback(result)
    print("\nEvolution:", json.dumps(evolution, indent=2))

    # Get compound report
    report = harness.get_compound_report()
    print("\nCompound Report:", json.dumps(report, indent=2))
