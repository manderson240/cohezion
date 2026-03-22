"""
Pattern Scout - Detects design patterns (Circuit Breaker, Strategy, Observer) in code.
Uses qwen2.5-coder:7b for semantic pattern recognition.
"""

import logging
from pathlib import Path

from cohezion.swarm.agents.base_scout import BaseScout, Finding


logger = logging.getLogger(__name__)


class PatternScout(BaseScout):
    """
    Detects semantic patterns like Circuit Breaker, Strategy, etc.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(model="qwen2.5-coder:7b", **kwargs)

    async def analyze(self, path: Path) -> list[Finding]:
        # Implementation similar to ArchitectureScout but focusing on internal logic
        # For brevity, we focus the prompt on GOF and Cohezion-specific patterns
        ast_summary = self._parse_python_ast(path)
        if not ast_summary:
            return []

        prompt = f"""
        Scan this Python code for design patterns.

        File: {path.name}
        Content Snippets: {path.read_text()[:3000]} # First 3k chars

        Look for:
        - Circuit Breaker (cohezion.reliability.get_circuit)
        - Strategy Pattern
        - Observer/Event emitter
        - 12D State vectors (FLUME)

        Return JSON structure: {{ "patterns": [...] }}
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
                        name=p.get("name", "Unknown Pattern"),
                        category="design_pattern",
                        description=p.get("description", "No description provided"),
                        file_path=str(path),
                        line_range=(1, ast_summary.loc),
                        confidence=p.get("confidence", 0.8),
                        code_snippet="N/A",
                    )
                )
            return findings
        except Exception as e:
            logger.error(f"PatternScout failed for {path}: {e}")
            return []
