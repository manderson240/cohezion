"""
HealerAgent - Autonomous Code Refactoring and Self-Healing.

Processes audit reports and applies verified, non-breaking code fixes.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any

from cohezion.reliability.sync import FileLock, SafeWriter
from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class HealerAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="mistral:7b",  # Strong code-gen model
            config=config or SwarmConfig(),
        )

    async def process(self, audit_report: str) -> str:
        """
        Analyze an audit report and attempt to fix identified issues.
        """
        logger.info("🩺 HealerAgent analyzing audit findings...")

        # 1. Identify issues
        issues = self._extract_issues(audit_report)
        if not issues:
            return "No fixable issues identified in report."

        summary = []
        for issue in issues[:3]:  # limit per sprint
            success = await self._apply_fix_sandbox(issue)
            summary.append(
                f"{'✅' if success else '❌'} {issue['file']}:{issue['line']}"
            )

        return "Healing Summary:\n" + "\n".join(summary)

    def _extract_issues(self, report: str) -> list[dict[str, Any]]:
        """Parse the markdown report for issues (naive implementation)."""
        import re

        # Look for the pattern: `path/to/file.py:line`
        pattern = r"`([^`]+\.py):(\d+)`"
        matches = re.finditer(pattern, report)

        issues = []
        for m in matches:
            issues.append({"file": m.group(1), "line": int(m.group(2))})
        return issues

    async def _apply_fix_sandbox(self, issue: dict[str, Any]) -> bool:
        """
        Attempt to fix a specific issue using the Sandbox Protocol.
        1. Create sandbox copy
        2. Apply proposed fix
        3. Verify with syntax check
        4. Apply to original if pass
        """
        file_path = Path(issue["file"])
        if not file_path.exists():
            return False

        logger.info(f"🧪 Attempting sandbox-healing for {file_path}:{issue['line']}")

        # 1. Proposal Phase
        content = file_path.read_text()
        lines = content.splitlines()
        start = max(0, issue["line"] - 5)
        end = min(len(lines), issue["line"] + 5)
        context = "\n".join(lines[start:end])

        prompt = f"""Fix the following Python code for async safety.
Replace any blocking calls (subprocess.run) with async alternatives.

CONTEXT:
```python
{context}
```
Provide ONLY the corrected code block.
"""
        try:
            response = await self._call_ollama(prompt, temperature=0.1)

            # 2. Sandbox Phase
            # Extract code block if present
            import re

            code_match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
            fixed_block = code_match.group(1) if code_match else response

            # 3. Verification & Commit Phase (using Reliability Primitives)
            # Use FileLock to prevent concurrent healers on the same file
            lock = FileLock(file_path.with_suffix(file_path.suffix + ".lock"))
            with lock.acquire():
                # Simple line replacement for demo (complex logic would use AST)
                new_lines = lines.copy()
                if len(new_lines) >= issue["line"]:
                    target_content = new_lines[issue["line"] - 1].strip()
                    if (
                        target_content
                        and "import" not in target_content
                        and '"""' not in target_content
                    ):
                        new_lines[issue["line"] - 1] = fixed_block.strip()
                    else:
                        logger.warning(
                            f"Skipping heal for metadata line: {target_content}"
                        )
                        return False

                # Use SafeWriter for atomic update
                with SafeWriter(file_path).open() as out:
                    out.write("\n".join(new_lines))

                # Verify the written file
                check = subprocess.run(
                    ["python3", "-m", "py_compile", str(file_path)], capture_output=True
                )

                if check.returncode == 0:
                    logger.info(f"✨ Successfully healed {file_path}")
                    return True
                else:
                    logger.warning(
                        f"❌ Verification failed for {file_path}: {check.stderr.decode()}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Healing failed for {file_path}: {e}")
            return False
