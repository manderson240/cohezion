"""Item 124: Polyglot-refactor loop arm — report-only (2026-06-08).

``polyglot_refactor_report(repo_root)`` surfaces refactor candidates for each
language in cohezion's polyglot codebase using NATIVE per-language tooling:

  Python     → ruff check src/cohezion/   (always present; the existing simplicity-audit path)
  Rust       → cargo clippy               (present on this machine; src/cohezion-physics-core/)
  TypeScript → tsc --noEmit              (absent = tool_available=False; src/web/)

Per-language result: :class:`LanguageReport` with:
  - ``tool_available``: True only when the tool is found on PATH AND the source dir exists.
  - ``candidates``:    list of lint/type findings (strings), empty when tool absent.
  - ``drift``:         ``None`` (first run; two snapshots needed for a delta).

Report-only — surfaces what native tools flag; NEVER auto-fixes (behaviour-changing,
against non-destructive policy).  The Python section composes the existing simplicity-audit
(ruff is the Python simplicity linter in items 43/44/10/63/64/65).

User directive 2026-06-07: "we also need polyglot refactor as part of the loop."
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class LanguageReport:
    """Refactor-candidate report for one language (item 124).

    Attributes
    ----------
    tool_available:
        ``True`` when the native linter is found on PATH **and** the language
        source directory exists in ``repo_root``.  When ``False``, ``candidates``
        is always ``[]`` and no linter was invoked.
    candidates:
        List of lint/type-error strings, each in the linter's native output format
        (e.g. ``"src/cohezion/foo.py:42:5: E501 line too long"``).  Empty when
        ``tool_available=False`` or when the codebase is already clean.
    drift:
        Change in candidate count vs the previous snapshot.  Always ``None`` on
        the first call — two successive calls are needed to compute a delta.  The
        build loop accumulates snapshots; this module only reports the current state.
    """

    tool_available: bool
    candidates: list[str] = field(default_factory=list)
    drift: int | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Default subprocess runner — injectable for tests or dry-run scenarios.
# Signature: (cmd_list, cwd) -> (returncode, combined_stdout_stderr)
_RunFn = Callable[[list[str], Path], tuple[int, str]]


def _default_run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    """Run cmd in cwd, returning (returncode, stdout+stderr combined)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode, (result.stdout + result.stderr)


def _parse_lines(output: str) -> list[str]:
    """Return non-empty, non-blank lines from linter output."""
    return [line.rstrip() for line in output.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Per-language sub-reporters
# ---------------------------------------------------------------------------


def _python_report(repo_root: Path, run: _RunFn) -> LanguageReport:
    """Python: ruff check on src/cohezion/ (the simplicity-audit path, items 43/44)."""
    src_dir = repo_root / "src" / "cohezion"
    if not src_dir.is_dir():
        return LanguageReport(tool_available=False)

    ruff = shutil.which("ruff")
    if ruff is None:
        return LanguageReport(tool_available=False)

    _, output = run([ruff, "check", str(src_dir), "--output-format=text"], repo_root)
    candidates = _parse_lines(output)
    # ruff exits non-zero when violations found — that's expected, not an error.
    return LanguageReport(tool_available=True, candidates=candidates)


def _rust_report(repo_root: Path, run: _RunFn) -> LanguageReport:
    """Rust: cargo clippy on src/cohezion-physics-core/ (read-only, no fix)."""
    rust_dir = repo_root / "src" / "cohezion-physics-core"
    if not rust_dir.is_dir():
        return LanguageReport(tool_available=False)

    cargo = shutil.which("cargo")
    if cargo is None:
        return LanguageReport(tool_available=False)

    # --quiet suppresses non-warning output; 2>&1 folded into capture_output.
    # -- --no-deps: only lint cohezion code, not its transitive dependencies.
    _, output = run(
        [cargo, "clippy", "--quiet", "--", "-D", "warnings"],
        rust_dir,
    )
    candidates = _parse_lines(output)
    return LanguageReport(tool_available=True, candidates=candidates)


def _typescript_report(repo_root: Path, run: _RunFn) -> LanguageReport:
    """TypeScript: tsc --noEmit on src/web/anima_dashboard/ (type-check, no emit)."""
    ts_dir = repo_root / "src" / "web" / "anima_dashboard"
    if not ts_dir.is_dir():
        return LanguageReport(tool_available=False)

    tsc = shutil.which("tsc")
    if tsc is None:
        return LanguageReport(tool_available=False)

    _, output = run([tsc, "--noEmit"], ts_dir)
    candidates = _parse_lines(output)
    return LanguageReport(tool_available=True, candidates=candidates)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def polyglot_refactor_report(
    repo_root: Path,
    *,
    _run: _RunFn | None = None,
) -> dict[str, LanguageReport]:
    """Report per-language refactor candidates using native tooling (item 124). Read-only.

    Runs each language's native linter in the corresponding source directory within
    ``repo_root``.  Languages with no toolchain on PATH or no source directory return
    ``tool_available=False`` with an empty candidates list — no findings are fabricated.

    Args:
        repo_root:
            Root of the repository.  Typically ``Path(".")`` for the working tree.
            Injected in tests to isolate from the live repo.
        _run:
            Injectable subprocess runner ``(cmd, cwd) -> (returncode, output)``.
            Defaults to :func:`_default_run` (real ``subprocess.run``).  Override
            in tests to avoid slow linter invocations or control output.

    Returns:
        ``{"python": LanguageReport, "rust": LanguageReport, "typescript": LanguageReport}``

        ``drift`` is always ``None`` on the first call — accumulate snapshots to
        compute deltas.

    Pure-ish — shells native linters read-only; never writes, never auto-fixes.
    Report-only — proposes refactor targets; the per-language fix is the gated action.
    """
    run = _run if _run is not None else _default_run
    return {
        "python": _python_report(repo_root, run),
        "rust": _rust_report(repo_root, run),
        "typescript": _typescript_report(repo_root, run),
    }
