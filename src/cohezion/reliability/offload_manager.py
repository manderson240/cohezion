"""
Offload Manager for Cohezion.
Classifies tasks as menial (offloadable) or critical (cortex-only).
"""

from typing import Any


class OffloadManager:
    def __init__(self):
        # Keywords that suggest a task is "menial" (low-complexity, documentation, formatting)
        self.menial_keywords = [
            "explain",
            "refactor simple",
            "add types",
            "summarize",
            "list",
            "write docstrings",
            "update comments",
            "format",
            "fix typo",
            "boilerplate",
            "hello world",
            "check syntax",
            "simple refactor",
        ]

        # Keywords that suggest a task is "critical" (logic, architecture, security)
        self.critical_keywords = [
            "security",
            "architecture",
            "design pattern",
            "deploy",
            "production",
            "circuit breaker",
            "manifold",
            "flume",
            "quadrature",
            "hiho",
            "refactor core",
            "protocol",
            "quantum",
            "physics",
            "simulation",
            "database schema",
            "regression",
            "auth",
            "encryption",
        ]

    def is_offloadable(self, query: str) -> bool:
        """Determines if a task query is suitable for a local SLM offload."""
        q = query.lower()

        # If it's explicitly critical, don't offload
        if any(kw in q for kw in self.critical_keywords):
            return False

        # If it contains menial keywords, it's highly likely offloadable
        if any(kw in q for kw in self.menial_keywords):
            return True

        # Heuristic: shorter queries (<200 chars) about documentation or small edits are offloadable
        if len(q) < 200 and any(kw in q for kw in ["doc", "comment", "format", "rename", "move"]):
            return True

        # Very short queries are almost always offloadable unless they hit critical keywords above
        return len(q) < 50

    def get_offload_recommendation(self, query: str) -> dict[str, Any]:
        """Provides a recommendation on whether to offload and which model to use."""
        offloadable = self.is_offloadable(query)

        if not offloadable:
            return {"offload": False, "target": "gemini-3-pro"}

        # Determine specific local target
        q = query.lower()
        target = "qwen3-coder-256k" if "code" in q or "python" in q else "phi4"

        return {
            "offload": True,
            "target": target,
            "reason": "Task identified as menial/supportive.",
        }
