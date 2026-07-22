"""Discriminating tests for scripts/ci/dormancy_scan.py (verification-depth.md layer 3).

Two failure classes this session exposed, both in the same self-improvement loop:
  - the FAILURE path (executor.py's ``elif not success`` branch calling
    ``FailureAttributor().classify()`` then ``skill_refiner.refine(..., failure_attribution=...)``)
    had never been reachable from production before this session's fix.
  - the SUCCESS path had a live ``token_metrics`` bug (``None`` vs ``{}`` default mismatch).

dormancy_scan.py already had a generic ``--self-test`` proving the SCANNER MECHANISM can go red
(a guaranteed-dormant sentinel) and green (a known-wired capability). This module goes one level
deeper per verification-depth.md corrective #1 ("test the CLAIM, not the component"): it proves
the FOUR NEW REGISTRY ENTRIES pinned to this session's fix specifically discriminate presence vs.
absence of their consumer — not that the scanner mechanism works in the abstract.

For each new entry:
  1. WIRED — scanning the real, current production file finds the consumer (floor met, green).
  2. DISCRIMINATES — scanning a synthetic copy of that same file with ONLY the consumer literal
     stripped (everything else, including the `def`, untouched) drops the count below the floor
     (red). This recreates the exact counterfactual the gate exists to catch: "if this session's
     fix were silently reverted, would the scan flag it before merge?"
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


_SCRIPTS_CI_DIR = Path(__file__).resolve().parents[2] / "scripts" / "ci"
if str(_SCRIPTS_CI_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_CI_DIR))

from dormancy_scan import REGISTRY, scan, self_test


REPO = Path(__file__).resolve().parents[2]

# The four entries added to guard the FAPO failure-path loop closed this session. Named here
# (rather than inferred by index) so a REGISTRY reorder can't silently desync this test file.
_NEW_ENTRY_NAMES = {
    "FA-exec: executor failure branch CONSUMES FailureAttributor().classify() on a failed execution",
    "FA-refine: executor failure branch CONSUMES refine(failure_attribution=...) (FAPO path reachable)",
    "FM-retrieve: _generate_failure_signal CONSUMES failure_memory.retrieve() before generic template",
    "FM-record: L1 refinement CONSUMES failure_memory.record() to store the new (failure, fix) pair",
}

# (entry_name, consumer_literal) — the exact substring that, if stripped, reverts the file to the
# pre-fix (dormant) state for that capability.
_CONSUMER_LITERALS = {
    "FA-exec: executor failure branch CONSUMES FailureAttributor().classify() on a failed execution": (
        "FailureAttributor().classify("
    ),
    "FA-refine: executor failure branch CONSUMES refine(failure_attribution=...) (FAPO path reachable)": (
        "failure_attribution=attribution"
    ),
    "FM-retrieve: _generate_failure_signal CONSUMES failure_memory.retrieve() before generic template": (
        "self._failure_memory.retrieve("
    ),
    "FM-record: L1 refinement CONSUMES failure_memory.record() to store the new (failure, fix) pair": (
        "self._failure_memory.record("
    ),
}


class TestScannerMechanismSanity:
    """The scanner's own falsification proof must still pass before trusting anything below."""

    def test_self_test_still_passes(self) -> None:
        assert self_test() == 0


class TestNewFapoLoopEntriesRegistered:
    def test_all_four_new_entries_present_in_registry(self) -> None:
        names = {entry[0] for entry in REGISTRY}
        missing = _NEW_ENTRY_NAMES - names
        assert not missing, f"new FAPO-loop entries missing from REGISTRY: {missing}"


@pytest.mark.parametrize(
    "entry", [e for e in REGISTRY if e[0] in _NEW_ENTRY_NAMES], ids=lambda e: e[0]
)
class TestNewEntriesWiredAndDiscriminate:
    """Each new entry, against the REAL repo, is currently wired (green) — proving genuine
    production consumption, not a registry entry pointing at nothing."""

    def test_currently_wired_against_real_source(self, entry: tuple[str, str, str, int]) -> None:
        failures = scan([entry])
        assert failures == [], f"expected wired against real source, got: {failures}"

    def test_stripping_the_consumer_flips_scan_to_red(
        self, entry: tuple[str, str, str, int], tmp_path: Path
    ) -> None:
        """Copy the real production file, strip ONLY the consumer literal (leaving the `def`
        and everything else intact), and confirm the SAME pattern+floor now fails. A wrong
        implementation of the pattern (e.g. one that also matches the `def` line, or matches
        an unrelated comment) would stay green here — that's exactly what this test forbids.
        """
        name, pattern, path_rel, floor = entry
        consumer_literal = _CONSUMER_LITERALS[name]

        real_path = REPO / path_rel
        text = real_path.read_text()
        assert consumer_literal in text, (
            f"fixture assumption broken: {consumer_literal!r} not found in {path_rel} — "
            "the production code moved and this test's literal is stale"
        )
        assert text.count(consumer_literal) == 1, (
            f"fixture assumption broken: {consumer_literal!r} appears "
            f"{text.count(consumer_literal)} times in {path_rel}, expected exactly 1"
        )

        dormant_text = text.replace(consumer_literal, "# <consumer-stripped-for-test>")
        dormant_file = tmp_path / real_path.name
        dormant_file.write_text(dormant_text)

        # count_matches() resolves `REPO / path_rel`; pathlib replaces the whole path when the
        # right-hand operand is already absolute, so passing str(dormant_file) here scans the
        # synthetic file directly, independent of REPO/tests/ exclusion (dormant_file's name
        # matches the real module, not a test_*.py name, and its path has no /tests/ segment).
        dormant_failures = scan([(name, pattern, str(dormant_file), floor)])
        assert len(dormant_failures) == 1, (
            f"{name}: stripping the consumer did not flip the scan to red — "
            f"pattern {pattern!r} does not discriminate presence vs. absence of the consumer"
        )
