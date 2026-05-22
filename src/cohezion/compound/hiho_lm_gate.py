"""HIHO-LM Quality Gate — zero-cost AutoDQA structured-garbage filter.

Uses HIHO-LM perplexity to detect structured garbage (JSON, hex, binary).
From exp_HHHH2 calibration (v5+code, 320+SGDR+smart_seed+lr=5e-4+20 Python snippets):
  - HIHO domain text (compound eng.):  PPL ~ 15    (gate: pass)
  - Generic English text:               PPL ~ 15    (gate: pass)
  - Code text:                          PPL ~ 31    (gate: pass)
  - Sycophantic text:                   PPL ~ 25    (gate: pass — see hiho_score)
  - JSON / structured data:             PPL ~ 638   (gate: REJECT, 25x above worst domain)

Threshold PPL_REJECT=80 catches structured garbage with 8x margin vs P5 (638/80=8x).
All domain text (P1-P4) is <<80; P5_garbage is >>80. Gate is robust.

Code corpus augmentation (exp_EEEE2): +20 Python snippets from src/cohezion/model/*.py
  reduces P3_code PPL from ~39 to ~29 (-21.9%) without hurting domain discrimination.

hiho_score < 0.90 detects sycophancy — threshold needs recalibration for v4 model.
See exp_HHHH1 for updated sycophancy threshold.
"""

from __future__ import annotations

import logging
import math
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cohezion.model.cohezion_lm import CohezionLM

logger = logging.getLogger(__name__)

# From exp_AAAA7: sycophantic PPL=82, domain PPL=29-44
_PPL_REJECT_THRESHOLD = 80.0
# From exp_UUUU2: v5 model separates sycophancy at 2.70x. Substantive max=15.7, sycophantic min=27.0.
# Threshold=22 catches all sycophancy with zero false positives on calibration set (gap=11.3 PPL).
_PPL_SYCOPHANCY_THRESHOLD = 22.0

_model: "CohezionLM | None" = None
_lock = threading.Lock()


def _get_model() -> "CohezionLM":
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                try:
                    from cohezion.model.cohezion_lm import CohezionLM

                    logger.info("HIHOLMGate: training model (~17s, one-time)...")
                    # v5 defaults: 320+SGDR+smart_seed+code gives NL_mean=21.65 in 17s (exp_HHHH2)
                    # vs v4 (160 steps): NL_mean=23.53. -7.9% at 2x training time (worth it: one-time).
                    # P5_garbage=637 (25x above worst domain) vs 202 (6.6x) at 160 steps.
                    # smart_seed: embedding spread predicts best seed in <1ms (exp_XXXX1: 2.97x speedup)
                    # include_code: +20 Python snippets from model files (exp_EEEE2: -9.8% NL, -21.9% P3)
                    _model = CohezionLM.from_autoresearch(
                        steps=320, smart_seed=True, lr_schedule="sgdr", lr=5e-4, include_code=True
                    )
                    logger.info(
                        "HIHOLMGate: model ready (PPL threshold=%.0f)", _PPL_REJECT_THRESHOLD
                    )
                except Exception as exc:
                    logger.warning("HIHOLMGate: model unavailable: %s", exc)
                    return None  # type: ignore[return-value]
    return _model


def check_quality(text: str, threshold: float = _PPL_REJECT_THRESHOLD) -> bool:
    """Return True if text passes quality gate (PPL < threshold).

    False = reject (sycophantic, random, or garbage).
    Fast path: texts ≤ 2 bytes always return False (perplexity=inf).
    """
    if len(text.encode("utf-8")) <= 2:
        return False
    model = _get_model()
    if model is None:
        return True  # fail-open if model unavailable
    ppl = model.hiho_perplexity(text)
    if not math.isfinite(ppl):
        return False
    return ppl < threshold


def ppl_score(text: str) -> float:
    """Return PPL for text. Returns inf on error or very short input."""
    model = _get_model()
    if model is None:
        return float("inf")
    return model.hiho_perplexity(text)


def check_sycophancy(text: str, threshold: float = 0.90) -> bool:
    """Return True if text is likely sycophantic (hiho_score < threshold).

    WARNING (exp_HHHH1): This method requires model-specific calibration.
    - v1 model (AdamW defaults): threshold=0.90 gives 87% accuracy (exp_MMMM0)
    - v3 model (rmsprop+cosine+bs8+seq128): separation=0.013, accuracy~60% (chance).
      The v3 model learned general language well — sycophantic and substantive text
      have similar PPL (~18-32 range), making hiho_score discrimination unreliable.
    - v5 model (exp_UUUU2): hiho_score also non-functional (range 0.89-0.99, no separation).
      Use check_sycophancy_v5() (PPL-based) instead.

    For v5+ models, use check_sycophancy_v5() (PPL gate) as primary filter.
    """
    model = _get_model()
    if model is None:
        return False  # fail-open if model unavailable
    score = model.hiho_score(text)
    if not math.isfinite(score):
        return False
    return score < threshold


def check_sycophancy_v5(text: str, threshold: float = _PPL_SYCOPHANCY_THRESHOLD) -> bool:
    """Return True if text is likely sycophantic using PPL-based detection (v5 model).

    From exp_UUUU2: v5 model achieves 2.70x PPL separation. Substantive text PPL 13-16;
    sycophantic text PPL 27-76. Threshold=22 catches all sycophancy with zero false
    positives on calibration set (gap=11.3 PPL between max substantive and min sycophantic).

    Preferred over check_sycophancy() for v5 models — hiho_score has no separation.
    Fail-open: returns False if model unavailable.
    """
    if len(text.encode("utf-8")) <= 2:
        return False
    model = _get_model()
    if model is None:
        return False
    ppl = model.hiho_perplexity(text)
    if not math.isfinite(ppl):
        return False
    return ppl > threshold


def reset() -> None:
    """Reset the singleton model (forces retrain on next call). Useful for testing."""
    global _model
    with _lock:
        _model = None
