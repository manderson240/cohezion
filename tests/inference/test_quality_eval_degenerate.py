"""GATE-THAT-CANNOT-FAIL: quality_eval accepted a repetition loop at full score.

Measured 2026-10-23 before the fix: "I cannot help with that request. " * 40 as
long_generation -> accept=True, score=1.0; "lorem ipsum dolor sit amet " * 30 as
medium_generation -> accept=True, score=1.0. Length gates are maximised by a loop.
"""

from __future__ import annotations

import pytest

from cohezion.inference.quality_eval import evaluate


_LOOP = "I cannot help with that request. " * 40

_PROSE = (
    "The scheduler records an outcome file only after the submission finishes, so a run "
    "killed by a reboot leaves no state and the resume service starts it again at login. "
    "Locks carry the holder's pid and boot id; a lock written during a previous boot is "
    "taken over instead of blocking the retry. Parsing starts at the CSV header because "
    "the command line tool can print an upgrade warning on standard output first, and "
    "the gate is only trusted once its offline deltas have agreed with the board."
)


@pytest.mark.parametrize("output_type", ["long_generation", "medium_generation", "unknown"])
def test_repetition_loop_is_rejected(output_type: str) -> None:
    verdict = evaluate(_LOOP, output_type)
    assert verdict.accept is False
    assert "repetition" in verdict.reason


@pytest.mark.parametrize("output_type", ["long_generation", "medium_generation", "unknown"])
def test_varied_prose_of_similar_length_still_passes(output_type: str) -> None:
    verdict = evaluate(_PROSE * 2 if output_type == "long_generation" else _PROSE, output_type)
    assert verdict.accept is True, verdict.reason


def test_code_is_exempt_from_the_repetition_check() -> None:
    table = "x = [\n" + "    0,\n" * 60 + "]\n"
    assert evaluate(table, "code").accept is True
