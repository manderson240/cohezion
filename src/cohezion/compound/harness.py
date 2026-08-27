"""Automated safety harness synthesizer for agent-generated code."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any


log = logging.getLogger("autoharness")

# A single pytest run can emit 50k+ characters. Unbounded, that lands straight in an agent's
# context (~12.5k tokens at 4 chars/token) and crowds out the work. Raised as a backlog item
# 2026-06-24 after reviewing LangChain Deep Agents, which caps tool output at the same value.
MAX_TOOL_OUTPUT_CHARS = 20_000


def _cap_output(text: str, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    """Cap captured subprocess output, keeping BOTH ends and saying so.

    Head and tail are both preserved because the two useful regions sit at opposite ends: a
    traceback opens the output, while a test runner's failure summary closes it. A head-only
    truncation would discard exactly the part worth reading.

    The elision marker is not decoration — silent truncation is indistinguishable from genuinely
    short output, which is the same class of failure as a silently-empty result.
    """
    if len(text) <= limit:
        return text
    # The marker must fit INSIDE the cap: adversarial review 2026-08-20 measured the previous
    # version returning limit + len(marker) chars, so a downstream consumer enforcing the same
    # limit would re-truncate and destroy the tail this function exists to preserve. The dropped
    # count and the marker length depend on each other (digit width), so iterate to a fixpoint —
    # converges in <= 2 passes because dropped only shifts by the marker's own length.
    dropped = len(text) - limit
    head = tail = 0
    marker = ""
    for _ in range(3):
        marker = f"\n... [truncated {dropped} chars; cap {limit}] ...\n"
        budget = max(limit - len(marker), 2)
        head = budget // 2
        tail = budget - head
        if len(text) - head - tail == dropped:
            break
        dropped = len(text) - head - tail
    return text[:head] + marker + text[-tail:]


class HarnessSynthesizer:
    """Synthesizes and executes verification harnesses for proposed code changes."""

    def __init__(self, model_provider: Any = None):
        self.model_provider = model_provider

    def generate_harness(self, proposed_code: str, target_module: str) -> str:
        """Use an LLM to synthesize a verification script.

        In a real implementation, this would call the LLM provider.
        For now, we use a template-based approach or a simple generic harness.
        """
        # Example generic harness template
        harness_template = f"""
import sys
import os
import traceback

def run_verification():
    try:
        # Import the proposed code
        {proposed_code}

        # Add invariant checks here (synthesized by LLM)
        log_info("Harness started...")

        # Verify module presence
        import {target_module}
        log_info(f"Module {{'{target_module}'}} imported successfully.")

        # Generic functional check if applicable
        # ...

        log_info("Harness completed successfully.")
        return True
    except Exception as e:
        print(f"HARNESS_FAILURE: {{e}}")
        traceback.print_exc()
        return False

def log_info(msg):
    print(f"HARNESS_INFO: {{msg}}")

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
"""
        return harness_template

    def verify(self, proposed_code: str, target_module: str) -> tuple[bool, str]:
        """Synthesize and run the harness, returns (success, output)."""
        harness_code = self.generate_harness(proposed_code, target_module)

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
            tmp.write(harness_code)
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                ["python3", str(tmp_path)], capture_output=True, text=True, timeout=60
            )
            success = result.returncode == 0
            output = _cap_output(result.stdout + result.stderr)
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Harness timed out after 60 seconds."
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
