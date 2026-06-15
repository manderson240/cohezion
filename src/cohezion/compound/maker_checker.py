"""Maker-Checker split for CompoundExecutor.

Implements the asymmetric Maker-Checker pattern from loop engineering research
(lushbinary.com/blog/loop-engineering-ai-coding-agents-guide/):
- Maker: fast execution tier (NPU/iGPU via Lemonade :13305)
- Checker: higher-effort verification tier (CPU/larger model via Lemonade :13305)

The Checker is always a separate concern from the Maker — not the same agent
re-reading its own output. Asymmetry is the key: the Checker uses a richer
model with more reasoning budget to catch what the fast Maker missed.

Integration: CompoundExecutor calls MakerCheckerVerifier.verify(output, task)
after execute_fn succeeds (Step 3), before skill refinement (Step 7). The
checker verdict is additive — it adds to metrics but never blocks the result.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)

# Default timeout for checker HTTP call — fast enough to not block result return
_CHECKER_TIMEOUT_SECONDS: float = 8.0

# Checker model: prefer CPU tier (higher reasoning) via Lemonade :13305
# Falls back to iGPU tier if CPU is slow or unavailable.
_CHECKER_SYSTEM_PROMPT = (
    "You are a rigorous output verifier. Given a task description and the output produced "
    "by an AI assistant, evaluate whether the output correctly addresses the task. "
    "Respond with exactly one JSON object: "
    '{{"verdict": "pass"|"fail"|"partial", "confidence": <0.0-1.0>, "reason": "<one sentence>"}}'
    " Do not include any other text."
)


@dataclass
class CheckerResult:
    """Result of a Maker-Checker verification pass.

    verdict: 'pass' | 'fail' | 'partial' | 'skipped' | 'error'
    confidence: 0.0-1.0 (1.0 = very confident in verdict)
    reason: one-sentence explanation
    latency_seconds: wall-clock time for the checker call
    model: which model was used for checking
    """

    verdict: str = "skipped"
    confidence: float = 0.0
    reason: str = ""
    latency_seconds: float = 0.0
    model: str = ""

    def to_metrics_dict(self) -> dict[str, Any]:
        return {
            "checker_verdict": self.verdict,
            "checker_confidence": self.confidence,
            "checker_reason": self.reason,
            "checker_latency_s": round(self.latency_seconds, 3),
            "checker_model": self.model,
        }


@dataclass
class MakerCheckerVerifier:
    """Asymmetric Maker-Checker verifier using Lemonade :13305.

    The Checker calls the CPU-tier model (higher reasoning) on the same
    Lemonade OmniRouter as the Maker. Because the router handles model
    selection, the Checker just requests a larger/slower model explicitly.

    Usage inside CompoundExecutor.execute_task():

        checker_result = self._maker_checker.verify(
            task_description=task_description,
            maker_output=output,
        )
        metrics.update(checker_result.to_metrics_dict())
    """

    lemonade_url: str = "http://localhost:13305"
    checker_model: str = "Granite-4.1-8B-Instruct-GGUF-Strix-Q4_K_M"
    timeout_seconds: float = _CHECKER_TIMEOUT_SECONDS
    enabled: bool = True

    # Internal state — not part of public API
    _last_result: CheckerResult = field(default_factory=CheckerResult, init=False, repr=False)

    def verify(
        self,
        task_description: str,
        maker_output: str,
        *,
        timeout: float | None = None,
    ) -> CheckerResult:
        """Verify Maker output against task description using a higher-effort model.

        Non-blocking by design: if the checker times out or fails, returns a
        CheckerResult with verdict='error' so the caller can still proceed.

        Args:
            task_description: The original task given to the Maker.
            maker_output: The output produced by the Maker.
            timeout: Override checker timeout for this call.

        Returns:
            CheckerResult with verdict, confidence, reason, and latency.
        """
        if not self.enabled:
            return CheckerResult(verdict="skipped", reason="maker_checker disabled")

        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        t0 = time.monotonic()

        try:
            result = self._call_checker(task_description, maker_output, effective_timeout)
        except Exception as exc:
            latency = time.monotonic() - t0
            logger.debug("Checker failed (non-blocking): %s", exc)
            result = CheckerResult(
                verdict="error",
                confidence=0.0,
                reason=f"checker_error: {type(exc).__name__}",
                latency_seconds=latency,
                model=self.checker_model,
            )

        self._last_result = result
        return result

    def verify_async(
        self,
        task_description: str,
        maker_output: str,
        *,
        timeout: float | None = None,
    ) -> CheckerResult:
        """Run verify() in a background thread, wait up to timeout for result.

        If the thread hasn't finished by timeout, returns a 'skipped' result.
        Used when the caller wants to bound total latency strictly.
        """
        if not self.enabled:
            return CheckerResult(verdict="skipped", reason="maker_checker disabled")

        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        container: list[CheckerResult] = []

        def _run() -> None:
            container.append(self.verify(task_description, maker_output))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=effective_timeout)

        if container:
            return container[0]
        return CheckerResult(
            verdict="skipped",
            reason=f"checker_timeout after {effective_timeout:.1f}s",
            latency_seconds=effective_timeout,
            model=self.checker_model,
        )

    def _call_checker(
        self,
        task_description: str,
        maker_output: str,
        timeout: float,
    ) -> CheckerResult:
        """Make the HTTP call to Lemonade :13305 for checker inference."""
        user_content = f"Task: {task_description[:800]}\n\nOutput to verify:\n{maker_output[:1200]}"

        payload = json.dumps(
            {
                "model": self.checker_model,
                "messages": [
                    {"role": "system", "content": _CHECKER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 120,
                "temperature": 0.0,
            }
        ).encode()

        t0 = time.monotonic()
        req = urllib.request.Request(
            f"{self.lemonade_url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())

        latency = time.monotonic() - t0
        raw_text = body["choices"][0]["message"]["content"].strip()

        return self._parse_checker_response(raw_text, latency)

    def _parse_checker_response(self, raw: str, latency: float) -> CheckerResult:
        """Parse checker LLM output into CheckerResult."""
        # Extract JSON from the response (model may wrap in markdown)
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            return CheckerResult(
                verdict="error",
                confidence=0.0,
                reason=f"unparseable_checker_response: {raw[:80]}",
                latency_seconds=latency,
                model=self.checker_model,
            )

        try:
            parsed = json.loads(json_match.group())
        except json.JSONDecodeError:
            return CheckerResult(
                verdict="error",
                confidence=0.0,
                reason="invalid_json_from_checker",
                latency_seconds=latency,
                model=self.checker_model,
            )

        verdict = parsed.get("verdict", "error")
        if verdict not in {"pass", "fail", "partial"}:
            verdict = "error"

        confidence = float(parsed.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        return CheckerResult(
            verdict=verdict,
            confidence=confidence,
            reason=str(parsed.get("reason", ""))[:200],
            latency_seconds=latency,
            model=self.checker_model,
        )


def build_maker_checker(
    lemonade_url: str = "http://localhost:13305",
    *,
    enabled: bool = True,
    timeout_seconds: float = _CHECKER_TIMEOUT_SECONDS,
) -> MakerCheckerVerifier:
    """Build a MakerCheckerVerifier wired to Lemonade :13305.

    Uses Granite-4.1-8B as the default checker model — it's bounded at
    ctx_size=16384 (no OOM risk, N3 invariant), available in the standard
    Lemonade catalog, and provides enough reasoning depth for output verification.
    """
    return MakerCheckerVerifier(
        lemonade_url=lemonade_url,
        enabled=enabled,
        timeout_seconds=timeout_seconds,
    )
