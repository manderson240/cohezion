"""R0Σ — Adversarial Challenger + Sigma Uncertainty Quantification.

R0 (R-Zero): Adversarial review that probes outputs for:
  1. Falsifiability — can this claim be tested/disproven?
  2. Physical consistency — does it violate established physics?
  3. Implementation soundness — would this actually compute correctly?
  4. Circular reasoning — is this real or word association?

Σ (Sigma): Uncertainty band wrapping every tier output.
  - sigma_n < 0.5σ from HIHO → HIGH confidence, accept
  - sigma_n < 1.0σ → MEDIUM confidence, observe
  - sigma_n > 1.0σ → LOW confidence, trigger R0 adversarial review

In Universe Research Engineer context:
  R0 = scientific adversary that challenges simulation findings
  Σ = variance in 3-perspective adversarial review scores
  If Σ > 1σ: URE re-runs simulation with perturbed COLIBRE parameters
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

_HIHO: float = 0.5
_HIGH_CONFIDENCE_THRESHOLD: float = 0.5  # sigma_n < 0.5 → HIGH
_MEDIUM_CONFIDENCE_THRESHOLD: float = 1.0  # sigma_n < 1.0 → MEDIUM


@dataclass
class UncertaintyBand:
    """Sigma: confidence interval around a compound loop output.

    Parameters
    ----------
    mean_score : float
        Mean quality score across perspectives [0, 1].
    std_dev : float
        Standard deviation of quality scores across perspectives.
    sigma_n : float
        Number of standard deviations from HIHO (0.5).
        sigma_n = abs(mean_score - 0.5) / std_dev (if std_dev > 0).
    """

    mean_score: float
    std_dev: float
    sigma_n: float

    @classmethod
    def from_scores(cls, scores: Sequence[float]) -> UncertaintyBand:
        """Compute UncertaintyBand from a list of perspective scores."""
        if not scores:
            return cls(mean_score=0.0, std_dev=1.0, sigma_n=float("inf"))
        mean = sum(scores) / len(scores)
        if len(scores) == 1:
            return cls(mean_score=mean, std_dev=0.0, sigma_n=0.0)
        variance = sum((s - mean) ** 2 for s in scores) / (len(scores) - 1)
        std = math.sqrt(variance)
        sigma_n = abs(mean - _HIHO) / std if std > 1e-9 else 0.0
        return cls(mean_score=mean, std_dev=std, sigma_n=sigma_n)

    @property
    def confidence(self) -> str:
        """Confidence tier based on distance from HIHO attractor."""
        if self.sigma_n < _HIGH_CONFIDENCE_THRESHOLD:
            return "HIGH"
        elif self.sigma_n < _MEDIUM_CONFIDENCE_THRESHOLD:
            return "MEDIUM"
        return "LOW"

    def trigger_r0(self) -> bool:
        """True when uncertainty > 1σ from HIHO — trigger adversarial review."""
        return self.sigma_n > _MEDIUM_CONFIDENCE_THRESHOLD

    def to_dict(self) -> dict[str, float | str]:
        return {
            "mean_score": self.mean_score,
            "std_dev": self.std_dev,
            "sigma_n": self.sigma_n,
            "confidence": self.confidence,
            "trigger_r0": self.trigger_r0(),
        }


# Challenger verdict levels (match Phase R0 plan)
CONFIRMED = "CONFIRMED"
CONDITIONAL = "CONDITIONAL"
WEAK = "WEAK"
REJECTED = "REJECTED"


@dataclass
class R0Challenge:
    """Single adversarial perspective on an output.

    Parameters
    ----------
    perspective : str
        One of: "scientific_rigor", "physical_consistency", "implementation"
    score : float
        Challenge score [0, 1]. 0 = completely rejects, 1 = fully endorses.
    verdict : str
        CONFIRMED / CONDITIONAL / WEAK / REJECTED
    reason : str
        Brief explanation of the challenge verdict.
    """

    perspective: str
    score: float
    verdict: str
    reason: str = ""

    def __post_init__(self) -> None:
        self.score = max(0.0, min(1.0, float(self.score)))
        if self.verdict not in (CONFIRMED, CONDITIONAL, WEAK, REJECTED):
            raise ValueError(f"Invalid verdict: {self.verdict!r}")


@dataclass
class R0ChallengeResult:
    """Aggregate result from 3-perspective adversarial review.

    Parameters
    ----------
    challenges : list[R0Challenge]
        Individual perspective challenges.
    """

    challenges: list[R0Challenge] = field(default_factory=list)

    @property
    def sigma_band(self) -> UncertaintyBand:
        """Compute Sigma band across all perspective scores."""
        return UncertaintyBand.from_scores([c.score for c in self.challenges])

    @property
    def consensus_verdict(self) -> str:
        """2/3 consensus rule: CONFIRMED if ≥2 CONFIRMED, else majority verdict."""
        if not self.challenges:
            return WEAK
        counts: dict[str, int] = {}
        for c in self.challenges:
            counts[c.verdict] = counts.get(c.verdict, 0) + 1
        # Check for 2/3 CONFIRMED threshold
        if counts.get(CONFIRMED, 0) >= 2:
            return CONFIRMED
        # Else return most frequent verdict (REJECTED breaks ties)
        return max(counts, key=lambda v: (counts[v], v == REJECTED))

    @property
    def mean_score(self) -> float:
        """Mean challenge score across all perspectives."""
        if not self.challenges:
            return 0.0
        return sum(c.score for c in self.challenges) / len(self.challenges)

    def is_accepted(self) -> bool:
        """True if consensus verdict is CONFIRMED or CONDITIONAL."""
        return self.consensus_verdict in (CONFIRMED, CONDITIONAL)

    def to_dict(self) -> dict:
        band = self.sigma_band
        return {
            "consensus": self.consensus_verdict,
            "mean_score": self.mean_score,
            "sigma_n": band.sigma_n,
            "confidence": band.confidence,
            "trigger_r0_rerun": band.trigger_r0(),
            "perspectives": [
                {"perspective": c.perspective, "score": c.score, "verdict": c.verdict}
                for c in self.challenges
            ],
        }


def synthesize_challenges(challenges: list[R0Challenge]) -> R0ChallengeResult:
    """Synthesize multiple adversarial challenges into a single result."""
    return R0ChallengeResult(challenges=challenges)
