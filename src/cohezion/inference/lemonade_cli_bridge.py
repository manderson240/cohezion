"""Direct Lemonade CLI & Official AMD Skills Execution Bridge.

Bypasses raw HTTP request loops by invoking the native `/usr/bin/lemonade` CLI
and AMD hardware skills directly for local inference, tool invocation, and multi-silicon routing.
"""

import subprocess
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from cohezion.reliability.system_wide_fleet_lock import SystemWideFleetLock
from cohezion.reliability.oom_guard import OOMGuard

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class CLIInferenceResult:
    content: str
    model: str
    exit_code: int
    duration_s: float
    substrate: str

class LemonadeCLIBridge:
    """Direct CLI Bridge for Lemonade Server & AMD Skills."""

    LEMONADE_BIN = "/usr/bin/lemonade"

    @classmethod
    def run_prompt(
        cls,
        prompt: str,
        model: str = "Gemma-4-E4B-it-GGUF",
        max_tokens: int = 256,
        temperature: float = 0.1,
    ) -> CLIInferenceResult:
        """Executes a model prompt directly via Lemonade CLI."""
        # Using lemonade CLI to query model status & execute
        t0 = time.perf_counter()
        mem = OOMGuard.get_memory_state()
        if not mem.is_safe:
            return CLIInferenceResult(
                content=f"Memory floor violated: {mem.available_gb:.1f} GiB available",
                model=model,
                exit_code=1,
                duration_s=0.0,
                substrate="OOM_GUARD_ABORT"
            )

        # Fallback invocation via direct CLI REPL or backend call
        cmd = [cls.LEMONADE_BIN, "chat", "--model", model, prompt]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30.0)
            dt = time.perf_counter() - t0
            output = res.stdout.strip() if res.returncode == 0 else res.stderr.strip()
            return CLIInferenceResult(
                content=output,
                model=model,
                exit_code=res.returncode,
                duration_s=dt,
                substrate="AMD_LEMONADE_CLI"
            )
        except Exception as e:
            dt = time.perf_counter() - t0
            return CLIInferenceResult(
                content=str(e),
                model=model,
                exit_code=1,
                duration_s=dt,
                substrate="CLI_EXCEPTION"
            )

import time
