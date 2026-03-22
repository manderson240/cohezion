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

    def log_execution_result(self, experiment_path: str, success: bool, output: str, metrics: dict[str, Any]):
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

    def get_experience_guidance(self, task_description: str, project: str = "cohezion") -> dict[str, Any]:
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
        self,
        source_path: str,
        pattern_name: str,
        description: str,
        code_example: str,
        domain: str,
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
                content += (
                    f"\n\n--- \nTags: #retrospective"
                    f" #{data.get('agent', 'agent').lower()}"
                    f" #{data.get('skill_name', 'skill').lower()}\n"
                )

                self.mcp.vault_write(filename, content)
                logger.info(f"Architectural insight persisted to Vault: {filename}")

            except Exception as e:
                logger.error(
                    f"Vault human-readable persistence failed for mission {data.get('mission_id')}: {e}"
                )



def get_vault_logger() -> VaultLogger:
    return VaultLogger()
