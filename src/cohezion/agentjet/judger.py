"""PhiScoreJudger: maps phi_score trajectory quality to scalar RL reward.

Reward mapping:
  phi >= 0.7  → positive reward: phi * 2 - 1   maps [0.7, 1.0] → [0.4, 1.0]
  phi  < 0.4  → HIHO violation: -1.0 (hard penalty)
  0.4 <= phi < 0.7 → small positive: (phi - 0.4) / 0.3 * 0.2  maps [0.4, 0.7) → [0, 0.2)

The HIHO stability band [0.4, 0.7] represents the coherence range where
the system operates at the boundary between exploitation and exploration.
Executions below 0.4 destabilise the HIHO invariant and receive a hard
negative reward to push training away from incoherent trajectories.
"""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)

# HIHO stability band boundaries
_HIHO_LOW: float = 0.4
_HIHO_HIGH: float = 0.7


class PhiScoreJudger:
    """Maps phi_score to a scalar reward for AgentJet RL training.

    The reward function enforces the HIHO stability invariant:

    * phi >= 0.7  — high quality, positive reward in [0.4, 1.0]
    * phi in [0.4, 0.7) — stability band, small positive in [0.0, 0.2)
    * phi < 0.4  — HIHO violation, hard penalty of -1.0

    Parameters
    ----------
    hiho_low : float
        Lower boundary of the HIHO stability band (default: 0.4).
    hiho_high : float
        Upper boundary of the HIHO stability band (default: 0.7).
    """

    def __init__(
        self,
        hiho_low: float = _HIHO_LOW,
        hiho_high: float = _HIHO_HIGH,
    ) -> None:
        if not 0.0 <= hiho_low < hiho_high <= 1.0:
            raise ValueError(
                f"HIHO band must satisfy 0 <= hiho_low < hiho_high <= 1, got [{hiho_low}, {hiho_high}]"
            )
        self._hiho_low = hiho_low
        self._hiho_high = hiho_high

    def judge(self, rollout: dict) -> float:
        """Compute scalar reward from a single rollout dict.

        Parameters
        ----------
        rollout : dict
            Must contain ``phi_score`` (float in [0.0, 1.0]). Additional
            keys (skill_name, coherence, etc.) are ignored.

        Returns
        -------
        float
            Scalar reward in the range [-1.0, 1.0].

        Notes
        -----
        Reward piecewise function:

        .. code-block:: text

            phi >= hiho_high  →  phi * 2 - 1
            phi <  hiho_low   →  -1.0
            else              →  (phi - hiho_low) / (hiho_high - hiho_low) * 0.2
        """
        try:
            phi: float = float(rollout["phi_score"])
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("PhiScoreJudger.judge: invalid rollout phi_score — %s", exc)
            return -1.0

        return self._compute_reward(phi)

    def batch_judge(self, rollouts: list[dict]) -> list[float]:
        """Compute rewards for a batch of rollout dicts.

        Parameters
        ----------
        rollouts : list[dict]
            Each dict must contain ``phi_score``.

        Returns
        -------
        list[float]
            Reward for each rollout, same order as input.
        """
        return [self.judge(r) for r in rollouts]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_reward(self, phi: float) -> float:
        """Core piecewise reward function.

        Parameters
        ----------
        phi : float
            Trajectory quality score in [0.0, 1.0].

        Returns
        -------
        float
            Scalar reward in [-1.0, 1.0].
        """
        # Clamp to valid range before computing reward
        phi = max(0.0, min(1.0, phi))

        if phi >= self._hiho_high:
            # High-quality execution: linear map [0.7, 1.0] → [0.4, 1.0]
            reward = phi * 2.0 - 1.0
        elif phi < self._hiho_low:
            # HIHO violation: hard penalty
            reward = -1.0
        else:
            # Stability band [0.4, 0.7): small positive proportional to proximity to high
            band_width = self._hiho_high - self._hiho_low
            reward = (phi - self._hiho_low) / band_width * 0.2

        logger.debug("PhiScoreJudger: phi=%.3f → reward=%.3f", phi, reward)
        return reward
