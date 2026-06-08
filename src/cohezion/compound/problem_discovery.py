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


def default_templates() -> list[ProblemTemplate]:
    """The real scattered audit instruments, unified as TIDE templates (lazy import — pay only
    when the default registry is actually used). Each ``key`` extracts a finding's stable id."""
    from cohezion.compound.exec_sandbox_audit import unsandboxed_exec_paths
    from cohezion.compound.simplicity_audit import (
        boolean_flag_params,
        complexity_outliers,
        compound_smells,
        eager_log_fstrings,
        long_functions,
        long_parameter_lists,
        mutable_default_args,
        needless_passthroughs,
        nesting_outliers,
        passthrough_functions,
        production_asserts,
        silent_except_swallows,
        stealth_bare_excepts,
    )

    return [
        ProblemTemplate("complexity_outlier", complexity_outliers, lambda f: str(f[0])),
        ProblemTemplate("nesting_outlier", nesting_outliers, lambda f: str(f[0])),
        # Item 157: wire long_functions + long_parameter_lists as standalone templates.
        # Both return list[tuple[str, int]] as (qualified_name, magnitude) — key is str(f[0]).
        ProblemTemplate("long_function", long_functions, lambda f: str(f[0])),
        ProblemTemplate("long_parameter_list", long_parameter_lists, lambda f: str(f[0])),
        ProblemTemplate("boolean_flag_params", boolean_flag_params, lambda f: str(f[0])),
        ProblemTemplate("mutable_default_args", mutable_default_args, lambda f: str(f[0])),
        ProblemTemplate("production_assert", production_asserts, lambda f: f"{f[0]}:{f[1]}"),
        ProblemTemplate("eager_log_fstring", eager_log_fstrings, lambda f: f"{f[0]}:{f[1]}"),
        ProblemTemplate("passthrough_function", passthrough_functions, str),
        ProblemTemplate("needless_passthrough", needless_passthroughs, lambda f: f.qualified_name),
        ProblemTemplate(
            "unsandboxed_exec", unsandboxed_exec_paths, lambda f: f"{f.location}:{f.sink}"
        ),
        # Item 155: wire items 65 + 110 instruments into TIDE (closing wiring gap).
        # Both return list[tuple[str, str]] as (location, kind) — same key shape as production_assert.
        ProblemTemplate("stealth_bare_except", stealth_bare_excepts, lambda f: f"{f[0]}:{f[1]}"),
        ProblemTemplate(
            "silent_except_swallow", silent_except_swallows, lambda f: f"{f[0]}:{f[1]}"
        ),
        # Item 156: wire compound_smells (item 105) into TIDE — multi-axis worst-offenders.
        # CompoundSmell.qualified_name is the stable id (same pattern as needless_passthrough).
        ProblemTemplate("compound_smell", compound_smells, lambda f: f.qualified_name),
    ]


def problem_count_by_class(problems: list[Problem]) -> dict[str, int]:
    """Count TIDE findings by ``problem_class`` — item 160.

    A pure frequency fold over the output of :func:`discover_problems`.  Returns
    ``{problem_class: count}`` for every class present in *problems*.  Classes
    absent from *problems* are absent from the result (never present with a zero
    value — this is NOT a histogram over all known template classes).

    Args:
        problems:
            A list of :class:`Problem` instances, typically the return value of
            :func:`discover_problems`.  Empty list → empty dict.

    Returns:
        ``{problem_class: count}`` mapping.  The values are positive integers;
        every key appeared at least once in *problems*.

    Pure (no I/O, no SurrealDB).  Composes with ``loop_telemetry`` (item 25) to
    add smell-density-per-class to the loop health report.
    """
    result: dict[str, int] = {}
    for problem in problems:
        result[problem.problem_class] = result.get(problem.problem_class, 0) + 1
    return result


def top_problem_classes(
    problems: list[Problem],
    *,
    n: int = 5,
) -> list[tuple[str, int]]:
    """Return the top-N problem classes by finding count — item 161.

    Ranks the output of :func:`problem_count_by_class` in descending order of
    count, with ties broken alphabetically by class name for determinism.
    Returns at most *n* entries; if fewer than *n* distinct classes exist in
    *problems*, all classes are returned (no error, no padding).

    Args:
        problems:
            A list of :class:`Problem` instances, typically the return value of
            :func:`discover_problems`.  Empty list → empty list.
        n:
            Maximum number of entries to return.  Must be ≥ 1.  If *n* ≥ the
            number of distinct classes in *problems*, all classes are returned.

    Returns:
        A list of ``(problem_class, count)`` pairs, sorted descending by count
        then ascending by class name for equal counts.  Length ≤ *n*.

    Pure (no I/O, no SurrealDB).  Composes with :func:`problem_count_by_class`.
    """
    counts = problem_count_by_class(problems)
    # Sort key: primary = descending count (-count), secondary = ascending name
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]


@dataclass(frozen=True)
class ProblemSummary:
    """Typed summary envelope over a :func:`discover_problems` result — item 163.

    Composes :func:`problem_count_by_class` (item 160) and
    :func:`top_problem_classes` (item 161) into a single immutable struct for
    the loop health report.

    Attributes:
        total:       Raw ``len(problems)`` — the number of findings in the list.
        by_class:    ``{problem_class: count}`` mapping from
                     :func:`problem_count_by_class`.
        top_classes: Top-N ``(problem_class, count)`` pairs from
                     :func:`top_problem_classes` (default ``n=5``).
        has_problems: ``True`` when *total* > 0.

    Frozen (immutable).  Construct via :func:`problem_summary`.
    """

    total: int
    by_class: dict[str, int]
    top_classes: list[tuple[str, int]]
    has_problems: bool


def problem_summary(problems: list[Problem]) -> ProblemSummary:
    """Build a :class:`ProblemSummary` from a TIDE findings list — item 163.

    Composes :func:`problem_count_by_class` and :func:`top_problem_classes`
    into a single typed summary struct suitable for the loop health report.

    Args:
        problems:
            A list of :class:`Problem` instances, typically the return value of
            :func:`discover_problems`.  Empty list → zero-total summary.

    Returns:
        A frozen :class:`ProblemSummary` with:
        - ``total`` = ``len(problems)`` (raw list length, NOT re-derived from counts)
        - ``by_class`` = :func:`problem_count_by_class` result
        - ``top_classes`` = :func:`top_problem_classes` result (default n=5)
        - ``has_problems`` = ``total > 0``

    Pure (no I/O, no SurrealDB).
    """
    total = len(problems)
    by_class = problem_count_by_class(problems)
    top = top_problem_classes(problems)
    return ProblemSummary(
        total=total,
        by_class=by_class,
        top_classes=top,
        has_problems=total > 0,
    )


def discover_and_summarize(
    paths: Iterable[Path],
    *,
    templates: list[ProblemTemplate] | None = None,
    exclude_known: frozenset[str] | set[str] = frozenset(),
) -> ProblemSummary:
    """Run TIDE discovery and summarize in one call — item 165.

    Composes :func:`discover_problems` (item 73) and :func:`problem_summary`
    (item 163) into a single convenience call.  All parameters are forwarded
    to :func:`discover_problems` unchanged; the resulting findings list is
    immediately wrapped by :func:`problem_summary`.

    A single discovery pass is performed — the same ``problems`` list is
    passed directly to ``problem_summary``, so ``summary.total`` is
    guaranteed to equal ``len(discover_problems(same_args))``.

    Args:
        paths:
            Iterable of :class:`~pathlib.Path` objects to audit.
        templates:
            Optional list of :class:`ProblemTemplate` instances.  ``None``
            (default) uses :func:`default_templates`.  ``[]`` → no audit
            → zero-total summary.
        exclude_known:
            Set of finding ids to suppress (already-actioned findings).
            Forwarded verbatim to :func:`discover_problems`.

    Returns:
        A frozen :class:`ProblemSummary` wrapping the TIDE findings.

    Pure (no I/O beyond what the instruments perform).  No SurrealDB.
    """
    problems = discover_problems(paths, templates=templates, exclude_known=exclude_known)
    return problem_summary(problems)


def discover_and_summarize_for(
    paths: Iterable[Path],
    *,
    templates: list[ProblemTemplate] | None = None,
    exclude_known: frozenset[str] | set[str] = frozenset(),
    problem_classes: set[str] | frozenset[str] | None = None,
) -> ProblemSummary:
    """Run TIDE discovery then summarize a filtered class subset — item 167.

    Extends :func:`discover_and_summarize` with an optional post-discovery class
    filter.  All instruments run on the full path list; only the findings whose
    ``problem_class`` is in *problem_classes* are passed to
    :func:`problem_summary`.  When *problem_classes* is ``None`` the call is
    identical to :func:`discover_and_summarize`.

    Filtering happens AFTER discovery, not before — this is intentional.
    Filtering the template list before running would skip instruments, which
    could produce misleading counts when ``exclude_known`` is also in play.

    Args:
        paths:
            Iterable of :class:`~pathlib.Path` objects to audit.
        templates:
            Optional list of :class:`ProblemTemplate` instances.  ``None``
            (default) uses :func:`default_templates`.  ``[]`` → no audit.
        exclude_known:
            Set of finding ids to suppress (already-actioned findings).
            Forwarded verbatim to :func:`discover_problems`.
        problem_classes:
            Optional set of ``problem_class`` strings to keep.  ``None``
            → no filtering (all findings passed through).  An empty set
            ``set()`` → total=0 (no classes selected).

    Returns:
        A frozen :class:`ProblemSummary` for the filtered findings.

    Pure (no I/O beyond what the instruments perform).  No SurrealDB.
    """
    problems = discover_problems(paths, templates=templates, exclude_known=exclude_known)
    if problem_classes is not None:
        problems = [p for p in problems if p.problem_class in problem_classes]
    return problem_summary(problems)


def default_template_classes() -> frozenset[str]:
    """Return the exact set of ``problem_class`` names in :func:`default_templates` — item 158.

    A structural meta-check on the TIDE wiring: callers (harness, CI) can assert
    ``len(default_template_classes()) >= 14`` without importing the heavy audit
    instruments (this function still calls ``default_templates`` internally, but
    the *count / class-name invariant* is cheap to assert at test-collection time).

    Returns:
        An immutable :class:`frozenset` of the ``problem_class`` strings from
        every :class:`ProblemTemplate` in the default registry.

    Pure (reads the template list; does not run any audit).  Zero-cost for callers
    that only need the count or class-name membership check.
    """
    return frozenset(t.problem_class for t in default_templates())
