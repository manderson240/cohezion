"""
Anti-Pattern Scout - Detects bad practices and technical debt.
Specifically checks for blocking sync calls, matplotlib usage, and missing documentation.
"""

import logging
from pathlib import Path

from cohezion.swarm.agents.base_scout import BaseScout, Finding


logger = logging.getLogger(__name__)


class AntiPatternScout(BaseScout):
    """
    Detects technical debt and 'Safe Mode' violations.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            model="phi3:mini", **kwargs
        )  # Use even smaller model for debt detection

    async def analyze(self, path: Path) -> list[Finding]:
        content = path.read_text()

        prompt = f"""
        Analyze this code for Anti-Patterns.

        Code:
        {content[:3000]}

        Check specifically for:
        1. Sync blocking calls in async functions.
        2. Usage of 'matplotlib' (Should use Plotly/Datashader).
        3. Lack of 'FUTURE HOOKS' section in skill/agent files.
        4. Bare except handlers.

        Return JSON structure: {{ "anti_patterns": [...] }}
        """

        try:
            response_json = await self._call_local_llm(prompt)
            import json

            data = json.loads(response_json)

            findings = []
            for ap in data.get("anti_patterns", []):
                findings.append(
                    Finding(
                        type="anti_pattern",
                        name=ap["name"],
                        category="tech_debt",
                        description=ap["description"],
                        file_path=str(path),
                        line_range=(1, len(content.splitlines())),
                        confidence=ap.get("confidence", 0.9),
                        code_snippet="N/A",
                        severity=ap.get("severity", "medium"),
                        remediation=ap.get("remediation", "Check Cohezion standards."),
                    )
                )
            return findings
        except Exception as e:
            logger.error(f"AntiPatternScout failed for {path}: {e}")
            return []
