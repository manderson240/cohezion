#!/usr/bin/env python3
"""Meta-gate: every gate CI runs must be able to prove it still works.

Motivation (2026-08-27). `ruff_ratchet.py` was pointed at a baseline nobody had
measured. It then failed unconditionally for weeks while reporting "this PR adds
new lint debt" -- and nothing could tell the difference between "the gate is
broken" and "your change is bad", because the gate had no way to check itself.

Several gates already solve this properly: `phantom_attr_scan.py`,
`doc_code_consistency.py`, `dormancy_scan.py` and now `ruff_ratchet.py` each
support ``--self-test``, which plants the historical defect, requires the scanner
to go RED, then removes it and requires GREEN. A gate that can still catch its own
founding defect has not rotted. This script makes that convention universal
instead of optional.

It EXECUTES each self-test rather than grepping for the flag, and the distinction
is not theoretical: `doc_code_consistency.py` shipped a ``--self-test`` that
printed "BROKEN -- a check cannot fail" and exited 1 for an unknown period. A
substring check would have certified it compliant while it detected nothing, and
the doc drift accumulating behind it -- including a phantom `curvature_coupling`
invariant -- went unseen.

Scope is DERIVED, never hand-listed: a script is a gate exactly when CI invokes
it (a workflow or `automerge_guard.sh`). So the requirement attaches by itself
the moment a script is promoted to a gate, and no one has to remember to add it
here.

``GRANDFATHERED`` names gates that predate this rule. It is a ratchet: it may
only shrink. Unlike a bare count, it names each debt explicitly -- the lint
baseline failed precisely because "471" carried no record of what it covered.

Usage:
    python scripts/ci/self_test_coverage.py             # gate
    python scripts/ci/self_test_coverage.py --self-test # this gate checks itself
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
CI_DIR = REPO / "scripts" / "ci"
SELF_TEST_FLAG = "--self-test"

# Files whose contents declare which scripts CI actually runs.
GATE_SOURCES = (
    *sorted((REPO / ".github" / "workflows").glob("*.yml")),
    CI_DIR / "automerge_guard.sh",
)

_INVOCATION = re.compile(r"scripts/ci/([a-zA-Z0-9_]+\.py)")

# Gates that predate this rule. RATCHET: entries may be removed, never added.
# Each one is a gate that currently cannot demonstrate it still detects anything.
GRANDFATHERED = frozenset(
    {
        "compound_audit.py",
        "daily_health_check.py",
        "frontier_digest.py",
        "graph_cardinality_audit.py",
        # ruff_ratchet.py removed 2026-08-27: it now replays the 66f5186d5 incident.
        # Leaving the gate that MOTIVATED this rule exempt from it meant the meta-gate
        # would print an identical line if the entire ratchet fix were reverted.
        "sync_skills_manifest.py",
        "systemd_unit_audit.py",
        "validate_agents.py",
        "validate_registry.py",
        "validate_skills.py",
        "version_governance.py",
    }
)


def ci_invoked_gates(sources: tuple[Path, ...] | None = None) -> set[str]:
    """Return the basenames of scripts/ci/*.py that CI actually invokes.

    ``sources`` defaults to the module-level ``GATE_SOURCES`` read at CALL time.
    Binding it as a default argument would freeze the value at import, making the
    constant look configurable while silently ignoring any change to it.
    """
    found: set[str] = set()
    for source in GATE_SOURCES if sources is None else sources:
        if source.is_file():
            found.update(_INVOCATION.findall(source.read_text(encoding="utf-8")))
    return found


def supports_self_test(script: Path) -> bool:
    """True when *script* accepts a ``--self-test`` flag.

    Presence only. ``self_test_passes`` is what establishes it still works.
    """
    if not script.is_file():
        return False
    return SELF_TEST_FLAG in script.read_text(encoding="utf-8")


def self_test_passes(script: Path, timeout: int = 180) -> bool:
    """Run ``script --self-test`` and report whether it succeeds.

    Presence of the flag is not evidence of health. ``doc_code_consistency.py``
    carried a ``--self-test`` that reported "BROKEN -- a check cannot fail" and
    exited 1 for an unknown period: it satisfied a substring check while being
    unable to detect anything, and CI stayed red and ignored behind it. Grepping
    for the flag would have certified that gate as compliant.

    A timeout or a crash counts as failure: a self-test that cannot complete has
    not demonstrated anything.
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(script), SELF_TEST_FLAG],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return proc.returncode == 0


def _self_test() -> int:
    """Plant the defect this gate exists to catch, require RED, then GREEN."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "workflow.yml").write_text(
            "run: python scripts/ci/planted_gate.py\n", encoding="utf-8"
        )
        # Explicit check rather than `assert`: python -O strips asserts, which would
        # turn this self-test into an unconditional pass -- the exact failure mode it
        # exists to prevent.
        if ci_invoked_gates((root / "workflow.yml",)) != {"planted_gate.py"}:
            print("SELF-TEST FAILED: could not derive the gate set from a CI invocation")
            return 1

        naked = root / "naked.py"
        naked.write_text("print('no self test here')\n", encoding="utf-8")
        if supports_self_test(naked):
            print("SELF-TEST FAILED: a script without the flag was reported compliant")
            return 1

        equipped = root / "equipped.py"
        equipped.write_text(f"if {SELF_TEST_FLAG!r} in sys.argv: ...\n", encoding="utf-8")
        if not supports_self_test(equipped):
            print("SELF-TEST FAILED: a script with the flag was reported non-compliant")
            return 1

    print("SELF-TEST OK: detects a gate that cannot verify itself (red) and one that can (green).")
    return 0


def main() -> int:
    if SELF_TEST_FLAG in sys.argv:
        return _self_test()

    gates = ci_invoked_gates()
    if not gates:
        # An empty derivation means the sources moved or could not be read. Say so
        # rather than passing vacuously -- a gate that checks nothing must never
        # report success.
        print(
            "❌ self_test_coverage: derived ZERO gates from "
            f"{', '.join(str(s.relative_to(REPO)) for s in GATE_SOURCES if s.is_file())}.\n"
            "   The workflow/guard files moved or are unreadable; this gate is blind."
        )
        return 1

    missing = sorted(g for g in gates if not supports_self_test(CI_DIR / g))
    newly_missing = [g for g in missing if g not in GRANDFATHERED]
    now_compliant = sorted(g for g in GRANDFATHERED if g in gates and g not in missing)

    # Presence is not health. Every gate that CLAIMS a self-test must prove it
    # still passes, or a broken one (see doc_code_consistency.py, which reported
    # "BROKEN -- a check cannot fail" while satisfying the substring check) is
    # certified as compliant by this very gate.
    claims_self_test = sorted(g for g in gates if g not in missing)
    rotted = [g for g in claims_self_test if not self_test_passes(CI_DIR / g)]
    if rotted:
        print(
            f"❌ self_test_coverage: {len(rotted)} gate(s) have a {SELF_TEST_FLAG} that "
            f"FAILS: {', '.join(rotted)}\n"
            f"   The flag is present but the gate can no longer demonstrate it detects "
            f"its own defect, so it is certifying nothing.\n"
            f"   Run it directly to see why: uv run python scripts/ci/<name> {SELF_TEST_FLAG}"
        )
        return 1

    if newly_missing:
        print(
            f"❌ self_test_coverage: {len(newly_missing)} CI gate(s) cannot verify "
            f"themselves: {', '.join(newly_missing)}\n"
            f"   A gate with no {SELF_TEST_FLAG} cannot tell 'I am broken' from 'your "
            f"change is bad'. Add one that plants the defect the gate exists to catch, "
            f"requires RED, then GREEN.\n"
            f"   See scripts/ci/phantom_attr_scan.py for the pattern."
        )
        return 1

    if now_compliant:
        print(
            f"✅ self_test_coverage: {len(now_compliant)} grandfathered gate(s) now "
            f"self-test: {', '.join(now_compliant)}\n"
            f"   Lock it in — remove them from GRANDFATHERED (the list only shrinks)."
        )
        return 0

    covered = len(gates) - len(missing)
    print(
        f"✅ self_test_coverage: {covered}/{len(gates)} CI gates self-test "
        f"({len(missing)} grandfathered)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
