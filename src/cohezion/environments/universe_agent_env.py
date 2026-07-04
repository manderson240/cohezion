"""UniverseAgentEnv — text-in / text-out agentic environment for LLM agents.

Wraps :class:`ManifoldEnv` (12D physics-grounded Gymnasium env) with a natural
language interface: observations are rich text descriptions of the 12D brane
state framed through an indigenous worldview (WorldviewExplorer), and actions
are free-form text commands parsed into velocity vectors.

This makes the manifold navigable by LLM agents (text in, text out) rather
than classical RL policies (vectors in, vectors out) — the environment shape
needed for LLM agent training frameworks (TRL, OpenEnv, agentic eval loops).

Action grammar (fail-safe: anything unrecognized becomes a no-op):
    "push toward equilibrium"   — proportional correction toward 0.5 per dim
    "push dimension N up/down"  — set velocity[N] = +/-0.3
    "hold"                      — zero velocity (physics self-converges?)
    "explore"                   — uniform random perturbation

Worldview framing:
    Each episode cycles deterministically through all traditions in the
    worldviews library (episode_count % n_traditions), surfacing that
    tradition's HIHO-equilibrium step (step index 7) in the observation.

Optional integrations (fail-open — env works without them):
    - JourneyTracker.record_env_state("universe_agent", ...) per step
    - JepaGate.check(action_text) pre-execution verdict (SKIP → no-op action)

Usage:
    from cohezion.environments import UniverseAgentEnv

    env = UniverseAgentEnv(max_steps=20, seed=42)
    obs, info = env.reset()          # obs is a str
    obs, reward, terminated, truncated, info = env.step(
        "push toward equilibrium"
    )
"""

from __future__ import annotations

import contextlib
import logging
import re
from typing import Any

import gymnasium as gym
import numpy as np

from cohezion.environments.manifold_env import ManifoldEnv
from cohezion.worldviews import get_traditions


logger = logging.getLogger(__name__)

# HIHO dynamic-equilibrium step in the 10-step cosmogony (worldview framing).
_HIHO_STEP_INDEX = 7

_DIM_ACTION_RE = re.compile(r"dimension\s+(\d+)\s+(up|down)")

_EQUILIBRIUM_KEYWORDS = ("toward equilibrium", "seek equilibrium", "converge")
_HOLD_KEYWORDS = ("hold", "wait", "do nothing")
_EXPLORE_KEYWORDS = ("explore", "random")


def _text_space(max_length: int) -> gym.Space:
    """gymnasium.spaces.Text when available, Discrete(1) placeholder otherwise.

    The actual observations/actions are Python str either way — the space is
    a declaration for framework compatibility, as is standard for text envs.
    """
    try:
        return gym.spaces.Text(min_length=1, max_length=max_length)
    except (AttributeError, TypeError):  # very old gymnasium
        return gym.spaces.Discrete(1)


class UniverseAgentEnv(gym.Env):
    """Text-action Gymnasium environment over the 12D HIHO manifold."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        max_steps: int = 100,
        seed: int | None = None,
        damping: float = 0.02,
        reward_mode: str = "verifiable",
        journey_tracker: Any = None,
        jepa_gate: Any = None,
    ) -> None:
        super().__init__()
        self.dim = 12
        self.max_steps = max_steps
        self._env = ManifoldEnv(
            dim=self.dim,
            max_steps=max_steps,
            damping=damping,
            reward_mode=reward_mode,
            seed=seed,
        )
        self._rng = np.random.default_rng(seed)
        self._traditions = get_traditions()
        self._episode_count = 0
        self._step_count = 0
        self._tradition = self._traditions[0]
        self._last_position = np.full(self.dim, 0.5, dtype=np.float32)
        self._last_deviation = 0.0

        self.observation_space = _text_space(8192)
        self.action_space = _text_space(512)

        # Optional integrations — fail-open (env must work without them).
        self._journey_tracker = journey_tracker
        if jepa_gate is None:
            try:
                from cohezion.compound.jepa_gate import JepaGate

                jepa_gate = JepaGate(world_model=None)  # always PROCEED
            except Exception:
                jepa_gate = None
        self._jepa_gate = jepa_gate

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(  # type: ignore[override]
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Reset the inner manifold and cycle to the next worldview tradition."""
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        obs, info = self._env.reset(seed=seed)

        self._tradition = self._traditions[self._episode_count % len(self._traditions)]
        self._episode_count += 1
        self._step_count = 0
        self._last_position = obs[: self.dim].astype(np.float32)
        self._last_deviation = float(info.get("hiho_deviation", 0.0))

        info["tradition"] = self._tradition.name
        return self.obs_to_text(obs, step=0), info

    def step(self, action: str) -> tuple[str, float, bool, bool, dict[str, Any]]:
        """Parse a text command, evolve the manifold, narrate the outcome."""
        action_text = str(action)
        velocity = self.parse_action(action_text)

        # JepaGate pre-execution verdict (fail-open: only SKIP changes anything)
        if self._jepa_gate is not None:
            try:
                verdict = self._jepa_gate.check(action_text)
                if getattr(verdict, "name", "") == "SKIP":
                    velocity = np.zeros(self.dim, dtype=np.float32)
            except Exception:
                pass

        obs, reward, terminated, truncated, info = self._env.step(velocity)
        self._step_count += 1
        self._last_position = obs[: self.dim].astype(np.float32)
        self._last_deviation = float(info.get("hiho_deviation", 0.0))

        if self._journey_tracker is not None:
            # Tracking must never break the env — fail-open.
            with contextlib.suppress(Exception):
                self._journey_tracker.record_env_state(
                    "universe_agent", self._step_count, obs, float(reward)
                )

        info["tradition"] = self._tradition.name
        info["parsed_velocity"] = velocity
        text = self.obs_to_text(obs, step=self._step_count, reward=float(reward))
        return text, float(reward), bool(terminated), bool(truncated), info

    # ------------------------------------------------------------------
    # Text interface
    # ------------------------------------------------------------------

    def parse_action(self, action_text: str) -> np.ndarray:
        """Parse a natural-language command into a 12D velocity vector.

        Fail-safe: any unrecognized text yields a zero (no-op) velocity.
        """
        text = str(action_text).lower().strip()
        velocity = np.zeros(self.dim, dtype=np.float32)

        if any(k in text for k in _EQUILIBRIUM_KEYWORDS):
            correction = (0.5 - self._last_position) * 3.0
            return np.clip(correction, -0.5, 0.5).astype(np.float32)

        match = _DIM_ACTION_RE.search(text)
        if match:
            n = int(match.group(1))
            if 0 <= n < self.dim:
                velocity[n] = 0.3 if match.group(2) == "up" else -0.3
            return velocity

        if any(k in text for k in _HOLD_KEYWORDS):
            return velocity

        if any(k in text for k in _EXPLORE_KEYWORDS):
            return self._rng.uniform(-0.5, 0.5, self.dim).astype(np.float32)

        return velocity  # fail-safe no-op

    def obs_to_text(self, obs: np.ndarray, step: int, reward: float | None = None) -> str:
        """Format the 12D brane state as a text observation with worldview framing."""
        position = obs[: self.dim]
        dims = ", ".join(f"dim[{i}]={v:.3f}" for i, v in enumerate(position))

        hiho = self._tradition.step_mappings[_HIHO_STEP_INDEX]
        worldview = (
            f'Worldview: {self._tradition.name} — "{hiho.indigenous_term}: {hiho.description}"'
        )

        lines = [
            "You are navigating a 12-dimensional brane toward HIHO equilibrium.",
            "",
            worldview,
            "",
            f"Current state: {dims}",
            "Equilibrium target: all dimensions = 0.500",
            f"Deviation from equilibrium: {self._last_deviation:.3f} (lower is better)",
        ]
        if reward is not None:
            lines.append(f"Last reward: {reward:+.4f}")
        lines += [
            "",
            "Available actions:",
            '  "push toward equilibrium" — proportional correction toward 0.5',
            '  "push dimension N up/down" — increment/decrement dimension N by 0.3',
            '  "hold" — no action (tests whether physics self-converges)',
            '  "explore" — random perturbation to escape local regions',
            "",
            f"Step: {step}/{self.max_steps}",
        ]
        return "\n".join(lines)
