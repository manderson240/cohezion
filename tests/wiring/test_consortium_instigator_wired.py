"""Discriminating test: the pipeline attack-vector library lives in the
adversarial-review package.

History: consortium_instigator.py (a 4th parallel red-team framework) was
retired 2026-08-14 (elegant-simplicity audit); its probe definitions were
merged as pure data into tdd_adversarial.pipeline_attack_vectors. This test
pins that the vectors are registered in the surviving system and keep the
shape a runner needs.
"""

from __future__ import annotations

from cohezion.compound.tdd_adversarial import PIPELINE_ATTACK_VECTORS


def test_pipeline_attack_vectors_registered() -> None:
    assert len(PIPELINE_ATTACK_VECTORS) >= 7, "attack-vector library lost entries"
    ids = {v["id"] for v in PIPELINE_ATTACK_VECTORS}
    for expected in (
        "empty-prompt",
        "large-prompt",
        "concurrent-three",
        "lemonade-down",
        "tight-timeout",
        "malformed-json",
        "control-chars",
    ):
        assert expected in ids, f"vector {expected} missing"


def test_vectors_have_runner_contract() -> None:
    for v in PIPELINE_ATTACK_VECTORS:
        for key in ("id", "description", "category", "severity", "payload", "failure_indicators"):
            assert key in v, f"vector {v.get('id', '?')} missing {key}"
        assert isinstance(v["payload"], dict)
        assert isinstance(v["failure_indicators"], list) and v["failure_indicators"]
