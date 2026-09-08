#!/usr/bin/env python3
"""mypy error ratchet (gating) — signature-based per-file baseline.

Implements the standard "no new type errors" gate for a large repo with
pre-existing type debt (2103 errors in 672 files at baseline). A global
error-count ratchet is rejected: a new error can hide behind fixing an old
one elsewhere. Instead each error is stored as a stable signature:

    <relative-path>:<error-code>:<message, line numbers stripped>

Line numbers are deliberately excluded (any edit above the error would
shift it and force churn). Message text is kept (stripped of line refs) so
two same-code errors in one file are tracked independently. Known drift
trade-off: refactors that change a message string re-read as "new" —
re-baseline only after confirming the error is genuinely pre-existing.

Fail-closed on: mypy producing no parseable errors AND exiting 0 (sanity:
a run with zero errors must re-baseline to shrink the file, never silently
pass against a stale baseline), unparseable output, missing baseline.

Usage:
  python scripts/ci/mypy_ratchet.py --self-test
  python scripts/ci/mypy_ratchet.py                 # gate
  python scripts/ci/mypy_ratchet.py --write-baseline
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE = Path(__file__).resolve().parent / "mypy_baseline.txt"
MYPY_CMD = ["uv", "run", "mypy", "src/cohezion/", "--ignore-missing-imports", "--no-error-summary", "--show-error-codes"]

# mypy line: "src/path/file.py:123: error: Message text  [error-code]"
MYPY_LINE_RE = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+): error: (?P<msg>.*?)\s+\[(?P<code>[\w-]+)\]\s*$")


def signature(path: str, msg: str, code: str) -> str:
    """Stable error signature: path + code + message with line refs stripped."""
    msg_stripped = re.sub(r"\bline \d+\b", "line N", msg).strip()
    return f"{path}:{code}:{msg_stripped}"


def parse_mypy_output(text: str) -> set[str]:
    """Extract error signatures from mypy output. Raises on zero errors
    found (fail-closed: 'mypy passed' must be an explicit re-baseline)."""
    sigs: set[str] = set()
    for raw in text.splitlines():
        # strip mypy's leading "path:note:" decorations if present
        line = raw.strip()
        m = MYPY_LINE_RE.match(line)
        if not m:
            continue
        path = m.group("path")
        if path.startswith("src/"):
            path = path[len("src/"):]
        sigs.add(signature(path, m.group("msg"), m.group("code")))
    if not sigs:
        raise ValueError("No mypy error lines parsed — refuse to gate on an empty/unknown output shape")
    return sigs


def read_baseline() -> set[str]:
    if not BASELINE.exists():
        raise FileNotFoundError(f"Baseline missing: {BASELINE}")
    return {
        line.strip()
        for line in BASELINE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def self_test() -> int:
    sample = (
        "src/cohezion/a.py:10: error: Need type annotation for \"x\"  [var-annotated]\n"
        "src/cohezion/b.py:20: error: Value of type \"dict[str, Any] | None\" is not indexable  [index]\n"
        "src/cohezion/b.py:44: error: see line 40 above  [misc]\n"
        "Found 3 errors in 2 files (checked 2 source files)\n"
    )
    sigs = parse_mypy_output(sample)
    assert len(sigs) == 3, sigs
    # line number must not be part of the signature
    assert all(":10:" not in s and ":20:" not in s and ":44:" not in s for s in sigs), sigs
    # "see line 40" message text has its line ref normalized
    assert any("see line N" in s for s in sigs), sigs
    # same path+code with different messages -> distinct signatures
    two_same_code = (
        "src/cohezion/c.py:1: error: first  [misc]\n"
        "src/cohezion/c.py:2: error: second  [misc]\n"
    )
    assert len(parse_mypy_output(two_same_code)) == 2
    # empty output must fail closed
    try:
        parse_mypy_output("Success: no issues found in 100 source files")
        raise AssertionError("expected ValueError on clean output")
    except ValueError:
        pass
    print("✓ self-test passed (signatures stable, line-free, fail-closed on empty)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="mypy error ratchet")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--write-baseline", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    proc = subprocess.run(MYPY_CMD, capture_output=True, text=True, cwd=REPO_ROOT, timeout=900)
    out = proc.stdout + proc.stderr
    current = parse_mypy_output(out)

    if args.write_baseline:
        header = (
            "# mypy error ratchet baseline (scripts/ci/mypy_ratchet.py)\n"
            f"# Recorded via --write-baseline from: {' '.join(MYPY_CMD)}\n"
            "# Signatures are path:code:message (line numbers stripped). Prune as\n"
            "# errors are fixed; never add signatures for NEW errors to green a build.\n\n"
        )
        BASELINE.write_text(header + "".join(f"{s}\n" for s in sorted(current)))
        print(f"✓ baseline written: {len(current)} signatures")
        return 0

    base = read_baseline()

    new = sorted(current - base)
    fixed = len(base - current)
    print(f"mypy: {len(current)} errors in code (baseline {len(base)}; fixed-since-baseline: {fixed})")

    if new:
        for s in new[:40]:
            print(f"✗ new type error: {s}", file=sys.stderr)
        if len(new) > 40:
            print(f"✗ ... and {len(new) - 40} more", file=sys.stderr)
        print("New code must type-check: fix the errors above. Do NOT re-baseline to make this pass.", file=sys.stderr)
        return 1
    if fixed:
        print(f"↑ {fixed} baseline errors no longer reproduce — prune the baseline:")
        print("  python scripts/ci/mypy_ratchet.py --write-baseline")
    print("✓ mypy ratchet within baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())