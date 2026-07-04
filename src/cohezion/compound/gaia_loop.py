"""GaiaLoop — GAIA SDK local-model orchestration for Cohezion compound improvement.

Uses the AMD OmniRouter at :13305 as the inference fleet. Models are pinned to
the safe fast tier to avoid max_loaded_models=1 thrash (N3 harness constraint):

  Fast: llama3.2-1b-FLM  (42 TPS, NPU)
  Reason: deepseek-r1-0528-8b-FLM  (10.6 TPS, NPU)
  Code: Bonsai-8B-gguf  (vulkan, tool-calling)

NEVER call load_model here — OmniRouter dispatches on demand.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_GAIA_BASE = "http://localhost:13305"
_FAST_MODEL = "llama3.2-1b-FLM"
_REASONING_MODEL = "deepseek-r1-0528-8b-FLM"


@dataclass
class GoalResult:
    goal: str
    model: str
    analysis: str
    metadata: dict[str, Any] = field(default_factory=dict)


class GaiaLoop:
    """GAIA SDK compound improvement loop backed by local AMD silicon.

    Each ``analyze_goal`` call dispatches to the OmniRouter at :13305 and returns
    a structured result the caller can act on. No persistent state; each call is
    independent so the loop can be interrupted and resumed safely.
    """

    def __init__(self, base_url: str = _GAIA_BASE, timeout: float = 60.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Core inference
    # ------------------------------------------------------------------

    def _chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 512,
    ) -> str:
        """Single-shot chat via GAIA OmniRouter. Returns empty string on failure."""
        try:
            import httpx  # lazy import — optional dep

            payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{self._base}/v1/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return str(data["choices"][0]["message"]["content"])
        except Exception as exc:
            logger.warning("GaiaLoop._chat(%s) failed: %s", model, exc)
            return ""

    # ------------------------------------------------------------------
    # Goal analysis
    # ------------------------------------------------------------------

    def analyze_goal(
        self,
        goal: str,
        context: str = "",
        model: str = _FAST_MODEL,
        *,
        reasoning: bool = False,
    ) -> GoalResult:
        """Ask a local model for the single most impactful next action on a goal.

        Set ``reasoning=True`` to use the NPU reasoning model (deepseek-r1-0528-8b-FLM)
        instead of the fast routing model.
        """
        if reasoning:
            model = _REASONING_MODEL
        context_line = f"\nContext: {context}" if context else ""
        msgs = [
            {
                "role": "system",
                "content": (
                    "You are a compound engineering advisor for the Cohezion project. "
                    "Analyze the goal and return a concise, actionable next step. Be brief."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal: {goal}{context_line}\n\n"
                    "What is the single most important next action? Answer in 1-2 sentences."
                ),
            },
        ]
        analysis = self._chat(msgs, model=model)
        return GoalResult(goal=goal, model=model, analysis=analysis)

    def prioritize_goals(
        self,
        goals: list[str],
        model: str = _FAST_MODEL,
    ) -> list[str]:
        """Ask the local model to rank goals by impact. Falls back to original order."""
        if not goals:
            return []
        numbered = "\n".join(f"{i + 1}. {g}" for i, g in enumerate(goals))
        msgs = [
            {
                "role": "user",
                "content": (
                    "Prioritize these engineering goals from most to least impactful for "
                    "an AI system. Return ONLY the numbers in priority order, "
                    "comma-separated. Example: 3, 1, 4, 2\n\n" + numbered
                ),
            }
        ]
        response = self._chat(msgs, model=model, max_tokens=50)
        try:
            indices = [
                int(x.strip()) - 1
                for x in response.replace(".", "").split(",")
                if x.strip().isdigit()
            ]
            ordered = [goals[i] for i in indices if 0 <= i < len(goals)]
            seen = set(indices)
            ordered += [g for i, g in enumerate(goals) if i not in seen]
            return ordered
        except Exception:
            return goals

    def batch_analyze(
        self,
        goals: list[str],
        model: str = _FAST_MODEL,
    ) -> list[GoalResult]:
        """Analyze each goal sequentially. Serialized — no parallel loads (N3 safe)."""
        return [self.analyze_goal(goal, model=model) for goal in goals]

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the GAIA OmniRouter is reachable."""
        try:
            import httpx

            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{self._base}/v1/models")
                return resp.status_code == 200
        except Exception:
            return False
