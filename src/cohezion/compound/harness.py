"""Automated safety harness synthesizer for agent-generated code."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any


log = logging.getLogger("autoharness")


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
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Harness timed out after 60 seconds."
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
