"""Structural verification leg for cohezion.model.CohezionLM (V-model audit 2026-06-05).

Closes the highest-priority gap: harness invariants LM1-LM7 assert CohezionLM
behaviour, but the module had no `tests/model/` dir. These are *structural* checks
(config + signature) -- no torch training -- so they are fast and deterministic.
"""

from __future__ import annotations

import inspect

import pytest

from cohezion.model.cohezion_lm import CohezionLMConfig


def test_byte_level_ffn_scale_is_one() -> None:
    # LM6: ffn_scale=1.0 is the audited-optimal byte-level config (exp_GGGG4).
    assert CohezionLMConfig.byte_level().ffn_scale == 1.0


def test_from_autoresearch_defaults_match_harness_LM7() -> None:
    # LM7: steps=80, n_seeds=3 are the optimal defaults (exp_NNNN5/QQQQ5).
    try:
        from cohezion.model.cohezion_lm import CohezionLM
    except (ImportError, AttributeError) as exc:  # torch-optional environment
        pytest.skip(f"CohezionLM unavailable (torch?): {exc}")
    if not hasattr(CohezionLM, "from_autoresearch"):
        pytest.skip("from_autoresearch only defined in the torch-backed CohezionLM")
    params = inspect.signature(CohezionLM.from_autoresearch).parameters
    assert params["steps"].default == 80
    assert params["n_seeds"].default == 3
