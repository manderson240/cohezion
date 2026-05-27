# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Architecture Scout - Identifies high-level design patterns and module coupling.
Uses qwen2.5-coder:7b to classify structural findings.
"""

import logging
from pathlib import Path

from cohezion.swarm.agents.base_scout import BaseScout, Finding


logger = logging.getLogger(__name__)


class ArchitectureScout(BaseScout):
    """
    Identifies architectural patterns (Repository, Service Layer, Factory, etc.)
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(model="qwen2.5-coder:7b", **kwargs)

    async def analyze(self, path: Path) -> list[Finding]:
        ast_summary = self._parse_python_ast(path)
        if not ast_summary:
            return []

        prompt = f"""
        Analyze the following Python module structure and identify its architectural role.

        File: {path.name}
        Classes: {ast_summary.classes}
        Functions: {ast_summary.functions}
        Imports: {ast_summary.imports}

        Identify:
        1. The primary architectural pattern/role (e.g., Persistence Client, Service, Controller, Agent, Skill).
        2. Any high-coupling issues (e.g., too many imports, class bloat).
        3. Integration with COHEZION core (SurrealDB, FLUME, ResourceGuard).

        Return a JSON object with this structure:
        {{
            "patterns": [
                {{
                    "name": "Pattern Name",
                    "category": "architecture",
                    "description": "Why it's this pattern",
                    "confidence": 0.0-1.0
                }}
            ]
        }}
        """

        try:
            response_json = await self._call_local_llm(prompt)
            import json

            data = json.loads(response_json)

            findings = []
            for p in data.get("patterns", []):
                findings.append(
                    Finding(
                        type="pattern",
                        name=p["name"],
                        category=p["category"],
                        description=p["description"],
                        file_path=str(path),
                        line_range=(1, ast_summary.loc),
                        confidence=p["confidence"],
                        code_snippet="N/A (Structural)",
                    )
                )
            return findings
        except Exception as e:
            logger.error(f"ArchitectureScout LLM call failed for {path}: {e}")
            return []
