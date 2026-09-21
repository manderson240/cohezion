"""The two gated test dirs must be deselected of live-service tests in BOTH gates.

tests/unit/ and tests/inference/ block merges (scripts/ci/automerge_guard.sh, ci.yml). Tests
marked `integration` assert on live fleet state (:13305 up, a model resident) that changes
between two runs of the SAME tree -- measured 2026-09-21: inference-alone failed the RC1
canary while a combined run passed it and failed STT/TTS/image instead. A gate whose verdict
depends on wall-clock fleet residency is not a gate. These checks fail if either gate stops
deselecting them, or if the marked tests stop being collected anywhere.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESELECT = '-m "not integration"'
# Every blocking pytest dir. tests/reliability + tests/security became gating on
# fix/standards-gates; the same deselection rule applies to them.
GATED_DIRS = ("tests/unit", "tests/inference", "tests/reliability", "tests/security")


def _pytest_lines(text: str, target: str) -> list[str]:
    return [
        ln for ln in text.splitlines() if "pytest" in ln and re.search(rf"{target}/?(\s|$)", ln)
    ]


def test_automerge_guard_deselects_live_tests_in_both_gated_steps() -> None:
    text = (ROOT / "scripts/ci/automerge_guard.sh").read_text()
    for target in GATED_DIRS:
        gating = [ln for ln in _pytest_lines(text, target) if ln.lstrip().startswith("step ")]
        assert gating, f"no gating pytest step for {target} in automerge_guard.sh"
        for ln in gating:
            assert DESELECT in ln, f"gating step runs live-service tests: {ln.strip()}"


def test_automerge_guard_still_runs_live_tests_as_advisory() -> None:
    """Deselecting must not silently retire them: an advisory step still runs `-m integration`."""
    text = (ROOT / "scripts/ci/automerge_guard.sh").read_text()
    assert any(
        ln.lstrip().startswith("step_advisory ") and "-m integration" in ln
        for ln in text.splitlines()
    ), "no advisory step runs the integration-marked tests"


def test_ci_workflow_deselects_live_tests_in_gated_steps() -> None:
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    for target in GATED_DIRS:
        lines = [
            ln
            for ln in _pytest_lines(text, target)
            if "--ignore" not in ln and "-m integration" not in ln  # the non-gating live step
        ]
        assert lines, f"no pytest invocation for {target} in ci.yml"
        for ln in lines:
            assert DESELECT in ln, f"ci.yml gated step runs live-service tests: {ln.strip()}"


def test_ci_workflow_still_runs_live_tests_non_gating() -> None:
    """ci.yml's broad step --ignores both gated dirs, so without this step the 21 marked
    tests would run in no CI step at all."""
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    lines = text.splitlines()
    hits = [
        i
        for i, ln in enumerate(lines)
        if "pytest tests/unit/ tests/inference/" in ln and "-m integration" in ln
    ]
    assert hits, "no ci.yml step runs the integration-marked tests from the gated dirs"
    assert any("continue-on-error: true" in "\n".join(lines[i : i + 3]) for i in hits), (
        "the live-service step must be non-gating (continue-on-error: true)"
    )
