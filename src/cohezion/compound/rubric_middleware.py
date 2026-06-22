"""RubricMiddleware — structured task output verification via Lemonade :13305.

Evaluates compound executor outputs against a caller-supplied rubric before
they are persisted to the semantic cache or used as MGPO learning signal.

Architecture (from LangChain trace-judge pattern):
  - System prompt: rubric definition
  - User message: task output to evaluate
  - Response format: JSON {"perceived_error": bool, "reason": str}
  - Fail-open: any inference or parse failure → RubricVerdict(passed=True)

Wiring in CompoundExecutor:
  Between success determination and Step 7 (skill refinement / MGPO accumulation).
  Failed verdict → should_refine=False, MGPO skip — keeps bad outputs out of
  the learning substrate.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_ROUTER_URL = "http://localhost:13305/v1/chat/completions"

_SYSTEM_TEMPLATE = """\
You are a task output judge. Evaluate the user-provided output against the rubric below.

Rubric:
{rubric}

Respond ONLY with valid JSON in exactly this format:
{{"perceived_error": <true|false>, "reason": "<one sentence explanation>"}}

perceived_error must be true if the output violates the rubric, false otherwise."""


@dataclass
class RubricVerdict:
    """Structured judgment from RubricMiddleware.evaluate()."""

    passed: bool
    reason: str
    raw_response: str = field(default="")


class RubricMiddleware:
    """Evaluates task outputs against a rubric via Lemonade :13305.

    Usage::

        rm = RubricMiddleware(rubric="Output must be factually grounded.")
        verdict = rm.evaluate(task_output=result.output, task_context=skill_name)
        if not verdict.passed:
            logger.info("Rubric rejected: %s", verdict.reason)
    """

    def __init__(
        self,
        rubric: str,
        model: str | None = None,
        timeout: float = 10.0,
        router_url: str = _ROUTER_URL,
    ) -> None:
        self.rubric = rubric
        self._model = model
        self._timeout = timeout
        self._router_url = router_url

    def evaluate(
        self,
        task_output: str,
        task_context: str = "",
    ) -> RubricVerdict:
        """Evaluate task_output against the rubric.

        Returns RubricVerdict(passed=True) on any inference or parse failure
        (fail-open) so the learning loop is never blocked by infrastructure.
        """
        try:
            raw = self._call_inference(task_output, task_context)
            return self._parse_verdict(raw)
        except Exception as exc:
            logger.debug("RubricMiddleware: evaluation failed (fail-open): %s", exc)
            return RubricVerdict(passed=True, reason="", raw_response="")

    # ── internal ──────────────────────────────────────────────────────────

    def _build_messages(self, task_output: str, task_context: str) -> list[dict]:
        system_content = _SYSTEM_TEMPLATE.format(rubric=self.rubric)
        user_content = task_output
        if task_context:
            user_content = f"[Context: {task_context}]\n\n{task_output}"
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _call_inference(self, task_output: str, task_context: str) -> str:
        body: dict = {
            "messages": self._build_messages(task_output, task_context),
            "response_format": {"type": "json_object"},
            "max_tokens": 256,
            "temperature": 0.0,
        }
        if self._model is not None:
            body["model"] = self._model

        resp = httpx.post(  # type: ignore[reportOptionalMemberAccess]
            self._router_url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _parse_verdict(self, raw: str) -> RubricVerdict:
        try:
            data = json.loads(raw)
            perceived_error = data.get("perceived_error")
            if perceived_error is None:
                # Key missing → fail-open
                return RubricVerdict(passed=True, reason="", raw_response=raw)
            reason = str(data.get("reason", ""))
            return RubricVerdict(
                passed=not bool(perceived_error),
                reason=reason,
                raw_response=raw,
            )
        except (json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
            logger.debug("RubricMiddleware: parse failed (fail-open): %s", exc)
            return RubricVerdict(passed=True, reason="", raw_response=raw)
