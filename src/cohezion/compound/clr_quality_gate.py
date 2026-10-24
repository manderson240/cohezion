"""CLR (Claim-Level Reasoning) quality gate for Mycelium re-injection.

3-claim binary verification on the cascade tier-0 model via OmniRouter :13305
(config.defaults.tier0_model; the NPU FLM by default, always sent think=false).
score = (mean_verdicts)^3; threshold 0.7 — unanimous YES (3/3=1.0) passes,
2/3 yields ~0.296 which fails, making this effectively a consensus gate.
Fail-open: returns True when inference unavailable (None score).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from cohezion.config.defaults import tier0_model, tier0_request_extras


logger = logging.getLogger(__name__)

_ROUTER_URL = "http://localhost:13305/v1/chat/completions"
_GAIA_ROUTER_URL = "http://localhost:13305/api/v1"
_CLAIMS = [
    "Does this pattern contain specific, reusable information worth memorizing? Reply YES or NO only.",
    "Is the execution outcome described verifiably successful? Reply YES or NO only.",
    "Would injecting this pattern improve future compound loop quality? Reply YES or NO only.",
]


# Thinking-safe budget for one YES/NO verdict. Tier 0 (Gemma-4-E2B by default) reasons before
# answering; at the old max_tokens=8 it could never reach the verdict, so every claim parsed as
# an empty/ambiguous NO (thinking-model-token-budget-gate-trap). Prompt is <=~250 tokens, so
# this fits the tier-0 recipe's ctx 4096 on one slot.
_VERDICT_MAX_TOKENS = 1024
_VERDICTS = {"yes": 1, "no": 0}


def _first_word_verdict(line: str) -> int | None:
    words = line.strip().lower().strip("*_`#>").split()
    if not words:
        return None
    return _VERDICTS.get(words[0].strip("*_`").rstrip(".,!?;:"))


def _parse_verdict(text: str) -> int | None:
    """Parse a YES/NO verdict by FIRST WORD (never substring: "unknown" is not "no").

    Returns 1 for yes, 0 for no/ambiguous, None for empty/inference failure.

    When the first word is not a verdict, the LAST line whose first word is YES/NO decides.
    That is where a thinking model's answer lands after its reasoning (content empty, answer
    taken from reasoning_content). Lines are matched by first word, so an echoed instruction
    ("Reply YES or NO only.") never counts, and a single-line hedge such as "I think yes"
    stays the conservative NO.
    """
    stripped = text.strip()
    if not stripped:
        return None
    verdict = _first_word_verdict(stripped)
    if verdict is not None:
        return verdict
    for line in reversed(stripped.splitlines()):
        verdict = _first_word_verdict(line)
        if verdict is not None:
            return verdict
    return 0  # ambiguous → conservative NO


def _message_answer(result: dict[str, Any]) -> str | None:
    """The FINISHED answer from an OpenAI-shaped reply, or None (gate fails open).

    Only ``content`` or a CLOSED final answer counts. A truncated reply (finish_reason
    "length", or completion_tokens at the budget -- lemonade can say "stop" while truncating)
    or bare reasoning_content is an unfinished chain of thought: its tentative "Yes, it
    mentions X." before "But wait..." is not a verdict.
    """
    from cohezion.inference.gaia_adapter import reply_final_answer

    return reply_final_answer(result, _VERDICT_MAX_TOKENS)


class CLRQualityGate:
    """3-claim binary NPU quality gate — score = (mean_verdicts)^3."""

    THRESHOLD: float = 0.7
    _CLAIMS = _CLAIMS

    def __init__(
        self,
        model: str | None = None,
        router_url: str = _ROUTER_URL,
        gaia_router_url: str = _GAIA_ROUTER_URL,
        timeout: float = 60.0,
        total_timeout: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._model = model or tier0_model()
        self._router_url = router_url
        self._gaia_router_url = gaia_router_url
        self._timeout = timeout
        # Bound on the WHOLE score() across all claims. CLR runs synchronously inside the async
        # post-execution pipeline and tier 0 serves one request at a time (-np 1), so queued
        # claims (each with GAIA's 900 s default timeout, plus an httpx retry) could block the
        # event loop for many minutes. Out of budget -> None -> fail open.
        self._total_timeout = total_timeout
        self._clock = clock
        self._deadline: float | None = None
        # Card temperature, not greedy 0.0: greedy decoding on a Gemma-family card degenerates
        # into loops/empty output (TR1). Models without a card entry keep the old 0.0.
        from cohezion.inference.model_card_defaults import get_sampling_defaults

        self._temperature = float(get_sampling_defaults(self._model).get("temperature", 0.0))
        # Sticky FLM think flag: every tier-0 request carries think=false (config.defaults).
        self._extras = tier0_request_extras(self._model) if self._model == tier0_model() else {}
        self._gaia_client: Any | None = self._init_gaia_client()

    def _init_gaia_client(self) -> Any | None:
        try:
            from gaia.llm.lemonade_client import LemonadeClient  # type: ignore[import]

            return LemonadeClient(base_url=self._gaia_router_url, model=self._model, verbose=False)
        except Exception as exc:
            logger.debug("CLRQualityGate: GAIA unavailable (%s), using httpx fallback", exc)
            return None

    def score(self, content: str) -> float | None:
        """Compute CLR score = (mean_verdicts)^3. Returns None on inference failure."""
        verdicts: list[int] = []
        self._deadline = self._clock() + self._total_timeout
        for claim in self._CLAIMS:
            v = self._verify_claim(claim, content)
            if v is None:
                return None
            verdicts.append(v)
        mean_v = sum(verdicts) / len(verdicts)
        return mean_v**3

    def passes(self, content: str) -> bool:
        """True if content passes CLR gate OR if inference is unavailable (fail-open)."""
        s = self.score(content)
        if s is None:
            return True  # fail-open: allow ingestion when inference unavailable
        return s >= self.THRESHOLD

    def _verify_claim(self, claim: str, context: str) -> int | None:
        prompt = f"Context:\n{context[:500]}\n\nClaim: {claim}"
        text = self._call_inference(prompt)
        if text is None:
            return None
        return _parse_verdict(text)

    def _remaining(self) -> float:
        """Seconds left for this call: the per-call timeout, capped by the score() deadline."""
        if self._deadline is None:
            return self._timeout
        return min(self._timeout, self._deadline - self._clock())

    def _call_inference(self, prompt: str) -> str | None:
        if self._remaining() <= 0:
            logger.debug("CLRQualityGate: total budget exhausted, failing open")
            return None
        if self._gaia_client is not None:
            try:
                result = self._gaia_client.chat_completions(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=_VERDICT_MAX_TOKENS,
                    temperature=self._temperature,
                    # Never let GAIA /load the model: its ensure-loaded path reloads at GAIA's
                    # own expected ctx (32768 floor), a second ctx authority competing with the
                    # saved recipe. The router auto-loads at the recipe ctx instead.
                    auto_download=False,
                    timeout=self._remaining(),
                    **self._extras,
                )
                return _message_answer(result)
            except Exception as exc:
                logger.debug("CLRQualityGate: GAIA call failed (%s)", exc)

        remaining = self._remaining()
        if remaining <= 0:
            return None  # no httpx retry past the deadline
        try:
            import httpx

            resp = httpx.post(
                self._router_url,
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": _VERDICT_MAX_TOKENS,
                    "temperature": self._temperature,
                    **self._extras,
                },
                headers={"Content-Type": "application/json"},
                timeout=remaining,
            )
            resp.raise_for_status()
            return _message_answer(resp.json())
        except Exception as exc:
            logger.debug("CLRQualityGate: httpx failed: %s", exc)
            return None
