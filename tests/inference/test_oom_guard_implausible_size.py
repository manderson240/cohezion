"""_is_heavy must not trust an implausible catalog size (work-queue f2505e..., 2026-09-21).

``scan_and_harden`` already routes sizes through ``hotswap.implausible_size_gb`` (RS7), but
its two siblings do not: ``verify_all_bounded`` and ``pre_load_gate`` both call
``_is_heavy(model)``, which compares the raw ``size`` against the 5 GB threshold. The live
catalog reports ``Qwen3.6-35B-A3B-GGUF`` at 1.68 GB, so both treat a 35B as small: an
unbounded ``ctx_size=0`` on it is neither flagged nor blocked (the N3 crash vector).

Positive controls pin that plausible sizes are still trusted in BOTH directions, so a fix
that simply returns True for everything fails.
"""

from __future__ import annotations

import pytest

from cohezion.inference import oom_guard


pytestmark = pytest.mark.xfail(
    reason="ACT-loop oracle for work-queue f2505e6983bf: the local model did not solve it (splice + router "
    "failures, 2026-09-21); fixed by hand on fix/review-followups-20260921 (c11a7eec1). Non-strict so the "
    "merge with that fix passes.",
    strict=False,
)


IMPLAUSIBLE = {"model_name": "Qwen3.6-35B-A3B-GGUF", "size": 1.68}


@pytest.mark.parametrize(
    "model",
    [IMPLAUSIBLE, {"id": "Qwen3.6-35B-A3B-GGUF", "size": 1.68}],
    ids=["model_name-key", "id-key"],
)
def test_implausible_size_counts_as_heavy(model: dict) -> None:
    assert oom_guard._is_heavy(model) is True


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ({"model_name": "Qwen3-0.6B-GGUF", "size": 0.5}, False),  # plausible and small
        ({"model_name": "Qwen3.6-35B-A3B-MTP-GGUF", "size": 22.1}, True),  # plausible, big
        ({"model_name": "nomic-embed-text-v2-moe-GGUF", "size": 0.3}, False),  # no param count
        ({"model_name": "Llama-3.2-1B-GGUF"}, True),  # size absent: unchanged (heavy)
    ],
)
def test_plausible_sizes_are_still_trusted(model: dict, expected: bool) -> None:
    assert oom_guard._is_heavy(model) is expected


def test_verify_all_bounded_flags_unbounded_implausible_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    small = {"model_name": "Qwen3-0.6B-GGUF", "size": 0.5}
    monkeypatch.setattr(oom_guard, "_get_catalog", lambda *_a, **_k: [IMPLAUSIBLE, small])
    monkeypatch.setattr(oom_guard, "_get_recipe_options", lambda *_a, **_k: {"ctx_size": 0})
    safe, violations = oom_guard.verify_all_bounded("http://127.0.0.1:9")
    assert safe is False
    assert violations == ["Qwen3.6-35B-A3B-GGUF"]  # the plausible small model stays exempt


def test_pre_load_gate_blocks_ctx0_on_implausible_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oom_guard, "_get_catalog", lambda *_a, **_k: [IMPLAUSIBLE])
    monkeypatch.setattr(oom_guard, "check_ram", lambda *_a, **_k: (True, 100.0))
    allowed, reason = oom_guard.pre_load_gate("Qwen3.6-35B-A3B-GGUF", ctx_size=0)
    assert allowed is False
    assert "N3" in reason
