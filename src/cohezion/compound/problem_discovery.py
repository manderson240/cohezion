"""TIDE-style proactive problem-discovery registry (backlog item 73, 2026-06-07).

Research round 13, VERIFIED — arXiv 2606.04743 (TIDE: template + iterative discovery). cohezion
has many scattered DETERMINISTIC, $0 audit instruments (complexity/nesting/passthrough/
exec-sandbox), each run ad-hoc. This unifies them under TIDE's framing:

  - the *thought-templates* are the existing instruments (a ``ProblemTemplate`` = a problem_class
    + the instrument that finds it + a ``key`` that gives each finding a stable id),
  - *iterative discovery conditioned on known* is ``exclude_known``: a finding already actioned
    (its id in ``exclude_known``) is SUPPRESSED so it does not re-surface every scan.

``discover_problems`` runs the registry over ``paths`` and returns the NOVEL findings. The
instruments are deterministic and read-only; the UNIFICATION + condition-on-known dedup is the new
bit. Report-only, pure (no LLM, no writes). The registry is injectable (stub templates in tests);
``default_templates()`` wires the real audit instruments.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProblemTemplate:
    """One audit instrument as a TIDE template: its problem_class + finder + stable-id key."""

    problem_class: str
    instrument: Callable[[list[Path]], list]  # paths -> findings (read-only audit)
    # a finding (heterogeneous across instruments: tuple/str/dataclass) -> its stable id.
    key: Callable[[Any], str]


@dataclass(frozen=True)
class Problem:
    """A discovered problem: its class + a stable ``{problem_class}:{finding}`` id."""

    problem_class: str
    finding_id: str


def discover_problems(
    paths: Iterable[Path],
    *,
    templates: list[ProblemTemplate] | None = None,
    exclude_known: frozenset[str] | set[str] = frozenset(),
) -> list[Problem]:
    """Run the template registry over ``paths``; return NOVEL problems (TIDE iterative discovery).

    Each template's instrument is run over the file list; every finding becomes a
    ``{problem_class}:{key(finding)}`` id. A finding whose id is in ``exclude_known`` is SUPPRESSED
    (already actioned). ``templates=None`` uses :func:`default_templates` (the real instruments);
    ``templates=[]`` scans nothing → ``[]``. Deterministic, pure (no writes, no LLM).
    """
    tmpls = default_templates() if templates is None else templates
    files = list(paths)
    out: list[Problem] = []
    for tmpl in tmpls:
        for finding in tmpl.instrument(files):
            fid = f"{tmpl.problem_class}:{tmpl.key(finding)}"
            if fid not in exclude_known:
                out.append(Problem(problem_class=tmpl.problem_class, finding_id=fid))
    return out


@dataclass(frozen=True)
class ProblemDelta:
    """The change between two TIDE problem scans: what was resolved vs newly introduced."""

    resolved: list[Problem]  # in the earlier scan, absent from the later → fixed
    introduced: list[Problem]  # in the later scan, absent from the earlier → new debt


def discovered_problem_delta(before: Iterable[Problem], after: Iterable[Problem]) -> ProblemDelta:
    """Delta between two problem scans (backlog item 127), compared by ``finding_id``.

    A problem in ``before`` but not ``after`` is RESOLVED (fixed since the last scan); one in
    ``after`` but not ``before`` is INTRODUCED (new debt). A problem present in BOTH is unchanged
    and appears in NEITHER list. This is what makes :func:`discover_problems` ITERATIVE — it
    measures the discovery loop's progress between ticks (mirrors
    ``DegradationDetector.diff_snapshots`` / the item-39/57/74/81 pure-delta family). Pure,
    report-only (no I/O); matching is by ``finding_id`` only.
    """
    before_by_id = {p.finding_id: p for p in before}
    after_by_id = {p.finding_id: p for p in after}
    resolved = [p for fid, p in before_by_id.items() if fid not in after_by_id]
    introduced = [p for fid, p in after_by_id.items() if fid not in before_by_id]
    return ProblemDelta(resolved=resolved, introduced=introduced)


def default_templates() -> list[ProblemTemplate]:
    """The real scattered audit instruments, unified as TIDE templates (lazy import — pay only
    when the default registry is actually used). Each ``key`` extracts a finding's stable id."""
    from cohezion.compound.exec_sandbox_audit import unsandboxed_exec_paths
    from cohezion.compound.simplicity_audit import (
        complexity_outliers,
        needless_passthroughs,
        nesting_outliers,
        passthrough_functions,
    )

    return [
        ProblemTemplate("complexity_outlier", complexity_outliers, lambda f: str(f[0])),
        ProblemTemplate("nesting_outlier", nesting_outliers, lambda f: str(f[0])),
        ProblemTemplate("passthrough_function", passthrough_functions, str),
        ProblemTemplate("needless_passthrough", needless_passthroughs, lambda f: f.qualified_name),
        ProblemTemplate(
            "unsandboxed_exec", unsandboxed_exec_paths, lambda f: f"{f.location}:{f.sink}"
        ),
    ]
