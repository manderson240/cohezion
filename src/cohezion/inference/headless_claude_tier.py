"""Headless Claude Code as a TieredOrchestrator tier.

Claude Code has tools (file read/write, bash, edit) that no pure LLM tier has.
When code-generation tasks fail the iGPU/CPU quality gate, HeadlessClaudeTier
can generate AND verify the code using its tool access.

Usage in orchestrator:
    from cohezion.inference.headless_claude_tier import HeadlessClaudeTier, build_claude_tier
    tier = build_claude_tier()

Security note: HeadlessClaudeTier runs a subprocess with network access.
Only use for trusted, sanitized prompts. The security_spec injection check
must pass before dispatching to this tier.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass

from cohezion.inference.orchestrator import OrchestrationResult


logger = logging.getLogger(__name__)

# Default timeout for headless Claude Code subprocesses.
# Code tasks can take time — Claude may need to iterate.
_DEFAULT_TIMEOUT_S = 120.0


@dataclass
class HeadlessClaudeTier:
    """Wraps headless Claude Code (`claude -p`) as a TieredOrchestrator tier.

    Headless Claude Code has tools: file read/write, bash, edit.
    It can generate code AND verify it — making it uniquely valuable for
    code tasks where correctness (not just text quality) matters.

    Parameters
    ----------
    label : str
        Identifier in OrchestrationResult tier_path.
    timeout_s : float
        Subprocess timeout in seconds. Code tasks may iterate (120s default).
    model : str
        Claude model to use via --model flag. None = use default.
    max_tokens : int
        Optional --max-tokens limit.
    """

    label: str = "headless-claude"
    timeout_s: float = _DEFAULT_TIMEOUT_S
    model: str | None = None
    max_tokens: int | None = None

    async def run(self, prompt: str, **_: object) -> OrchestrationResult:
        """Invoke Claude Code headlessly, wrap result in OrchestrationResult."""
        start = time.perf_counter()
        text = ""
        error: str | None = None

        cmd = ["claude", "--output-format", "json", "--print", prompt]
        if self.model:
            cmd += ["--model", self.model]
        if self.max_tokens:
            cmd += ["--max-tokens", str(self.max_tokens)]

        try:
            from cohezion.inference.sandbox import SandboxedSubprocess

            loop = asyncio.get_running_loop()

            with SandboxedSubprocess(allow_anthropic=True) as sb:
                result = await loop.run_in_executor(
                    None,
                    lambda: _run_subprocess(cmd, timeout=self.timeout_s, env=sb.env, cwd=sb.cwd),
                )
            if result.get("error"):
                error = result["error"]
            else:
                text = result.get("result", "").strip()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logger.warning("HeadlessClaudeTier error: %s", error)

        latency_ms = (time.perf_counter() - start) * 1000
        return OrchestrationResult(
            text=text,
            primary_model=self.label,
            final_model=self.label,
            escalation_count=0,
            tier_path=[],
            cost_usd=0.0,  # headless Claude Code uses Anthropic API — caller tracks cost
            latency_ms=latency_ms,
            ttft_ms=None,
            error=error,
        )


def _run_subprocess(
    cmd: list[str],
    timeout: float,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
) -> dict[str, str]:
    """Run a subprocess and parse JSON output. Returns dict with 'result' or 'error'."""
    import subprocess

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=cwd,
        )
        if proc.returncode != 0:
            return {"error": f"exit {proc.returncode}: {proc.stderr[:500]}"}

        stdout = proc.stdout.strip()
        if not stdout:
            return {"result": proc.stderr.strip() or ""}

        # Try JSON parse (--output-format json)
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                return {"result": parsed.get("result", str(parsed))}
            return {"result": str(parsed)}
        except json.JSONDecodeError:
            return {"result": stdout}

    except subprocess.TimeoutExpired:
        return {"error": f"Timeout after {timeout:.0f}s"}
    except FileNotFoundError:
        return {"error": "claude CLI not found — install Claude Code"}


def build_claude_tier(
    *,
    model: str | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> HeadlessClaudeTier:
    """Factory for HeadlessClaudeTier with sensible defaults."""
    return HeadlessClaudeTier(label="headless-claude", model=model, timeout_s=timeout_s)
