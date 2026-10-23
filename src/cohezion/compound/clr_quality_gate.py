"""CLR (Claim-Level Reasoning) quality gate for Mycelium re-injection.

3-claim binary verification on the cascade tier-0 model via OmniRouter :13305
(config.defaults.tier0_model; iGPU GGUF since 2026-10-23, no longer the NPU FLM).
score = (mean_verdicts)^3; threshold 0.7 — unanimous YES (3/3=1.0) passes,
2/3 yields ~0.296 which fails, making this effectively a consensus gate.
Fail-open: returns True when inference unavailable (None score).
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.config.defaults import tier0_client_kwargs, tier0_model


logger = logging.getLogger(__name__)

_ROUTER_URL = "http://localhost:13305/v1/chat/completions"
_GAIA_ROUTER_URL = "http://localhost:13305/api/v1"
_CLAIMS = [
    "Does this pattern contain specific, reusable information worth memorizing? Reply YES or NO only.",
    "Is the execution outcome described verifiably successful? Reply YES or NO only.",
    "Would injecting this pattern improve future compound loop quality? Reply YES or NO only.",
]


def _parse_verdict(text: str) -> int | None:
    """Parse YES/NO verdict from first word only.

    First-word parsing prevents substring matching bugs (e.g. "unknown" containing "no").
    Returns 1 for yes, 0 for no/ambiguous, None for empty/inference failure.
    """
    stripped = text.strip().lower()
    if not stripped:
        return None
    first_word = stripped.split()[0].rstrip(".,!?;:")
    if first_word == "yes":
        return 1
    if first_word == "no":
        return 0
    return 0  # ambiguous → conservative NO


class CLRQualityGate:
    """3-claim binary NPU quality gate — score = (mean_verdicts)^3."""

    THRESHOLD: float = 0.7
    _CLAIMS = _CLAIMS

    def __init__(
        self,
        model: str | None = None,
        router_url: str = _ROUTER_URL,
        gaia_router_url: str = _GAIA_ROUTER_URL,
        timeout: float = 10.0,
    ) -> None:
        self._model = model or tier0_model()
        self._router_url = router_url
        self._gaia_router_url = gaia_router_url
        self._timeout = timeout
        self._gaia_client: Any | None = self._init_gaia_client()

    def _init_gaia_client(self) -> Any | None:
        try:
            from gaia.llm.lemonade_client import LemonadeClient  # type: ignore[import]

            return LemonadeClient(
                base_url=self._gaia_router_url,
                model=self._model,
                verbose=False,
                **tier0_client_kwargs(self._model),  # bounded tier-0 ctx on GAIA's own load
            )
        except Exception as exc:
            logger.debug("CLRQualityGate: GAIA unavailable (%s), using httpx fallback", exc)
            return None

    def score(self, content: str) -> float | None:
        """Compute CLR score = (mean_verdicts)^3. Returns None on inference failure."""
        verdicts: list[int] = []
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

    def _call_inference(self, prompt: str) -> str | None:
        if self._gaia_client is not None:
            try:
                result = self._gaia_client.chat_completions(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=8,
                    temperature=0.0,
                )
                text = result["choices"][0]["message"].get("content", "").strip()
                return text or None
            except Exception as exc:
                logger.debug("CLRQualityGate: GAIA call failed (%s)", exc)

        try:
            import httpx

            resp = httpx.post(
                self._router_url,
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8,
                    "temperature": 0.0,
                },
                headers={"Content-Type": "application/json"},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            return text or None
        except Exception as exc:
            logger.debug("CLRQualityGate: httpx failed: %s", exc)
            return None
