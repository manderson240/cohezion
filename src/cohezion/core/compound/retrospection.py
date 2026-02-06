"""
Compound Engineering Retrospection System.

Implements the RETROSPECTIVE_SKILL PRIME: analyzes completed work phases,
extracts reusable patterns, tracks token efficiency, and synthesizes
compound blocks that accelerate future development.
"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PhaseRetrospector:
    """Analyzes completed work phases for reusable patterns and compound blocks.

    Parameters
    ----------
    skills_dir : Path
        Directory containing PRIME skill markdown files.
    knowledge_dir : Path
        Directory for persisting learnings (KEY_LEARNINGS.md).
    """

    def __init__(
        self,
        skills_dir: Path | None = None,
        knowledge_dir: Path | None = None,
    ):
        root = Path(__file__).parent.parent.parent.parent.parent
        self.skills_dir = skills_dir or root / "src" / "cohezion" / "skills"
        self.knowledge_dir = (
            knowledge_dir or root / "src" / "cohezion" / "knowledge_graph"
        )
        self._pattern_counts: Counter = Counter()
        self._compound_blocks: list[dict[str, Any]] = []

    def scan_for_patterns(self) -> dict[str, Any]:
        """Scan all PRIME skills and extract recurring structural patterns.

        Returns
        -------
        dict
            Pattern analysis with counts, common sections, and compound block candidates.
        """
        sections: Counter = Counter()
        see_also_graph: dict[str, list[str]] = {}
        hook_inventory: list[dict[str, Any]] = []
        skill_count = 0

        for md_file in sorted(self.skills_dir.glob("*.md")):
            try:
                content = md_file.read_text(errors="ignore")
                skill_name = md_file.stem
                skill_count += 1
                lines = content.split("\n")

                # Count section headers
                for line in lines:
                    if line.startswith("## "):
                        section = line[3:].strip().upper()
                        sections[section] += 1

                # Extract SEE ALSO references (builds the skill dependency graph)
                in_see_also = False
                refs: list[str] = []
                for line in lines:
                    if "## SEE ALSO" in line.upper():
                        in_see_also = True
                        continue
                    if in_see_also and line.startswith("#"):
                        break
                    if in_see_also and line.strip().startswith("- "):
                        ref = line.strip()[2:].strip()
                        refs.append(ref)
                if refs:
                    see_also_graph[skill_name] = refs

                # Extract FUTURE HOOKS
                in_hooks = False
                hooks: list[str] = []
                for line in lines:
                    if "## FUTURE HOOKS" in line.upper():
                        in_hooks = True
                        continue
                    if in_hooks and line.startswith("#"):
                        break
                    if in_hooks and line.strip().startswith("- "):
                        hooks.append(line.strip()[2:])
                if hooks:
                    hook_inventory.append(
                        {
                            "skill": skill_name,
                            "hooks": hooks,
                            "count": len(hooks),
                        }
                    )

            except Exception as e:
                logger.warning("Failed to scan %s: %s", md_file.name, e)

        # Identify compound block candidates (sections appearing in 3+ skills)
        compound_candidates = {
            section: count for section, count in sections.items() if count >= 3
        }

        # Find most-referenced skills (high compound impact)
        ref_counts: Counter = Counter()
        for refs in see_also_graph.values():
            for ref in refs:
                ref_counts[ref.replace(".md", "")] += 1

        result = {
            "total_skills": skill_count,
            "section_frequency": dict(sections.most_common(20)),
            "compound_block_candidates": compound_candidates,
            "skill_dependency_graph": see_also_graph,
            "most_referenced_skills": dict(ref_counts.most_common(10)),
            "hook_inventory": sorted(
                hook_inventory, key=lambda x: x["count"], reverse=True
            ),
            "timestamp": datetime.now().isoformat(),
        }

        self._compound_blocks = [
            {"name": section, "frequency": count}
            for section, count in compound_candidates.items()
        ]

        return result

    def extract_compound_blocks(self) -> list[dict[str, Any]]:
        """Return patterns that qualify as reusable compound blocks.

        A compound block is a structural pattern used in 3+ skills.
        """
        if not self._compound_blocks:
            self.scan_for_patterns()
        return self._compound_blocks

    def write_retrospective(self, analysis: dict[str, Any] | None = None) -> Path:
        """Write a retrospective summary to KEY_LEARNINGS.md.

        Parameters
        ----------
        analysis : dict, optional
            Pre-computed analysis. If None, runs scan_for_patterns().

        Returns
        -------
        Path
            Path to the updated KEY_LEARNINGS file.
        """
        if analysis is None:
            analysis = self.scan_for_patterns()

        learnings_path = self.knowledge_dir / "KEY_LEARNINGS.md"

        # Append a new retrospective section
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n\n## Retrospective - {timestamp}\n\n"
        entry += f"**Skills Analyzed:** {analysis['total_skills']}\n\n"

        if analysis["compound_block_candidates"]:
            entry += "### Compound Blocks (3+ occurrences)\n"
            for section, count in sorted(
                analysis["compound_block_candidates"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                entry += f"- **{section}**: {count} skills\n"
            entry += "\n"

        if analysis["most_referenced_skills"]:
            entry += "### Most Referenced Skills (High Compound Impact)\n"
            for skill, count in analysis["most_referenced_skills"].items():
                entry += f"- {skill}: referenced by {count} other skills\n"
            entry += "\n"

        hooks = analysis.get("hook_inventory", [])
        if hooks:
            total_hooks = sum(h["count"] for h in hooks)
            entry += (
                f"### Future Hooks: {total_hooks} total across {len(hooks)} skills\n\n"
            )

        try:
            if learnings_path.exists():
                existing = learnings_path.read_text()
                learnings_path.write_text(existing + entry)
            else:
                learnings_path.parent.mkdir(parents=True, exist_ok=True)
                learnings_path.write_text(f"# Key Learnings\n{entry}")
            logger.info("Retrospective written to %s", learnings_path)
        except Exception as e:
            logger.error("Failed to write retrospective: %s", e)

        return learnings_path


class TokenEfficiencyTracker:
    """Tracks and optimizes token usage across the agent swarm.

    Parameters
    ----------
    metrics_dir : Path
        Directory for persisting token usage metrics.
    """

    def __init__(self, metrics_dir: Path | None = None):
        root = Path(__file__).parent.parent.parent.parent.parent
        self.metrics_dir = metrics_dir or root / "src" / "cohezion" / "knowledge_graph"
        self._metrics_file = self.metrics_dir / "token_efficiency.json"
        self._session_data: dict[str, Any] = {
            "by_agent": defaultdict(lambda: {"calls": 0, "tokens": 0, "cache_hits": 0}),
            "by_model": defaultdict(
                lambda: {"calls": 0, "tokens": 0, "avg_latency_ms": 0}
            ),
            "by_task_type": defaultdict(lambda: {"calls": 0, "tokens": 0}),
            "wasteful_patterns": [],
        }
        self._load()

    def record(
        self,
        agent_name: str,
        model: str,
        task_type: str,
        tokens_used: int,
        cached: bool = False,
        latency_ms: float = 0.0,
    ) -> None:
        """Record a single LLM call for efficiency tracking.

        Parameters
        ----------
        agent_name : str
            Name of the calling agent.
        model : str
            Ollama model used.
        task_type : str
            Type of task (coding, analysis, etc).
        tokens_used : int
            Approximate token count.
        cached : bool
            Whether this was a cache hit.
        latency_ms : float
            Call latency in milliseconds.
        """
        agent_data = self._session_data["by_agent"][agent_name]
        agent_data["calls"] += 1
        agent_data["tokens"] += tokens_used
        if cached:
            agent_data["cache_hits"] += 1

        model_data = self._session_data["by_model"][model]
        model_data["calls"] += 1
        model_data["tokens"] += tokens_used
        # Running average
        n = model_data["calls"]
        model_data["avg_latency_ms"] = (
            model_data["avg_latency_ms"] * (n - 1) + latency_ms
        ) / n

        task_data = self._session_data["by_task_type"][task_type]
        task_data["calls"] += 1
        task_data["tokens"] += tokens_used

    def detect_waste(self) -> list[dict[str, Any]]:
        """Identify wasteful token usage patterns.

        Returns
        -------
        list[dict]
            List of identified wasteful patterns with recommendations.
        """
        patterns: list[dict[str, Any]] = []

        # Pattern 1: Agents with low cache hit rate (< 10%)
        for agent, data in self._session_data["by_agent"].items():
            if data["calls"] >= 10:
                hit_rate = data["cache_hits"] / data["calls"]
                if hit_rate < 0.1:
                    patterns.append(
                        {
                            "type": "low_cache_utilization",
                            "agent": agent,
                            "cache_hit_rate": round(hit_rate, 3),
                            "recommendation": (
                                f"Enable semantic caching for {agent} - "
                                f"{data['calls']} calls with {hit_rate:.1%} cache hits"
                            ),
                        }
                    )

        # Pattern 2: Models with high avg latency (> 30s) suggesting oversized context
        for model, data in self._session_data["by_model"].items():
            if data["calls"] >= 5 and data["avg_latency_ms"] > 30000:
                avg_tokens = data["tokens"] / data["calls"]
                patterns.append(
                    {
                        "type": "high_latency_model",
                        "model": model,
                        "avg_latency_ms": round(data["avg_latency_ms"]),
                        "avg_tokens": round(avg_tokens),
                        "recommendation": (
                            f"Consider context pruning or model downgrade for {model}"
                        ),
                    }
                )

        # Pattern 3: Task types consuming disproportionate tokens
        total_tokens = sum(
            d["tokens"] for d in self._session_data["by_task_type"].values()
        )
        if total_tokens > 0:
            for task_type, data in self._session_data["by_task_type"].items():
                share = data["tokens"] / total_tokens
                if share > 0.5 and data["calls"] >= 5:
                    patterns.append(
                        {
                            "type": "token_concentration",
                            "task_type": task_type,
                            "token_share": round(share, 3),
                            "recommendation": (
                                f"Task type '{task_type}' consuming {share:.0%} of tokens"
                                " - consider batching or offloading"
                            ),
                        }
                    )

        self._session_data["wasteful_patterns"] = patterns
        return patterns

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of token efficiency metrics.

        Returns
        -------
        dict
            Summary with totals, per-agent, per-model, and optimization suggestions.
        """
        total_calls = sum(d["calls"] for d in self._session_data["by_agent"].values())
        total_tokens = sum(d["tokens"] for d in self._session_data["by_agent"].values())
        total_cache = sum(
            d["cache_hits"] for d in self._session_data["by_agent"].values()
        )

        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cache_hits": total_cache,
            "cache_hit_rate": round(total_cache / max(1, total_calls), 3),
            "avg_tokens_per_call": round(total_tokens / max(1, total_calls)),
            "by_agent": dict(self._session_data["by_agent"]),
            "by_model": dict(self._session_data["by_model"]),
            "by_task_type": dict(self._session_data["by_task_type"]),
            "wasteful_patterns": self._session_data["wasteful_patterns"],
            "timestamp": datetime.now().isoformat(),
        }

    def _load(self) -> None:
        """Load persisted metrics if available."""
        if self._metrics_file.exists():
            try:
                data = json.loads(self._metrics_file.read_text())
                for key in ["by_agent", "by_model", "by_task_type"]:
                    if key in data:
                        self._session_data[key].update(data[key])
            except Exception as e:
                logger.warning("Failed to load token metrics: %s", e)

    def persist(self) -> None:
        """Save current metrics to disk."""
        try:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            summary = self.get_summary()
            self._metrics_file.write_text(json.dumps(summary, indent=2))
            logger.info("Token efficiency metrics saved to %s", self._metrics_file)
        except Exception as e:
            logger.error("Failed to persist token metrics: %s", e)


class RetrospectionEngine:
    """Unified retrospection engine combining pattern analysis and token tracking.

    Wires into the agent lifecycle: call ``run_retrospective()`` after every N tasks
    to analyze patterns, detect waste, and update the knowledge graph.

    Parameters
    ----------
    auto_interval : int
        Run retrospection automatically every N tasks (0 to disable).
    """

    def __init__(self, auto_interval: int = 50):
        self.retrospector = PhaseRetrospector()
        self.token_tracker = TokenEfficiencyTracker()
        self.auto_interval = auto_interval
        self._task_counter = 0

    def tick(
        self,
        agent_name: str,
        model: str,
        task_type: str,
        tokens: int,
        cached: bool = False,
        latency_ms: float = 0.0,
    ) -> dict[str, Any] | None:
        """Record a task completion and trigger retrospection if interval reached.

        Returns retrospection results if triggered, None otherwise.
        """
        self.token_tracker.record(
            agent_name, model, task_type, tokens, cached, latency_ms
        )
        self._task_counter += 1

        if self.auto_interval > 0 and self._task_counter % self.auto_interval == 0:
            return self.run_retrospective()
        return None

    def run_retrospective(self) -> dict[str, Any]:
        """Execute a full retrospection cycle.

        Returns
        -------
        dict
            Combined results from pattern analysis and efficiency tracking.
        """
        logger.info("Running compound engineering retrospective...")

        # Phase 1: Pattern analysis
        patterns = self.retrospector.scan_for_patterns()

        # Phase 2: Token waste detection
        waste = self.token_tracker.detect_waste()

        # Phase 3: Write findings to knowledge graph
        self.retrospector.write_retrospective(patterns)
        self.token_tracker.persist()

        result = {
            "patterns": patterns,
            "token_efficiency": self.token_tracker.get_summary(),
            "waste_detected": waste,
            "task_count": self._task_counter,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            "Retrospective complete: %d skills analyzed, %d wasteful patterns detected",
            patterns["total_skills"],
            len(waste),
        )
        return result
