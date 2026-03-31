import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cohezion.core.mcp_client import get_mcp_client


logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    project: str
    skill_name: str
    task_description: str
    operation_type: str
    start_time: datetime
    mcp_client: Any


class VaultLogger:
    """
    Unified Vault Logger for Cohezion.
    - Implements the VaultExecutionLogger contract for machine-readable guidance.
    - Implements human-readable Obsidian retrospectives with importance sampling.
    """

    def __init__(self, novelty_threshold: float = 0.8, mcp_client: Any | None = None):
        self._mcp = mcp_client
        self.novelty_threshold = novelty_threshold

    @property
    def mcp(self):
        if self._mcp is None:
            self._mcp = get_mcp_client()
        return self._mcp

    # ── VaultExecutionLogger Contract ──────────────────────────────────

    def log_execution_start(self, ctx: ExecutionContext) -> str:
        """Log the start of an execution to the Vault."""
        try:
            path = (
                f"experiments/{ctx.project}/{ctx.skill_name}/{int(ctx.start_time.timestamp())}.json"
            )
            data = {
                "project": ctx.project,
                "skill_name": ctx.skill_name,
                "task_description": ctx.task_description,
                "operation_type": ctx.operation_type,
                "start_time": ctx.start_time.isoformat(),
                "status": "started",
            }
            self.mcp.vault_write(path, json.dumps(data, indent=2))
            return path
        except Exception as e:
            logger.error(f"Failed to log execution start to Vault: {e}")
            return ""

    def log_execution_result(
        self, experiment_path: str, success: bool, output: str, metrics: dict[str, Any]
    ):
        """Update the execution log with results."""
        if not experiment_path:
            return
        try:
            # Read existing
            content = self.mcp.vault_read(experiment_path)
            data = json.loads(content)

            # Update
            data["success"] = success
            data["output_summary"] = output[:1000] if output else ""
            data["metrics"] = metrics
            data["status"] = "completed"
            data["end_time"] = datetime.now().isoformat()

            self.mcp.vault_write(experiment_path, json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to log execution result to Vault: {e}")

    def get_experience_guidance(
        self, task_description: str, project: str = "cohezion"
    ) -> dict[str, Any]:
        """Fetch similar patterns from the Vault for guidance."""
        try:
            # Simple keyword extraction for search
            keywords = [w for w in task_description.lower().split() if len(w) > 4][:3]
            query = " ".join(keywords) if keywords else "general"

            logger.debug(f"Searching Vault for guidance: {query}")
            patterns = self.mcp.vault_search(query)

            return {
                "relevant_context": patterns,
                "guidance": f"Retrieved {len(patterns)} historical patterns from the Cohezion Vault matching: {query}"
                if patterns
                else "No prior patterns found for this specific intent.",
            }
        except Exception as e:
            logger.error(f"Failed to fetch guidance from Vault: {e}")
            return {"relevant_context": [], "guidance": "Vault guidance unavailable."}

    def extract_execution_pattern(
        self, source_path: str, pattern_name: str, description: str, code_example: str, domain: str
    ) -> str:
        """Extract a reusable pattern from a successful execution."""
        try:
            path = f"patterns/domains/{domain}/{pattern_name}.md"
            content = f"""# Pattern: {pattern_name}
- **Domain**: {domain}
- **Description**: {description}
- **Source**: {source_path}

## Example
```python
{code_example}
```
"""
            self.mcp.vault_write(path, content)
            return path
        except Exception as e:
            logger.error(f"Failed to extract pattern to Vault: {e}")
            return ""

    def log_decision_point(
        self, project: str, title: str, context: str, decision: str, rationale: str
    ) -> str:
        """Log a critical decision point to the vault."""
        try:
            timestamp = int(datetime.now().timestamp())
            path = f"decisions/{project}/inflection_{timestamp}.md"
            content = f"""# Decision: {title}

- **Project**: {project}
- **Timestamp**: {datetime.now().isoformat()}

## Context
{context}

## Decision
{decision}

## Rationale
{rationale}
"""
            self.mcp.vault_write(path, content)
            return path
        except Exception as e:
            logger.error(f"Failed to log decision point to Vault: {e}")
            return ""

    # ── Execution Traces (Meta-Harness L225 Pattern) ─────────────────

    def log_execution_trace(
        self,
        ctx: ExecutionContext,
        success: bool,
        output: str,
        metrics: dict[str, Any],
        token_metrics: dict[str, Any] | None = None,
    ) -> str:
        """Log structured execution trace to execution_traces/ directory.

        Meta-Harness pattern (arXiv:2603.28052): expose execution history as
        browsable filesystem files (grep/cat) rather than cramming into prompts.
        SkillRefiner browses these traces instead of reading summaries.

        Directory structure:
            execution_traces/{skill_name}/{timestamp}_{operation}.json

        Returns:
            Trace file path, or empty string on failure
        """
        try:
            timestamp = int(datetime.now().timestamp())
            trace_path = f"execution_traces/{ctx.skill_name}/{timestamp}_{ctx.operation_type}.json"
            trace_data = {
                "project": ctx.project,
                "skill_name": ctx.skill_name,
                "task_description": ctx.task_description,
                "operation_type": ctx.operation_type,
                "start_time": ctx.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "success": success,
                "output_summary": output[:500] if output else "",
                "metrics": {
                    k: v for k, v in metrics.items() if isinstance(v, (int, float, str, bool))
                },
                "token_metrics": token_metrics or {},
                "coherence": metrics.get("coherence", 0.0),
                "anomaly_score": metrics.get("anomaly_score", 0.0),
                "natural_capital": metrics.get("natural_capital", 0.0),
                "bioelectric_coherence": metrics.get("bioelectric_coherence", 0.0),
            }
            self.mcp.vault_write(trace_path, json.dumps(trace_data, indent=2))

            # Prune old traces (keep last 100 per skill)
            self._prune_traces(ctx.skill_name)

            return trace_path
        except Exception as e:
            logger.debug("Failed to log execution trace: %s", e)
            return ""

    def _prune_traces(self, skill_name: str, max_traces: int = 100) -> None:
        """Keep only the last N traces per skill (non-blocking)."""
        try:
            # List traces for this skill
            traces = self.mcp.vault_search(f"execution_traces/{skill_name}/")
            if isinstance(traces, list) and len(traces) > max_traces:
                # Sort by name (timestamp-based) and remove oldest
                sorted_traces = sorted(traces)
                to_remove = sorted_traces[: len(sorted_traces) - max_traces]
                for trace_path in to_remove:
                    try:
                        self.mcp.vault_delete(trace_path)
                    except Exception:
                        pass
        except Exception:
            pass  # Non-blocking: pruning failure is not critical

    def browse_recent_traces(self, skill_name: str, n: int = 5) -> list[dict[str, Any]]:
        """Browse recent execution traces for a skill.

        Used by SkillRefiner to find relevant prior executions
        via filesystem instead of prompt summaries.

        Args:
            skill_name: Skill to browse traces for
            n: Number of recent traces to return

        Returns:
            List of trace data dicts, most recent first
        """
        results: list[dict[str, Any]] = []
        try:
            traces = self.mcp.vault_search(f"execution_traces/{skill_name}/")
            if not isinstance(traces, list):
                return results

            # Get most recent N traces
            recent = sorted(traces, reverse=True)[:n]
            for trace_path in recent:
                try:
                    content = self.mcp.vault_read(trace_path)
                    data = json.loads(content)
                    results.append(data)
                except Exception:
                    continue
        except Exception:
            pass
        return results

    # ── Obsidian Mission Retrospectives ────────────────────────────────

    async def log_batch(self, batch: list[dict[str, Any]]):
        """Log high-value mission summaries to the Vault for humans."""
        for data in batch:
            # Importance Sampling
            novelty = data.get("novelty", 1.0)
            if novelty < self.novelty_threshold:
                continue

            try:
                mission_id = data.get("mission_id", "unknown")
                summary = data.get("summary", "No summary provided.")
                decisions = data.get("decisions", [])

                # Format as Obsidian Markdown
                content = f"""# Mission Retrospective: {mission_id}
- **Novelty Score**: {novelty:.2f}
- **Status**: {data.get("status", "complete")}

## Summary
{summary}

## Key Decisions
"""
                for d in decisions:
                    content += f"- {d}\n"

                filename = f"missions/{mission_id}.md"
                # Add links to relevant project and skill for Obsidian Graph connectivity
                content += f"\n\n--- \nTags: #retrospective #{data.get('agent', 'agent').lower()} #{data.get('skill_name', 'skill').lower()}\n"

                self.mcp.vault_write(filename, content)
                logger.info(f"Architectural insight persisted to Vault: {filename}")

            except Exception as e:
                logger.error(
                    f"Vault human-readable persistence failed for mission {data.get('mission_id')}: {e}"
                )


def get_vault_logger() -> VaultLogger:
    return VaultLogger()
