"""SkillOpt backend adapter for Lemonade OmniRouter (:13305).

Implements the SkillOpt model backend contract so optimization runs
use local AMD silicon at $0 cost instead of cloud APIs.

Usage (offline self-evolution mode):
    from cohezion.skillopt.lemonade_backend import LemonadeBackend
    from skillopt import SkillOptSleep

    backend = LemonadeBackend()
    optimizer = SkillOptSleep(model=backend)
    optimizer.run("path/to/skill.md", corpus_path="path/to/traces/")
"""

from __future__ import annotations

import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_ROUTER_URL = "http://localhost:13305/v1"
_DEFAULT_MODEL = "Gemma-4-31B-it-GGUF"  # CPU tier — best quality for text editing
_FAST_MODEL = "Gemma-4-E4B-it-GGUF"  # iGPU tier — for scoring passes


class LemonadeBackend:
    """SkillOpt model backend wired to the Lemonade OmniRouter.

    Routing:
      - optimize / gradient calls → CPU tier (Gemma-4-31B, complex edits)
      - evaluate / score calls    → iGPU tier (Gemma-4-E4B, faster scoring)
    """

    def __init__(
        self,
        base_url: str = _ROUTER_URL,
        optimize_model: str = _DEFAULT_MODEL,
        score_model: str = _FAST_MODEL,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url
        self.optimize_model = optimize_model
        self.score_model = score_model
        self._client = httpx.Client(timeout=timeout)

    # ------------------------------------------------------------------ #
    # SkillOpt backend contract                                            #
    # ------------------------------------------------------------------ #

    def complete(self, prompt: str, *, mode: str = "optimize", **kwargs: Any) -> str:
        """Generate a completion. `mode` selects optimize vs score tier."""
        model = self.score_model if mode == "score" else self.optimize_model
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.2),
        }
        try:
            resp = self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("LemonadeBackend.complete failed (%s), returning empty", exc)
            return ""

    def is_available(self) -> bool:
        """Return True if the Lemonade router is reachable."""
        try:
            self._client.get(f"{self.base_url}/models", timeout=2.0).raise_for_status()
            return True
        except Exception:
            return False

    # SkillOpt expects a callable interface as well
    def __call__(self, prompt: str, **kwargs: Any) -> str:
        return self.complete(prompt, **kwargs)
