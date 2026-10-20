#!/usr/bin/env python3
"""Ruff debt ratchet — freeze the lint backlog, allow only downward movement.

The CI ``lint`` job runs ``ruff check`` with ``continue-on-error: true`` because
the repo carries a pre-existing ruff backlog. That makes the required ``lint``
check toothless: a PR can add brand-new violations and CI stays green.

This ratchet restores teeth without forcing a full cleanup first: it fails CI only
when the violation count *exceeds* a committed baseline. New lint debt is blocked;
legacy debt is tolerated but visible and monotonically shrinking. When a PR reduces
the count, lower the baseline (``--update``). When the baseline reaches 0, delete
this script and make ``ruff check`` itself gating.

The baseline carries a provenance stamp, because a baseline nobody measured is
worse than no gate at all -- see ``_PROVENANCE`` for the incident that motivated it.

Usage:
    python scripts/ci/ruff_ratchet.py            # gate: fail if count != baseline, or if
                                                  # the baseline was RAISED vs the base ref
    python scripts/ci/ruff_ratchet.py --update   # rewrite baseline to measured count
                                                  # (refuses to RAISE a measured one)
    python scripts/ci/ruff_ratchet.py --merge-reset --reason "..." [--at <merge-ref>]
                                                  # re-baseline absorbing debt inherited
                                                  # via the named MERGE commit (2 parents
                                                  # required); measures the CURRENT tree

Monotonicity (2026-09-21, coding-standards audit R2). Baseline history was
749 -> 456 -> 434 -> 478 -> 475 -> 483 -> 1198 -> 905: a ratchet that anyone can
re-set upward is a counter, not a gate, and one that tolerates count < baseline lets
paydown be silently re-spent. So the gate now also:

* fails when the measured count is BELOW the baseline -- lower it in the same
  commit (``--update``), so every reduction is locked in where it happened;
* fails when the committed baseline is HIGHER than the one at
  ``merge-base(HEAD, $RUFF_RATCHET_BASE_REF)`` (default ``origin/main``), unless
  ``LINT_BASELINE_RAISE_REASON`` carries a written reason, which is logged. This
  also covers ``--merge-reset`` and hand edits: the file may say anything, the
  gate compares it to trunk. When the base cannot be read the check reports
  UNKNOWN; set ``RUFF_RATCHET_REQUIRE_BASE=1`` (CI does) to make that a failure.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
# Note: NOT named ruff_*.txt — that pattern is .gitignore'd (ruff report outputs).
BASELINE_FILE = Path(__file__).resolve().parent / "lint_baseline.txt"
TARGETS = ["src/", "tests/"]


def _current_count() -> int:
    """Return the number of ruff-check violations across TARGETS (deterministic JSON count)."""
    cmd = ["ruff", "check", *TARGETS, "--output-format", "json"]
    # Prefer `uv run ruff` so the locked ruff version (uv.lock) is used — a
    # standalone ruff on PATH (e.g. ~/.local/bin/ruff) can be a different
    # version and produce a different violation count, causing CI/local skew.
    try:
        proc = subprocess.run(["uv", "run", *cmd], cwd=REPO, capture_output=True, text=True)
    except FileNotFoundError:
        # uv not available — fall back to bare ruff on PATH.
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    try:
        return len(json.loads(proc.stdout or "[]"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(proc.stdout[:2000] + "\n" + proc.stderr[:2000] + "\n")
        raise SystemExit(f"ruff_ratchet: could not parse ruff JSON output: {exc}") from exc


# Written by --update so the gate can tell a MEASURED baseline from a typed one.
# History (2026-08-27): commit 66f5186d5 hand-edited the baseline 749 -> 471 while the
# tree actually held 683 -> 758 violations. --update can only ever write the measured
# count, so that number came from a text editor, not a measurement. The gate then failed
# unconditionally and reported "this PR adds new lint debt" to every author -- false and
# unactionable, so it was ignored, and with policing gone the count drifted to 1302.
# This stamp makes an unmeasured baseline self-declaring. It is accident-proof, not
# tamper-proof: someone can copy the comment. Accident is the failure mode we had.
_PROVENANCE = "# measured-by: ruff_ratchet.py --update"
_RAISE_ENV = "LINT_BASELINE_RAISE_REASON"
_REQUIRE_BASE_ENV = "RUFF_RATCHET_REQUIRE_BASE"


def _parse_count(text: str) -> int | None:
    counts = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    return int(counts[0]) if counts else None


def _base_baseline() -> tuple[int | None, str]:
    """Return ``(baseline, where)`` as committed at merge-base(HEAD, base ref).

    ``None`` means UNKNOWN (no base ref, shallow clone, file absent there) --
    never "no raise". Falls back to the ref tip when no merge-base exists.
    """
    ref = os.environ.get("RUFF_RATCHET_BASE_REF", "origin/main")
    try:
        rel = BASELINE_FILE.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return None, f"baseline file outside repo ({BASELINE_FILE})"
    mb = subprocess.run(
        ["git", "merge-base", "HEAD", ref], cwd=REPO, capture_output=True, text=True
    )
    commit = mb.stdout.strip() if mb.returncode == 0 and mb.stdout.strip() else ref
    show = subprocess.run(
        ["git", "show", f"{commit}:{rel}"], cwd=REPO, capture_output=True, text=True
    )
    if show.returncode != 0:
        return None, f"cannot read {rel} at {commit} ({show.stderr.strip()[:120]})"
    try:
        return _parse_count(show.stdout), f"{ref} @ {commit[:12]}"
    except ValueError:
        return None, f"unparseable baseline at {commit}"


def _check_not_raised(baseline: int) -> int:
    """0 if the committed baseline did not rise vs the base ref (or a reason overrides)."""
    base, where = _base_baseline()
    if base is None:
        print(f"⚠️  ruff_ratchet: UNKNOWN whether the baseline was raised: {where}")
        if os.environ.get(_REQUIRE_BASE_ENV, "").strip() in ("1", "true", "yes"):
            print(
                f"❌ ruff_ratchet: {_REQUIRE_BASE_ENV} is set, so an unreadable base fails closed."
            )
            return 1
        return 0
    if baseline <= base:
        return 0
    reason = os.environ.get(_RAISE_ENV, "").strip()
    if not reason:
        print(
            f"❌ ruff_ratchet: baseline RAISED {base} -> {baseline} vs {where}. The ratchet "
            f"only moves down. If the raise is genuinely unavoidable, set "
            f'{_RAISE_ENV}="<written reason>" and it will be logged.'
        )
        return 1
    print(f"LINT-BASELINE-RAISE OVERRIDE: {base} -> {baseline} vs {where}; reason: {reason}")
    return 0


def _read_baseline() -> tuple[int, bool]:
    """Return ``(count, was_measured)`` for the committed baseline.

    ``was_measured`` is False when the file carries no provenance stamp, which
    means the number was typed rather than produced by a real ruff run.
    """
    if not BASELINE_FILE.exists():
        raise SystemExit(f"ruff_ratchet: missing baseline file {BASELINE_FILE}")
    text = BASELINE_FILE.read_text()
    count = _parse_count(text)
    if count is None:
        raise SystemExit(f"ruff_ratchet: no count found in {BASELINE_FILE}")
    return count, _PROVENANCE in text


def _self_test() -> int:
    """Replay the 66f5186d5 incident and require this gate to diagnose it.

    A gate that cannot demonstrate it still detects its founding defect has
    rotted. Here the defect is a baseline nobody measured: 471 committed by hand
    while the tree held 758. The gate must call that a MISCONFIGURATION rather
    than blaming the author, because blaming the author is what got it ignored.
    """
    import io
    import tempfile
    from contextlib import redirect_stdout

    global BASELINE_FILE, _current_count, _base_baseline
    real_file, real_count, real_base = BASELINE_FILE, _current_count, _base_baseline
    real_env = {k: os.environ.pop(k, None) for k in (_RAISE_ENV, _REQUIRE_BASE_ENV)}
    real_argv = sys.argv
    # main() dispatches on --self-test, so the probe must call it without that flag
    # or it recurses into itself forever.
    sys.argv = [a for a in sys.argv if a != "--self-test"]
    ok = True
    try:
        with tempfile.TemporaryDirectory() as tmp:
            BASELINE_FILE = Path(tmp) / "lint_baseline.txt"
            _current_count = lambda: 758  # noqa: E731 - one-line stub for the probe
            _base_baseline = lambda: (None, "self-test: no base")  # noqa: E731

            def run() -> tuple[int, str]:
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = main()
                return rc, out.getvalue()

            # 1. The historical case: unstamped baseline, tree above it.
            BASELINE_FILE.write_text("471\n")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = main()
            text = out.getvalue()
            hit = rc == 1 and "UNVERIFIED" in text and "adds new lint debt" not in text
            print(f"self-test unverified-baseline: {'PASS' if hit else 'FAIL'}")
            ok &= hit

            # 2. Negative control: a MEASURED baseline over budget IS the author's debt.
            BASELINE_FILE.write_text(f"471\n{_PROVENANCE}\n")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = main()
            text = out.getvalue()
            hit = rc == 1 and "adds new lint debt" in text and "UNVERIFIED" not in text
            print(f"self-test measured-baseline-control: {'PASS' if hit else 'FAIL'}")
            ok &= hit

            # 3. Green path must still pass.
            BASELINE_FILE.write_text(f"758\n{_PROVENANCE}\n")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = main()
            hit = rc == 0 and "no new lint debt" in out.getvalue()
            print(f"self-test green-path: {'PASS' if hit else 'FAIL'}")
            ok &= hit

            # 4. (b) Count BELOW a measured baseline must fail until it is lowered,
            #    or paydown can be silently re-spent (905 recorded vs 896 measured).
            BASELINE_FILE.write_text(f"800\n{_PROVENANCE}\n")
            rc, text = run()
            hit = rc == 1 and "lower the baseline" in text
            print(f"self-test below-baseline-must-tighten: {'PASS' if hit else 'FAIL'}")
            ok &= hit

            # 5. (c) Baseline RAISED vs base ref, no reason -> refuse.
            BASELINE_FILE.write_text(f"758\n{_PROVENANCE}\n")
            _base_baseline = lambda: (700, "self-test base")  # noqa: E731
            rc, text = run()
            hit = rc == 1 and "RAISED 700 -> 758" in text
            print(f"self-test raise-refused: {'PASS' if hit else 'FAIL'}")
            ok &= hit

            # 6. (c) Whitespace is not a reason.
            os.environ[_RAISE_ENV] = "   "
            rc, text = run()
            hit = rc == 1 and "OVERRIDE" not in text
            print(f"self-test blank-reason-refused: {'PASS' if hit else 'FAIL'}")
            ok &= hit

            # 7. (c) A written reason permits the raise AND is logged.
            os.environ[_RAISE_ENV] = "self-test: inherited debt from merge X"
            rc, text = run()
            hit = rc == 0 and "OVERRIDE: 700 -> 758" in text and "merge X" in text
            print(f"self-test raise-with-reason-logged: {'PASS' if hit else 'FAIL'}")
            ok &= hit
            os.environ.pop(_RAISE_ENV, None)

            # 8. Unreadable base fails closed only when required (CI sets it).
            _base_baseline = lambda: (None, "self-test: no base")  # noqa: E731
            os.environ[_REQUIRE_BASE_ENV] = "1"
            rc, text = run()
            hit = rc == 1 and "UNKNOWN" in text
            print(f"self-test unknown-base-fails-closed-when-required: {'PASS' if hit else 'FAIL'}")
            ok &= hit
    finally:
        BASELINE_FILE, _current_count, _base_baseline = real_file, real_count, real_base
        sys.argv = real_argv
        for k, v in real_env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    print("self-test:", "OK" if ok else "BROKEN — this gate can no longer diagnose its own defect")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()

    current = _current_count()

    if "--merge-reset" in sys.argv:
        # Sanctioned repair route for merge boundaries: a count-based ratchet
        # cannot tell "new debt" from "debt that rode in on merged commits".
        # Guardrails: --at must name a true merge commit (2 parents) + a
        # --reason for the audit trail; writes the same provenance stamp as
        # --update. The MEASUREMENT happens on the current tree (so the lock/
        # config state that CI will actually run against defines the floor);
        # --at only identifies the merge being absorbed.
        argv = sys.argv
        reason = argv[argv.index("--reason") + 1] if "--reason" in argv and argv.index("--reason") + 1 < len(argv) else None
        at = argv[argv.index("--at") + 1] if "--at" in argv and argv.index("--at") + 1 < len(argv) else "HEAD"
        if not reason or not reason.strip() or reason.startswith("--"):
            print('ruff_ratchet: --merge-reset requires: --merge-reset --reason "<why>" [--at <merge-ref>]')
            return 1
        if any(f in argv for f in ("--update", "--self-test")):
            print("ruff_ratchet: --merge-reset cannot be combined with --update/--self-test")
            return 1
        revs = subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", at],
            cwd=REPO, capture_output=True, text=True)
        if revs.returncode != 0:
            print(f"ruff_ratchet: --at ref {at!r} not resolvable: {revs.stderr.strip()[:200]}")
            return 1
        toks = revs.stdout.split()
        n_parents = len(toks) - 1
        if n_parents < 2:
            print(
                f"ruff_ratchet: refusing --merge-reset on {at} ({n_parents} parent). "
                f"Merge-resets are only for merge commits; use --update (downward-only) otherwise."
            )
            return 1
        old, _ = _read_baseline()
        BASELINE_FILE.write_text(f"{current}\n{_PROVENANCE}\n")
        print(
            f"ruff_ratchet: MERGE-RESET baseline {old} -> {current} "
            f"(reason: {reason}; merge commit {toks[0][:12]} verified). "
            f"Inherited debt is now the floor."
        )
        return 0

    if "--update" in sys.argv:
        old, old_measured = _read_baseline() if BASELINE_FILE.exists() else (None, False)
        # "Only moves down" is right for a real baseline and wrong for a fictitious
        # one: it left NO sanctioned way to repair a typed number, so the only route
        # out of a permanently-red gate was to hand-edit the file again -- the very
        # act that broke it. Replacing an unverified value with a measurement is
        # establishing ground truth, not inflating debt, so it is allowed once.
        if old is not None and current > old and old_measured:
            sys.stderr.write(
                f"ruff_ratchet: refusing to RAISE baseline {old} -> {current}. "
                f"The ratchet only moves down.\n"
            )
            return 1
        if old is not None and current > old and not old_measured:
            print(
                f"ruff_ratchet: replacing UNVERIFIED baseline {old} with the first "
                f"measured value {current}. Subsequent updates may only move down."
            )
        BASELINE_FILE.write_text(f"{current}\n{_PROVENANCE}\n")
        delta = "" if old is None else f" (was {old}, {current - old:+d})"
        print(f"ruff_ratchet: baseline set to {current}{delta}")
        return 0

    baseline, was_measured = _read_baseline()
    if _check_not_raised(baseline):
        return 1
    if current > baseline and not was_measured:
        # Do NOT blame the author. An unmeasured baseline can sit below anything
        # the tree has ever achieved, in which case this gate fails for everyone
        # forever and teaches the team to ignore it.
        print(
            f"❌ ruff_ratchet: baseline {baseline} is UNVERIFIED — it carries no "
            f"provenance stamp, so it was typed rather than measured, and the tree "
            f"may never have met it (current: {current}).\n"
            f"   This is a gate misconfiguration, not new debt in your change.\n"
            f"   Re-measure it: python scripts/ci/ruff_ratchet.py --update"
        )
        return 1
    if current > baseline:
        print(
            f"❌ ruff_ratchet: {current} violations > baseline {baseline} "
            f"(+{current - baseline}). This PR adds new lint debt — fix the new "
            f"violations. Do NOT raise the baseline.\n"
            f"   See them: uv run ruff check {' '.join(TARGETS)}"
        )
        return 1
    if current < baseline:
        # Fail, don't congratulate: an unlocked reduction is slack the next PR can
        # re-spend without tripping the gate.
        print(
            f"❌ ruff_ratchet: {current} < baseline {baseline} — debt reduced by "
            f"{baseline - current}, so lower the baseline in this same commit: "
            f"python scripts/ci/ruff_ratchet.py --update"
        )
        return 1
    print(f"✅ ruff_ratchet: {current} == baseline {baseline} (no new lint debt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
