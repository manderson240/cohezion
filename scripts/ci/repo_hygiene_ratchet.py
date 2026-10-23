#!/usr/bin/env python3
"""Tracked-file hygiene gate: ignore debt (ratchet) and LFS debt (zero tolerance).

Two rules the repository declares and, until 2026-10-22, nothing enforced:

* ``.gitignore`` says which paths must not be tracked. 188 tracked files matched
  those rules anyway (added with ``-f`` or before the rule existed). This half is
  a ratchet like ``ruff_ratchet.py``: it fails only when the count EXCEEDS the
  committed, measured baseline, so legacy debt is tolerated and new debt is not.
* ``.gitattributes`` says which paths are LFS pointers. 22 media files were
  committed as raw blobs. The ``lfs-pointer-check`` pre-commit hook only runs where
  pre-commit is installed, which CI and most checkouts are not. This half is zero
  tolerance: any tracked path whose attributes route it to LFS must be a pointer.

Both measurements come from git itself (``ls-files -i``, ``check-attr``), never
from a re-implementation of its glob rules.

Usage:
    python scripts/ci/repo_hygiene_ratchet.py             # gate
    python scripts/ci/repo_hygiene_ratchet.py --update    # lower the ignore-debt baseline
    python scripts/ci/repo_hygiene_ratchet.py --self-test # prove the gate can still fail
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
BASELINE_FILE = Path(__file__).resolve().parent / "ignore_debt_baseline.txt"
PROVENANCE = "# measured-by: repo_hygiene_ratchet.py --update"
_POINTER_MAGIC = b"version https://git-lfs.github.com/spec/v1"
_POINTER_MAX_BYTES = 300  # a pointer is ~130 bytes; anything larger is content


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    proc = subprocess.run(["git", *args], cwd=repo, input=stdin, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(
            f"repo_hygiene_ratchet: git {' '.join(args)} failed: {proc.stderr.decode()[:400]}"
        )
    return proc.stdout


def ignore_debt(repo: Path) -> list[str]:
    """Tracked paths that match the repository's own ignore rules."""
    out = _git(repo, "ls-files", "-i", "-c", "--exclude-standard", "-z")
    return sorted(p.decode() for p in out.split(b"\0") if p)


def lfs_debt(repo: Path) -> list[str]:
    """Tracked paths whose attributes route them to LFS but whose index blob is raw content."""
    tracked = [p for p in _git(repo, "ls-files", "-z").split(b"\0") if p]
    if not tracked:
        return []
    attrs = _git(repo, "check-attr", "-z", "--stdin", "filter", stdin=b"\0".join(tracked) + b"\0")
    fields = attrs.split(b"\0")
    lfs_paths = [
        fields[i].decode() for i in range(0, len(fields) - 2, 3) if fields[i + 2] == b"lfs"
    ]
    if not lfs_paths:
        return []
    query = "".join(f":{p}\n" for p in lfs_paths).encode()
    sizes = _git(repo, "cat-file", "--batch-check=%(objectsize)", stdin=query).decode().split("\n")
    debt: list[str] = []
    for path, size_text in zip(lfs_paths, sizes, strict=False):
        if not size_text.strip().isdigit():
            continue  # e.g. "missing": not a blob we can judge here
        if int(size_text) > _POINTER_MAX_BYTES:
            debt.append(path)
            continue
        blob = _git(repo, "cat-file", "-p", f":{path}")
        if not blob.startswith(_POINTER_MAGIC):
            debt.append(path)
    return sorted(debt)


def read_baseline(path: Path) -> tuple[int, bool]:
    """``(count, was_measured)``: a baseline without the provenance stamp was typed, not measured."""
    if not path.exists():
        raise SystemExit(f"repo_hygiene_ratchet: missing baseline file {path}")
    text = path.read_text()
    counts = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not counts:
        raise SystemExit(f"repo_hygiene_ratchet: no count found in {path}")
    return int(counts[0]), PROVENANCE in text


def gate(repo: Path, baseline_path: Path) -> int:
    rc = 0
    lfs = lfs_debt(repo)
    if lfs:
        print(f"❌ repo_hygiene_ratchet: {len(lfs)} LFS-routed file(s) stored as raw content:")
        for p in lfs:
            print(f"   {p}")
        print(
            "   Fix: git add --renormalize -- <paths>  (converts to pointers, no history rewrite)"
        )
        rc = 1
    else:
        print("✅ repo_hygiene_ratchet: every LFS-routed tracked file is a pointer")

    debt = ignore_debt(repo)
    baseline, measured = read_baseline(baseline_path)
    if not measured:
        print(
            f"❌ repo_hygiene_ratchet: baseline {baseline} is UNVERIFIED (no provenance stamp). "
            f"Run --update to record a measured count; the tree currently holds {len(debt)}."
        )
        return 1
    if len(debt) > baseline:
        print(
            f"❌ repo_hygiene_ratchet: {len(debt)} tracked files match .gitignore > baseline {baseline} — this change adds new ignore debt"
        )
        print("   New debt is one of these paths; untrack it (git rm --cached) or fix the rule:")
        for p in debt[:20]:
            print(f"   {p}")
        return 1
    if len(debt) < baseline:
        print(
            f"✅ repo_hygiene_ratchet: ignore debt {len(debt)} < baseline {baseline} — reduced by {baseline - len(debt)}. Lock it in: --update"
        )
    else:
        print(
            f"✅ repo_hygiene_ratchet: ignore debt {len(debt)} == baseline {baseline} (no new ignore debt)"
        )
    return rc


def update(repo: Path, baseline_path: Path) -> int:
    current = len(ignore_debt(repo))
    old, measured = read_baseline(baseline_path) if baseline_path.exists() else (None, False)
    if old is not None and measured and current > old:
        sys.stderr.write(
            f"repo_hygiene_ratchet: refusing to RAISE baseline {old} -> {current}; untrack the new debt instead.\n"
        )
        return 1
    baseline_path.write_text(f"{current}\n{PROVENANCE}\n")
    print(
        f"repo_hygiene_ratchet: baseline set to {current}"
        + (f" (was {old})" if old is not None else "")
    )
    return 0


def _fixture(tmp: Path) -> Path:
    """A repo with one tracked ignored file and one raw blob under an LFS attribute.

    The files are committed BEFORE .gitattributes exists, so no LFS filter (not even
    a globally installed ``filter.lfs.process``) can turn the raw blob into a pointer.
    """
    repo = tmp / "r"
    repo.mkdir()
    cfg = ["-c", "user.email=t@t", "-c", "user.name=t"]
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text("*.log\n")
    (repo / "tracked.log").write_text("debt\n")
    (repo / "raw.bin").write_bytes(b"\x00raw")
    _git(repo, *cfg, "add", "-f", ".gitignore", "tracked.log", "raw.bin")
    _git(repo, *cfg, "commit", "-q", "-m", "fixture")
    (repo / ".gitattributes").write_text("*.bin filter=lfs diff=lfs merge=lfs -text\n")
    _git(repo, *cfg, "add", ".gitattributes")
    _git(repo, *cfg, "commit", "-q", "-m", "attributes")
    return repo


def self_test() -> int:
    """The gate must still be able to FAIL on the two defects it exists to catch."""
    import io
    from contextlib import redirect_stdout

    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = _fixture(Path(tmp))
        baseline = Path(tmp) / "b.txt"

        baseline.write_text(f"1\n{PROVENANCE}\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gate(repo, baseline)
        hit = rc == 1 and "raw.bin" in out.getvalue()
        print(f"self-test raw-lfs-blob-fails: {'PASS' if hit else 'FAIL'}")
        ok &= hit

        _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "rm", "--cached", "-q", "raw.bin")
        _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "drop")

        baseline.write_text(f"0\n{PROVENANCE}\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gate(repo, baseline)
        hit = rc == 1 and "adds new ignore debt" in out.getvalue()
        print(f"self-test ignore-debt-above-baseline-fails: {'PASS' if hit else 'FAIL'}")
        ok &= hit

        baseline.write_text("1\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gate(repo, baseline)
        hit = rc == 1 and "UNVERIFIED" in out.getvalue()
        print(f"self-test unstamped-baseline-unverified: {'PASS' if hit else 'FAIL'}")
        ok &= hit

        baseline.write_text(f"1\n{PROVENANCE}\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gate(repo, baseline)
        hit = rc == 0
        print(f"self-test green-path: {'PASS' if hit else 'FAIL'}")
        ok &= hit

    print("self-test:", "OK" if ok else "BROKEN — this gate can no longer detect its own defects")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if "--update" in sys.argv:
        return update(REPO, BASELINE_FILE)
    return gate(REPO, BASELINE_FILE)


if __name__ == "__main__":
    sys.exit(main())
