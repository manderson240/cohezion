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

import math
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
    severity: str = ""


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


def top_problem_classes_excluding(
    problems: list[Problem],
    *,
    exclude_classes: frozenset[str] | set[str] = frozenset(),
    n: int = 5,
) -> list[tuple[str, int]]:
    """Return the top-N problem classes with an exclusion guard — item 169.

    Extends :func:`top_problem_classes` with an optional set of class names to
    omit from the result.  Exclusion happens BEFORE ranking, so *n* refers to
    the top-n from the *non-excluded* classes only.  Tie-breaking is identical
    to :func:`top_problem_classes` (descending count, ascending class name).

    When *exclude_classes* is empty, the result is identical to
    :func:`top_problem_classes` for the same *problems* and *n*.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → empty list.
        exclude_classes:
            Set of ``problem_class`` strings to omit from the ranking result.
            ``frozenset()`` (default) → no exclusion.
        n:
            Maximum number of entries to return.

    Returns:
        A list of ``(problem_class, count)`` pairs, sorted descending by count
        then ascending by class name.  Classes in *exclude_classes* are absent.
        Length ≤ *n*.

    Pure (no I/O, no SurrealDB).
    """
    counts = problem_count_by_class(problems)
    # Exclude before ranking
    filtered = {cls: cnt for cls, cnt in counts.items() if cls not in exclude_classes}
    ranked = sorted(filtered.items(), key=lambda item: (-item[1], item[0]))
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


def discover_and_summarize_excluding(
    paths: Iterable[Path],
    *,
    templates: list[ProblemTemplate] | None = None,
    exclude_known: frozenset[str] | set[str] = frozenset(),
    exclude_classes: frozenset[str] | set[str] = frozenset(),
    n: int = 5,
) -> ProblemSummary:
    """Run TIDE discovery, summarize, then rebuild top_classes with an exclusion guard — item 171.

    Composes :func:`discover_and_summarize` (item 165) with
    :func:`top_problem_classes_excluding` (item 169) so callers can suppress a
    known-noisy class from the ``top_classes`` ranking without losing any information
    from ``total`` or ``by_class``.

    Exclusion happens ONLY on ``top_classes`` — ``total`` and ``by_class`` always
    reflect ALL findings (the ``problem_classes`` filter in
    :func:`discover_and_summarize_for` is intentionally different and more
    aggressive).

    Args:
        paths:
            Iterable of :class:`~pathlib.Path` objects to audit.
        templates:
            Optional list of :class:`ProblemTemplate` instances.  ``None``
            (default) uses :func:`default_templates`.  ``[]`` → no audit.
        exclude_known:
            Set of finding ids to suppress (already-actioned).
            Forwarded verbatim to :func:`discover_and_summarize`.
        exclude_classes:
            Set of ``problem_class`` strings to omit from the ``top_classes``
            ranking result.  Does NOT affect ``total`` or ``by_class``.
            ``frozenset()`` (default) → no exclusion (result identical to
            :func:`discover_and_summarize`).
        n:
            Maximum number of entries in the returned ``top_classes`` list.

    Returns:
        A frozen :class:`ProblemSummary` where:
        - ``total`` = total finding count (unaffected by exclusion).
        - ``by_class`` = per-class counts (unaffected by exclusion).
        - ``top_classes`` = top-n from the NON-excluded classes.
        - ``has_problems`` = ``total > 0``.

    Pure (no I/O beyond what the instruments perform).  No SurrealDB.
    """
    base = discover_and_summarize(paths, templates=templates, exclude_known=exclude_known)
    if not exclude_classes:
        return base
    # Rebuild top_classes with exclusion; total + by_class are preserved verbatim.
    filtered_top = top_problem_classes_excluding(
        # Re-derive problems list from by_class to avoid a second full scan.
        # We need a list[Problem]; rebuild from by_class counts (ordering is irrelevant).
        [
            Problem(problem_class=cls, finding_id=f"{cls}:{i}")
            for cls, count in base.by_class.items()
            for i in range(count)
        ],
        exclude_classes=exclude_classes,
        n=n,
    )
    return ProblemSummary(
        total=base.total,
        by_class=base.by_class,
        top_classes=filtered_top,
        has_problems=base.has_problems,
    )


@dataclass(frozen=True)
class ProblemDiff:
    """Delta between two TIDE discovery scans — item 172.

    Classifies finding ids from two :func:`discover_problems` result lists into
    three partitions:

    - ``added``    — ids present in *after* but NOT in *before* (new smells).
    - ``resolved`` — ids present in *before* but NOT in *after* (fixed smells).
    - ``stable``   — ids present in BOTH before and after (unchanged smells).

    Every finding id appears in exactly ONE partition.  The union
    ``set(added) | set(resolved) | set(stable)`` == the union of all ids in
    both lists.

    Frozen (immutable).  Construct via :func:`problem_diff`.
    """

    added: list[str]
    resolved: list[str]
    stable: list[str]


def problem_diff(before: list[Problem], after: list[Problem]) -> ProblemDiff:
    """Compare two TIDE discovery results and classify findings — item 172.

    Pure set-difference fold over the ``finding_id`` keys of *before* and
    *after*.  Each id falls into exactly one of three partitions:

    - ``added``    — in *after* but NOT in *before*.
    - ``resolved`` — in *before* but NOT in *after*.
    - ``stable``   — in both *before* and *after*.

    Ordering within each partition is deterministic: sorted by ``finding_id``
    for stable output across runs.

    Args:
        before:
            Finding list from the earlier scan (output of :func:`discover_problems`).
        after:
            Finding list from the later scan.

    Returns:
        A frozen :class:`ProblemDiff` with the three partitions as ``list[str]``
        of ``finding_id`` values.

    Pure (no I/O, no SurrealDB).
    """
    before_ids = {p.finding_id for p in before}
    after_ids = {p.finding_id for p in after}
    added = sorted(after_ids - before_ids)
    resolved = sorted(before_ids - after_ids)
    stable = sorted(before_ids & after_ids)
    return ProblemDiff(added=added, resolved=resolved, stable=stable)


def problem_diff_summary(diff: ProblemDiff) -> str:
    """Return a compact human-readable audit-log string for *diff* — item 173.

    Lists added and resolved finding ids in sorted order.  When there are
    neither added nor resolved ids (an all-stable or empty diff), returns
    exactly ``"No changes."``.  Stable ids are never mentioned (they are the
    unchanged background, not the signal).

    Mirrors :func:`cohezion.inference.tournament_deposit.diff_summary` (item 166)
    but operates on :class:`ProblemDiff` / code-smell finding ids.

    Args:
        diff:
            A :class:`ProblemDiff` from :func:`problem_diff`.

    Returns:
        A newline-joined string of labelled findings, or ``"No changes."``
        when *diff* has no added or resolved ids.

    Pure (no I/O, no SurrealDB).
    """
    lines: list[str] = []
    for fid in diff.added:
        lines.append(f"added:    {fid}")
    for fid in diff.resolved:
        lines.append(f"resolved: {fid}")
    if not lines:
        return "No changes."
    return "\n".join(lines)


def problem_diff_pipeline(
    paths_before: Iterable[Path],
    paths_after: Iterable[Path],
    *,
    templates: list[ProblemTemplate] | None = None,
    exclude_known_before: frozenset[str] | set[str] = frozenset(),
    exclude_known_after: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[Problem], list[Problem], ProblemDiff, str]:
    """End-to-end two-scan TIDE delta pipeline — item 174.

    Runs :func:`discover_problems` on both path sets, calls :func:`problem_diff`,
    calls :func:`problem_diff_summary`, and returns all four artifacts as a
    4-tuple ``(before_problems, after_problems, diff, summary)``.

    Mirrors :func:`cohezion.inference.tournament_deposit.snapshot_pipeline`
    (item 168) but for code-smell TIDE discovery instead of tournament snapshots.

    When *paths_before* and *paths_after* resolve to the same findings (same
    templates + same paths + same exclude_known), the diff is all-stable and
    the summary is ``"No changes."``.

    Args:
        paths_before:
            Iterable of :class:`~pathlib.Path` objects for the BEFORE scan.
        paths_after:
            Iterable of :class:`~pathlib.Path` objects for the AFTER scan.
        templates:
            Optional list of :class:`ProblemTemplate` instances.  ``None``
            (default) uses :func:`default_templates`.  ``[]`` → no audit.
        exclude_known_before:
            Set of finding ids to suppress from the BEFORE scan.
        exclude_known_after:
            Set of finding ids to suppress from the AFTER scan.

    Returns:
        ``(before_problems, after_problems, diff, summary)`` where:
        - *before_problems* = :func:`discover_problems` on *paths_before*.
        - *after_problems*  = :func:`discover_problems` on *paths_after*.
        - *diff*    = :class:`ProblemDiff` from :func:`problem_diff`.
        - *summary* = ``str`` from :func:`problem_diff_summary`.

    Pure (no I/O beyond what the instruments perform).  No SurrealDB.
    """
    before_problems = discover_problems(
        paths_before, templates=templates, exclude_known=exclude_known_before
    )
    after_problems = discover_problems(
        paths_after, templates=templates, exclude_known=exclude_known_after
    )
    diff = problem_diff(before_problems, after_problems)
    summary = problem_diff_summary(diff)
    return (before_problems, after_problems, diff, summary)


def filter_problems(
    problems: list[Problem],
    predicate: Callable[[Problem], bool],
) -> list[Problem]:
    """Filter a TIDE finding list with a caller-supplied predicate — item 175.

    Returns the sublist of *problems* for which *predicate* returns ``True``.
    Preserves order.  The predicate receives each :class:`Problem` instance
    (not the raw finding id string).

    Args:
        problems:
            A list of :class:`Problem` instances (e.g., from
            :func:`discover_problems`).  Empty list → ``[]``.
        predicate:
            A callable that accepts one :class:`Problem` and returns ``bool``.
            Called once per element; order is preserved for matching elements.

    Returns:
        A new list of :class:`Problem` instances for which *predicate* is
        ``True``.  May be empty.  Never raises on empty input.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if predicate(p)]


def group_problems_by_class(problems: list[Problem]) -> dict[str, list[Problem]]:
    """Group a TIDE finding list by ``problem_class`` — item 176.

    Structural complement of :func:`problem_count_by_class` (item 160): where
    that function returns ``{problem_class: count}``, this one returns
    ``{problem_class: [Problem, ...]}``.  Callers that need the actual
    ``finding_id`` values per class (e.g. the diff pipeline, CI gates) should
    use this function; callers that only need counts should use
    :func:`problem_count_by_class`.

    Finding order within each group is the same as the input list order.
    Classes absent from *problems* are absent from the result.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``{}``.

    Returns:
        A ``dict`` mapping each ``problem_class`` to the list of
        :class:`Problem` instances of that class, in input order.

    Pure (no I/O, no SurrealDB).
    """
    result: dict[str, list[Problem]] = {}
    for p in problems:
        if p.problem_class not in result:
            result[p.problem_class] = []
        result[p.problem_class].append(p)
    return result


def most_frequent_problem_class(problems: list[Problem]) -> str | None:
    """Return the ``problem_class`` with the highest finding count — item 177.

    Convenience accessor composing :func:`problem_count_by_class` with an
    ``argmax`` reduction.  Useful as a single-call "what is the worst smell
    right now?" query for loop health dashboards.

    Ties are broken alphabetically (ascending class name) for determinism.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``None``.

    Returns:
        The ``problem_class`` string with the highest count, or ``None``
        when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    counts = problem_count_by_class(problems)
    if not counts:
        return None
    # Sort: descending count (-count), ascending class name for tie-break; return first.
    ranked = sorted(counts, key=lambda cls: (-counts[cls], cls))
    return ranked[0]


def has_problem_class(problems: list[Problem], problem_class: str) -> bool:
    """Return ``True`` if any finding belongs to *problem_class* — item 178.

    Convenience presence check composing naturally with :func:`discover_problems`
    and :func:`filter_problems`.  Useful as a CI gate: ``assert not
    has_problem_class(problems, "complexity_outlier")``.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``False``.
        problem_class:
            The exact ``problem_class`` string to look for.

    Returns:
        ``True`` if at least one finding has a matching ``problem_class``;
        ``False`` otherwise (including when *problems* is empty).

    Pure (no I/O, no SurrealDB).
    """
    return any(p.problem_class == problem_class for p in problems)


def has_any_problem_class(problems: list[Problem], classes: frozenset[str]) -> bool:
    """Return ``True`` if any finding belongs to at least one class in *classes* — item 179.

    Multi-class generalisation of :func:`has_problem_class`.  Enables composite
    CI gates::

        assert not has_any_problem_class(findings, frozenset({"production_assert", "complexity_outlier"}))

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``False``.
        classes:
            A :class:`frozenset` of ``problem_class`` strings.  Empty set →
            ``False`` (nothing to match against).

    Returns:
        ``True`` if at least one finding has a ``problem_class`` that is a
        member of *classes*; ``False`` otherwise (including when *problems* or
        *classes* is empty).

    Pure (no I/O, no SurrealDB).
    """
    if not classes:
        return False
    return any(p.problem_class in classes for p in problems)


def assert_no_duplicate_finding_ids(problems: list[Problem]) -> None:
    """Raise if any ``finding_id`` appears more than once — item 180.

    Structural integrity guard for finding lists.  Prevents silent data
    corruption when two templates emit overlapping IDs and downstream
    diff/group logic silently deduplicates.

    All duplicate IDs are reported in a single :class:`AssertionError` so a
    single CI run surfaces every gap (exhaustive, not fail-fast).

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → no-op.

    Raises:
        AssertionError: If one or more ``finding_id`` values appear more than
            once.  The message lists ALL duplicate IDs.

    Pure (no I/O, no SurrealDB).
    """
    from collections import Counter

    counts = Counter(p.finding_id for p in problems)
    duplicates = sorted(fid for fid, n in counts.items() if n > 1)
    if duplicates:
        raise AssertionError(
            f"assert_no_duplicate_finding_ids: duplicate finding_id values detected: {duplicates}"
        )


def assert_class_counts_under(problems: list[Problem], thresholds: dict[str, int]) -> None:
    """Raise if any monitored class exceeds its count threshold — item 181.

    CI ratchet guard.  Once a class is driven below a threshold, this guard
    locks the improvement in::

        assert_class_counts_under(findings, {"complexity_outlier": 5})

    Classes absent from *thresholds* are ignored entirely.  All violations
    are reported in a single :class:`AssertionError` (exhaustive, not
    fail-fast).

    Args:
        problems:
            A list of :class:`Problem` instances.
        thresholds:
            ``{problem_class: max_allowed_count}``.  Empty dict → no-op.

    Raises:
        AssertionError: If one or more monitored classes exceed their
            threshold.  The message lists ALL violating classes with their
            actual count vs. the threshold.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return
    counts = problem_count_by_class(problems)
    violations = sorted(cls for cls, limit in thresholds.items() if counts.get(cls, 0) > limit)
    if violations:
        detail = ", ".join(
            f"{cls}={counts.get(cls, 0)} (limit {thresholds[cls]})" for cls in violations
        )
        raise AssertionError(f"assert_class_counts_under: threshold exceeded — {detail}")


def sorted_finding_ids(problems: list[Problem]) -> list[str]:
    """Return a sorted list of all ``finding_id`` values — item 182.

    Deterministic snapshot accessor.  Enables stable snapshot assertions::

        assert sorted_finding_ids(findings) == expected_ids

    Duplicates are preserved (not deduplicated) — if two findings share an
    ID, both appear in the result.  Callers that want uniqueness enforcement
    should first run :func:`assert_no_duplicate_finding_ids`.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.

    Returns:
        A lexicographically sorted list of ``finding_id`` strings, length
        equal to ``len(problems)``.

    Pure (no I/O, no SurrealDB).
    """
    return sorted(p.finding_id for p in problems)


def rename_problem_class(problems: list[Problem], old_class: str, new_class: str) -> list[Problem]:
    """Return a new list with every matching ``problem_class`` renamed — item 183.

    Safe, non-destructive rename.  Findings whose ``problem_class`` equals
    *old_class* are replaced with a new :class:`Problem` carrying *new_class*;
    all other findings are returned as-is.  ``finding_id`` values are **not**
    rewritten — IDs remain stable across the rename so downstream diffs and
    caches are unaffected.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        old_class:
            The ``problem_class`` value to replace.
        new_class:
            The replacement ``problem_class`` value.

    Returns:
        A new list of :class:`Problem` instances; length equals
        ``len(problems)``.  The input list is not mutated.

    Pure (no I/O, no SurrealDB).
    """
    return [
        Problem(problem_class=new_class, finding_id=p.finding_id)
        if p.problem_class == old_class
        else p
        for p in problems
    ]


def present_problem_classes(problems: list[Problem], classes: frozenset[str]) -> frozenset[str]:
    """Return the subset of *classes* that appear at least once in *problems* — item 184.

    Watchlist intersection query.  Answers "which of these N classes fired?" rather
    than "what classes exist in the findings?" (which would be all distinct classes,
    not just those in the watchlist)::

        fired = present_problem_classes(findings, frozenset({"production_assert", "complexity_outlier"}))

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``frozenset()``.
        classes:
            Watchlist of ``problem_class`` strings to query.  Empty →
            ``frozenset()``.

    Returns:
        A :class:`frozenset` containing exactly those members of *classes* that
        appear at least once in *problems*.  Always a subset of *classes*.

    Pure (no I/O, no SurrealDB).
    """
    if not classes:
        return frozenset()
    present = {p.problem_class for p in problems}
    return frozenset(classes & present)


def deduplicate_problems(problems: list[Problem]) -> list[Problem]:
    """Return a new list with duplicate ``finding_id`` values removed — item 185.

    Keeps the FIRST occurrence of each ``finding_id``; subsequent duplicates
    are dropped.  Insertion order is preserved for the surviving elements.

    Enables safe merge of two overlapping discovery runs::

        combined = deduplicate_problems(run_a + run_b)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.

    Returns:
        A new list of :class:`Problem` instances, length ≤ ``len(problems)``.
        The input list is not mutated.

    Pure (no I/O, no SurrealDB).
    """
    seen: set[str] = set()
    result: list[Problem] = []
    for p in problems:
        if p.finding_id not in seen:
            seen.add(p.finding_id)
            result.append(p)
    return result


def merge_problems(a: list[Problem], b: list[Problem]) -> list[Problem]:
    """Return an order-preserving union of two finding lists — item 186.

    All findings from *a* appear first, then findings from *b* whose
    ``finding_id`` was not already present in *a*.  Equivalent to
    ``deduplicate_problems(a + b)`` but documents the merge semantics
    explicitly.

    Enables parallel scanning::

        merged = merge_problems(run_a, run_b)

    Args:
        a: First (higher-priority) finding list.
        b: Second finding list.  Findings whose ID already appears in *a*
           are dropped.

    Returns:
        A new list of :class:`Problem` instances; length ≤
        ``len(a) + len(b)``.  Neither input list is mutated.

    Pure (no I/O, no SurrealDB).
    """
    return deduplicate_problems(a + b)


def count_problems(problems: list[Problem]) -> int:
    """Return the total finding count for a problem list — item 187.

    Names the concept so CI scripts write ``count_problems(findings) > threshold``
    rather than ``len(findings) > threshold``, making intent explicit.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``0``.

    Returns:
        The total number of findings (``len(problems)``).

    Pure (no I/O, no SurrealDB).
    """
    return len(problems)


def exclude_problems(
    problems: list[Problem],
    exclude_ids: frozenset[str],
) -> list[Problem]:
    """Return a new list with findings in *exclude_ids* removed — item 188.

    Post-hoc counterpart to the ``exclude_known`` parameter in
    :func:`discover_problems`.  Enables suppression after a scan::

        novel = exclude_problems(all_findings, previously_actioned_ids)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        exclude_ids:
            A :class:`frozenset` of ``finding_id`` strings to suppress.
            Empty set → all findings returned unchanged.

    Returns:
        A new list containing every finding whose ``finding_id`` is NOT in
        *exclude_ids*.  Insertion order is preserved.  The input list is not
        mutated.

    Pure (no I/O, no SurrealDB).
    """
    if not exclude_ids:
        return list(problems)
    return [p for p in problems if p.finding_id not in exclude_ids]


def finding_ids(problems: list[Problem]) -> list[str]:
    """Return finding_id values in insertion order — item 189.

    Named accessor that avoids inline comprehensions at call sites::

        frozenset(finding_ids(actioned))  # vs frozenset(p.finding_id for p in actioned)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.

    Returns:
        A list of ``finding_id`` strings in the same order as *problems*.
        Duplicates are preserved (no deduplication).

    Pure (no I/O, no SurrealDB).
    """
    return [p.finding_id for p in problems]


def problem_classes(problems: list[Problem]) -> list[str]:
    """Return ``problem_class`` values in insertion order — item 190.

    Insertion-order class extraction with duplicates preserved::

        set(problem_classes(findings))      # distinct class names
        Counter(problem_classes(findings))  # alternative to problem_count_by_class

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.

    Returns:
        A list of ``problem_class`` strings; length equals ``len(problems)``.
        Insertion order is preserved; duplicates are NOT deduplicated.

    Pure (no I/O, no SurrealDB).
    """
    return [p.problem_class for p in problems]


def unique_problem_classes(problems: list[Problem]) -> frozenset[str]:
    """Return the distinct ``problem_class`` values as a frozenset — item 191.

    Completes the TIDE accessor trio:

    * :func:`finding_ids`          — IDs in insertion order
    * :func:`problem_classes`      — class labels in insertion order
    * :func:`unique_problem_classes` — distinct-class frozenset (this function)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``frozenset()``.

    Returns:
        A :class:`frozenset` of the distinct ``problem_class`` strings.
        Hashable and immutable — suitable as a dict key or for set algebra.
        Empty list → ``frozenset()``.

    Pure (no I/O, no SurrealDB).
    """
    return frozenset(p.problem_class for p in problems)


def filter_by_class(
    problems: list[Problem],
    keep_classes: frozenset[str],
) -> list[Problem]:
    """Return only findings whose ``problem_class`` is in *keep_classes* — item 192.

    The class-domain positive dual of :func:`exclude_problems` (which removes
    by finding ID).  This function KEEPS by class::

        filter_by_class(findings, frozenset({"complexity_outlier"}))

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        keep_classes:
            A :class:`frozenset` of ``problem_class`` strings to retain.
            Empty frozenset → ``[]`` (empty set matches nothing).

    Returns:
        A new list of findings whose ``problem_class`` is in *keep_classes*,
        preserving insertion order.  Empty if nothing matches.

    Pure (no I/O, no SurrealDB).
    """
    if not keep_classes:
        return []
    return [p for p in problems if p.problem_class in keep_classes]


def partition_problems_by_class(
    problems: list[Problem],
    target_classes: frozenset[str],
) -> tuple[list[Problem], list[Problem]]:
    """Split *problems* into ``(matched, rest)`` in a single pass — item 193.

    Returns a two-tuple where the first element contains all findings whose
    ``problem_class`` is in *target_classes* and the second contains all others.
    Both lists preserve the original insertion order.  Empty *target_classes*
    → ``([], list(problems))``.  Pure; no I/O.

    Avoids two separate filtering passes for callers that need both halves::

        matched, rest = partition_problems_by_class(
            findings, frozenset({"complexity_outlier"})
        )

    Args:
        problems:
            A list of :class:`Problem` instances.
        target_classes:
            A :class:`frozenset` of ``problem_class`` strings to match.
            Empty frozenset → all findings go into *rest*.

    Returns:
        ``(matched, rest)`` — a tuple of two :class:`Problem` lists.
        ``matched + rest`` covers every finding in *problems* exactly once.

    Pure (no I/O, no SurrealDB).
    """
    if not target_classes:
        return ([], list(problems))
    matched: list[Problem] = []
    rest: list[Problem] = []
    for p in problems:
        if p.problem_class in target_classes:
            matched.append(p)
        else:
            rest.append(p)
    return (matched, rest)


def first_problem_of_class(
    problems: list[Problem],
    problem_class: str,
) -> Problem | None:
    """Return the first finding whose ``problem_class`` matches — item 194.

    Enables walrus-operator idioms without a manual ``next(iter(...), None)``::

        if p := first_problem_of_class(findings, "complexity_outlier"):
            report(p.finding_id)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``None``.
        problem_class:
            The ``problem_class`` string to search for.

    Returns:
        The first :class:`Problem` in *problems* whose ``problem_class``
        equals *problem_class*, or ``None`` if no such finding exists.

    Pure (no I/O, no SurrealDB).
    """
    for p in problems:
        if p.problem_class == problem_class:
            return p
    return None


def problems_for_finding_id(
    problems: list[Problem],
    finding_id: str,
) -> list[Problem]:
    """Return all findings whose ``finding_id`` equals *finding_id* — item 195.

    Reverse direction of :func:`finding_ids` (Problem → ID).  This goes
    ID → Problem list.  Usually returns 0 or 1 elements; returns all
    duplicates when they exist (complement of :func:`deduplicate_problems`)::

        assert problems_for_finding_id(findings, fid)   # membership check
        p_list = problems_for_finding_id(all_findings, target_id)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        finding_id:
            The ``finding_id`` string to search for.

    Returns:
        A list of all :class:`Problem` instances in *problems* whose
        ``finding_id`` equals *finding_id*.  Empty list if not found.
        Multiple elements if duplicate IDs exist.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.finding_id == finding_id]


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


def assert_default_classes_cover(required: frozenset[str] | set[str]) -> None:
    """Assert that the default TIDE registry covers every required class — item 170.

    Raises :exc:`AssertionError` with an actionable message listing the MISSING
    class names if any class in *required* is absent from
    :func:`default_template_classes`.  Empty *required* is a no-op (never
    raises).

    Intended for CI guards that enforce the TIDE wiring invariant without
    importing the heavy audit instruments themselves.

    Args:
        required:
            Set of ``problem_class`` strings that MUST be present in the
            default registry.  :class:`frozenset` or :class:`set`.

    Raises:
        AssertionError: If one or more *required* classes are absent from
            :func:`default_template_classes`.  The message lists ALL missing
            class names so a single CI run surfaces every gap.

    Pure (reads the template list; no writes, no I/O).
    """
    if not required:
        return  # empty required → no-op
    present = default_template_classes()
    missing = sorted(required - present)  # sorted for deterministic message
    if missing:
        raise AssertionError(f"default_template_classes() is missing required classes: {missing}")


def most_frequent_class(problems: list[Problem]) -> str | None:
    """Return the ``problem_class`` with the highest finding count — item 196.

    On ties the class that appears FIRST in *problems* wins (insertion-order
    tiebreaking).  Use :func:`top_problem_classes` for a ranked list::

        if cls := most_frequent_class(findings):
            flag_hotspot(cls)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``None``.

    Returns:
        The ``problem_class`` string with the maximum count, or ``None``
        when *problems* is empty.  Ties resolved by first occurrence.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    # max() with strict > keeps the FIRST maximum-count key on ties
    # (Python dicts preserve insertion order so the first class seen wins).
    return max(counts, key=counts.__getitem__)


def least_frequent_class(problems: list[Problem]) -> str | None:
    """Return the ``problem_class`` with the lowest finding count — item 197.

    On ties the class whose final appearance in *problems* is LAST wins
    (last-occurrence tiebreaking — most-recently-seen rarest class).
    Symmetric complement of :func:`most_frequent_class`::

        if cls := least_frequent_class(findings):
            audit_rare_class(cls)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``None``.

    Returns:
        The ``problem_class`` string with the minimum count, or ``None``
        when *problems* is empty.  Ties resolved by last occurrence.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    last_seen: dict[str, int] = {}
    for i, p in enumerate(problems):
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
        last_seen[p.problem_class] = i  # updated to the latest index
    # Sort key: (count, -last_seen_index) — smaller count wins; among ties,
    # a LARGER last_seen index maps to a SMALLER negative index, so the
    # last-occurrence class is selected.
    return min(counts, key=lambda cls: (counts[cls], -last_seen[cls]))


def class_frequency_map(problems: list[Problem]) -> dict[str, int]:
    """Return ``{problem_class: count}`` with keys in first-occurrence order — item 198.

    Semantically identical to :func:`problem_count_by_class` but the name
    makes the insertion-order key guarantee explicit: callers can rely on
    ``list(class_frequency_map(findings).keys())`` returning classes in the
    order they first appeared in *problems*::

        freq = class_frequency_map(findings)
        list(freq.keys())   # classes in first-occurrence order

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``{}``.

    Returns:
        ``{problem_class: count}`` with keys ordered by first occurrence.
        Values are positive integers; absent classes have no entry (no
        zero-count phantom keys).

    Pure (no I/O, no SurrealDB).
    """
    return problem_count_by_class(problems)


def class_finding_count(problems: list[Problem], problem_class: str) -> int:
    """Return the number of findings for *problem_class* — item 199.

    The scalar per-class accessor that avoids building a full frequency
    dict when only one class count is needed::

        assert class_finding_count(findings, "complexity_outlier") == 0

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``0``.
        problem_class:
            The class name to count.  Absent class → ``0`` (not
            ``None``, no ``KeyError``).

    Returns:
        The number of findings whose ``problem_class`` equals
        *problem_class*.  Always a non-negative integer.

    Pure (no I/O, no SurrealDB).
    """
    return sum(1 for p in problems if p.problem_class == problem_class)


def problems_above_threshold(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> list[Problem]:
    """Return findings from classes whose count exceeds the configured limit — item 200.

    Functional complement of :func:`assert_class_counts_under` — instead of
    raising, returns the offending findings so callers can act on them::

        high_priority = problems_above_threshold(
            findings, {"complexity_outlier": 2}
        )

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.  Only classes
            present in *thresholds* are monitored; all others are excluded
            from the result.  Empty *thresholds* → ``[]``.

    Returns:
        A new list containing only findings whose class is in *thresholds*
        AND whose class count exceeds the configured limit.  Findings are
        returned in insertion order.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds or not problems:
        return []
    counts = problem_count_by_class(problems)
    return [
        p
        for p in problems
        if p.problem_class in thresholds and counts[p.problem_class] > thresholds[p.problem_class]
    ]


def problems_within_threshold(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> list[Problem]:
    """Return findings from monitored classes whose count is at or below the limit — item 201.

    Complement of :func:`problems_above_threshold` — this keeps findings from
    classes that are within tolerance, enabling selection of the "safe" subset::

        safe_classes = problems_within_threshold(
            findings, {"complexity_outlier": 5}
        )

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.  Only classes
            present in *thresholds* are monitored; all others are excluded.
            Empty *thresholds* → ``[]``.

    Returns:
        A new list containing only findings whose class is in *thresholds*
        AND whose class count does NOT exceed the configured limit
        (``count <= limit``).  Insertion order is preserved.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds or not problems:
        return []
    counts = problem_count_by_class(problems)
    return [
        p
        for p in problems
        if p.problem_class in thresholds and counts[p.problem_class] <= thresholds[p.problem_class]
    ]


def partition_problems_by_threshold(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> tuple[list[Problem], list[Problem]]:
    """Split findings into (above-threshold, within-threshold) in one pass — item 202.

    One-pass combination of :func:`problems_above_threshold` and
    :func:`problems_within_threshold`.  Unmonitored classes (absent from
    *thresholds*) appear in neither partition::

        above, within = partition_problems_by_threshold(
            findings, {"complexity_outlier": 3}
        )

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``([], [])``.
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.  Unmonitored
            classes are excluded from both partitions.
            Empty *thresholds* → ``([], [])``.

    Returns:
        A 2-tuple ``(above, within)`` where:

        * ``above``  — findings from monitored classes whose count exceeds the limit.
        * ``within`` — findings from monitored classes whose count is ≤ the limit.

        Insertion order is preserved within each partition.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds or not problems:
        return ([], [])
    counts = problem_count_by_class(problems)
    above: list[Problem] = []
    within: list[Problem] = []
    for p in problems:
        if p.problem_class not in thresholds:
            continue
        if counts[p.problem_class] > thresholds[p.problem_class]:
            above.append(p)
        else:
            within.append(p)
    return (above, within)


def threshold_violations(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, int]:
    """Per-class threshold breach report: how far over budget each monitored class is — item 203.

    Returns ``{problem_class: excess_count}`` for every monitored class whose
    finding count strictly EXCEEDS its configured threshold.  The value is the
    *excess* (``count - threshold``), not the raw count, so the caller can
    reason about budget overruns directly::

        violations = threshold_violations(findings, {"complexity_outlier": 2})
        # → {"complexity_outlier": 1}  if 3 findings exist (3 - 2 = 1 over)

    Classes whose count equals the threshold are NOT violations (0 excess) and
    are absent from the result.  Unmonitored classes (absent from *thresholds*)
    are also absent.  Empty *thresholds* → ``{}``.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``{}``.
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.  Only classes
            present in *thresholds* are monitored.  Empty → ``{}``.

    Returns:
        ``{problem_class: excess_count}`` where every value is a positive
        integer (> 0).  Classes at or below their threshold are absent.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds or not problems:
        return {}
    counts = problem_count_by_class(problems)
    return {
        cls: counts[cls] - limit
        for cls, limit in thresholds.items()
        if cls in counts and counts[cls] > limit
    }


def worst_violation(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> tuple[str, int] | None:
    """Return ``(problem_class, excess_count)`` for the class with the largest excess.

    The scalar counterpart to :func:`threshold_violations`.  When multiple
    classes share the same excess, the class whose first occurrence appears
    earliest in *problems* wins (stable, deterministic output)::

        if v := worst_violation(findings, limits):
            alert(f"{v[0]} exceeds budget by {v[1]}")

    Args:
        problems:
            A list of :class:`Problem` instances.
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.

    Returns:
        ``(problem_class, excess_count)`` for the highest-excess class, or
        ``None`` when there are no violations.

    Pure (no I/O, no SurrealDB).
    """
    violations = threshold_violations(problems, thresholds)
    if not violations:
        return None
    # Build first-occurrence index for deterministic tie-breaking.
    first_seen: dict[str, int] = {}
    for i, p in enumerate(problems):
        if p.problem_class not in first_seen:
            first_seen[p.problem_class] = i
    best = max(violations, key=lambda cls: (violations[cls], -first_seen.get(cls, 0)))
    return (best, violations[best])


def violation_summary(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> int:
    """Return the total excess across all violating classes — item 205.

    Folds all per-class excess counts from :func:`threshold_violations` into
    a single integer.  Use as a single boolean health gate::

        if violation_summary(findings, limits) > 0:
            alert("budget exceeded")

    Args:
        problems:
            A list of :class:`Problem` instances.
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.

    Returns:
        Sum of all ``excess_count`` values from
        :func:`threshold_violations`.  0 when there are no violations,
        when *thresholds* is empty, or when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return sum(threshold_violations(problems, thresholds).values())


def classes_under_threshold(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> frozenset[str]:
    """Return the frozenset of monitored classes whose count is at or below the threshold — item 206.

    Complements :func:`threshold_violations`: that function returns classes that
    EXCEEDED their limit; this returns the set-theoretic complement among
    monitored classes — the ones still within budget.  When *problems* is
    empty, all monitored classes have count=0, which satisfies any positive
    threshold, so they are all included::

        safe = classes_under_threshold(findings, limits)
        if "complexity_outlier" in safe:
            proceed()

    Args:
        problems:
            A list of :class:`Problem` instances.
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.

    Returns:
        ``frozenset[str]`` of every monitored class whose count ≤ threshold.
        Empty *thresholds* → ``frozenset()``.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return frozenset()
    counts = problem_count_by_class(problems)
    return frozenset(cls for cls, limit in thresholds.items() if counts.get(cls, 0) <= limit)


def budget_status(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, str]:
    """Per-class budget compliance summary — item 207.

    Returns ``{problem_class: status}`` for every monitored class, where
    ``status`` is ``"ok"`` (count ≤ threshold) or ``"over"`` (count > threshold).
    Provides the full picture that :func:`threshold_violations` (over-only) and
    :func:`classes_under_threshold` (ok-only) each show only half of::

        status_by_class = budget_status(findings, limits)
        # {"complexity_outlier": "over", "nesting_outlier": "ok"}

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → all monitored
            classes map to ``"ok"`` (count=0 ≤ any positive threshold).
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.  Only classes
            present in *thresholds* are monitored.  Empty → ``{}``.

    Returns:
        ``{problem_class: "ok" | "over"}`` for every key in *thresholds*.
        Values are the literal strings ``"ok"`` or ``"over"`` — never counts
        or booleans.  Unmonitored classes are absent.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return {}
    counts = problem_count_by_class(problems)
    return {
        cls: "over" if counts.get(cls, 0) > limit else "ok" for cls, limit in thresholds.items()
    }


def finding_ids_for_class(
    problems: list[Problem],
    problem_class: str,
) -> list[str]:
    """Return all finding-ids belonging to the given class — item 208.

    The bulk ID-extraction face: extracts ``finding_id`` strings for every
    :class:`Problem` in *problems* whose ``problem_class`` matches.  Preserves
    input order; absent class returns ``[]``; empty list returns ``[]``::

        ids = finding_ids_for_class(findings, "complexity_outlier")
        # ["complexity_outlier:src/foo.py", ...]

    Args:
        problems:
            A list of :class:`Problem` instances.
        problem_class:
            The class to filter by.

    Returns:
        ``list[str]`` of ``finding_id`` values in input order.
        ``[]`` when *problem_class* is absent or *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return [p.finding_id for p in problems if p.problem_class == problem_class]


def group_finding_ids_by_class(
    problems: list[Problem],
) -> dict[str, list[str]]:
    """Build a class→ids reverse-index in one pass — item 209.

    Returns ``{problem_class: [finding_id, ...]}`` with keys in
    first-occurrence order (CPython 3.7+ dict insertion order) and values
    in input order within each class.  Avoids O(n) repeated calls to
    :func:`finding_ids_for_class` when multiple classes are needed::

        index = group_finding_ids_by_class(findings)
        complexity_ids = index.get("complexity_outlier", [])

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``{}``.

    Returns:
        ``{problem_class: [finding_id, ...]}`` in first-occurrence key order.

    Pure (no I/O, no SurrealDB).
    """
    result: dict[str, list[str]] = {}
    for p in problems:
        if p.problem_class not in result:
            result[p.problem_class] = []
        result[p.problem_class].append(p.finding_id)
    return result


def count_unique_finding_ids(problems: list[Problem]) -> int:
    """Return the number of distinct finding_ids — item 210.

    Deduplication health check: if this is less than ``len(problems)``,
    the same finding_id appears on multiple :class:`Problem` instances::

        n = count_unique_finding_ids(findings)
        if n < len(findings):
            warn(f"{len(findings) - n} duplicate ids detected")

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → 0.

    Returns:
        ``int`` — the number of distinct ``finding_id`` values.

    Pure (no I/O, no SurrealDB).
    """
    return len({p.finding_id for p in problems})


def has_duplicate_finding_ids(problems: list[Problem]) -> bool:
    """Return True iff any finding_id appears more than once — item 211.

    Boolean face of :func:`count_unique_finding_ids`::

        if has_duplicate_finding_ids(findings):
            warn("duplicate ids detected")

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``False``.

    Returns:
        ``True`` when any ``finding_id`` appears on multiple :class:`Problem`
        instances; ``False`` when all ids are distinct or the list is empty.

    Pure (no I/O, no SurrealDB).
    """
    return count_unique_finding_ids(problems) < len(problems)


def deduplicate_by_finding_id(problems: list[Problem]) -> list[Problem]:
    """Return a new list with duplicate finding_ids removed — item 212.

    Keeps the FIRST occurrence of each ``finding_id`` in input order.
    The corrective complement to :func:`has_duplicate_finding_ids`::

        clean = deduplicate_by_finding_id(findings)
        assert not has_duplicate_finding_ids(clean)

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.

    Returns:
        ``list[Problem]`` — a new list with duplicate ``finding_id`` entries
        removed; each id appears at most once in the result, at its first
        position from the original list.

    Pure (no I/O, no SurrealDB).
    """
    seen: set[str] = set()
    result: list[Problem] = []
    for p in problems:
        if p.finding_id not in seen:
            seen.add(p.finding_id)
            result.append(p)
    return result


def problems_not_in_class_set(
    problems: list[Problem],
    exclude: set[str],
) -> list[Problem]:
    """Return Problems whose class is NOT in the exclude set — item 213.

    Inverse of :func:`problems_for_class_set`; useful for filtering out
    noise classes while keeping signal::

        signal = problems_not_in_class_set(findings, {"long_line", "whitespace"})

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        exclude:
            Set of ``problem_class`` values to remove.  Empty set → full
            list returned unchanged.

    Returns:
        ``list[Problem]`` — Problems whose ``problem_class`` is not in
        *exclude*, in input order.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.problem_class not in exclude]


def class_counts_above_threshold(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, int]:
    """Raw counts for monitored classes that exceed their threshold — item 214.

    Count-dual of :func:`threshold_violations` (which returns excess).
    Returns ``{problem_class: count}`` (the raw finding count) for every
    class whose count is strictly above its threshold::

        counts_over = class_counts_above_threshold(findings, limits)
        # {"complexity_outlier": 7}  (raw count, not excess)

    Args:
        problems:
            A list of :class:`Problem` instances.
        thresholds:
            ``{problem_class: max_allowed_count}`` mapping.  Only classes
            present in *thresholds* are monitored.  Empty → ``{}``.

    Returns:
        ``{problem_class: count}`` for every monitored class with
        ``count > threshold``.  At-threshold and under-threshold classes
        are absent.  Unmonitored classes are absent.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return {}
    counts = problem_count_by_class(problems)
    return {
        cls: counts[cls]
        for cls, limit in thresholds.items()
        if cls in counts and counts[cls] > limit
    }


def most_common_class(problems: list[Problem]) -> str | None:
    """Return the problem_class with the highest finding count — item 215.

    Tie broken by first occurrence: the class that appears first in
    *problems* wins when two classes share the maximum count::

        top = most_common_class(findings)   # "complexity_outlier"

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``None``.

    Returns:
        The ``problem_class`` string with the highest count, or ``None``
        when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    # Build first-occurrence index alongside counts
    first_seen: dict[str, int] = {}
    counts: dict[str, int] = {}
    for i, p in enumerate(problems):
        if p.problem_class not in first_seen:
            first_seen[p.problem_class] = i
            counts[p.problem_class] = 0
        counts[p.problem_class] += 1
    # Pick class with highest count; first occurrence breaks ties
    return max(counts, key=lambda cls: (counts[cls], -first_seen[cls]))


def top_k_classes(problems: list[Problem], k: int) -> list[str]:
    """Return the top-K most frequent problem classes — item 216.

    Returns up to *k* class names in descending count order.  Ties broken
    by first occurrence.  List generalization of :func:`most_common_class`::

        top3 = top_k_classes(findings, 3)
        # ["complexity_outlier", "nesting_outlier", "long_function"]

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        k:
            Number of classes to return.  ``k ≤ 0`` → ``[]``.  When
            *k* exceeds the number of distinct classes, all classes are
            returned.

    Returns:
        ``list[str]`` of up to *k* class names in descending count order.

    Pure (no I/O, no SurrealDB).
    """
    if k <= 0 or not problems:
        return []
    first_seen: dict[str, int] = {}
    counts: dict[str, int] = {}
    for i, p in enumerate(problems):
        if p.problem_class not in first_seen:
            first_seen[p.problem_class] = i
            counts[p.problem_class] = 0
        counts[p.problem_class] += 1
    ordered = sorted(counts, key=lambda cls: (counts[cls], -first_seen[cls]), reverse=True)
    return ordered[:k]


def count_problems_added_since(
    problems: list[Problem],
    id_prefixes: set[str],
) -> int:
    """Count Problems whose finding_id starts with any given prefix — item 217.

    Models "how many new problems appeared in this scan?" when scan IDs
    share a common prefix::

        n = count_problems_added_since(findings, {"scan-2026-06-08:"})

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``0``.
        id_prefixes:
            Set of prefix strings.  A problem is counted when its
            ``finding_id`` starts with ANY element of the set.
            Empty set → ``0``.

    Returns:
        ``int`` — the count of problems matching at least one prefix.

    Pure (no I/O, no SurrealDB).
    """
    if not id_prefixes or not problems:
        return 0
    return sum(
        1 for p in problems if any(p.finding_id.startswith(prefix) for prefix in id_prefixes)
    )


def filter_by_finding_id_prefix(
    problems: list[Problem],
    id_prefixes: set[str],
) -> list[Problem]:
    """Return Problems whose finding_id starts with any given prefix — item 218.

    List face of :func:`count_problems_added_since` — returns the actual
    matching :class:`Problem` objects rather than a count::

        recent = filter_by_finding_id_prefix(findings, {"scan-2026-06-08:"})

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.
        id_prefixes:
            Set of prefix strings.  A problem is included when its
            ``finding_id`` starts with ANY element of the set.
            Empty set → ``[]``.

    Returns:
        ``list[Problem]`` — matching problems in input order.

    Pure (no I/O, no SurrealDB).
    """
    if not id_prefixes or not problems:
        return []
    return [p for p in problems if any(p.finding_id.startswith(prefix) for prefix in id_prefixes)]


def partition_by_threshold(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> tuple[frozenset[str], frozenset[str]]:
    """Split monitored classes into over-threshold and at-or-under-threshold sets.

    Returns ``(over, under)`` where:
    - ``over``  = monitored classes whose count *strictly exceeds* their threshold
    - ``under`` = monitored classes whose count is *at or below* their threshold

    The two sets are always disjoint and their union equals
    ``frozenset(thresholds.keys())``.  Unmonitored classes (not in *thresholds*)
    are absent from both sets.

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``(frozenset(), frozenset())``.

    Returns:
        ``tuple[frozenset[str], frozenset[str]]`` -- ``(over, under)``.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return frozenset(), frozenset()
    counts = problem_count_by_class(problems)
    over: set[str] = set()
    under: set[str] = set()
    for cls, limit in thresholds.items():
        if counts.get(cls, 0) > limit:
            over.add(cls)
        else:
            under.add(cls)
    return frozenset(over), frozenset(under)


def threshold_headroom(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, int]:
    """Return per-class remaining budget for monitored classes within threshold.

    For every monitored class whose count is AT OR BELOW its threshold,
    returns ``{class: threshold - count}``.  Over-threshold classes are absent.
    Unmonitored classes (not in *thresholds*) are absent.

    The positive complement to ``threshold_violations``:
    - ``threshold_violations`` gives the *excess* for over-budget classes
    - ``threshold_headroom`` gives the *remaining budget* for under-budget classes

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``{}``.

    Returns:
        ``dict[str, int]`` -- ``{class: threshold - count}`` for compliant classes.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return {}
    counts = problem_count_by_class(problems)
    return {
        cls: limit - counts.get(cls, 0)
        for cls, limit in thresholds.items()
        if counts.get(cls, 0) <= limit
    }


def class_violation_ratio(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, float]:
    """Return relative load (count / threshold) for every monitored class.

    Returns ``{cls: count / threshold}`` for every monitored class whose
    threshold is ``> 0``.  A ratio ``> 1.0`` indicates the class exceeds its
    threshold; ``== 1.0`` means exactly at threshold; ``< 1.0`` means under.

    Unlike ``threshold_headroom`` (which covers only under-threshold classes
    and returns the *absolute* remaining budget), this function covers ALL
    monitored classes with a *relative* load measure.

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Classes with ``threshold == 0`` are excluded (division
                    guard).  Empty mapping -> ``{}``.

    Returns:
        ``dict[str, float]`` -- ``{cls: count / threshold}`` for every
        monitored class with threshold > 0.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return {}
    counts = problem_count_by_class(problems)
    return {cls: counts.get(cls, 0) / limit for cls, limit in thresholds.items() if limit > 0}


def most_critical_class(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> str | None:
    """Return the class name with the highest ``count / threshold`` ratio.

    Delegates to :func:`class_violation_ratio` to compute ratios, then picks
    the class with the maximum value.  Ties are broken by first occurrence in
    *problems* (the class seen earliest in the input list wins); if no class
    appears in problems (all counts are 0), the first key in *thresholds* with
    a positive limit wins.

    Zero-threshold classes are excluded (same guard as :func:`class_violation_ratio`).
    Returns ``None`` when there are no eligible classes (empty *thresholds* or all
    thresholds are zero).

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.

    Returns:
        ``str`` class name with highest ratio, or ``None`` if no eligible class.

    Pure (no I/O, no SurrealDB).
    """
    ratios = class_violation_ratio(problems, thresholds)
    if not ratios:
        return None
    # Build first-seen index for tie-breaking (classes absent from problems get index=inf)
    first_seen: dict[str, int] = {}
    for i, p in enumerate(problems):
        if p.problem_class not in first_seen:
            first_seen[p.problem_class] = i
    return max(ratios, key=lambda cls: (ratios[cls], -first_seen.get(cls, len(problems))))


def problems_by_ratio_rank(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> list[Problem]:
    """Return Problems sorted by their class's violation ratio, highest first.

    Problems from the highest ``count / threshold`` class appear first.
    Within a class, the original input order is preserved (stable sort).
    Zero-threshold and unmonitored classes are placed last.

    Args:
        problems:   List of ``Problem`` instances to sort.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> all problems placed last (unmonitored),
                    preserving input order.

    Returns:
        ``list[Problem]`` — the same Problem objects, reordered.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return []
    ratios = class_violation_ratio(problems, thresholds)
    # Sort key: (-ratio, original_index)
    # Unmonitored / zero-threshold classes get ratio = -1.0 (sort last)
    return sorted(
        problems,
        key=lambda p: (-(ratios.get(p.problem_class, -1.0)),),
    )


def summarize_scan(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict:
    """Compose TIDE functions into a single-call scan summary.

    Returns a ``dict`` with exactly these 7 keys, all values obtained by
    calling existing pure TIDE functions (no reimplementation)::

        {
            "total":               int   -- len(problems),
            "violations_count":    int   -- number of monitored classes over threshold,
            "worst_violation":     tuple | None  -- (class, excess) or None,
            "most_critical_class": str | None    -- class with highest ratio,
            "violation_summary":   int   -- sum of all excesses,
            "classes_over":        frozenset[str] -- over-threshold monitored classes,
            "classes_under":       frozenset[str] -- at-or-under monitored classes,
        }

    Args:
        problems:   List of ``Problem`` instances from a TIDE scan.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.

    Returns:
        ``dict`` with the 7 summary keys listed above.

    Pure (no I/O, no SurrealDB).
    """
    violations = threshold_violations(problems, thresholds)
    classes_over, classes_under = partition_by_threshold(problems, thresholds)
    return {
        "total": len(problems),
        "violations_count": len(violations),
        "worst_violation": worst_violation(problems, thresholds),
        "most_critical_class": most_critical_class(problems, thresholds),
        "violation_summary": violation_summary(problems, thresholds),
        "classes_over": classes_over,
        "classes_under": classes_under,
    }


def scan_delta(before: dict, after: dict) -> dict:
    """Diff two ``summarize_scan()`` result dicts, returning a change summary.

    Compares two scan summaries (produced by :func:`summarize_scan`) and
    returns a dict with 5 keys describing what changed between them:

    - ``new_violations``    -- int: how many additional classes crossed over threshold
    - ``resolved_violations`` -- int: how many classes moved back under threshold
    - ``total_delta``       -- int: change in total finding count (may be negative)
    - ``newly_over``        -- frozenset[str]: classes that are newly above threshold
    - ``newly_under``       -- frozenset[str]: classes that are newly below threshold

    Identical *before* and *after* → all-zero/empty delta.

    Args:
        before: A ``summarize_scan()`` dict from the earlier scan.
        after:  A ``summarize_scan()`` dict from the later scan.

    Returns:
        ``dict`` with keys ``new_violations``, ``resolved_violations``,
        ``total_delta``, ``newly_over``, ``newly_under``.

    Pure (no I/O, no SurrealDB).
    """
    before_over: frozenset[str] = before.get("classes_over", frozenset())
    after_over: frozenset[str] = after.get("classes_over", frozenset())
    newly_over = after_over - before_over
    newly_under = before_over - after_over
    before_count: int = before.get("violations_count", 0)
    after_count: int = after.get("violations_count", 0)
    return {
        "new_violations": max(0, after_count - before_count),
        "resolved_violations": max(0, before_count - after_count),
        "total_delta": after.get("total", 0) - before.get("total", 0),
        "newly_over": newly_over,
        "newly_under": newly_under,
    }


def scan_is_healthy(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> bool:
    """Return True iff no monitored class exceeds its threshold.

    A boolean reduction of :func:`violation_summary`: delegates entirely to
    that function and returns ``violation_summary(...) == 0``.  Suitable for
    CI gates and health checks that need a single True/False result::

        assert scan_is_healthy(findings, limits), "Health gate failed"

    Args:
        problems:   List of ``Problem`` instances from a TIDE scan.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``True`` (no rules = no violations).

    Returns:
        ``bool`` -- ``True`` when all monitored classes are within budget.

    Pure (no I/O, no SurrealDB).
    """
    return violation_summary(problems, thresholds) == 0


def classes_within_budget(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> frozenset[str]:
    """Return monitored classes with COUNT STRICTLY BELOW their threshold.

    Distinct from :func:`classes_under_threshold` (which includes at-threshold):
    - ``classes_under_threshold``:  ``count <= threshold``  (headroom >= 0)
    - ``classes_within_budget``:    ``count <  threshold``  (headroom >  0)

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``frozenset()``.

    Returns:
        ``frozenset[str]`` of monitored class names with positive headroom.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return frozenset()
    counts = problem_count_by_class(problems)
    return frozenset(cls for cls, limit in thresholds.items() if counts.get(cls, 0) < limit)


def classes_at_threshold(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> frozenset[str]:
    """Return monitored classes whose finding count equals the threshold exactly.

    These are "yellow-zone" classes: compliant (not yet a violation) but with
    zero headroom remaining (count == threshold).  Distinct from:
    - :func:`classes_within_budget`:    ``count <  threshold`` (headroom > 0)
    - :func:`classes_at_threshold`:     ``count == threshold`` (headroom = 0)
    - over-threshold (via :func:`threshold_violations`): ``count > threshold``

    The three sets form a complete tripartite partition of all monitored
    classes::

        classes_within_budget | classes_at_threshold | {over-threshold}
            == frozenset(thresholds.keys())   (pairwise disjoint)

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``frozenset()``.

    Returns:
        ``frozenset[str]`` of monitored class names at the exact threshold.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return frozenset()
    counts = problem_count_by_class(problems)
    return frozenset(cls for cls, limit in thresholds.items() if counts.get(cls, 0) == limit)


def signed_headroom(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, int]:
    """Return signed headroom for every monitored class.

    Maps each monitored class to ``threshold - count``:
    - Positive → class is under budget (remaining headroom).
    - Zero     → class is exactly at threshold (no headroom left).
    - Negative → class is a violation (how many findings over the limit).

    Unlike :func:`threshold_headroom` (which omits violating classes), this
    function covers ALL monitored classes in *thresholds*.  Unmonitored
    classes (absent from *thresholds*) are not included in the result.

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``{}``.

    Returns:
        ``dict[str, int]`` mapping each monitored class to its signed headroom.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return {}
    counts = problem_count_by_class(problems)
    return {cls: limit - counts.get(cls, 0) for cls, limit in thresholds.items()}


def most_pressing_violation(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> str | None:
    """Return the monitored class with the most-negative signed headroom.

    Scans :func:`signed_headroom` for the entry with the minimum value.
    Returns the class name only when that minimum is strictly negative
    (i.e. a genuine violation exists).  Returns ``None`` when:
    - All headroom values are ≥ 0 (no violations).
    - *thresholds* is empty.

    Distinct from :func:`worst_violation` (which returns a
    ``(class, excess)`` tuple using the excess count) — this function
    measures depth via ``threshold - count`` (signed) and returns just
    the class name.

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``None``.

    Returns:
        The class name of the most-over-threshold class, or ``None`` when no
        violations exist.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return None
    headroom = signed_headroom(problems, thresholds)
    if not headroom:
        return None
    min_class = min(headroom, key=lambda cls: headroom[cls])
    return min_class if headroom[min_class] < 0 else None


def violation_depth(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, int]:
    """Return a map of violating classes to their excess count above threshold.

    For each monitored class where ``count > threshold``, returns
    ``count - threshold`` (always positive).  Compliant classes and
    at-threshold classes are absent.

    This is the positive-valued complement of :func:`signed_headroom`'s
    negative portion: ``violation_depth[cls] == -signed_headroom[cls]`` for
    every violating class.  More readable for "how many findings over the
    limit?" compared to negative signed headroom.

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``{}``.

    Returns:
        ``dict[str, int]`` of violating classes mapped to positive excess counts.
        Returns ``{}`` when no violations or *thresholds* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return {}
    counts = problem_count_by_class(problems)
    return {
        cls: counts.get(cls, 0) - limit
        for cls, limit in thresholds.items()
        if counts.get(cls, 0) > limit
    }


def total_violation_depth(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> int:
    """Return the total excess count across all violating classes.

    Sums ``violation_depth(problems, thresholds).values()``, giving a single
    integer representing the aggregate budget overrun.  Returns 0 when no
    classes are violating or when *thresholds* is empty.

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``0``.

    Returns:
        ``int`` total excess count.  Always ≥ 0.

    Pure (no I/O, no SurrealDB).
    """
    return sum(violation_depth(problems, thresholds).values())


def scan_pressure(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> float:
    """Return a composite pressure score for the scan.

    Combines violation count and total violation depth into one float::

        scan_pressure = violations_count + total_violation_depth

    A score of 0.0 means the scan is fully healthy.  Higher values indicate
    more violating classes (horizontal pressure) and deeper violations
    (vertical pressure).

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``0.0``.

    Returns:
        ``float`` composite pressure score ≥ 0.0.

    Pure (no I/O, no SurrealDB).
    """
    violations = threshold_violations(problems, thresholds)
    return float(len(violations) + total_violation_depth(problems, thresholds))


def classes_near_threshold(
    problems: list[Problem],
    thresholds: dict[str, int],
    tolerance: int = 1,
) -> frozenset[str]:
    """Return monitored classes within *tolerance* findings of their threshold.

    A class is "near threshold" when::

        0 <= threshold - count <= tolerance

    Includes at-threshold classes (headroom = 0) and classes with remaining
    headroom ≤ *tolerance*.  Excludes over-threshold (violating) classes and
    classes further than *tolerance* from their limit.

    Special case: ``tolerance=0`` is equivalent to :func:`classes_at_threshold`
    (only classes with exactly headroom = 0 are included).

    Args:
        problems:   List of ``Problem`` instances to examine.
        thresholds: Mapping of ``{problem_class: max_allowed_count}``.
                    Empty mapping -> ``frozenset()``.
        tolerance:  Maximum allowed headroom for inclusion. Default 1.

    Returns:
        ``frozenset[str]`` of near-threshold class names.

    Pure (no I/O, no SurrealDB).
    """
    if not thresholds:
        return frozenset()
    counts = problem_count_by_class(problems)
    return frozenset(
        cls for cls, limit in thresholds.items() if 0 <= limit - counts.get(cls, 0) <= tolerance
    )


def sample_problems_by_class(
    problems: list[Problem],
    n: int = 5,
) -> dict[str, list[Problem]]:
    """Return at most *n* Problem objects per class, preserving insertion order.

    A bounded variant of :func:`group_problems_by_class`: instead of returning
    all problems for each class, only the first *n* are kept.  Useful when a
    class has many findings and full listing is impractical.

    When *n* = 0, the dict contains the class keys (for classes present in
    *problems*) but each value is an empty list.  When a class has fewer than
    *n* problems, all of them are returned (no padding).

    Args:
        problems:   List of ``Problem`` instances to examine.
        n:          Maximum number of problems to return per class.  Default 5.

    Returns:
        ``dict[str, list[Problem]]`` mapping each present class to its first
        *n* problems.  Classes with 0 problems are absent.
        Empty *problems* → ``{}``.

    Pure (no I/O, no SurrealDB).
    """
    groups: dict[str, list[Problem]] = {}
    for p in problems:
        bucket = groups.setdefault(p.problem_class, [])
        if len(bucket) < n:
            bucket.append(p)
        elif n == 0 and p.problem_class not in groups:
            groups[p.problem_class] = []
    return groups


def problems_added_since_scan(
    problems: list[Problem],
    baseline_ids: frozenset[str],
) -> list[Problem]:
    """Return problems whose finding_id was not present in a prior scan.

    Compares each problem's ``finding_id`` against *baseline_ids* (the set
    of finding IDs from a previous scan).  Problems absent from the baseline
    are "new" findings.  Input order is preserved among returned problems.

    Args:
        problems:     Current list of ``Problem`` instances.
        baseline_ids: ``frozenset[str]`` of finding IDs from the prior scan.
                      Empty frozenset → all current problems are new.

    Returns:
        ``list[Problem]`` of problems not present in the baseline, in
        original input order.  Returns ``[]`` when *problems* is empty or
        all problems are already in the baseline.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.finding_id not in baseline_ids]


def problems_resolved_since_scan(
    baseline: list[Problem],
    current_ids: frozenset[str],
) -> list[Problem]:
    """Return baseline problems that no longer appear in the current scan.

    Compares each baseline problem's ``finding_id`` against *current_ids*
    (the set of finding IDs from the latest scan).  Problems absent from
    *current_ids* have been fixed since the baseline.

    This is the symmetric complement of :func:`problems_added_since_scan`:
    - ``problems_added_since_scan(current, baseline_ids)`` → new problems.
    - ``problems_resolved_since_scan(baseline, current_ids)`` → fixed problems.

    Args:
        baseline:    Prior list of ``Problem`` instances.
        current_ids: ``frozenset[str]`` of finding IDs from the current scan.
                     Empty frozenset → all baseline problems are resolved.

    Returns:
        ``list[Problem]`` of resolved problems (baseline order preserved).
        Returns ``[]`` when *baseline* is empty or all baseline problems
        are still present.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in baseline if p.finding_id not in current_ids]


def problem_list_delta(
    baseline: list[Problem],
    current: list[Problem],
) -> tuple[list[Problem], list[Problem]]:
    """Return the added and resolved problem lists between two scans.

    Computes the symmetric diff between *baseline* and *current* by
    ``finding_id``::

        added    = problems in current not in baseline
        resolved = problems in baseline not in current

    Delegates to :func:`problems_added_since_scan` and
    :func:`problems_resolved_since_scan`.  Both output lists preserve their
    respective input orders.

    NOTE: This function operates on raw ``Problem`` lists.  It is distinct
    from :func:`scan_delta` (item 225), which diffs two
    ``summarize_scan()`` summary dicts.

    Args:
        baseline: Prior list of ``Problem`` instances.
        current:  Current list of ``Problem`` instances.

    Returns:
        ``(added, resolved)`` — a 2-tuple of ``list[Problem]``.

    Pure (no I/O, no SurrealDB).
    """
    baseline_ids = frozenset(p.finding_id for p in baseline)
    current_ids = frozenset(p.finding_id for p in current)
    added = problems_added_since_scan(current, baseline_ids)
    resolved = problems_resolved_since_scan(baseline, current_ids)
    return added, resolved


def classes_with_single_problem(problems: list[Problem]) -> frozenset[str]:
    """Return the set of class names that appear exactly once in *problems*.

    A class with 0 or ≥2 occurrences is excluded.  This is a low-noise
    triage signal: a class with a single finding may warrant a spot-check
    without the overhead of a full threshold review.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        ``frozenset[str]`` of class names whose count is exactly 1.

    Pure (no I/O, no SurrealDB).
    """
    counts = problem_count_by_class(problems)
    return frozenset(cls for cls, n in counts.items() if n == 1)


def classes_above_count(problems: list[Problem], n: int) -> frozenset[str]:
    """Return class names whose problem count is strictly greater than *n*.

    Classes with count ≤ *n* are excluded.  Passing ``n=0`` returns all
    non-empty classes (since every non-empty class has count > 0).

    Args:
        problems: List of :class:`Problem` instances from a scan.
        n:        Integer threshold (exclusive lower bound).

    Returns:
        ``frozenset[str]`` of class names with count > *n*.

    Pure (no I/O, no SurrealDB).
    """
    counts = problem_count_by_class(problems)
    return frozenset(cls for cls, count in counts.items() if count > n)


def classes_below_count(problems: list[Problem], n: int) -> frozenset[str]:
    """Return class names whose problem count is strictly less than *n*.

    Only classes actually present in the scan (count ≥ 1) are considered.
    Because every present class has count ≥ 1, passing ``n=1`` always returns
    an empty frozenset.  Passing ``n=2`` returns the same result as
    :func:`classes_with_single_problem`.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        n:        Integer threshold (exclusive upper bound).

    Returns:
        ``frozenset[str]`` of class names with 0 < count < *n*.

    Pure (no I/O, no SurrealDB).
    """
    counts = problem_count_by_class(problems)
    return frozenset(cls for cls, count in counts.items() if count < n)


def classes_with_max_severity(
    problems: list[Problem],
    severity: str,
) -> frozenset[str]:
    """Return class names that contain at least one problem at *severity*.

    Filters problems by exact case-sensitive ``problem.severity`` match, then
    collects the unique class names.  A class appears in the result even if
    only one of its many problems carries the target severity.

    Args:
        problems: List of ``Problem`` instances (each with an optional
                  ``severity`` field, default ``""``).
        severity: Exact severity string to match (case-sensitive).

    Returns:
        ``frozenset[str]`` of class names that have at least one problem
        with ``severity == severity``.  Empty *problems* or no matches →
        ``frozenset()``.

    Pure (no I/O, no SurrealDB).
    """
    return frozenset(p.problem_class for p in problems if p.severity == severity)


def total_problems_in_classes(
    problems: list[Problem],
    classes: frozenset[str],
) -> int:
    """Return the total number of problems whose class is in *classes*.

    Classes in *classes* that are not present in the scan contribute 0 —
    no ``KeyError`` is raised.  Empty *classes* or empty *problems* → 0.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        classes:  ``frozenset[str]`` of class names to aggregate.

    Returns:
        ``int`` — sum of problem counts for all classes in *classes*.

    Pure (no I/O, no SurrealDB).
    """
    counts = problem_count_by_class(problems)
    return sum(counts.get(cls, 0) for cls in classes)


def threshold_class_partition(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, frozenset[str]]:
    """Partition monitored classes into within-budget / at-threshold / over-budget.

    Returns a dict with exactly three ``frozenset[str]`` values::

        {
            "within_budget":  classes whose count  < threshold,
            "at_threshold":   classes whose count == threshold,
            "over_budget":    classes whose count  > threshold,
        }

    The three sets are disjoint; their union equals ``frozenset(thresholds)``.
    Unmonitored classes (absent from *thresholds*) appear in none of the sets.

    NOTE: Distinct from :func:`partition_problems_by_threshold` (item 202),
    which returns a 2-tuple of ``Problem`` lists.  This function operates on
    class names and produces a three-way dict.

    Args:
        problems:   List of :class:`Problem` instances from a scan.
        thresholds: ``{problem_class: max_allowed_count}`` mapping.

    Returns:
        ``dict[str, frozenset[str]]`` with keys
        ``"within_budget"``, ``"at_threshold"``, ``"over_budget"``.

    Pure (no I/O, no SurrealDB).
    """
    counts = problem_count_by_class(problems)
    within: list[str] = []
    at: list[str] = []
    over: list[str] = []
    for cls, limit in thresholds.items():
        count = counts.get(cls, 0)
        if count < limit:
            within.append(cls)
        elif count == limit:
            at.append(cls)
        else:
            over.append(cls)
    return {
        "within_budget": frozenset(within),
        "at_threshold": frozenset(at),
        "over_budget": frozenset(over),
    }


def headroom_summary(
    problems: list[Problem],
    thresholds: dict[str, int],
) -> dict[str, object]:
    """Return a rich headroom report covering all monitored classes.

    Builds on :func:`signed_headroom` to produce a summary with four keys::

        {
            "compliant": list[str],   # classes with headroom > 0, sorted asc
            "exact":     list[str],   # classes with headroom == 0, sorted asc
            "violated":  list[str],   # classes with headroom < 0, sorted asc
            "worst":     str | None,  # class with lowest headroom, or None
        }

    The three lists are disjoint; their union (as a set) equals
    ``frozenset(thresholds)``.  ``worst`` is ``None`` when there are no
    violations.

    Args:
        problems:   List of :class:`Problem` instances from a scan.
        thresholds: ``{problem_class: max_allowed_count}`` mapping.

    Returns:
        ``dict`` with keys ``"compliant"``, ``"exact"``, ``"violated"``,
        ``"worst"``.

    Pure (no I/O, no SurrealDB).
    """
    headroom = signed_headroom(problems, thresholds)
    compliant: list[str] = sorted(cls for cls, h in headroom.items() if h > 0)
    exact: list[str] = sorted(cls for cls, h in headroom.items() if h == 0)
    violated: list[str] = sorted(cls for cls, h in headroom.items() if h < 0)
    worst: str | None = min(violated, key=lambda cls: headroom[cls]) if violated else None
    return {
        "compliant": compliant,
        "exact": exact,
        "violated": violated,
        "worst": worst,
    }


def filter_problems_by_severity(
    problems: list[Problem],
    severity: str,
) -> list[Problem]:
    """Return all problems whose severity matches *severity* (exact, case-sensitive).

    The ``Problem.severity`` field is an optional ``str`` with default ``""``.
    This function is the Problem-list complement of
    :func:`classes_with_max_severity`, which returns class names instead.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        severity: Exact severity string to match (case-sensitive).

    Returns:
        ``list[Problem]`` — matching problems in input order.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.severity == severity]


def count_by_severity(problems: list[Problem]) -> dict[str, int]:
    """Return a count of problems per severity level.

    Problems with the default ``severity=""`` are excluded — they carry no
    severity label and should not pollute the output dict.  This function is
    the severity-axis complement of :func:`problem_count_by_class`.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        ``dict[str, int]`` mapping each non-empty severity label to its count.
        Empty *problems* → ``{}``.

    Pure (no I/O, no SurrealDB).
    """
    result: dict[str, int] = {}
    for p in problems:
        if p.severity:  # skip default empty string
            result[p.severity] = result.get(p.severity, 0) + 1
    return result


def dominant_severity(problems: list[Problem]) -> str | None:
    """Return the severity level with the highest problem count.

    Tie-break: lexicographically smallest severity string wins.
    Returns ``None`` when no problem has a non-empty severity (i.e. all
    problems use the default ``severity=""``).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        The severity string with the highest count, or ``None``.

    Pure (no I/O, no SurrealDB).
    """
    counts = count_by_severity(problems)
    if not counts:
        return None
    return max(counts, key=lambda sev: (counts[sev], [-ord(c) for c in sev]))


def severity_fraction(problems: list[Problem], severity: str) -> float:
    """Return the fraction of labelled problems at *severity*.

    The denominator is the count of problems with a non-empty ``severity``
    field — unlabelled problems (``severity=""``) are excluded from both the
    numerator and the denominator.  Returns ``0.0`` when the severity is
    absent or when no problems carry a severity label.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        severity: Exact severity string to measure (case-sensitive).

    Returns:
        ``float`` in ``[0.0, 1.0]`` — ``count_at_severity / total_labelled``.

    Pure (no I/O, no SurrealDB).
    """
    counts = count_by_severity(problems)
    total_labelled = sum(counts.values())
    if total_labelled == 0:
        return 0.0
    return float(counts.get(severity, 0)) / total_labelled


def problems_above_severity_fraction(
    problems: list[Problem],
    severity: str,
    min_fraction: float,
) -> list[Problem]:
    """Return problems at *severity* only when their fraction STRICTLY exceeds *min_fraction*.

    Combines :func:`severity_fraction` and :func:`filter_problems_by_severity`
    into a single fraction-gated alerting call.  When the fraction equals
    *min_fraction*, returns ``[]`` (strict ``>`` boundary).

    Args:
        problems:     List of :class:`Problem` instances from a scan.
        severity:     Exact severity string to test (case-sensitive).
        min_fraction: Minimum fraction (exclusive) required to trigger.

    Returns:
        ``list[Problem]`` of matching problems (input order preserved) when
        ``severity_fraction(problems, severity) > min_fraction``; ``[]``
        otherwise.

    Pure (no I/O, no SurrealDB).
    """
    if severity_fraction(problems, severity) > min_fraction:
        return filter_problems_by_severity(problems, severity)
    return []


def severity_report(problems: list[Problem]) -> dict[str, object]:
    """Return a one-call severity analytics summary.

    Consolidates :func:`count_by_severity`, :func:`dominant_severity`, and
    per-severity fractions into a single dict::

        {
            "counts":         dict[str, int],
            "dominant":       str | None,
            "fractions":      dict[str, float],
            "labelled_total": int,
        }

    ``fractions`` sums to 1.0 (floating-point tolerance) when
    ``labelled_total > 0``.  All four fields are computed from the same
    ``count_by_severity`` call, ensuring mutual consistency.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        ``dict`` with keys ``"counts"``, ``"dominant"``, ``"fractions"``,
        ``"labelled_total"``.

    Pure (no I/O, no SurrealDB).
    """
    counts = count_by_severity(problems)
    labelled_total = sum(counts.values())
    fractions: dict[str, float] = (
        {sev: float(cnt) / labelled_total for sev, cnt in counts.items()}
        if labelled_total > 0
        else {}
    )
    dom = dominant_severity(problems)
    return {
        "counts": counts,
        "dominant": dom,
        "fractions": fractions,
        "labelled_total": labelled_total,
    }


def classes_at_severity(problems: list[Problem], severity: str) -> frozenset[str]:
    """Return the set of class names that have ≥1 problem at *severity*.

    Bridges the severity analytics family with the class-level analytics
    family.  Passing ``severity=""`` returns classes that have unlabelled
    problems (``problem.severity == ""``).

    Args:
        problems: List of :class:`Problem` instances from a scan.
        severity: Exact severity string to match (case-sensitive).

    Returns:
        ``frozenset[str]`` of class names.  Empty when no problems match.

    Pure (no I/O, no SurrealDB).
    """
    return frozenset(p.problem_class for p in problems if p.severity == severity)


def cross_class_severity_map(problems: list[Problem]) -> dict[str, dict[str, int]]:
    """Return the two-dimensional class × severity count breakdown.

    For each class present in the scan, returns an inner dict mapping
    severity string → count.  Unlabelled problems (``severity=""``) are
    included under key ``""`` in the inner dict (unlike
    :func:`count_by_severity`, which excludes ``""``).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        ``{class_name: {severity: count}}`` for all classes in the scan.
        Empty input → ``{}``.

    Pure (no I/O, no SurrealDB).
    """
    result: dict[str, dict[str, int]] = {}
    for p in problems:
        inner = result.setdefault(p.problem_class, {})
        inner[p.severity] = inner.get(p.severity, 0) + 1
    return result


def top_classes_by_severity(
    problems: list[Problem],
    severity: str,
    n: int,
) -> list[str]:
    """Return the top *n* class names ranked by their count at *severity*.

    Classes are ranked by their problem count at *severity* in descending
    order.  Ties are broken alphabetically ascending by class name.  Classes
    that have no problems at *severity* are excluded from the result.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        severity: Exact severity string to rank by (case-sensitive).
        n:        Maximum number of class names to return.  n=0 → ``[]``.

    Returns:
        ``list[str]`` of at most *n* class names, ranked as described above.

    Pure (no I/O, no SurrealDB).
    """
    if n == 0:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        if p.severity == severity:
            counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    ranked = sorted(counts, key=lambda cls: (-counts[cls], cls))
    return ranked[:n]


def any_class_above_severity_fraction(
    problems: list[Problem],
    severity: str,
    min_fraction: float,
) -> bool:
    """Return True if any class has ≥ *min_fraction* of its problems at *severity*.

    The fraction is computed **per class** as::

        count_at_severity_for_class / total_problems_in_class

    The denominator includes all problems for that class (all severities plus
    unlabelled).  This is distinct from the global
    :func:`severity_fraction`, which uses all labelled problems as the
    denominator.

    Args:
        problems:     List of :class:`Problem` instances from a scan.
        severity:     Exact severity string (case-sensitive).
        min_fraction: Inclusive lower bound on the per-class fraction.

    Returns:
        ``True`` if at least one class satisfies the threshold; ``False``
        otherwise (including empty input).

    Pure (no I/O, no SurrealDB).
    """
    # Build per-class total count and at-severity count in a single pass.
    total: dict[str, int] = {}
    at_sev: dict[str, int] = {}
    for p in problems:
        total[p.problem_class] = total.get(p.problem_class, 0) + 1
        if p.severity == severity:
            at_sev[p.problem_class] = at_sev.get(p.problem_class, 0) + 1
    return any(cnt / total[cls] >= min_fraction for cls, cnt in at_sev.items())


def severity_concentration_report(
    problems: list[Problem],
    severity: str,
    min_fraction: float,
) -> dict[str, dict[str, object]]:
    """Return a per-class severity concentration summary.

    For every class with at least one problem, returns an inner dict with
    exactly four keys::

        {
            "total":             int,   # total problems in this class
            "at_severity":       int,   # problems at *severity* in this class
            "fraction":          float, # at_severity / total (per-class)
            "exceeds_threshold": bool,  # fraction >= min_fraction
        }

    Classes that have no problems at *severity* still appear with
    ``at_severity=0`` and ``fraction=0.0``.

    Args:
        problems:     List of :class:`Problem` instances from a scan.
        severity:     Exact severity string (case-sensitive).
        min_fraction: Inclusive lower bound used to set ``exceeds_threshold``.

    Returns:
        ``{class_name: {…}}`` for every class present; empty input → ``{}``.

    Pure (no I/O, no SurrealDB).
    """
    total: dict[str, int] = {}
    at_sev: dict[str, int] = {}
    for p in problems:
        total[p.problem_class] = total.get(p.problem_class, 0) + 1
        if p.severity == severity:
            at_sev[p.problem_class] = at_sev.get(p.problem_class, 0) + 1
    result: dict[str, dict[str, object]] = {}
    for cls, tot in total.items():
        cnt = at_sev.get(cls, 0)
        frac = cnt / tot
        result[cls] = {
            "total": tot,
            "at_severity": cnt,
            "fraction": frac,
            "exceeds_threshold": frac >= min_fraction,
        }
    return result


def most_concentrated_class(
    problems: list[Problem],
    severity: str,
) -> str | None:
    """Return the class with the highest fraction of its problems at *severity*.

    The fraction is ``count_at_severity / total_problems_in_class``.  This is a
    concentration metric — a class with 1/1 = 100% concentration beats a class
    with 10/1000 = 1% even though the latter has more raw problems.

    Tie-break: alphabetically ascending class name.  Returns ``None`` when no
    class has any problems at *severity* or when *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        severity: Exact severity string (case-sensitive).

    Returns:
        Class name string or ``None``.

    Pure (no I/O, no SurrealDB).
    """
    total: dict[str, int] = {}
    at_sev: dict[str, int] = {}
    for p in problems:
        total[p.problem_class] = total.get(p.problem_class, 0) + 1
        if p.severity == severity:
            at_sev[p.problem_class] = at_sev.get(p.problem_class, 0) + 1
    if not at_sev:
        return None
    return max(at_sev, key=lambda cls: (at_sev[cls] / total[cls], [-ord(c) for c in cls]))


def severity_dispersion(problems: list[Problem]) -> int:
    """Return the count of distinct non-empty severity strings in the scan.

    Unlabelled problems (``severity=""``) are excluded — they do not
    contribute to the severity-tier count.  The result measures the *width*
    of the active severity space (e.g. 0 for an all-unlabelled scan, 1 for a
    scan with only HIGH findings, 3 for HIGH/MEDIUM/LOW).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        Number of distinct non-empty severity labels.  Empty or all-unlabelled
        input → ``0``.

    Pure (no I/O, no SurrealDB).
    """
    return len({p.severity for p in problems if p.severity})


def class_severity_entropy(problems: list[Problem], cls: str) -> float:
    """Return the Shannon entropy (bits) of the severity distribution for *cls*.

    The distribution is computed ONLY over labelled (non-empty severity)
    problems that belong to *cls*.  Unlabelled problems are excluded from both
    the counts and the total.  The entropy formula is::

        H = -sum(p_i * log2(p_i))  for each non-empty severity i in the class

    Returns ``0.0`` when the class has at most one distinct labelled severity,
    when it has no labelled problems, when *cls* is not present in *problems*,
    or when *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        cls:      Class name to compute entropy for.

    Returns:
        Shannon entropy in bits (float).  Always ≥ 0.0.

    Pure (no I/O, no SurrealDB).
    """
    counts: dict[str, int] = {}
    for p in problems:
        if p.problem_class == cls and p.severity:
            counts[p.severity] = counts.get(p.severity, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return float(-sum((c / total) * math.log2(c / total) for c in counts.values()))


def highest_entropy_class(problems: list[Problem]) -> str | None:
    """Return the class with the highest Shannon entropy across its severities.

    Uses :func:`class_severity_entropy` to compute per-class entropy, then
    returns the class with the maximum value.  Tie-break: alphabetically
    ascending class name.

    Returns ``None`` when no class has at least two distinct labelled
    severities (i.e. every class has H=0.0) or when *problems* is empty.
    This prevents returning a degenerate result for mono-severity scans.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        Class name string or ``None``.

    Pure (no I/O, no SurrealDB).
    """
    classes = {p.problem_class for p in problems}
    if not classes:
        return None
    entropies = {cls: class_severity_entropy(problems, cls) for cls in classes}
    # Only consider classes with H > 0 (≥2 distinct labelled severities).
    candidates = {cls: h for cls, h in entropies.items() if h > 0.0}
    if not candidates:
        return None
    return max(candidates, key=lambda cls: (candidates[cls], [-ord(c) for c in cls]))


def problems_in_class(problems: list[Problem], cls: str) -> list[Problem]:
    """Return all problems whose ``problem_class`` equals *cls*, in input order.

    This is the foundational per-class filter.  Higher-order per-class
    functions (entropy, concentration, top-N) can be expressed as a
    composition of :func:`problems_in_class` followed by a summary operation.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        cls:      Exact class name to filter by (case-sensitive).

    Returns:
        New ``list[Problem]`` containing only problems where
        ``p.problem_class == cls``, in the same order as *problems*.
        Empty list if *cls* is not present or *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.problem_class == cls]


def unique_finding_ids(problems: list[Problem]) -> frozenset[str]:
    """Return a frozenset of all distinct ``finding_id`` values in *problems*.

    Useful for deduplication checks: if ``len(unique_finding_ids(problems))
    < len(problems)``, the scan contains duplicate findings.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        :class:`frozenset` of ``finding_id`` strings.  Duplicate ids appear
        only once.  Empty input → ``frozenset()``.

    Pure (no I/O, no SurrealDB).
    """
    return frozenset(p.finding_id for p in problems)


def duplicate_finding_ids(problems: list[Problem]) -> frozenset[str]:
    """Return finding_ids that appear in two or more problems.

    The positive dedup signal: if the returned frozenset is non-empty, the
    scan contains redundant findings that should be investigated or merged.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        :class:`frozenset` of ``finding_id`` strings that appear ≥ 2 times.
        Empty when all ids are unique or *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return frozenset(fid for fid, cnt in counts.items() if cnt >= 2)


def problems_with_any_severity(problems: list[Problem]) -> list[Problem]:
    """Return problems whose ``severity`` is a non-empty string — item 380.

    The labelled-only filter: complement of :func:`problems_without_severity`.
    Answers "give me only the labelled problems" — useful for severity
    distribution analysis, priority queuing, or any computation that must
    exclude unlabelled records.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        New ``list[Problem]`` containing problems where ``p.severity != ""``,
        in input order.  Empty list when all problems are unlabelled or
        *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.severity]


def problems_without_severity(problems: list[Problem]) -> list[Problem]:
    """Return problems whose ``severity`` is the empty string.

    The direct complement to :func:`filter_problems_by_severity`: instead of
    filtering by a specific severity value, this returns the problems that
    lack any severity label.  Useful for labelling coverage audits.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        New ``list[Problem]`` containing problems where ``p.severity == ""``,
        in input order.  Empty list when all problems are labelled or
        *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if not p.severity]


def labelled_problem_count(problems: list[Problem]) -> int:
    """Return the count of problems that have a non-empty severity label.

    Equals ``len(problems) - len(problems_without_severity(problems))``.
    Useful as the denominator when computing severity fractions and for
    quick labelling-coverage checks.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        Count of problems where ``p.severity != ""``.  ``0`` when all
        problems are unlabelled or *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return sum(1 for p in problems if p.severity)


def labelled_fraction(problems: list[Problem]) -> float:
    """Return the fraction of problems that carry a non-empty severity label — item 381.

    Scalar labelling-coverage metric: ``labelled_count / total_count``.
    Equivalent to :func:`labelling_coverage`; provided as an alternative name
    that reads naturally alongside :func:`labelled_problem_count`.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``0.0``.

    Returns:
        Float in ``[0.0, 1.0]``.  ``0.0`` when *problems* is empty or all
        problems are unlabelled.  ``1.0`` when every problem has a non-empty
        ``severity`` field.

    Pure (no I/O, no SurrealDB).
    """
    total = len(problems)
    if total == 0:
        return 0.0
    return sum(1 for p in problems if p.severity) / total


def unlabelled_fraction(problems: list[Problem]) -> float:
    """Return the fraction of problems that carry an empty severity label — item 382.

    Scalar unlabelled-coverage metric: ``unlabelled_count / total_count``.
    Complement of :func:`labelled_fraction`:
    ``labelled_fraction(p) + unlabelled_fraction(p) == 1.0`` for any
    non-empty *problems*.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``0.0``.

    Returns:
        Float in ``[0.0, 1.0]``.  ``0.0`` when *problems* is empty or all
        problems are labelled.  ``1.0`` when every problem has an empty
        ``severity`` field.

    Pure (no I/O, no SurrealDB).
    """
    total = len(problems)
    if total == 0:
        return 0.0
    return sum(1 for p in problems if not p.severity) / total


def labelling_coverage(problems: list[Problem]) -> float:
    """Return the fraction of problems that have a non-empty severity label.

    The denominator is ``len(problems)`` (total problems including unlabelled),
    so unlabelled problems always reduce coverage below 1.0.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        Float in ``[0.0, 1.0]``.  ``0.0`` when *problems* is empty or all
        problems are unlabelled.  ``1.0`` when every problem is labelled.

    Pure (no I/O, no SurrealDB).
    """
    total = len(problems)
    if total == 0:
        return 0.0
    return labelled_problem_count(problems) / total


def class_labelling_coverage(problems: list[Problem]) -> dict[str, float]:
    """Return the fraction of labelled problems for each class in the scan.

    For every class present in *problems*, computes the fraction of that
    class's own problems that carry a non-empty :attr:`~Problem.severity`
    label.  The denominator is the class's total problem count (not the
    global total).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        ``{class_name: fraction}`` where *fraction* is in ``[0.0, 1.0]``.
        Classes with all-unlabelled problems appear with value ``0.0``.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    classes = {p.problem_class for p in problems}
    return {cls: labelling_coverage(problems_in_class(problems, cls)) for cls in classes}


def scan_summary(problems: list[Problem]) -> dict[str, object]:
    """Return a one-call executive summary of the scan.

    Composes the full TIDE analytics family into a single dict with exactly
    seven keys::

        {
            "total":             int,         # len(problems)
            "labelled":          int,         # labelled_problem_count
            "coverage":          float,       # labelling_coverage
            "class_count":       int,         # distinct problem_class count
            "severity_counts":   dict,        # count_by_severity (no "")
            "dominant_severity": str | None,  # dominant_severity
            "has_duplicates":    bool,        # bool(duplicate_finding_ids)
        }

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        Summary dict as described above.  All values zero/None/False/empty
        when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    sr = severity_report(problems)
    return {
        "total": len(problems),
        "labelled": labelled_problem_count(problems),
        "coverage": labelling_coverage(problems),
        "class_count": len({p.problem_class for p in problems}),
        "severity_counts": sr["counts"],
        "dominant_severity": sr["dominant"],
        "has_duplicates": bool(duplicate_finding_ids(problems)),
    }


def top_class_by_problem_count(problems: list[Problem]) -> str | None:
    """Return the class name with the most total problems (all severities).

    Counts every problem in each class regardless of severity label.
    Tie-break: ascending class name (alphabetically smallest wins).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        Class name (str) with the highest total count, or ``None`` when
        *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return max(counts, key=lambda cls: (counts[cls], [-ord(c) for c in cls]))


def classes_above_problem_count(problems: list[Problem], min_count: int) -> frozenset[str]:
    """Return the frozenset of class names whose total problem count >= min_count.

    Counts every problem in a class regardless of severity label.

    Args:
        problems:  List of :class:`Problem` instances from a scan.
        min_count: Minimum total count threshold (inclusive).

    Returns:
        frozenset of class names meeting the threshold, or ``frozenset()``
        when *problems* is empty or no class meets the threshold.

    Pure (no I/O, no SurrealDB).
    """
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return frozenset(cls for cls, cnt in counts.items() if cnt >= min_count)


def severity_rank_in_class(problems: list[Problem], cls: str, severity: str) -> int | None:
    """Return the 1-based frequency rank of *severity* among labelled problems in *cls*.

    Rank 1 = most frequent.  Ties broken by severity string ascending.
    Only labelled problems (severity != '') are included in the frequency counts.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        cls:      Class name to examine.
        severity: Severity label to rank.

    Returns:
        1-based rank (int), or ``None`` when *severity* does not appear in
        *cls*, when *cls* is absent, or when *cls* has no labelled problems.

    Pure (no I/O, no SurrealDB).
    """
    if not severity:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        if p.problem_class == cls and p.severity:
            counts[p.severity] = counts.get(p.severity, 0) + 1
    if severity not in counts:
        return None
    # Sort by (-count, severity_asc) to build rank order
    ranked = sorted(counts.keys(), key=lambda s: (-counts[s], s))
    return ranked.index(severity) + 1


def class_problem_fraction(problems: list[Problem], cls: str) -> float:
    """Return the fraction of ALL problems that belong to *cls*.

    The denominator is ``len(problems)`` (all classes combined), so this
    measures the weight of *cls* in the overall scan, not within the class.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        cls:      Class name to measure.

    Returns:
        float in [0.0, 1.0]: count(cls) / len(problems).
        0.0 when *cls* is absent or *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    total = len(problems)
    if total == 0:
        return 0.0
    cls_count = sum(1 for p in problems if p.problem_class == cls)
    return float(cls_count / total)


def problems_at_severity(problems: list[Problem], severity: str) -> list[Problem]:
    """Return all problems whose severity exactly equals *severity*.

    Case-sensitive exact match across all classes.  Preserves input order.
    When *severity* is ``""`` (empty string), returns unlabelled problems only.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        severity: Severity label to filter on (exact, case-sensitive).

    Returns:
        list of :class:`Problem` instances with ``problem.severity == severity``,
        in the same order as *problems*.  Empty list when *problems* is empty
        or no problem matches.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.severity == severity]


def count_classes_with_severity(problems: list[Problem], severity: str) -> int:
    """Return the number of distinct classes that have ≥1 problem at *severity*.

    Case-sensitive exact match on severity.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        severity: Severity label to count classes for (exact, case-sensitive).

    Returns:
        int — count of distinct class names with at least one problem whose
        severity == *severity*.  0 when *problems* is empty or no match found.

    Pure (no I/O, no SurrealDB).
    """
    return len({p.problem_class for p in problems if p.severity == severity})


def most_common_severity(problems: list[Problem]) -> str | None:
    """Return the labelled severity with the highest frequency across all problems.

    Only labelled problems (severity != '') are counted.
    Tie-break: ascending severity string (alphabetically smaller wins).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        str — the most frequent labelled severity label, or ``None`` when
        *problems* is empty or all problems are unlabelled.

    Pure (no I/O, no SurrealDB).
    """
    counts: dict[str, int] = {}
    for p in problems:
        if p.severity:
            counts[p.severity] = counts.get(p.severity, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda s: (counts[s], [-ord(c) for c in s]))


def severity_gini(problems: list[Problem]) -> float:
    """Return the Gini impurity of the labelled severity distribution.

    Gini impurity = 1 - Σ(p_i²) over non-empty severities.
    Range: 0.0 (single severity, pure) to (1 - 1/k) maximum (k labels, uniform).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        float Gini impurity in [0.0, 1.0).  0.0 when *problems* is empty,
        all problems are unlabelled, or only one distinct severity exists.

    Pure (no I/O, no SurrealDB).
    """
    counts: dict[str, int] = {}
    for p in problems:
        if p.severity:
            counts[p.severity] = counts.get(p.severity, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return float(1.0 - sum((c / total) ** 2 for c in counts.values()))


def top_severity_pairs(problems: list[Problem], n: int = 5) -> list[tuple[str, str, int]]:
    """Return the top-n (class, severity, count) tuples by problem count.

    Counts labelled problems only (severity != '').  Sorted by count
    descending; ties broken by (class ascending, severity ascending).

    Args:
        problems: List of :class:`Problem` instances from a scan.
        n:        Maximum number of entries to return (default 5).

    Returns:
        list of ``(class_name, severity, count)`` tuples, at most *n* entries.
        Empty list when *problems* is empty, all unlabelled, or *n* == 0.

    Pure (no I/O, no SurrealDB).
    """
    if n == 0:
        return []
    counts: dict[tuple[str, str], int] = {}
    for p in problems:
        if p.severity:
            key = (p.problem_class, p.severity)
            counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
    return [(cls, sev, cnt) for (cls, sev), cnt in ranked[:n]]


def class_severity_vector(
    problems: list[Problem], cls: str, severities: list[str]
) -> tuple[int, ...]:
    """Return a fixed-order count vector for *cls* indexed by *severities*.

    Each element of the returned tuple is the count of problems in *cls*
    with the corresponding severity (exact match).  The order mirrors
    *severities* exactly — absent severities get count 0.

    Args:
        problems:   List of :class:`Problem` instances from a scan.
        cls:        Class name to build the vector for.
        severities: Ordered list of severity labels.

    Returns:
        tuple of int counts, one per entry in *severities* in the same order.
        Returns ``()`` when *severities* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not severities:
        return ()
    counts: dict[str, int] = {}
    for p in problems:
        if p.problem_class == cls and p.severity:
            counts[p.severity] = counts.get(p.severity, 0) + 1
    return tuple(counts.get(sev, 0) for sev in severities)


def compare_severity_distributions(scan_a: list[Problem], scan_b: list[Problem]) -> dict[str, int]:
    """Return the per-severity delta between two scans (count_b - count_a).

    Only labelled problems (severity != '') are counted.  Severities that
    appear in only one scan use 0 for the other scan.

    Args:
        scan_a: List of :class:`Problem` instances from the baseline scan.
        scan_b: List of :class:`Problem` instances from the comparison scan.

    Returns:
        dict mapping severity label → (count_b - count_a).  Positive values
        mean the severity increased in scan_b; negative means it decreased.
        Empty dict when both scans are empty or all problems are unlabelled.

    Pure (no I/O, no SurrealDB).
    """

    def _counts(scan: list[Problem]) -> dict[str, int]:
        c: dict[str, int] = {}
        for p in scan:
            if p.severity:
                c[p.severity] = c.get(p.severity, 0) + 1
        return c

    counts_a = _counts(scan_a)
    counts_b = _counts(scan_b)
    all_severities = set(counts_a) | set(counts_b)
    return {sev: counts_b.get(sev, 0) - counts_a.get(sev, 0) for sev in all_severities}


def severity_change_summary(scan_a: list[Problem], scan_b: list[Problem]) -> dict[str, object]:
    """Return a human-readable summary of severity changes between two scans.

    Delegates to :func:`compare_severity_distributions` and categorises each
    severity into improved (negative delta), worsened (positive), or unchanged.

    Args:
        scan_a: Baseline scan (list of :class:`Problem` instances).
        scan_b: Comparison scan (list of :class:`Problem` instances).

    Returns:
        dict with exactly four keys:
        - "improved"  (list[str]): severities with fewer problems in scan_b.
        - "worsened"  (list[str]): severities with more problems in scan_b.
        - "unchanged" (list[str]): severities with no change.
        - "net_delta" (int): sum of all individual deltas.

    Pure (no I/O, no SurrealDB).
    """
    deltas = compare_severity_distributions(scan_a, scan_b)
    improved = sorted(sev for sev, d in deltas.items() if d < 0)
    worsened = sorted(sev for sev, d in deltas.items() if d > 0)
    unchanged = sorted(sev for sev, d in deltas.items() if d == 0)
    return {
        "improved": improved,
        "worsened": worsened,
        "unchanged": unchanged,
        "net_delta": sum(deltas.values()),
    }


def finding_ids_unique_to_class(problems: list[Problem]) -> dict[str, frozenset[str]]:
    """Return per-class frozensets of finding_ids that appear in ONLY that class.

    Finding_ids shared across two or more classes are excluded from all classes'
    frozensets.  Classes with no exclusive ids still appear with an empty frozenset.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping class_name → frozenset of finding_ids exclusive to that class.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    # Build finding_id -> set of classes that contain it
    id_to_classes: dict[str, set[str]] = {}
    for p in problems:
        id_to_classes.setdefault(p.finding_id, set()).add(p.problem_class)
    # Exclusive ids: those belonging to exactly one class
    exclusive_ids: set[str] = {fid for fid, classes in id_to_classes.items() if len(classes) == 1}
    # Build per-class frozensets of exclusive ids
    class_ids: dict[str, set[str]] = {}
    for p in problems:
        class_ids.setdefault(p.problem_class, set())
    for fid in exclusive_ids:
        cls = next(iter(id_to_classes[fid]))
        class_ids[cls].add(fid)
    return {cls: frozenset(ids) for cls, ids in class_ids.items()}


def finding_ids_by_class(problems: list[Problem]) -> dict[str, frozenset[str]]:
    """Return a mapping from each class to the frozenset of its finding_ids.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping class_name → frozenset of finding_id strings for all
        problems in that class.  Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    result: dict[str, set[str]] = {}
    for p in problems:
        result.setdefault(p.problem_class, set()).add(p.finding_id)
    return {cls: frozenset(ids) for cls, ids in result.items()}


def shared_finding_ids(problems: list[Problem]) -> frozenset[str]:
    """Return the frozenset of finding_ids that appear in two or more distinct classes.

    A finding_id is "shared" when it belongs to AT LEAST two distinct
    ``problem_class`` values.  Finding_ids exclusive to a single class are
    excluded.  This is the exact complement of the per-class frozensets
    returned by :func:`finding_ids_unique_to_class`.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        frozenset of finding_id strings that appear under 2+ distinct
        problem_class values.  Returns ``frozenset()`` when *problems* is
        empty or when every finding_id appears in only one class.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    # Invert: finding_id -> set of classes containing it
    id_to_classes: dict[str, set[str]] = {}
    for p in problems:
        id_to_classes.setdefault(p.finding_id, set()).add(p.problem_class)
    return frozenset(fid for fid, classes in id_to_classes.items() if len(classes) >= 2)


def all_class_pairs_by_overlap(
    problems: list[Problem],
) -> list[tuple[str, str, int]]:
    """Return all distinct class pairs ranked by their shared finding_id count.

    Each pair ``(cls_a, cls_b, count)`` satisfies ``cls_a < cls_b``
    (canonical alphabetical ordering).  All pairs of distinct classes are
    included, even those with zero overlap.  Returns ``[]`` when there is
    only one class or no problems.

    Sorting: primary key = count **descending**; tie-break = cls_a ascending,
    then cls_b ascending.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        List of ``(cls_a, cls_b, count)`` tuples, sorted by overlap descending
        then lexicographically.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return []
    # Build class -> frozenset of distinct finding_ids
    ids_by_cls: dict[str, frozenset[str]] = {}
    class_ids_mutable: dict[str, set[str]] = {}
    for p in problems:
        class_ids_mutable.setdefault(p.problem_class, set()).add(p.finding_id)
    ids_by_cls = {cls: frozenset(ids) for cls, ids in class_ids_mutable.items()}
    classes = sorted(ids_by_cls)
    if len(classes) < 2:
        return []
    result: list[tuple[str, str, int]] = []
    for i in range(len(classes)):
        for j in range(i + 1, len(classes)):
            cls_a = classes[i]
            cls_b = classes[j]
            count = len(ids_by_cls[cls_a] & ids_by_cls[cls_b])
            result.append((cls_a, cls_b, count))
    result.sort(key=lambda t: (-t[2], t[0], t[1]))
    return result


def class_co_occurrence_count(problems: list[Problem], cls_a: str, cls_b: str) -> int:
    """Return the number of distinct finding_ids shared between cls_a and cls_b.

    Counts DISTINCT finding_id values that appear in both classes, not Problem
    instances.  Duplicate Problems with the same finding_id contribute only once.

    When ``cls_a == cls_b`` the result is the count of distinct finding_ids in
    that class (intersection of the set with itself).  Returns 0 when either
    class is absent from *problems* or when *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        cls_a:    First class name.
        cls_b:    Second class name.

    Returns:
        int — cardinality of
        ``{ids in cls_a} ∩ {ids in cls_b}``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    ids_a: set[str] = {p.finding_id for p in problems if p.problem_class == cls_a}
    ids_b: set[str] = {p.finding_id for p in problems if p.problem_class == cls_b}
    return len(ids_a & ids_b)


def problem_count_by_severity_in_class(problems: list[Problem], cls: str) -> dict[str, int]:
    """Return {severity: count} for labelled problems in the specified class.

    Only problems whose ``problem_class == cls`` AND ``severity != ""`` are
    counted.  Unlabelled problems (``severity=""``) and problems from other
    classes are excluded.  Returns ``{}`` when the class is absent, all its
    problems are unlabelled, or *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        cls:      Target class name.

    Returns:
        dict mapping severity string → count of labelled problems.

    Pure (no I/O, no SurrealDB).
    """
    counts: dict[str, int] = {}
    for p in problems:
        if p.problem_class == cls and p.severity:
            counts[p.severity] = counts.get(p.severity, 0) + 1
    return counts


def dominant_severity_per_class(problems: list[Problem]) -> dict[str, str]:
    """Return the most common labelled severity for each class.

    For every class that has at least one labelled problem, maps the class name
    to its most frequent severity label.  Classes whose problems are all
    unlabelled (``severity=""``) are omitted from the result.

    Tie-breaking: when two severities share the same count, the
    lexicographically smallest severity label wins.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping class_name → dominant severity string.  Empty dict when
        *problems* is empty or no class has a labelled problem.

    Pure (no I/O, no SurrealDB).
    """
    # Accumulate per-class severity counts
    class_counts: dict[str, dict[str, int]] = {}
    for p in problems:
        if p.severity:
            class_counts.setdefault(p.problem_class, {})
            class_counts[p.problem_class][p.severity] = (
                class_counts[p.problem_class].get(p.severity, 0) + 1
            )
    # For each class pick the severity with max count (lex-smallest on tie)
    return {
        cls: max(sev_counts, key=lambda s: (sev_counts[s], [-ord(c) for c in s]))
        for cls, sev_counts in class_counts.items()
    }


def classes_without_severity(problems: list[Problem]) -> frozenset[str]:
    """Return the frozenset of class names where every problem is unlabelled.

    A class is included only when ALL of its problems have ``severity=""``.
    If a class has even one labelled problem it is excluded.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        frozenset of class names that have zero labelled problems.
        Returns ``frozenset()`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    all_classes: set[str] = set()
    labelled_classes: set[str] = set()
    for p in problems:
        all_classes.add(p.problem_class)
        if p.severity:
            labelled_classes.add(p.problem_class)
    return frozenset(all_classes - labelled_classes)


def labelling_coverage_fraction(problems: list[Problem]) -> float:
    """Return the fraction of problems that have a non-empty severity label.

    Coverage = len(labelled) / len(total).  A score of 1.0 means every
    problem is labelled; 0.0 means none are (or the input is empty).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        float in [0.0, 1.0] representing the labelling coverage.
        Returns 0.0 when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    total = len(problems)
    if total == 0:
        return 0.0
    labelled = sum(1 for p in problems if p.severity)
    return float(labelled / total)


def per_class_labelling_coverage(problems: list[Problem]) -> dict[str, float]:
    """Return the labelling coverage fraction for each class individually.

    For every class, computes ``labelled_in_class / total_in_class`` where the
    denominator is the class's OWN problem count (not the global total).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping class_name → float coverage in [0.0, 1.0].
        Returns ``{}`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    # Accumulate per-class (total, labelled) counts
    totals: dict[str, int] = {}
    labelled_counts: dict[str, int] = {}
    for p in problems:
        totals[p.problem_class] = totals.get(p.problem_class, 0) + 1
        if p.severity:
            labelled_counts[p.problem_class] = labelled_counts.get(p.problem_class, 0) + 1
    return {cls: float(labelled_counts.get(cls, 0) / totals[cls]) for cls in totals}


def worst_labelled_classes(problems: list[Problem]) -> list[tuple[str, float]]:
    """Return classes sorted by labelling coverage ascending (worst first).

    Delegates per-class coverage to :func:`per_class_labelling_coverage` then
    sorts by coverage ascending with class name as the lexicographic tie-breaker.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        List of ``(class_name, coverage)`` tuples sorted by coverage ascending,
        then class name ascending on ties.  Returns ``[]`` when *problems* is
        empty.

    Pure (no I/O, no SurrealDB).
    """
    coverage = per_class_labelling_coverage(problems)
    return sorted(coverage.items(), key=lambda t: (t[1], t[0]))


def problem_class_profile(problems: list[Problem], cls: str) -> dict[str, object]:
    """Return a structured summary profile for a single problem class.

    Bundles five per-class metrics:

    * ``total``             — total Problem count in this class (0 if absent).
    * ``unique_ids``        — count of DISTINCT finding_ids in this class (0 if absent).
    * ``labelling_coverage``— fraction of class problems with a severity label (0.0 if absent).
    * ``dominant_severity`` — most-common labelled severity (None if all unlabelled or absent).
    * ``severity_counts``   — {severity: count} for labelled problems (excludes severity='').

    Args:
        problems: List of :class:`Problem` instances from a scan.
        cls:      Target class name.

    Returns:
        dict with exactly the five keys above.  Always returns all five keys —
        never raises even when the class is absent.

    Pure (no I/O, no SurrealDB).
    """
    class_problems = [p for p in problems if p.problem_class == cls]
    total = len(class_problems)
    unique_ids = len({p.finding_id for p in class_problems})
    if total == 0:
        return {
            "total": 0,
            "unique_ids": 0,
            "labelling_coverage": 0.0,
            "dominant_severity": None,
            "severity_counts": {},
        }
    labelled = sum(1 for p in class_problems if p.severity)
    labelling_coverage = float(labelled / total)
    # severity_counts (labelled only)
    severity_counts: dict[str, int] = {}
    for p in class_problems:
        if p.severity:
            severity_counts[p.severity] = severity_counts.get(p.severity, 0) + 1
    # dominant severity — None when no labelled problems
    dominant_severity: str | None = None
    if severity_counts:
        dominant_severity = max(
            severity_counts, key=lambda s: (severity_counts[s], [-ord(c) for c in s])
        )
    return {
        "total": total,
        "unique_ids": unique_ids,
        "labelling_coverage": labelling_coverage,
        "dominant_severity": dominant_severity,
        "severity_counts": severity_counts,
    }


def full_scan_report(problems: list[Problem]) -> dict[str, object]:
    """Return a richer top-level structured summary for an entire scan.

    Provides seven keys that extend beyond the basic :func:`scan_summary`:

    * ``total``                — total Problem count.
    * ``unique_ids``           — count of GLOBALLY distinct finding_ids
                                 (shared ids counted once, not per class).
    * ``class_count``          — number of distinct problem classes.
    * ``labelling_coverage``   — fraction of problems with a severity label.
    * ``severity_distribution``— {severity: count} for labelled problems only.
    * ``top_class_by_count``   — class with the most total problems; ``None``
                                 if empty; tie-break: alphabetically smallest.
    * ``most_critical_class``  — class with the most CRITICAL problems; falls
                                 back to the class with the most HIGH problems
                                 when no CRITICAL exist; ``None`` if empty or
                                 no labelled problems at all.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict with exactly the seven keys above.  All keys present even when
        *problems* is empty (zero/None/empty defaults).

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {
            "total": 0,
            "unique_ids": 0,
            "class_count": 0,
            "labelling_coverage": 0.0,
            "severity_distribution": {},
            "top_class_by_count": None,
            "most_critical_class": None,
        }

    total = len(problems)
    unique_ids = len({p.finding_id for p in problems})
    class_count = len({p.problem_class for p in problems})

    # labelling_coverage
    labelled_count = sum(1 for p in problems if p.severity)
    labelling_coverage = float(labelled_count / total)

    # severity_distribution (labelled only)
    severity_distribution: dict[str, int] = {}
    for p in problems:
        if p.severity:
            severity_distribution[p.severity] = severity_distribution.get(p.severity, 0) + 1

    # top_class_by_count
    class_totals: dict[str, int] = {}
    for p in problems:
        class_totals[p.problem_class] = class_totals.get(p.problem_class, 0) + 1
    top_class_by_count: str | None = min(class_totals, key=lambda c: (-class_totals[c], c))

    # most_critical_class: prefer CRITICAL, fallback to HIGH
    most_critical_class: str | None = None
    for target_sev in ("CRITICAL", "HIGH"):
        sev_counts: dict[str, int] = {}
        for p in problems:
            if p.severity == target_sev:
                sev_counts[p.problem_class] = sev_counts.get(p.problem_class, 0) + 1
        if sev_counts:
            most_critical_class = min(sev_counts, key=lambda c: (-sev_counts[c], c))
            break

    return {
        "total": total,
        "unique_ids": unique_ids,
        "class_count": class_count,
        "labelling_coverage": labelling_coverage,
        "severity_distribution": severity_distribution,
        "top_class_by_count": top_class_by_count,
        "most_critical_class": most_critical_class,
    }


def severity_escalation_classes(
    scan_a: list[Problem],
    scan_b: list[Problem],
    severity: str,
) -> frozenset[str]:
    """Return classes where the count of *severity*-labelled problems strictly increased.

    A class is "escalated" when its count of problems with ``severity`` in
    *scan_b* is STRICTLY GREATER than in *scan_a* (``count_b > count_a``).
    New classes in *scan_b* only (count_a = 0) are included when count_b > 0.

    Args:
        scan_a:    Earlier scan's :class:`Problem` list.
        scan_b:    Later scan's :class:`Problem` list.
        severity:  The severity label to track (e.g. ``"CRITICAL"``).

    Returns:
        frozenset of class names where the *severity* count strictly increased.
        Returns ``frozenset()`` when both scans are empty or severity is absent.

    Pure (no I/O, no SurrealDB).
    """

    def _class_severity_counts(scan: list[Problem], sev: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in scan:
            if p.severity == sev:
                counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
        return counts

    counts_a = _class_severity_counts(scan_a, severity)
    counts_b = _class_severity_counts(scan_b, severity)
    all_classes = set(counts_a) | set(counts_b)
    return frozenset(cls for cls in all_classes if counts_b.get(cls, 0) > counts_a.get(cls, 0))


def severity_improvement_classes(
    scan_a: list[Problem],
    scan_b: list[Problem],
    severity: str,
) -> frozenset[str]:
    """Return classes where the count of *severity*-labelled problems strictly decreased.

    A class is "improved" when its count of problems with ``severity`` in
    *scan_b* is STRICTLY LESS than in *scan_a* (``count_b < count_a``).
    Classes present only in *scan_b* (count_a = 0) are excluded.
    Classes disappearing completely (count_b = 0, count_a > 0) ARE included.

    Args:
        scan_a:    Earlier scan's :class:`Problem` list.
        scan_b:    Later scan's :class:`Problem` list.
        severity:  The severity label to track (e.g. ``"CRITICAL"``).

    Returns:
        frozenset of class names where the *severity* count strictly decreased.
        Returns ``frozenset()`` when both scans are empty or severity is absent.

    Pure (no I/O, no SurrealDB).
    """

    def _class_severity_counts(scan: list[Problem], sev: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in scan:
            if p.severity == sev:
                counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
        return counts

    counts_a = _class_severity_counts(scan_a, severity)
    counts_b = _class_severity_counts(scan_b, severity)
    all_classes = set(counts_a) | set(counts_b)
    return frozenset(cls for cls in all_classes if counts_b.get(cls, 0) < counts_a.get(cls, 0))


def cross_scan_class_delta(
    scan_a: list[Problem],
    scan_b: list[Problem],
) -> dict[str, int]:
    """Return per-class total problem count delta between two scans.

    For every class appearing in either scan, computes
    ``count_b(cls) - count_a(cls)``.

    * Positive delta — more problems in scan_b (class grew or appeared).
    * Zero delta     — unchanged class count (class present in result with 0).
    * Negative delta — fewer problems in scan_b (class shrank or disappeared).

    Args:
        scan_a: Problems from the baseline scan.
        scan_b: Problems from the comparison scan.

    Returns:
        dict mapping class name to integer delta.  Every class that appears in
        either scan is included, even if delta is 0.  Returns ``{}`` when both
        scans are empty.

    Pure (no I/O, no SurrealDB).
    """

    def _class_counts(scan: list[Problem]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in scan:
            counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
        return counts

    counts_a = _class_counts(scan_a)
    counts_b = _class_counts(scan_b)
    all_classes = set(counts_a) | set(counts_b)
    return {cls: counts_b.get(cls, 0) - counts_a.get(cls, 0) for cls in all_classes}


def top_growing_classes(
    scan_a: list[Problem],
    scan_b: list[Problem],
    n: int = 5,
) -> list[tuple[str, int]]:
    """Return the top *n* classes with the largest positive problem count delta.

    Uses :func:`cross_scan_class_delta` internally and filters to ``delta > 0``.
    Sorted by delta descending; ties broken by class name ascending.

    Args:
        scan_a: Problems from the baseline scan.
        scan_b: Problems from the comparison scan.
        n:      Maximum number of results to return (default 5).
                ``n=0`` returns an empty list.

    Returns:
        List of ``(class, delta)`` tuples.  Only classes with strictly positive
        delta are included.  Returns ``[]`` when *n* is 0, when both scans are
        empty, or when no class grew.

    Pure (no I/O, no SurrealDB).
    """
    if n == 0:
        return []
    deltas = cross_scan_class_delta(scan_a, scan_b)
    growing = [(cls, delta) for cls, delta in deltas.items() if delta > 0]
    growing.sort(key=lambda pair: (-pair[1], pair[0]))
    return growing[:n]


def top_shrinking_classes(
    scan_a: list[Problem],
    scan_b: list[Problem],
    n: int = 5,
) -> list[tuple[str, int]]:
    """Return the top *n* classes with the most negative problem count delta.

    Uses :func:`cross_scan_class_delta` internally and filters to ``delta < 0``.
    Sorted by delta ascending (most negative / most improved first); ties
    broken by class name ascending.

    Args:
        scan_a: Problems from the baseline scan.
        scan_b: Problems from the comparison scan.
        n:      Maximum number of results to return (default 5).
                ``n=0`` returns an empty list.

    Returns:
        List of ``(class, delta)`` tuples.  Only classes with strictly negative
        delta are included.  Returns ``[]`` when *n* is 0, when both scans are
        empty, or when no class shrank.

    Pure (no I/O, no SurrealDB).
    """
    if n == 0:
        return []
    deltas = cross_scan_class_delta(scan_a, scan_b)
    shrinking = [(cls, delta) for cls, delta in deltas.items() if delta < 0]
    shrinking.sort(key=lambda pair: (pair[1], pair[0]))
    return shrinking[:n]


def class_stability_report(
    scan_a: list[Problem],
    scan_b: list[Problem],
) -> dict[str, str]:
    """Classify every class across two scans as "growing", "stable", or "shrinking".

    Uses :func:`cross_scan_class_delta` to compute per-class deltas, then maps:
    - ``delta > 0`` → ``"growing"``
    - ``delta == 0`` → ``"stable"``
    - ``delta < 0`` → ``"shrinking"``

    Every class appearing in either scan is included.  Classes with unchanged
    count are labelled ``"stable"`` (not omitted), distinguishing this function
    from :func:`top_growing_classes` / :func:`top_shrinking_classes` which filter
    to non-zero deltas only.

    Args:
        scan_a: Problems from the baseline scan.
        scan_b: Problems from the comparison scan.

    Returns:
        Dict mapping class name → stability label.  Returns ``{}`` when both
        scans are empty.

    Pure (no I/O, no SurrealDB).
    """
    deltas = cross_scan_class_delta(scan_a, scan_b)
    return {
        cls: ("growing" if d > 0 else "shrinking" if d < 0 else "stable")
        for cls, d in deltas.items()
    }


def scan_diff_summary(
    scan_a: list[Problem],
    scan_b: list[Problem],
) -> dict[str, int]:
    """Return aggregate statistics comparing two problem scans.

    Keys returned:
    - ``total_a`` / ``total_b`` — raw problem counts for each scan.
    - ``delta_total`` — ``total_b - total_a`` (positive = more in scan_b).
    - ``classes_grown`` — count of classes where ``delta > 0``.
    - ``classes_stable`` — count of classes where ``delta == 0``.
    - ``classes_shrunk`` — count of classes where ``delta < 0``.
    - ``new_classes`` — classes in scan_b but absent from scan_a.
    - ``disappeared_classes`` — classes in scan_a but absent from scan_b.

    Note: ``new_classes`` ⊆ ``classes_grown`` and
    ``disappeared_classes`` ⊆ ``classes_shrunk``, because a class absent
    in one scan has an implicit count of 0.

    Args:
        scan_a: Problems from the baseline scan.
        scan_b: Problems from the comparison scan.

    Returns:
        Dict with 8 integer-valued keys.  Returns all-zero dict when both
        scans are empty.

    Pure (no I/O, no SurrealDB).
    """
    total_a = len(scan_a)
    total_b = len(scan_b)
    classes_a: set[str] = {p.problem_class for p in scan_a}
    classes_b: set[str] = {p.problem_class for p in scan_b}
    stability = class_stability_report(scan_a, scan_b)
    classes_grown = sum(1 for label in stability.values() if label == "growing")
    classes_stable = sum(1 for label in stability.values() if label == "stable")
    classes_shrunk = sum(1 for label in stability.values() if label == "shrinking")
    new_classes = len(classes_b - classes_a)
    disappeared_classes = len(classes_a - classes_b)
    return {
        "total_a": total_a,
        "total_b": total_b,
        "delta_total": total_b - total_a,
        "classes_grown": classes_grown,
        "classes_stable": classes_stable,
        "classes_shrunk": classes_shrunk,
        "new_classes": new_classes,
        "disappeared_classes": disappeared_classes,
    }


def severity_delta_per_class(
    scan_a: list[Problem],
    scan_b: list[Problem],
) -> dict[str, dict[str, int]]:
    """Return per-class, per-severity count deltas between two scans.

    For every ``(class, severity)`` pair that exists in either scan with a
    non-zero delta, returns ``count_b - count_a``.  Pairs with zero delta are
    omitted (no change = not interesting in a diff context).  Problems with an
    empty severity label are ignored.

    Args:
        scan_a: Problems from the baseline scan.
        scan_b: Problems from the comparison scan.

    Returns:
        Nested dict ``{class_name: {severity: delta}}``.  Only classes with at
        least one non-zero severity delta have an entry.  Returns ``{}`` when
        both scans are empty.

    Pure (no I/O, no SurrealDB).
    """

    # Build per-(class, severity) counts for each scan, ignoring unlabelled.
    def _counts(scan: list[Problem]) -> dict[tuple[str, str], int]:
        c: dict[tuple[str, str], int] = {}
        for p in scan:
            if p.severity:
                key = (p.problem_class, p.severity)
                c[key] = c.get(key, 0) + 1
        return c

    counts_a = _counts(scan_a)
    counts_b = _counts(scan_b)
    all_keys = set(counts_a) | set(counts_b)

    result: dict[str, dict[str, int]] = {}
    for cls, sev in all_keys:
        delta = counts_b.get((cls, sev), 0) - counts_a.get((cls, sev), 0)
        if delta != 0:
            result.setdefault(cls, {})[sev] = delta
    return result


def most_volatile_class(
    scan_a: list[Problem],
    scan_b: list[Problem],
) -> str | None:
    """Return the class name with the highest total absolute severity delta.

    Uses :func:`severity_delta_per_class` to obtain per-class, per-severity
    deltas, then sums ``abs(delta)`` across all severities for each class to
    compute a *volatility score*.  The class with the highest score is returned.
    Ties are broken by class name ascending (lexicographically smallest wins).

    Returns ``None`` when no labelled problems exist in either scan (i.e. when
    ``severity_delta_per_class`` returns an empty dict).

    Args:
        scan_a: Problems from the baseline scan.
        scan_b: Problems from the comparison scan.

    Returns:
        Class name with maximum total absolute delta, or ``None``.

    Pure (no I/O, no SurrealDB).
    """
    deltas = severity_delta_per_class(scan_a, scan_b)
    if not deltas:
        return None
    return max(
        deltas,
        key=lambda cls: (sum(abs(v) for v in deltas[cls].values()), [-ord(c) for c in cls]),
    )


def severity_heatmap(
    problems: list[Problem],
) -> dict[str, dict[str, int]]:
    """Return a class × severity count matrix for a single problem scan.

    Builds a two-dimensional count of problems grouped by class and then by
    severity.  Only labelled problems (``severity != ''``) contribute.  Classes
    whose problems are all unlabelled are omitted from the result.

    This is equivalent to calling :func:`problem_count_by_severity_in_class`
    for every class simultaneously, but in a single pass.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        ``{class_name: {severity: count}}``.  Inner dict only contains
        severities with at least one problem (no zero-count keys).  Returns
        ``{}`` when *problems* is empty or all problems are unlabelled.

    Pure (no I/O, no SurrealDB).
    """
    result: dict[str, dict[str, int]] = {}
    for p in problems:
        if p.severity:
            inner = result.setdefault(p.problem_class, {})
            inner[p.severity] = inner.get(p.severity, 0) + 1
    return result


def most_severe_class(
    problems: list[Problem],
    severity_order: list[str],
) -> str | None:
    """Return the class whose dominant severity ranks highest in *severity_order*.

    Uses :func:`dominant_severity_per_class` to determine each class's dominant
    severity, then ranks those severities by their position in *severity_order*
    (lower index = higher priority).  Classes whose dominant severity is absent
    from *severity_order* are treated as having the lowest possible rank.

    Ties in rank are broken by class name ascending (lexicographically smallest
    class name wins when two classes share the same severity rank).

    Args:
        problems:       Flat list of :class:`Problem` records.
        severity_order: Caller-supplied list of severity strings from most
                        severe to least severe (e.g. ``["CRITICAL","HIGH","LOW"]``).

    Returns:
        Class name with the highest-priority dominant severity, or ``None``
        when there are no labelled classes.

    Pure (no I/O, no SurrealDB).
    """
    dominant = dominant_severity_per_class(problems)
    if not dominant:
        return None
    # Build rank lookup; absent severities get the worst rank.
    worst_rank = len(severity_order)
    rank = {sev: idx for idx, sev in enumerate(severity_order)}
    return min(
        dominant,
        key=lambda cls: (rank.get(dominant[cls], worst_rank), cls),
    )


def classes_above_severity_threshold(
    problems: list[Problem],
    severity_order: list[str],
    threshold: str,
    n: int = 1,
) -> frozenset[str]:
    """Return classes with at least *n* problems at or above *threshold* severity.

    "At or above" means the problem's severity has the same rank as *threshold*
    or a more-severe (lower-index) rank in *severity_order*.  Problems whose
    severity is absent from *severity_order* are treated as below every threshold
    (not counted).

    Special case: ``n=0`` returns a frozenset of **all** class names present in
    *problems* (regardless of threshold), because any non-negative count ≥ 0.

    Args:
        problems:       Flat list of :class:`Problem` records.
        severity_order: Severity strings from most severe to least severe.
        threshold:      The minimum severity level to count.
        n:              Minimum cumulative count required (default 1).

    Returns:
        Frozenset of class names satisfying the criterion.  Returns
        ``frozenset()`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    # n=0: every class qualifies trivially.
    if n == 0:
        return frozenset(p.problem_class for p in problems)
    # Determine the threshold rank; problems with lower rank (more severe) also count.
    rank = {sev: idx for idx, sev in enumerate(severity_order)}
    threshold_rank = rank.get(threshold, len(severity_order))
    # Sum counts at or above threshold rank per class.
    class_counts: dict[str, int] = {}
    for p in problems:
        sev_rank = rank.get(p.severity, len(severity_order))
        if sev_rank <= threshold_rank:
            class_counts[p.problem_class] = class_counts.get(p.problem_class, 0) + 1
    return frozenset(cls for cls, count in class_counts.items() if count >= n)


def finding_id_severity_map(
    problems: list[Problem],
) -> dict[str, frozenset[str]]:
    """Map each finding_id to the frozenset of labelled severities it carries.

    A finding_id may appear in multiple :class:`Problem` records across different
    classes or with different severity labels.  This function collects the
    distinct *labelled* severities for each finding_id.  Problems with
    ``severity=''`` (unlabelled) do not contribute to the frozenset.
    Finding_ids whose records are all unlabelled are omitted from the result.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        ``{finding_id: frozenset[severity]}``.  Only finding_ids with at
        least one labelled record appear.  Each frozenset contains only
        non-empty severity strings.  Returns ``{}`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    id_severities: dict[str, set[str]] = {}
    for p in problems:
        if p.severity:
            id_severities.setdefault(p.finding_id, set()).add(p.severity)
    return {fid: frozenset(sevs) for fid, sevs in id_severities.items()}


def multi_severity_finding_ids(
    problems: list[Problem],
) -> frozenset[str]:
    """Return finding_ids that carry two or more distinct labelled severities.

    A finding_id that appears in records with different severity labels (e.g.
    ``HIGH`` in one record and ``LOW`` in another) has a labelling conflict or
    progressive escalation.  This function surfaces such ids by delegating to
    :func:`finding_id_severity_map` and filtering to entries with
    ``len(severity_set) >= 2``.

    Finding_ids with a single repeated severity (e.g. ``HIGH`` in 10 records)
    are excluded because they have only one *distinct* severity label.
    Unlabelled-only finding_ids are also excluded (they never appear in
    ``finding_id_severity_map``).

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Frozenset of finding_ids with ≥ 2 distinct labelled severities.
        Returns ``frozenset()`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    severity_map = finding_id_severity_map(problems)
    return frozenset(fid for fid, sevs in severity_map.items() if len(sevs) >= 2)


def problems_by_finding_id(
    problems: list[Problem],
) -> dict[str, list[Problem]]:
    """Group :class:`Problem` records by their ``finding_id``.

    Returns a dict mapping each distinct ``finding_id`` to the list of
    :class:`Problem` records that carry it, preserving their original order
    from the input list.  All records are included — both labelled and
    unlabelled — unlike :func:`finding_id_severity_map` which excludes
    unlabelled records.

    Useful for drilling into a specific finding to inspect how it is classified
    across different problem classes or severities.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        ``{finding_id: [Problem, ...]}``.  Returns ``{}`` when *problems*
        is empty.

    Pure (no I/O, no SurrealDB).
    """
    result: dict[str, list[Problem]] = {}
    for p in problems:
        result.setdefault(p.finding_id, []).append(p)
    return result


def problem_class_pairs(
    problems: list[Problem],
) -> frozenset[frozenset[str]]:
    """Return the set of all unordered pairs of distinct problem classes.

    For every pair of distinct classes ``(a, b)`` both of which appear at
    least once in *problems*, returns a 2-element ``frozenset({a, b})``.
    Each unordered pair appears exactly once.  Classes with no problems are
    excluded (irrelevant here since we derive classes from *problems*).

    If *problems* contains fewer than 2 distinct classes, returns an empty
    frozenset because no pair can be formed.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Frozenset of 2-element frozensets.  Returns ``frozenset()`` when
        *problems* is empty or has fewer than 2 distinct classes.

    Pure (no I/O, no SurrealDB).
    """
    classes = sorted({p.problem_class for p in problems})
    if len(classes) < 2:
        return frozenset()
    return frozenset(
        frozenset({classes[i], classes[j]})
        for i in range(len(classes))
        for j in range(i + 1, len(classes))
    )


def unique_finding_ids_across_classes(
    problems: list[Problem],
) -> frozenset[str]:
    """Return finding_ids that appear in exactly one distinct problem class.

    A finding_id is *unique to one class* when all of its :class:`Problem`
    records belong to the same ``problem_class``.  Finding_ids that appear in
    records from two or more distinct classes are excluded (they are *shared*,
    as detected by :func:`shared_finding_ids`).

    A finding_id may appear in multiple records within the same class — the
    record count is irrelevant; only the count of *distinct classes* matters.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Frozenset of finding_ids with exactly one distinct class.  Returns
        ``frozenset()`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    id_to_classes: dict[str, set[str]] = {}
    for p in problems:
        id_to_classes.setdefault(p.finding_id, set()).add(p.problem_class)
    return frozenset(fid for fid, classes in id_to_classes.items() if len(classes) == 1)


def problem_density_by_class(problems: list[Problem]) -> dict[str, float]:
    """Return each class's share of total problems as a float in [0.0, 1.0].

    Density is ``count(class) / len(problems)``.  All densities sum to 1.0
    (within floating-point precision).

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        ``{class_name: density}`` where density ∈ [0.0, 1.0].  Returns ``{}``
        when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    total = len(problems)
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return {cls: cnt / total for cls, cnt in counts.items()}


def problems_above_density_threshold(
    problems: list[Problem],
    threshold: float,
) -> list[Problem]:
    """Return problems whose class density (class_count/total) >= threshold — item 331.

    Delegates density computation to :func:`problem_density_by_class` and
    filters the original list to retain only problems whose class meets or
    exceeds the threshold.  Insertion order is preserved.

    Args:
        problems:
            Flat list of :class:`Problem` records.  Empty list -> ``[]``.
        threshold:
            Minimum density (inclusive) for a class to qualify.  A value of
            ``0.0`` returns all problems; a value above ``1.0`` returns ``[]``
            because no class density can exceed 1.0.

    Returns:
        A new list of :class:`Problem` objects, preserving the original order,
        from classes whose density >= threshold.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return []
    densities = problem_density_by_class(problems)
    qualifying = {cls for cls, d in densities.items() if d >= threshold}
    return [p for p in problems if p.problem_class in qualifying]


def problems_below_density_threshold(
    problems: list[Problem],
    threshold: float,
) -> list[Problem]:
    """Return problems whose class density (class_count/total) < threshold -- item 332.

    Symmetric complement of :func:`problems_above_density_threshold` -- together
    they form a disjoint partition of the full problem list (above uses ``>=``,
    below uses ``<``).

    Args:
        problems:
            Flat list of :class:`Problem` records.  Empty list -> ``[]``.
        threshold:
            Exclusive upper bound on density for a class to qualify.  A value
            of ``0.0`` returns ``[]`` (no density is below 0.0); a value above
            ``1.0`` returns all problems (every class has density <= 1.0).

    Returns:
        A new list of :class:`Problem` objects, preserving the original order,
        from classes whose density < threshold.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return []
    densities = problem_density_by_class(problems)
    qualifying = {cls for cls, d in densities.items() if d < threshold}
    return [p for p in problems if p.problem_class in qualifying]


def severity_density_by_class(
    problems: list[Problem],
) -> dict[str, dict[str, float]]:
    """Return a nested density map: ``{class: {severity: count/class_total}}``.

    For each class, the denominator is the total number of problems **in that
    class** (not the grand total).  Only labelled problems (``severity != ''``)
    contribute to the inner dict; unlabelled problems reduce the per-class sum
    below 1.0 but are not themselves listed.  Classes that have no labelled
    problems at all are omitted entirely.  The empty-string key ``''`` never
    appears as an inner-dict key.

    Density = count(class, severity) / count(class).

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Nested ``{class_name: {severity_label: density}}`` where each density
        value is in ``[0.0, 1.0]``.  Returns ``{}`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    class_total: dict[str, int] = {}
    class_sev_counts: dict[str, dict[str, int]] = {}
    for p in problems:
        class_total[p.problem_class] = class_total.get(p.problem_class, 0) + 1
        if p.severity:
            inner = class_sev_counts.setdefault(p.problem_class, {})
            inner[p.severity] = inner.get(p.severity, 0) + 1
    result: dict[str, dict[str, float]] = {}
    for cls, sev_counts in class_sev_counts.items():
        total = class_total[cls]
        result[cls] = {sev: cnt / total for sev, cnt in sev_counts.items()}
    return result


def severity_entropy_map(problems: list[Problem]) -> dict[str, float]:
    """Return a Shannon-entropy value for each class's labelled-severity distribution.

    For each class present in *problems*, computes::

        H(class) = -sum(p_i * log2(p_i))

    where ``p_i = count(class, severity_i) / total_labelled(class)``.  The
    denominator is the count of **labelled** (non-empty severity) problems for
    that class, mirroring the convention of
    :func:`class_severity_entropy` (the existing per-class helper).

    Unlabelled problems are excluded from both the counts and the total.
    Classes that have **zero labelled problems** are still included in the
    result, with ``H = 0.0`` (maximum certainty — there is nothing to be
    uncertain about).  Classes with exactly one distinct labelled severity also
    return ``H = 0.0``.

    This is the batch counterpart of :func:`class_severity_entropy`.

    Args:
        problems: Flat list of :class:`Problem` records from a single scan.

    Returns:
        ``{class_name: entropy_in_bits}`` for every class observed in
        *problems*.  Returns ``{}`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    # Collect all classes and their labelled-severity counts.
    all_classes: set[str] = set()
    labelled_counts: dict[str, dict[str, int]] = {}
    for p in problems:
        all_classes.add(p.problem_class)
        if p.severity:
            inner = labelled_counts.setdefault(p.problem_class, {})
            inner[p.severity] = inner.get(p.severity, 0) + 1
    result: dict[str, float] = {}
    for cls in all_classes:
        counts = labelled_counts.get(cls, {})
        total = sum(counts.values())
        if total == 0:
            result[cls] = 0.0
        else:
            result[cls] = float(-sum((c / total) * math.log2(c / total) for c in counts.values()))
    return result


def severity_entropy_by_class(problems: list[Problem]) -> dict[str, float]:
    """Return the Shannon entropy (bits) of the severity distribution for every class.

    For each class, computes H = -Σ p_i * log2(p_i) over the labelled severity
    fractions within that class.  The denominator is the class-local total
    (consistent with :func:`severity_density_by_class`).

    Unlabelled problems (``severity=""``) are excluded from the distribution
    but DO count towards the per-class total.  A class whose problems are all
    unlabelled has H = 0.0 (not omitted).  A class with exactly one distinct
    labelled severity also has H = 0.0 (maximally certain).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping each class name → Shannon entropy in bits (float ≥ 0.0).
        Empty input → {}.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    # Per-class totals (all problems) and per-(class, severity) labelled counts
    class_total: dict[str, int] = {}
    sev_counts: dict[str, dict[str, int]] = {}
    for p in problems:
        class_total[p.problem_class] = class_total.get(p.problem_class, 0) + 1
        if p.severity:
            inner = sev_counts.setdefault(p.problem_class, {})
            inner[p.severity] = inner.get(p.severity, 0) + 1
    result: dict[str, float] = {}
    for cls, total in class_total.items():
        counts = sev_counts.get(cls, {})
        if not counts:
            result[cls] = 0.0
        else:
            result[cls] = float(-sum((c / total) * math.log2(c / total) for c in counts.values()))
    return result


def highest_entropy_class_in_scan(problems: list[Problem]) -> str | None:
    """Return the class name with the highest severity-distribution entropy.

    Delegates to :func:`severity_entropy_by_class` for per-class Shannon
    entropy values and returns the class name whose entropy is maximum.

    Tie-break: alphabetically ascending class name (smallest name wins).

    Returns ``None`` when:
    - *problems* is empty, OR
    - every class has entropy 0.0 (no class has more than one distinct
      labelled severity — no spread to distinguish).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        Class name with the highest Shannon entropy, or ``None``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    entropies = severity_entropy_by_class(problems)
    # Only consider classes with meaningful entropy (> 0.0)
    nonzero = {cls: h for cls, h in entropies.items() if h > 0.0}
    if not nonzero:
        return None
    return min(nonzero, key=lambda cls: (-nonzero[cls], cls))


def class_count_by_severity(problems: list[Problem]) -> dict[str, int]:
    """Return the number of distinct classes that have ≥1 problem at each severity.

    This is the inverse aggregation of :func:`severity_heatmap`: instead of
    asking "how many problems of severity S does class C have?" it asks "how
    many distinct classes are exposed to severity S?"

    Only labelled problems (``severity != ''``) contribute.  A class with
    five HIGH-severity problems still counts as **one** class for the ``HIGH``
    bucket.  The empty-string key ``''`` is never present in the result.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        ``{severity_label: distinct_class_count}`` for every non-empty
        severity label present in *problems*.  Returns ``{}`` when *problems*
        is empty or all severities are unlabelled.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    sev_classes: dict[str, set[str]] = {}
    for p in problems:
        if p.severity:
            sev_classes.setdefault(p.severity, set()).add(p.problem_class)
    return {sev: len(classes) for sev, classes in sev_classes.items()}


def severity_coverage_ratio(problems: list[Problem]) -> dict[str, float]:
    """Return the fraction of all classes affected by each labelled severity.

    Normalises :func:`class_count_by_severity` by the total number of distinct
    classes present in the scan (including classes that have only unlabelled
    problems).  A ratio of 1.0 means every class in the scan has at least one
    problem at that severity.

    Unlabelled problems (severity='') are excluded from the numerator but the
    classes they belong to still count in the denominator.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping severity_label → fraction of all classes affected (float
        in [0.0, 1.0]).  Empty input → {}.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    total_classes = len({p.problem_class for p in problems})
    counts = class_count_by_severity(problems)
    return {sev: count / total_classes for sev, count in counts.items()}


def class_finding_id_counts(problems: list[Problem]) -> dict[str, int]:
    """Return the number of distinct finding_ids for each class.

    Counts how many unique ``finding_id`` values appear in the problems
    belonging to each class.  A finding_id that appears in multiple records
    of the same class still counts as 1.  All problems are included regardless
    of severity label (including unlabelled).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping class_name → distinct finding_id count.
        Empty input → {}.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    class_fids: dict[str, set[str]] = {}
    for p in problems:
        class_fids.setdefault(p.problem_class, set()).add(p.finding_id)
    return {cls: len(fids) for cls, fids in class_fids.items()}


def finding_id_class_map(problems: list[Problem]) -> dict[str, frozenset[str]]:
    """Return an inverse index mapping each finding_id to the classes it appears in.

    For every unique ``finding_id`` in *problems*, builds the frozenset of
    class names (``problem_class``) that contain at least one Problem with
    that finding_id.  All problems are included regardless of severity label
    (including unlabelled).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping finding_id → frozenset of class names that contain it.
        Empty input → {}.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    fid_classes: dict[str, set[str]] = {}
    for p in problems:
        fid_classes.setdefault(p.finding_id, set()).add(p.problem_class)
    return {fid: frozenset(classes) for fid, classes in fid_classes.items()}


def cross_class_finding_ids(problems: list[Problem]) -> frozenset[str]:
    """Return finding_ids that appear in two or more distinct classes.

    Delegates to :func:`finding_id_class_map` to build the per-fid class set,
    then filters to those with cardinality ≥ 2.  A finding_id that occurs N
    times in a single class still belongs to only one class and is excluded.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        ``frozenset`` of finding_id strings that span ≥ 2 distinct classes.
        Returns ``frozenset()`` when *problems* is empty or no finding_id
        appears in more than one class.

    Pure (no I/O, no SurrealDB).
    """
    return frozenset(
        fid for fid, classes in finding_id_class_map(problems).items() if len(classes) >= 2
    )


def most_common_finding_id(problems: list[Problem]) -> str | None:
    """Return the finding_id with the highest total Problem record count.

    Counts raw Problem records per finding_id (not distinct classes or
    distinct severities).  Tie-break: alphabetically ascending finding_id
    (lexicographically smallest wins).

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        The finding_id string with the most records, or ``None`` when
        *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return min(counts, key=lambda fid: (-counts[fid], fid))


def problem_count_by_severity(problems: list[Problem]) -> dict[str, int]:
    """Return the total number of Problem records at each labelled severity.

    Counts raw Problem records per severity label across all classes.  Unlike
    :func:`class_count_by_severity` (which counts distinct classes), this
    function counts total records — a class with five HIGH problems contributes
    5 to the HIGH bucket.

    Unlabelled problems (severity='') are excluded from both keys and counts.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        dict mapping severity_label → total record count.  Empty input → {}.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    result: dict[str, int] = {}
    for p in problems:
        if p.severity:
            result[p.severity] = result.get(p.severity, 0) + 1
    return result


def severity_rank_distribution(
    problems: list[Problem],
    severity_order: list[str],
) -> dict[str, float]:
    """Return the fraction of total labelled problems at each severity.

    For every severity label that has ≥ 1 labelled problem, computes::

        fraction = count(severity) / total_labelled_problems

    The denominator is the count of **labelled** (non-empty severity) problems
    only — unlabelled problems are excluded from both the numerator and the
    denominator.  All labelled fractions therefore sum to 1.0 (within float
    precision).

    Severities present in *severity_order* but absent from *problems* are
    omitted from the result.  Severities present in *problems* but absent from
    *severity_order* are still included (they rank after all ordered severities).

    Args:
        problems:       Flat list of :class:`Problem` records.
        severity_order: Caller-supplied ordering of severity labels (e.g.
                        ``["CRITICAL", "HIGH", "MEDIUM", "LOW"]``).  Used only
                        for ranking; does not restrict which severities appear
                        in the result.

    Returns:
        ``{severity_label: fraction}`` for every severity with ≥ 1 labelled
        problem.  Returns ``{}`` when *problems* is empty or all problems are
        unlabelled.

    Pure (no I/O, no SurrealDB).
    """
    counts = problem_count_by_severity(problems)
    total = sum(counts.values())
    if total == 0:
        return {}
    rank = {sev: i for i, sev in enumerate(severity_order)}
    # Sort: ordered severities first (by rank), then unordered (rank=len).
    sorted_sevs = sorted(counts, key=lambda s: (rank.get(s, len(severity_order)), s))
    return {sev: counts[sev] / total for sev in sorted_sevs}


def top_severity_class(
    problems: list[Problem],
    severity_order: list[str],
) -> str | None:
    """Return the class with the highest count at the most-severe rank present.

    Iterates through *severity_order* from index 0 (most severe) and finds the
    first rank where at least one class has problems.  Among those classes,
    returns the one with the highest count.  Tie-break: alphabetically
    ascending class name.

    Falls through to the next rank if the current rank has no problems in any
    class.  Returns ``None`` when:
    - *problems* is empty,
    - all problems are unlabelled (no severity), OR
    - *severity_order* is empty.

    Args:
        problems:       List of :class:`Problem` instances from a scan.
        severity_order: Caller-supplied severity ordering (most severe first).

    Returns:
        Class name with the most problems at the highest-present severity rank,
        or ``None``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems or not severity_order:
        return None
    # Build per-class, per-severity counts
    class_sev_counts: dict[str, dict[str, int]] = {}
    for p in problems:
        if p.severity:
            inner = class_sev_counts.setdefault(p.problem_class, {})
            inner[p.severity] = inner.get(p.severity, 0) + 1
    if not class_sev_counts:
        return None
    # Fall through severity_order to find the first rank with ≥1 class
    for sev in severity_order:
        counts_at_rank = {
            cls: inner[sev] for cls, inner in class_sev_counts.items() if sev in inner
        }
        if counts_at_rank:
            return min(counts_at_rank, key=lambda cls: (-counts_at_rank[cls], cls))
    return None


def multi_severity_classes(problems: list[Problem]) -> frozenset[str]:
    """Return class names appearing at 2+ distinct labelled severity levels.

    A class is included when it has labelled problems (``severity != ''``) at
    at least two different severity values.  Unlabelled records do not
    contribute to the severity count.  Classes whose labelled problems all
    share a single severity are excluded.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Immutable set of class names with heterogeneous severity profiles.
        ``frozenset()`` when *problems* is empty or no class spans multiple
        severities.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    class_severities: dict[str, set[str]] = {}
    for p in problems:
        if p.severity:
            class_severities.setdefault(p.problem_class, set()).add(p.severity)
    return frozenset(cls for cls, sevs in class_severities.items() if len(sevs) >= 2)


def single_severity_classes(problems: list[Problem]) -> frozenset[str]:
    """Return class names with exactly one distinct labelled severity level.

    Complement of :func:`multi_severity_classes`.  Together they partition all
    classes that have at least one labelled problem:
    ``multi_severity_classes(p) ∪ single_severity_classes(p) == labelled_classes``
    and the two sets are disjoint.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Immutable set of class names whose labelled problems all share a single
        severity value.  ``frozenset()`` when *problems* is empty or no class
        has exactly one distinct labelled severity.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    class_severities: dict[str, set[str]] = {}
    for p in problems:
        if p.severity:
            class_severities.setdefault(p.problem_class, set()).add(p.severity)
    return frozenset(cls for cls, sevs in class_severities.items() if len(sevs) == 1)


def severity_span(problems: list[Problem]) -> dict[str, int]:
    """Return the count of distinct labelled severity levels per class.

    The span is the quantified form of the ``multi_severity_classes`` /
    ``single_severity_classes`` dichotomy: ``span == 1`` means the class is
    homogeneous (same severity for every labelled problem); ``span >= 2``
    means heterogeneous.  The relationship holds exactly:

    .. code-block:: python

        multi_severity_classes(p) == {cls for cls, s in severity_span(p).items() if s >= 2}
        single_severity_classes(p) == {cls for cls, s in severity_span(p).items() if s == 1}

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        ``{class_name: distinct_severity_count}`` for every class with at
        least one labelled problem.  Classes with only unlabelled problems are
        excluded.  Returns ``{}`` for empty input.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    class_severities: dict[str, set[str]] = {}
    for p in problems:
        if p.severity:
            class_severities.setdefault(p.problem_class, set()).add(p.severity)
    return {cls: len(sevs) for cls, sevs in class_severities.items()}


def max_severity_span_class(problems: list[Problem]) -> str | None:
    """Return the class name with the greatest severity span.

    Delegates to :func:`severity_span` and picks the class with the highest
    distinct-severity count.  Ties are broken by ascending class name
    (alphabetically earliest wins).

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Class name with the highest span, or ``None`` when *problems* is empty
        or contains no labelled problems.

    Pure (no I/O, no SurrealDB).
    """
    spans = severity_span(problems)
    if not spans:
        return None
    return min(spans, key=lambda cls: (-spans[cls], cls))


def classes_for_finding_id(problems: list[Problem], finding_id: str) -> frozenset[str]:
    """Return all class names that have at least one record with the given finding_id.

    Inverse of :func:`finding_ids_for_class`.  When a finding_id appears
    across multiple classes, all of those class names are returned.

    Args:
        problems: Flat list of :class:`Problem` records.
        finding_id: The finding identifier to look up (exact match).

    Returns:
        Immutable set of ``problem_class`` values from records whose
        ``finding_id`` matches exactly.  ``frozenset()`` when *problems* is
        empty or no record matches.

    Pure (no I/O, no SurrealDB).
    """
    return frozenset(p.problem_class for p in problems if p.finding_id == finding_id)


def problems_for_class(problems: list[Problem], class_name: str) -> list[Problem]:
    """Return all Problem records whose problem_class matches class_name.

    Closes the bidirectional-index quadrant:

    - :func:`finding_ids_for_class` — class → IDs
    - :func:`classes_for_finding_id` — ID → classes
    - :func:`problems_for_finding_id` — ID → full records
    - :func:`problems_for_class` — class → full records (this function)

    Args:
        problems: Flat list of :class:`Problem` records.
        class_name: The class name to look up (exact match).

    Returns:
        New list of :class:`Problem` objects in original order whose
        ``problem_class`` equals *class_name*.  ``[]`` when *problems* is
        empty or no record matches.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.problem_class == class_name]


def severity_class_matrix(problems: list[Problem]) -> dict[str, dict[str, int]]:
    """Return a 2D count matrix keyed by severity then class.

    Transpose of :func:`severity_heatmap` (which keys by class then severity).
    For each labelled severity, produces an inner dict mapping class names to
    their record count at that severity.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        ``{severity: {class_name: count}}`` for all labelled problems.
        Unlabelled records (``severity == ''``) are excluded.  Returns ``{}``
        for empty input.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    result: dict[str, dict[str, int]] = {}
    for p in problems:
        if p.severity:
            inner = result.setdefault(p.severity, {})
            inner[p.problem_class] = inner.get(p.problem_class, 0) + 1
    return result


def labelled_problems(problems: list[Problem]) -> list[Problem]:
    """Return only Problem records that have a non-empty severity label.

    Complement of the unlabelled filter: where unlabelled returns records with
    ``severity == ''``, this returns records with ``severity != ''``.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        New list of :class:`Problem` objects in original order whose
        ``severity`` is not empty.  ``[]`` when *problems* is empty or all
        records are unlabelled.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.severity]


# ---------------------------------------------------------------------------
# Item 345 — unlabelled_problems (2026-06-08)
# ---------------------------------------------------------------------------


def unlabelled_problems(problems: list[Problem]) -> list[Problem]:
    """Return only problems whose severity is empty (complement of labelled_problems).

    ``unlabelled_problems(problems) -> list[Problem]``:
    Returns only :class:`Problem` objects where ``severity == ''``.
    Complement of :func:`labelled_problems`.  Empty input → [].
    Pure (no I/O, no SurrealDB).

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        New list of :class:`Problem` objects in original order whose
        ``severity`` is empty.  ``[]`` when *problems* is empty or all
        records are labelled.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if not p.severity]


# ---------------------------------------------------------------------------
# Item 347 — problems_by_severity_rank (2026-06-08)
# ---------------------------------------------------------------------------


def problems_by_severity_rank(
    problems: list[Problem],
    severity_order: list[str],
) -> list[Problem]:
    """Return all Problem records ordered by a caller-supplied severity ranking.

    ``problems_by_severity_rank(problems, severity_order) -> list[Problem]``:
    Problems whose severity appears in *severity_order* are returned first,
    ordered by the position of their severity in *severity_order* (lower index
    = earlier in result).  Problems with unknown or empty severity are appended
    last, in their original insertion order.  Within any tier, the original
    insertion order is preserved (stable sort).  Empty input or empty
    *severity_order* (all unranked) returns the list in original insertion
    order.

    Args:
        problems: Flat list of :class:`Problem` records.
        severity_order: Caller-supplied list of severity strings in descending
            priority order (e.g. ``['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']``).
            Duplicates are ignored (first occurrence governs rank).

    Returns:
        All :class:`Problem` objects, ranked problems first (in severity_order
        position order), unranked/unlabelled appended last.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return []
    # Build rank map: severity → position index (first occurrence governs)
    rank: dict[str, int] = {}
    for i, sev in enumerate(severity_order):
        if sev not in rank:
            rank[sev] = i
    unranked_sentinel = len(severity_order)
    # Python's sorted() is stable: ties within a tier preserve insertion order
    return sorted(problems, key=lambda p: rank.get(p.severity, unranked_sentinel))


# ---------------------------------------------------------------------------
# Item 348 — top_n_problem_classes (2026-06-08)
# ---------------------------------------------------------------------------


def top_n_problem_classes(problems: list[Problem], n: int) -> list[str]:
    """Return the top N problem classes ranked by total problem count descending.

    ``top_n_problem_classes(problems, n) -> list[str]``:
    Returns up to *n* class names ordered by total :class:`Problem` record
    count descending.  Ties broken by ascending class name.
    *n=0* → [].  *n* > number of distinct classes → all classes returned.
    Empty input → [].  Pure (no I/O, no SurrealDB).

    Args:
        problems: Flat list of :class:`Problem` records.
        n:        Maximum number of class names to return.

    Returns:
        List of up to *n* class names, highest-count first, ties broken
        ascending alphabetically.

    Pure (no I/O, no SurrealDB).
    """
    if n == 0 or not problems:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    ranked = sorted(counts, key=lambda cls: (-counts[cls], cls))
    return ranked[:n]


# ---------------------------------------------------------------------------
# Item 349 — bottom_n_problem_classes (2026-06-08)
# ---------------------------------------------------------------------------


def bottom_n_problem_classes(problems: list[Problem], n: int) -> list[str]:
    """Return the bottom N problem classes ranked by total problem count ascending.

    ``bottom_n_problem_classes(problems, n) -> list[str]``:
    Returns up to *n* class names ordered by total :class:`Problem` record
    count ascending (fewest first).  Ties broken by ascending class name.
    *n=0* → [].  *n* > number of distinct classes → all classes returned.
    Empty input → [].  Pure (no I/O, no SurrealDB).

    Complements :func:`top_n_problem_classes` (highest-count first).

    Args:
        problems: Flat list of :class:`Problem` records.
        n:        Maximum number of class names to return.

    Returns:
        List of up to *n* class names, lowest-count first, ties broken
        ascending alphabetically.

    Pure (no I/O, no SurrealDB).
    """
    if n == 0 or not problems:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    ranked = sorted(counts, key=lambda cls: (counts[cls], cls))
    return ranked[:n]


# ---------------------------------------------------------------------------
# Item 350 — class_problem_ratio (2026-06-08)
# ---------------------------------------------------------------------------


def class_problem_ratio(problems: list[Problem], class_name: str) -> float:
    """Return the fraction of all problems belonging to a given class.

    ``class_problem_ratio(problems, class_name) -> float``:
    Returns ``count(class_name) / len(problems)`` as a :class:`float` in
    the range [0.0, 1.0].  Unknown class → 0.0.  Empty input → 0.0.
    Pure (no I/O, no SurrealDB).

    Complements :func:`problem_density_by_class` for single-class lookups
    without building the full density dict.

    Args:
        problems:   Flat list of :class:`Problem` records.
        class_name: The class to measure concentration for.

    Returns:
        Ratio in [0.0, 1.0]; 0.0 when *problems* is empty or *class_name*
        is not present.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    class_count = sum(1 for p in problems if p.problem_class == class_name)
    return class_count / len(problems)


# ---------------------------------------------------------------------------
# Item 351 — severity_ratio (2026-06-08)
# ---------------------------------------------------------------------------


def severity_ratio(problems: list[Problem], severity: str) -> float:
    """Return the fraction of ALL problems at a given severity level.

    ``severity_ratio(problems, severity) -> float``:
    Returns ``count(severity) / len(problems)`` as a :class:`float` in
    [0.0, 1.0].  The denominator is ALL problems (labelled + unlabelled),
    not just labelled ones.  Unknown severity → 0.0.  Empty input → 0.0.
    Pure (no I/O, no SurrealDB).

    Complements :func:`class_problem_ratio` for the severity axis.

    Args:
        problems: Flat list of :class:`Problem` records.
        severity: The severity string to measure concentration for.

    Returns:
        Ratio in [0.0, 1.0]; 0.0 when *problems* is empty or *severity*
        is not present.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    sev_count = sum(1 for p in problems if p.severity == severity)
    return sev_count / len(problems)


# ---------------------------------------------------------------------------
# Item 352 — classes_with_finding_id_overlap (2026-06-08)
# ---------------------------------------------------------------------------


def classes_with_finding_id_overlap(
    problems: list[Problem],
) -> frozenset[frozenset[str]]:
    """Return all unordered pairs of classes sharing at least one finding ID.

    ``classes_with_finding_id_overlap(problems) -> frozenset[frozenset[str]]``:
    Returns a :class:`frozenset` of 2-element :class:`frozenset` pairs
    {class_a, class_b} where both classes have at least one :class:`Problem`
    with the same ``finding_id``.  A finding_id shared by N classes produces
    C(N,2) pairs.  Self-pairs (same class twice) are never emitted.
    Empty input → frozenset().  Pure (no I/O, no SurrealDB).

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        frozenset of 2-element frozensets; each inner frozenset is an
        unordered pair of class names that share a finding_id.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    # Build finding_id → set of classes index
    id_classes: dict[str, set[str]] = {}
    for p in problems:
        id_classes.setdefault(p.finding_id, set()).add(p.problem_class)
    # Emit C(n,2) pairs for each finding_id with 2+ distinct classes
    pairs: set[frozenset[str]] = set()
    for classes in id_classes.values():
        class_list = sorted(classes)  # deterministic iteration
        for i, a in enumerate(class_list):
            for b in class_list[i + 1 :]:
                pairs.add(frozenset({a, b}))
    return frozenset(pairs)


# ---------------------------------------------------------------------------
# Item 353 — finding_id_overlap_count (2026-06-08)
# ---------------------------------------------------------------------------


def finding_id_overlap_count(problems: list[Problem], class_a: str, class_b: str) -> int:
    """Return the count of finding IDs shared between two problem classes.

    ``finding_id_overlap_count(problems, class_a, class_b) -> int``:
    Returns the number of distinct ``finding_id`` values that appear in both
    *class_a* and *class_b*.  Delegates to :func:`finding_ids_for_class` for
    each class, then returns the size of their intersection.
    Same class for both arguments → count of that class's own distinct
    finding_ids (self-intersection).  Either unknown class → 0.
    Empty input → 0.  Pure (no I/O, no SurrealDB).

    Args:
        problems: Flat list of :class:`Problem` records.
        class_a:  First class name.
        class_b:  Second class name.

    Returns:
        Integer count of shared finding_ids (≥ 0).

    Pure (no I/O, no SurrealDB).
    """
    ids_a = frozenset(finding_ids_for_class(problems, class_a))
    ids_b = frozenset(finding_ids_for_class(problems, class_b))
    return len(ids_a & ids_b)


# ---------------------------------------------------------------------------
# Item 354 — problems_unique_to_class (2026-06-08)
# ---------------------------------------------------------------------------


def problems_unique_to_class(problems: list[Problem], class_name: str) -> list[Problem]:
    """Return problems for class_name whose finding_id appears in no other class.

    ``problems_unique_to_class(problems, class_name) -> list[Problem]``:
    Returns all :class:`Problem` objects in *class_name* whose ``finding_id``
    does NOT appear under any other ``problem_class`` in *problems*.
    Finding IDs that are shared across classes are excluded.
    Within-class duplicates (same ``finding_id``, same class, multiple records)
    are included — the finding_id is still class-exclusive.
    Preserves original order.  Unknown class → [].  Empty → [].
    Pure (no I/O, no SurrealDB).

    Args:
        problems:   Flat list of :class:`Problem` records.
        class_name: The class whose exclusive problems to return.

    Returns:
        New list of :class:`Problem` objects from *class_name* whose
        ``finding_id`` is exclusive to that class.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return []
    # Build finding_id -> set of classes index in one pass
    id_classes: dict[str, set[str]] = {}
    for p in problems:
        id_classes.setdefault(p.finding_id, set()).add(p.problem_class)
    # Exclusive finding_ids: appear in ONLY this class
    exclusive_ids = {fid for fid, classes in id_classes.items() if classes == {class_name}}
    return [p for p in problems if p.problem_class == class_name and p.finding_id in exclusive_ids]


# ---------------------------------------------------------------------------
# Item 355 — count_problems_with_severity (2026-06-08)
# ---------------------------------------------------------------------------


def count_problems_with_severity(problems: list[Problem]) -> int:
    """Return the count of Problem records that have a non-empty severity label.

    ``count_problems_with_severity(problems) -> int``:
    Equivalent to ``len(labelled_problems(problems))``.  Returns the number
    of :class:`Problem` objects whose ``severity`` is not ``''``.
    Empty input → 0.  Pure (no I/O, no SurrealDB).

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Integer count of labelled (non-empty severity) problems.

    Pure (no I/O, no SurrealDB).
    """
    return sum(1 for p in problems if p.severity)


# ---------------------------------------------------------------------------
# Item 356 — count_unlabelled_problems (2026-06-08)
# ---------------------------------------------------------------------------


def count_unlabelled_problems(problems: list[Problem]) -> int:
    """Return the integer count of problems without any severity label.

    ``count_unlabelled_problems(problems) -> int``:
    Returns the number of :class:`Problem` records whose ``severity`` is empty.
    Equivalent to ``len(unlabelled_problems(problems))``.
    Empty input → 0.  Pure (no I/O, no SurrealDB).

    Together with :func:`count_problems_with_severity`, partitions all problems:
    ``count_problems_with_severity(p) + count_unlabelled_problems(p) == len(p)``.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        Integer count of unlabelled (empty severity) problems.

    Pure (no I/O, no SurrealDB).
    """
    return sum(1 for p in problems if not p.severity)


# ---------------------------------------------------------------------------
# Item 358 — problems_with_class_prefix (2026-06-08)
# ---------------------------------------------------------------------------


def problems_with_class_prefix(problems: list[Problem], prefix: str) -> list[Problem]:
    """Return all problems whose class name starts with the given prefix.

    ``problems_with_class_prefix(problems, prefix) -> list[Problem]``:
    Returns all :class:`Problem` objects whose ``problem_class`` starts with
    *prefix*.  Empty *prefix* matches every problem (``str.startswith("")``
    is always ``True``).  Case-sensitive.  Preserves original order.
    Empty *problems* → [].  Pure (no I/O, no SurrealDB).

    Useful for namespace-based filtering (e.g. ``'security/'``, ``'perf/'``).

    Args:
        problems: Flat list of :class:`Problem` records.
        prefix:   Class name prefix to match against (case-sensitive).

    Returns:
        New list of :class:`Problem` objects whose class starts with
        *prefix*, in original order.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.problem_class.startswith(prefix)]


# ---------------------------------------------------------------------------
# Item 359 — problems_with_finding_id_prefix (2026-06-08)
# ---------------------------------------------------------------------------


def problems_with_finding_id_prefix(
    problems: list[Problem],
    prefix: str,
) -> list[Problem]:
    """Return all Problem records whose finding_id starts with the given prefix.

    ``problems_with_finding_id_prefix(problems, prefix) -> list[Problem]``:
    Mirror of :func:`problems_with_class_prefix` on the ``finding_id`` axis.
    Returns :class:`Problem` objects where ``finding_id.startswith(prefix)``.
    Empty *prefix* matches all (Python str semantics).  Case-sensitive.
    Preserves original insertion order.  Empty input → [].
    Pure (no I/O, no SurrealDB).

    Args:
        problems: Flat list of :class:`Problem` records.
        prefix:   Finding-id prefix to filter on (case-sensitive; ``''``
                  matches all).

    Returns:
        New list of :class:`Problem` objects whose finding_id starts with
        *prefix*, in original order.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.finding_id.startswith(prefix)]


# ---------------------------------------------------------------------------
# Item 360 — class_name_contains (2026-06-08)
# ---------------------------------------------------------------------------


def class_name_contains(problems: list[Problem], substring: str) -> list[Problem]:
    """Return all problems whose class name contains the given substring.

    ``class_name_contains(problems, substring) -> list[Problem]``:
    Returns all :class:`Problem` objects whose ``problem_class`` contains
    *substring* anywhere (start, middle, or end).  Empty *substring* matches
    every problem (``'' in s`` is always ``True``).  Case-sensitive.
    Preserves original order.  Empty *problems* → [].
    Pure (no I/O, no SurrealDB).

    Complements :func:`problems_with_class_prefix` which matches only at start.

    Args:
        problems:  Flat list of :class:`Problem` records.
        substring: String to search for inside class names (case-sensitive).

    Returns:
        New list of :class:`Problem` objects whose ``problem_class`` contains
        *substring*, in original order.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if substring in p.problem_class]


# ---------------------------------------------------------------------------
# Item 361 — deduplicate_exact_problems (2026-06-08)
# ---------------------------------------------------------------------------


def deduplicate_exact_problems(problems: list[Problem]) -> list[Problem]:
    """Return a new list with exact-duplicate Problem records removed — item 361.

    Two :class:`Problem` objects are considered exact duplicates when ALL three
    fields match: ``problem_class``, ``finding_id``, AND ``severity``.  Same
    class+finding_id with different severity = two distinct records (both kept).

    Keeps the FIRST occurrence; insertion order of surviving records is
    preserved.  Empty *problems* → ``[]``.

    This differs from :func:`deduplicate_problems` (item 185), which
    deduplicates by ``finding_id`` alone.

    Args:
        problems:
            A list of :class:`Problem` instances.  Empty list → ``[]``.

    Returns:
        A new list of :class:`Problem` instances, length ≤ ``len(problems)``.
        The input list is not mutated.

    Pure (no I/O, no SurrealDB).
    """
    seen: set[Problem] = set()
    result: list[Problem] = []
    for p in problems:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Item 363 — group_problems_by_severity (2026-06-08)
# ---------------------------------------------------------------------------


def group_problems_by_severity(
    problems: list[Problem],
) -> dict[str, list[Problem]]:
    """Group all problems by severity, including unlabelled under key ''.

    ``group_problems_by_severity(problems) -> dict[str, list[Problem]]``:
    Returns a :class:`dict` mapping each distinct ``severity`` value to a
    list of :class:`Problem` objects with that severity.  Unlabelled problems
    (``severity == ''``) are mapped under key ``''`` — they are NOT dropped.
    All problems are covered: the union of all values equals *problems*.
    Original order preserved within each group.
    Empty input → {}.  Pure (no I/O, no SurrealDB).

    Mirror of :func:`group_problems_by_class` on the severity axis.

    Args:
        problems: Flat list of :class:`Problem` records.

    Returns:
        dict mapping severity (including ``''``) to ordered list of Problems.

    Pure (no I/O, no SurrealDB).
    """
    result: dict[str, list[Problem]] = {}
    for p in problems:
        result.setdefault(p.severity, []).append(p)
    return result


# ---------------------------------------------------------------------------
# Item 365 — least_common_finding_id (2026-06-08)
# ---------------------------------------------------------------------------


def least_common_finding_id(problems: list[Problem]) -> str | None:
    """Return the finding_id with the lowest total Problem record count — item 365.

    Counts raw Problem records per ``finding_id``.  Tie-break: alphabetically
    ascending ``finding_id`` (lexicographically smallest wins).

    Complement of :func:`most_common_finding_id`; useful for spotting rare /
    low-priority issues or data-entry errors.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        The ``finding_id`` string with the fewest records, or ``None`` when
        *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return min(counts, key=lambda fid: (counts[fid], fid))


# ---------------------------------------------------------------------------
# Item 366 — finding_ids_above_count (2026-06-08)
# ---------------------------------------------------------------------------


def finding_ids_above_count(problems: list[Problem], n: int) -> frozenset[str]:
    """Return finding_ids whose total record count is strictly greater than n — item 366.

    Counts raw :class:`Problem` records per ``finding_id`` across the full
    list.  Returns only those ``finding_id`` strings where count ``> n``
    (strictly greater; count ``== n`` is excluded).

    Special cases:
    - ``n=0`` → every distinct ``finding_id`` qualifies (all counts ≥ 1 > 0).
    - Empty *problems* → ``frozenset()``.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        n:        Integer threshold; finding_ids with count > n are returned.

    Returns:
        :class:`frozenset` of ``finding_id`` strings.  Unordered; use ``in``
        for membership queries, ``&``/``|`` for set algebra with other frozensets.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return frozenset(fid for fid, cnt in counts.items() if cnt > n)


# ---------------------------------------------------------------------------
# Item 367 — finding_ids_at_most_count (2026-06-08)
# ---------------------------------------------------------------------------


def finding_ids_at_most_count(problems: list[Problem], n: int) -> frozenset[str]:
    """Return finding_ids whose total record count is at most n — item 367.

    Counts raw :class:`Problem` records per ``finding_id`` across the full
    list.  Returns only those ``finding_id`` strings where count ``<= n``.

    Special cases:
    - ``n=0`` → ``frozenset()`` (every id appears at least once; no id has
      count ≤ 0).
    - Empty *problems* → ``frozenset()``.

    Complement of :func:`finding_ids_above_count`: their union equals the set
    of all distinct ``finding_id`` values, and their intersection is empty.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        n:        Integer ceiling; finding_ids with count <= n are returned.

    Returns:
        :class:`frozenset` of ``finding_id`` strings.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return frozenset(fid for fid, cnt in counts.items() if cnt <= n)


# ---------------------------------------------------------------------------
# Item 368 — classes_with_severity (2026-06-08)
# ---------------------------------------------------------------------------


def classes_with_severity(problems: list[Problem], severity: str) -> frozenset[str]:
    """Return class names that have at least one problem with the given severity — item 368.

    A class qualifies if ANY of its :class:`Problem` records matches *severity*
    exactly.  Classes with only other severities are excluded.

    Args:
        problems: List of :class:`Problem` instances from a scan.
        severity: Target severity string (e.g. ``'HIGH'``, ``'CRITICAL'``).
                  Unknown or unlabelled (``''``) values simply return an empty
                  frozenset — no error is raised.

    Returns:
        :class:`frozenset` of ``problem_class`` strings.  Empty when
        *problems* is empty or when no record has the target severity.

    Pure (no I/O, no SurrealDB).
    """
    return frozenset(p.problem_class for p in problems if p.severity == severity)


# ---------------------------------------------------------------------------
# Item 369 — count_distinct_severities (2026-06-08)
# ---------------------------------------------------------------------------


def count_distinct_severities(problems: list[Problem]) -> int:
    """Return the number of distinct severity values present — item 369.

    Counts how many distinct ``severity`` strings appear across *problems*.
    Unlabelled problems (``severity == ''``) contribute ``''`` to the set —
    they are NOT filtered out.  An all-unlabelled list returns ``1`` (one
    distinct value: ``''``).

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``0``.

    Returns:
        Integer ≥ 0.  ``0`` only when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return len({p.severity for p in problems})


# ---------------------------------------------------------------------------
# Item 370 — count_distinct_classes (2026-06-08)
# ---------------------------------------------------------------------------


def count_distinct_classes(problems: list[Problem]) -> int:
    """Return the number of distinct class names present — item 370.

    Counts how many distinct ``problem_class`` strings appear across
    *problems*.  Mirror of :func:`count_distinct_severities` on the class
    axis.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``0``.

    Returns:
        Integer ≥ 0.  ``0`` only when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return len({p.problem_class for p in problems})


# ---------------------------------------------------------------------------
# Item 371 — problems_in_class_set (2026-06-08)
# ---------------------------------------------------------------------------


def problems_in_class_set(
    problems: list[Problem],
    class_set: frozenset[str] | set[str],
) -> list[Problem]:
    """Return problems whose class is a member of class_set — item 371.

    Filters by exact ``problem_class`` membership in *class_set*.  An empty
    *class_set* returns an empty list (not all problems).  Original insertion
    order is preserved for matching records.

    Generalises :func:`problems_for_class` to multiple classes at once:
    ``problems_for_class(p, cls)`` ≡
    ``problems_in_class_set(p, {cls})``.

    Args:
        problems:  List of :class:`Problem` instances.
        class_set: Set (or frozenset) of class name strings to match against.

    Returns:
        New list of :class:`Problem` objects whose ``problem_class`` is in
        *class_set*, in original order.  Empty when *problems* or *class_set*
        is empty, or when no record's class is in the set.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.problem_class in class_set]


# ---------------------------------------------------------------------------
# Item 373 — class_count_above_threshold (2026-06-08)
# ---------------------------------------------------------------------------


def class_count_above_threshold(problems: list[Problem], n: int) -> frozenset[str]:
    """Return class names whose total record count exceeds n — item 373.

    Sister to :func:`finding_ids_above_count` on the class axis.  Returns a
    :class:`frozenset` of ``problem_class`` strings where the number of
    :class:`Problem` records for that class is strictly greater than *n*.

    Args:
        problems: List of :class:`Problem` instances.
        n: Threshold.  ``n=0`` returns all distinct class names.

    Returns:
        :class:`frozenset` of class name strings with count > *n*.
        Empty when *problems* is empty or no class exceeds the threshold.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return frozenset(cls for cls, cnt in counts.items() if cnt > n)


# ---------------------------------------------------------------------------
# Item 374 — class_count_at_most_threshold (2026-06-08)
# ---------------------------------------------------------------------------


def class_count_at_most_threshold(problems: list[Problem], n: int) -> frozenset[str]:
    """Return class names whose total record count is at most n — item 374.

    Complement of :func:`class_count_above_threshold`.  Partition invariant:
    ``class_count_above_threshold(p, n) | class_count_at_most_threshold(p, n)``
    equals the full set of distinct class names for any *n*.

    Args:
        problems: List of :class:`Problem` instances.
        n: Ceiling threshold.  ``n=0`` always returns an empty frozenset
           (no class can have count ≤ 0 if it appears in the list).

    Returns:
        :class:`frozenset` of class name strings with count ≤ *n*.
        Empty when *problems* is empty or *n* < 1.

    Pure (no I/O, no SurrealDB).
    """
    if not problems or n < 1:
        return frozenset()
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return frozenset(cls for cls, cnt in counts.items() if cnt <= n)


# ---------------------------------------------------------------------------
# Item 375 — finding_id_to_classes (2026-06-08)
# ---------------------------------------------------------------------------


def finding_id_to_classes(
    problems: list[Problem],
) -> dict[str, frozenset[str]]:
    """Build a reverse index mapping each finding_id to its owning classes — item 375.

    Returns a :class:`dict` mapping each distinct ``finding_id`` string to the
    :class:`frozenset` of ``problem_class`` values that have at least one
    :class:`Problem` with that finding_id.  This is the inverse of the
    class→finding_id index: here the **key is the finding_id**.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``{}``.

    Returns:
        ``dict[str, frozenset[str]]``.  Every distinct finding_id in
        *problems* appears exactly once as a key.  Values are non-empty
        :class:`frozenset` objects.  Empty when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    result: dict[str, set[str]] = {}
    for p in problems:
        result.setdefault(p.finding_id, set()).add(p.problem_class)
    return {fid: frozenset(classes) for fid, classes in result.items()}


# ---------------------------------------------------------------------------
# Item 376 — class_to_finding_ids (2026-06-08)
# ---------------------------------------------------------------------------


def class_to_finding_ids(
    problems: list[Problem],
) -> dict[str, frozenset[str]]:
    """Build a forward index mapping each class to its finding_ids — item 376.

    Mirror of :func:`finding_id_to_classes` with keys and values swapped.
    Returns a :class:`dict` mapping each distinct ``problem_class`` string to
    the :class:`frozenset` of ``finding_id`` values that appear under it.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``{}``.

    Returns:
        ``dict[str, frozenset[str]]``.  Every distinct class in *problems*
        appears exactly once as a key.  Values are non-empty :class:`frozenset`
        objects of finding_id strings (duplicates collapsed by the set).
        Empty when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    index: dict[str, set[str]] = {}
    for p in problems:
        index.setdefault(p.problem_class, set()).add(p.finding_id)
    return {cls: frozenset(fids) for cls, fids in index.items()}


# ---------------------------------------------------------------------------
# Item 377 — severity_to_finding_ids (2026-06-08)
# ---------------------------------------------------------------------------


def severity_to_finding_ids(
    problems: list[Problem],
) -> dict[str, frozenset[str]]:
    """Build an index mapping each severity to its finding_ids — item 377.

    Returns a :class:`dict` mapping each distinct ``severity`` string to the
    :class:`frozenset` of ``finding_id`` values whose records carry that
    severity.  The empty string ``''`` is included as a key when any
    unlabelled :class:`Problem` is present (severity not filtered out).

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``{}``.

    Returns:
        ``dict[str, frozenset[str]]``.  Every distinct severity (including
        ``''``) in *problems* appears exactly once as a key.  Values are
        non-empty :class:`frozenset` objects of finding_id strings.
        Empty when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    index: dict[str, set[str]] = {}
    for p in problems:
        index.setdefault(p.severity, set()).add(p.finding_id)
    return {sev: frozenset(fids) for sev, fids in index.items()}


# ---------------------------------------------------------------------------
# Item 378 — class_to_severities (2026-06-08)
# ---------------------------------------------------------------------------


def class_to_severities(
    problems: list[Problem],
) -> dict[str, frozenset[str]]:
    """Build an index mapping each class to its distinct severity palette — item 378.

    Returns a :class:`dict` mapping each distinct ``problem_class`` string to
    the :class:`frozenset` of distinct ``severity`` strings present among its
    records.  The empty string ``''`` is included as a severity value when any
    unlabelled :class:`Problem` belongs to that class.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``{}``.

    Returns:
        ``dict[str, frozenset[str]]``.  Every distinct class in *problems*
        appears exactly once as a key.  Values are non-empty :class:`frozenset`
        objects of severity strings (including ``''`` if unlabelled records
        exist for that class).  Empty when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    index: dict[str, set[str]] = {}
    for p in problems:
        index.setdefault(p.problem_class, set()).add(p.severity)
    return {cls: frozenset(sevs) for cls, sevs in index.items()}


def severity_to_classes(
    problems: list[Problem],
) -> dict[str, frozenset[str]]:
    """Build an index mapping each severity to the classes that carry it — item 379.

    Returns a :class:`dict` mapping each distinct ``severity`` string to the
    :class:`frozenset` of ``problem_class`` names that have at least one
    :class:`Problem` with that severity.  The empty string ``''`` is included
    as a key when any unlabelled :class:`Problem` is present.
    Transpose of :func:`class_to_severities`.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``{}``.

    Returns:
        ``dict[str, frozenset[str]]``.  Every distinct severity (including
        ``''``) in *problems* appears exactly once as a key.  Values are
        non-empty :class:`frozenset` objects of class name strings.
        Empty when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    index: dict[str, set[str]] = {}
    for p in problems:
        index.setdefault(p.severity, set()).add(p.problem_class)
    return {sev: frozenset(classes) for sev, classes in index.items()}


# ---------------------------------------------------------------------------
# Item 383 — top_n_classes_by_count
# ---------------------------------------------------------------------------


def top_n_classes_by_count(problems: list[Problem], n: int) -> list[str]:
    """Return the top-N class names ranked by descending problem record count — item 383.

    Ties in count are broken by class name ascending (lexicographic).
    Returns at most *n* entries; returns ``[]`` when *n* ≤ 0 or *problems*
    is empty.

    Args:
        problems: List of :class:`Problem` instances.
        n: Maximum number of classes to return.  ``0`` → ``[]``.

    Returns:
        ``list[str]`` of at most *n* class name strings, sorted by descending
        record count then ascending class name.  Empty when *problems* is
        empty or *n* is 0.

    Pure (no I/O, no SurrealDB).
    """
    if not problems or n <= 0:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [cls for cls, _ in ranked[:n]]


def top_n_finding_ids_by_count(problems: list[Problem], n: int) -> list[str]:
    """Return the top-n finding_ids ranked by total occurrence count — item 384.

    Mirror of :func:`top_n_classes_by_count` on the ``finding_id`` axis.
    Finding_ids are sorted descending by their total occurrence count across
    all classes.  Ties are broken lexicographically ascending.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``[]``.
        n: Maximum number of finding_id strings to return.  ``0`` → ``[]``.

    Returns:
        ``list[str]`` of at most *n* finding_id strings, sorted by descending
        occurrence count then ascending finding_id.  Empty when *problems* is
        empty or *n* is ``0``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems or n <= 0:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [fid for fid, _ in ranked[:n]]


def finding_ids_shared_across_classes(problems: list[Problem]) -> frozenset[str]:
    """Return finding_ids that appear under ≥2 distinct classes — item 386.

    A finding_id is "shared" when it has :class:`Problem` records in at least
    two distinct ``problem_class`` values.  Finding_ids present in only one
    class are excluded even if they have many records within that class.

    Uses :func:`finding_id_to_classes` as a building block.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``frozenset()``.

    Returns:
        :class:`frozenset` of finding_id strings where the number of distinct
        classes containing that finding_id is ≥ 2.  Empty when *problems* is
        empty or all finding_ids appear in only one class.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    index = finding_id_to_classes(problems)
    return frozenset(fid for fid, classes in index.items() if len(classes) >= 2)


# ---------------------------------------------------------------------------
# Item 387 — classes_with_shared_finding_ids
# ---------------------------------------------------------------------------


def classes_with_shared_finding_ids(problems: list[Problem]) -> frozenset[str]:
    """Return class names that own at least one cross-class finding_id — item 387.

    Dual of :func:`finding_ids_shared_across_classes`.  A class is included
    when ANY of its finding_ids also appears in a different class.  Classes
    whose finding_ids are all unique to that class are excluded.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        :class:`frozenset` of ``problem_class`` strings.  Empty when
        *problems* is empty or no finding_id spans more than one class.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    # finding_id → set of classes that have it
    fid_to_classes: dict[str, set[str]] = {}
    for p in problems:
        fid_to_classes.setdefault(p.finding_id, set()).add(p.problem_class)
    # collect all class names from shared finding_ids
    result: set[str] = set()
    for classes in fid_to_classes.values():
        if len(classes) >= 2:
            result.update(classes)
    return frozenset(result)


# ---------------------------------------------------------------------------
# Item 388 — problem_class_histogram
# ---------------------------------------------------------------------------


def problem_class_histogram(problems: list[Problem]) -> dict[str, int]:
    """Return a frequency histogram of problem_class values — item 388.

    Maps each distinct ``problem_class`` string to the total number of
    :class:`Problem` records with that class.  All records are counted
    regardless of severity label (including unlabelled records).  The same
    finding_id appearing N times under a class contributes N to the count.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        ``dict[str, int]`` mapping class name → total record count.
        Every distinct class appears exactly once.  Empty when *problems*
        is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Item 389 — severity_histogram
# ---------------------------------------------------------------------------


def severity_histogram(problems: list[Problem]) -> dict[str, int]:
    """Return a frequency histogram of severity values — item 389.

    Maps each distinct ``severity`` string to the total number of
    :class:`Problem` records with that severity.  The empty string ``''``
    is included as a key when any unlabelled records are present.  The
    sum of all values equals ``len(problems)``.

    Mirrors :func:`problem_class_histogram` on the severity axis.

    Args:
        problems: List of :class:`Problem` instances from a scan.

    Returns:
        ``dict[str, int]`` mapping severity → total record count.
        ``''`` is included if any unlabelled records exist.  Empty when
        *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    return counts


def finding_id_histogram(problems: list[Problem]) -> dict[str, int]:
    """Return a frequency histogram of finding_id values across all problems — item 390.

    Maps every distinct :attr:`Problem.finding_id` to the total number of
    :class:`Problem` records that carry it.  The same ``finding_id`` appearing
    under two different ``problem_class`` values counts as 2 separate records —
    no deduplication is performed.

    Completes the three-axis histogram set alongside
    :func:`problem_class_histogram` and :func:`severity_histogram`.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``{}``.

    Returns:
        ``dict[str, int]`` — ``{finding_id: record_count}`` for every distinct
        ``finding_id`` present.  The sum of all values equals ``len(problems)``.
        Returns ``{}`` for empty input.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return counts


def most_common_problem_class(problems: list[Problem]) -> str | None:
    """Return the problem_class with the highest total Problem record count — item 392.

    Counts raw Problem records per :attr:`Problem.problem_class`.
    Tie-break: alphabetically ascending class name (lexicographically smallest wins).

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``None``.

    Returns:
        The class name string with the most records, or ``None`` when
        *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return min(counts, key=lambda cls: (-counts[cls], cls))


def problems_by_class(problems: list[Problem]) -> dict[str, list[Problem]]:
    """Group Problem records into a dict keyed by problem_class — item 394.

    Returns a mapping from each distinct :attr:`Problem.problem_class` to the
    list of :class:`Problem` records in that class.  Input order within each
    class list is preserved.  The original :class:`Problem` objects are
    referenced directly (no copies).

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``{}``.

    Returns:
        ``dict[str, list[Problem]]`` — ``{class_name: [Problem, ...]}`` for
        every distinct class.  Empty when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    result: dict[str, list[Problem]] = {}
    for p in problems:
        result.setdefault(p.problem_class, []).append(p)
    return result


def problems_by_severity(problems: list[Problem]) -> dict[str, list[Problem]]:
    """Group Problem records into a dict keyed by severity — item 395.

    Returns a mapping from each distinct :attr:`Problem.severity` to the list
    of :class:`Problem` records with that severity.  The empty string ``''``
    is a valid key for unlabelled records.  Input order within each list is
    preserved.  The original :class:`Problem` objects are referenced directly.

    Args:
        problems: List of :class:`Problem` instances.  Empty → ``{}``.

    Returns:
        ``dict[str, list[Problem]]`` — ``{severity: [Problem, ...]}`` for
        every distinct severity present.  Empty when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    result: dict[str, list[Problem]] = {}
    for p in problems:
        result.setdefault(p.severity, []).append(p)
    return result


def problem_count_for_class(problems: list[Problem], target_class: str) -> int:
    """Return the total Problem record count for a specific class — item 396.

    Counts all :class:`Problem` records where :attr:`Problem.problem_class`
    equals *target_class*, regardless of severity label.  Returns ``0`` when
    the class is absent or *problems* is empty — never raises.

    Args:
        problems: List of :class:`Problem` instances.
        target_class: The class name to count records for.

    Returns:
        Integer count of records in *target_class*.  ``0`` when not found.

    Pure (no I/O, no SurrealDB).
    """
    return sum(1 for p in problems if p.problem_class == target_class)


def problem_count_for_severity(problems: list[Problem], target_severity: str) -> int:
    """Return the total Problem record count for a specific severity — item 397.

    Counts all :class:`Problem` records where :attr:`Problem.severity` equals
    *target_severity*.  The empty string ``''`` is a valid target and returns
    the count of unlabelled records.  Returns ``0`` when the severity is absent
    or *problems* is empty — never raises.

    Args:
        problems: List of :class:`Problem` instances.
        target_severity: The severity label to count records for (``''`` for
            unlabelled).

    Returns:
        Integer count of records with *target_severity*.  ``0`` when not found.

    Pure (no I/O, no SurrealDB).
    """
    return sum(1 for p in problems if p.severity == target_severity)


def has_problems_for_class(problems: list[Problem], target_class: str) -> bool:
    """Return True if at least one Problem record matches target_class — item 398.

    Short-circuits at the first matching record.  Returns ``False`` when the
    class is absent or *problems* is empty — never raises.

    Args:
        problems: List of :class:`Problem` instances.
        target_class: The class name to test for.

    Returns:
        ``True`` if any record has ``problem_class == target_class``,
        ``False`` otherwise.

    Pure (no I/O, no SurrealDB).
    """
    return any(p.problem_class == target_class for p in problems)


def has_problems_for_severity(problems: list[Problem], target_severity: str) -> bool:
    """Return True if at least one Problem record matches target_severity — item 399.

    The empty string ``''`` is a valid target and returns ``True`` when any
    unlabelled records exist.  Short-circuits at the first matching record.
    Returns ``False`` when the severity is absent or *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances.
        target_severity: The severity label to test for (``''`` for unlabelled).

    Returns:
        ``True`` if any record has ``severity == target_severity``,
        ``False`` otherwise.

    Pure (no I/O, no SurrealDB).
    """
    return any(p.severity == target_severity for p in problems)


def severities_for_class(problems: list[Problem], target_class: str) -> frozenset[str]:
    """Return the distinct severity labels present in a specific class — item 402.

    Collects all :attr:`Problem.severity` strings (including ``''`` for
    unlabelled records) from records where :attr:`Problem.problem_class`
    equals *target_class*, deduplicated into a :class:`frozenset`.

    Args:
        problems: List of :class:`Problem` instances.
        target_class: The class to inspect.

    Returns:
        :class:`frozenset` of distinct severity strings present in
        *target_class*.  ``frozenset()`` when the class is absent or
        *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return frozenset(p.severity for p in problems if p.problem_class == target_class)


def class_count_for_finding_id(problems: list[Problem], target_fid: str) -> int:
    """Return the count of distinct classes that contain a specific finding_id — item 403.

    Counts distinct :attr:`Problem.problem_class` values among all records
    where :attr:`Problem.finding_id` equals *target_fid*.  The same class
    appearing multiple times with *target_fid* counts only once.  Returns
    ``0`` when the fid is absent or *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances.
        target_fid: The finding_id to inspect.

    Returns:
        Integer count of distinct classes that own *target_fid*.
        ``0`` when not found.

    Pure (no I/O, no SurrealDB).
    """
    return len(frozenset(p.problem_class for p in problems if p.finding_id == target_fid))


def is_cross_class_finding_id(problems: list[Problem], target_fid: str) -> bool:
    """Return True if target_fid appears in two or more distinct classes — item 404.

    A cross-class finding_id is one whose records span ≥ 2 distinct
    :attr:`Problem.problem_class` values.  Single-class fids and absent fids
    return ``False``.

    Args:
        problems: List of :class:`Problem` instances.
        target_fid: The finding_id to test.

    Returns:
        ``True`` if *target_fid* spans ≥ 2 distinct classes, ``False``
        otherwise.

    Pure (no I/O, no SurrealDB).
    """
    return class_count_for_finding_id(problems, target_fid) >= 2


def unique_classes_count(problems: list[Problem]) -> int:
    """Return the count of distinct problem_class values — item 405.

    Each distinct :attr:`Problem.problem_class` is counted once regardless
    of how many records share it.  Returns ``0`` for empty input.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Integer count of distinct classes.  ``0`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return len(frozenset(p.problem_class for p in problems))


def unique_finding_ids_count(problems: list[Problem]) -> int:
    """Return the count of distinct finding_id values — item 406.

    Each distinct :attr:`Problem.finding_id` is counted once regardless of
    how many classes or records share it.  Returns ``0`` for empty input.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Integer count of distinct finding_ids.  ``0`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return len(frozenset(p.finding_id for p in problems))


def average_problems_per_class(problems: list[Problem]) -> float:
    """Return the mean Problem record count per distinct class — item 407.

    Computes ``total_records / distinct_class_count`` as a float.  Returns
    ``0.0`` for empty input (no :class:`ZeroDivisionError`).

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Float mean of records per distinct class.  ``0.0`` when *problems*
        is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    n_classes = len(frozenset(p.problem_class for p in problems))
    return len(problems) / n_classes


def max_problems_in_any_class(problems: list[Problem]) -> int:
    """Return the maximum record count across all classes — item 408.

    Returns the highest value in the :func:`problem_class_histogram` — i.e.,
    the record count of the most-populated class.  Returns ``0`` for empty
    input (no :class:`ValueError` from :func:`max` on an empty sequence).

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Integer maximum class count.  ``0`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return max(counts.values())


def min_problems_in_any_class(problems: list[Problem]) -> int:
    """Return the minimum record count across all classes — item 409.

    Returns the lowest value in the :func:`problem_class_histogram` — i.e.,
    the record count of the least-populated class.  Returns ``0`` for empty
    input (no :class:`ValueError` from :func:`min` on an empty sequence).

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Integer minimum class count.  ``0`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return min(counts.values())


def class_distribution_range(problems: list[Problem]) -> int:
    """Return the range (max - min) of class record counts — item 410.

    Computes ``max_count - min_count`` from the :func:`problem_class_histogram`.
    Returns ``0`` for empty input or when all classes have equal counts.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Integer spread between the most and least populated classes.
        ``0`` when *problems* is empty or all classes are equal.

    Pure (no I/O, no SurrealDB).
    """
    return max_problems_in_any_class(problems) - min_problems_in_any_class(problems)


def problems_exceeding_threshold(problems: list[Problem], threshold: int) -> list[Problem]:
    """Return Problem records whose finding_id count meets or exceeds threshold — item 411.

    Computes a :func:`finding_id_histogram` over the full *problems* list and
    returns every record whose :attr:`Problem.finding_id` has a total count
    ``>= threshold``.  Input order is preserved.

    A *threshold* of ``0`` or ``1`` returns all records because every
    finding_id appears at least once.

    Args:
        problems: List of :class:`Problem` instances.
        threshold: Minimum total fid occurrence count to include a record.

    Returns:
        :class:`list` of :class:`Problem` records (input order preserved) whose
        fid total count ``>= threshold``.  ``[]`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return [p for p in problems if counts[p.finding_id] >= threshold]


def problems_below_threshold(problems: list[Problem], threshold: int) -> list[Problem]:
    """Return Problem records whose finding_id count is below threshold — item 412.

    Computes a :func:`finding_id_histogram` over the full *problems* list and
    returns every record whose :attr:`Problem.finding_id` has a total count
    strictly ``< threshold``.  Input order is preserved.

    A *threshold* of ``0`` or ``1`` returns ``[]`` because every finding_id
    appears at least once (count >= 1).

    Args:
        problems: List of :class:`Problem` instances.
        threshold: Exclusive upper bound; records with fid count < threshold are returned.

    Returns:
        :class:`list` of :class:`Problem` records (input order preserved) whose
        fid total count ``< threshold``.  ``[]`` when *problems* is empty or
        *threshold* <= 1.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return [p for p in problems if counts[p.finding_id] < threshold]


def singleton_finding_ids(problems: list[Problem]) -> frozenset[str]:
    """Return the frozenset of finding_ids that appear in exactly one record — item 413.

    A *singleton* finding_id is one whose total count in *problems* is exactly
    ``1``.  Finding_ids with count ``>= 2`` are excluded.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        :class:`frozenset` of finding_id strings with a total count of
        exactly ``1``.  ``frozenset()`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return frozenset(fid for fid, cnt in counts.items() if cnt == 1)


def repeated_finding_ids(problems: list[Problem]) -> frozenset[str]:
    """Return the frozenset of finding_ids that appear in two or more records — item 414.

    A *repeated* finding_id is one whose total count in *problems* is ``>= 2``.
    Finding_ids appearing in different classes still count as repeated — only
    the total histogram count matters.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        :class:`frozenset` of finding_id strings with a total count ``>= 2``.
        ``frozenset()`` when *problems* is empty or all fids are singletons.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return frozenset(fid for fid, cnt in counts.items() if cnt >= 2)


def top_n_classes(problems: list[Problem], n: int) -> list[tuple[str, int]]:
    """Return the top-N classes with their record counts as (name, count) tuples — item 415.

    Pairs each class name with its total record count and returns the *n*
    highest-count classes, sorted by descending count then ascending name for
    tie-breaking.  Returns at most *n* entries; ``[]`` when *n* ≤ 0 or
    *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances.
        n: Maximum number of (class, count) pairs to return.

    Returns:
        ``list[tuple[str, int]]`` of at most *n* ``(class_name, count)`` pairs,
        sorted descending by count then ascending class name.  ``[]`` when
        *problems* is empty or *n* ≤ 0.

    Pure (no I/O, no SurrealDB).
    """
    if not problems or n <= 0:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]


def top_n_finding_ids(problems: list[Problem], n: int) -> list[tuple[str, int]]:
    """Return the top-N finding_ids with their record counts as (fid, count) tuples — item 416.

    Pairs each finding_id with its total record count and returns the *n*
    highest-count fids, sorted by descending count then ascending fid for
    tie-breaking.  Returns at most *n* entries; ``[]`` when *n* ≤ 0 or
    *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances.
        n: Maximum number of (fid, count) pairs to return.

    Returns:
        ``list[tuple[str, int]]`` of at most *n* ``(finding_id, count)`` pairs,
        sorted descending by count then ascending fid.  ``[]`` when
        *problems* is empty or *n* ≤ 0.

    Pure (no I/O, no SurrealDB).
    """
    if not problems or n <= 0:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]


def class_coverage_ratio(problems: list[Problem]) -> dict[str, float]:
    """Return each class's fraction of total records — item 419.

    For each :attr:`Problem.problem_class`, computes its record count divided
    by the total number of records.  All values are in ``(0.0, 1.0]`` and sum
    to ``1.0``.  ``{}`` when *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        ``dict[str, float]`` mapping each class to its proportion of total
        records.  ``{}`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    total = len(problems)
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return {cls: count / total for cls, count in counts.items()}


def finding_id_coverage_ratio(problems: list[Problem]) -> dict[str, float]:
    """Return each finding_id's fraction of total records — item 420.

    For each :attr:`Problem.finding_id`, computes its record count divided by
    the total number of records.  All values are in ``(0.0, 1.0]`` and sum to
    ``1.0``.  ``{}`` when *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        ``dict[str, float]`` mapping each finding_id to its proportion of
        total records.  ``{}`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return {}
    total = len(problems)
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return {fid: count / total for fid, count in counts.items()}


def dominant_class(problems: list[Problem]) -> str | None:
    """Return the problem_class with the most records — item 421.

    Ties are broken alphabetically ascending (the lexicographically smallest
    class name wins).  Returns ``None`` when *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        The :attr:`Problem.problem_class` string with the highest record count,
        or ``None`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return min(counts, key=lambda cls: (-counts[cls], cls))


def dominant_finding_id(problems: list[Problem]) -> str | None:
    """Return the finding_id with the highest total record count -- item 422.

    Returns the :attr:`Problem.finding_id` string that appears the most times
    across the full dataset.  Ties are broken alphabetically ascending (the
    lexicographically smallest finding_id wins).  Returns ``None`` when
    *problems* is empty.

    Dual of :func:`dominant_class` operating on the finding_id axis.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        The :attr:`Problem.finding_id` string with the highest record count,
        or ``None`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    return min(counts, key=lambda fid: (-counts[fid], fid))


def class_entropy(problems: list[Problem]) -> float:
    """Return the Shannon entropy of the class distribution in bits -- item 423.

    Computes H = -sum(p * log2(p)) where *p* is the fraction of total records
    belonging to each :attr:`Problem.problem_class`.  Uses log base-2, so the
    result is in bits.

    Special cases:

    - Empty *problems* -> 0.0 (no uncertainty)
    - Single class -> 0.0 (-1.0 * log2(1.0) = 0)

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Shannon entropy of the class distribution in bits.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    total = len(problems)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def finding_id_entropy(problems: list[Problem]) -> float:
    """Return the Shannon entropy of the finding_id distribution in bits — item 424.

    Computes ``H = -Σ p · log₂(p)`` where ``p`` is each finding_id's fraction
    of the total record count.  A single fid gives ``H=0.0``.  Two equal fids
    give ``H=1.0`` bit.  Empty gives ``0.0``.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Shannon entropy in bits (``float >= 0.0``).  ``0.0`` when *problems*
        is empty or contains only one distinct finding_id.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    total = len(problems)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def class_gini_impurity(problems: list[Problem]) -> float:
    """Return the Gini impurity of the class distribution — item 425.

    Computes ``G = 1 - Σ p²`` where ``p`` is each class's fraction from
    :func:`class_coverage_ratio`.  A single class gives ``G=0.0`` (pure).
    Two equal classes give ``G=0.5``.  Empty gives ``0.0``.

    Unlike :func:`class_entropy` (which uses ``-p·log₂(p)``), Gini uses
    ``p²`` — making it quadratic rather than logarithmic.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Gini impurity in ``[0.0, 1.0)``.  ``0.0`` when *problems* is empty
        or contains only one distinct class.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    total = len(problems)
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    return 1.0 - sum((c / total) ** 2 for c in counts.values())


def class_balance_score(problems: list[Problem]) -> float:
    """Return the normalised class balance score -- item 426.

    Computes ``H / log2(n)`` where ``H`` is :func:`class_entropy` and ``n``
    is the number of distinct classes.  The score is 1.0 when all classes have
    equal record counts (maximum balance) and approaches 0.0 when one class
    dominates.

    Special cases:

    - Empty *problems* -> 1.0 (vacuously balanced)
    - Single class -> 1.0 (trivially balanced; entropy = 0, max_entropy = 0,
      so the ratio is defined as 1.0 by convention)

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Normalised balance score as a float in ``[0.0, 1.0]``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 1.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.problem_class] = counts.get(p.problem_class, 0) + 1
    n = len(counts)
    if n == 1:
        return 1.0
    total = len(problems)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    max_entropy = math.log2(n)
    return entropy / max_entropy


def finding_id_balance_score(problems: list[Problem]) -> float:
    """Return the normalised finding_id balance score -- item 427.

    Computes ``H / log2(n)`` where ``H`` is :func:`finding_id_entropy` and
    ``n`` is the number of distinct finding_ids.  The score is 1.0 when all
    finding_ids appear equally often (maximum balance) and approaches 0.0 when
    one finding_id dominates.

    Dual of :func:`class_balance_score` operating on the finding_id axis.

    Special cases:

    - Empty *problems* -> 1.0 (vacuously balanced)
    - Single finding_id -> 1.0 (trivially balanced)

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Normalised balance score as a float in ``[0.0, 1.0]``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 1.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.finding_id] = counts.get(p.finding_id, 0) + 1
    n = len(counts)
    if n == 1:
        return 1.0
    total = len(problems)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    max_entropy = math.log2(n)
    return entropy / max_entropy


def class_pair_co_occurrence(problems: list[Problem], class_a: str, class_b: str) -> int:
    """Return the count of distinct finding_ids in both class_a and class_b -- item 428.

    Computes the size of the set intersection of finding_ids belonging to
    *class_a* and finding_ids belonging to *class_b*.  Each finding_id is
    counted at most once regardless of how many records it has in either class.

    Special cases:

    - Empty *problems* -> 0
    - Unknown class -> 0 (empty set intersects to empty)
    - *class_a* == *class_b* -> count of distinct finding_ids in that class

    Args:
        problems: List of :class:`Problem` instances.
        class_a: First problem class name.
        class_b: Second problem class name.

    Returns:
        Number of distinct finding_ids that appear in both classes.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    fids_a: set[str] = {p.finding_id for p in problems if p.problem_class == class_a}
    fids_b: set[str] = {p.finding_id for p in problems if p.problem_class == class_b}
    return len(fids_a & fids_b)


def class_pair_exclusive_fids(
    problems: list[Problem], class_a: str, class_b: str
) -> frozenset[str]:
    """Return finding_ids in class_a that are NOT in class_b -- item 429.

    Computes the set difference ``fids_a - fids_b`` where *fids_a* is the set
    of distinct finding_ids in *class_a* and *fids_b* is the set of distinct
    finding_ids in *class_b*.  The result is asymmetric: swapping *class_a*
    and *class_b* generally yields a different result.

    Special cases:

    - Empty *problems* -> ``frozenset()``
    - Unknown class -> treated as empty set (no raise)

    Args:
        problems: List of :class:`Problem` instances.
        class_a: The class whose finding_ids form the base set.
        class_b: The class whose finding_ids are excluded.

    Returns:
        Frozenset of finding_id strings exclusive to *class_a*.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    classes_present = {p.problem_class for p in problems}
    if class_a not in classes_present or class_b not in classes_present:
        return frozenset()
    fids_a: frozenset[str] = frozenset(p.finding_id for p in problems if p.problem_class == class_a)
    fids_b: frozenset[str] = frozenset(p.finding_id for p in problems if p.problem_class == class_b)
    return fids_a - fids_b


def fid_class_jaccard(problems: list[Problem], class_a: str, class_b: str) -> float:
    """Return the Jaccard similarity between two classes on the finding_id axis -- item 430.

    Computes ``|fids_a ∩ fids_b| / |fids_a ∪ fids_b|`` where fids_a and fids_b are
    the sets of distinct finding_ids for *class_a* and *class_b* respectively.

    Special cases:

    - Empty *problems* -> 0.0
    - Unknown class (either/both) -> 0.0 (empty union -> treated as no overlap)
    - *class_a* == *class_b* -> 1.0 (identical sets: intersection == union)
    - Disjoint fid sets -> 0.0

    Args:
        problems: List of :class:`Problem` instances.
        class_a: First problem class name.
        class_b: Second problem class name.

    Returns:
        Jaccard similarity as a float in ``[0.0, 1.0]``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    fids_a: frozenset[str] = frozenset(p.finding_id for p in problems if p.problem_class == class_a)
    fids_b: frozenset[str] = frozenset(p.finding_id for p in problems if p.problem_class == class_b)
    union_size = len(fids_a | fids_b)
    if union_size == 0:
        return 0.0
    return len(fids_a & fids_b) / union_size


def problems_with_severity(problems: list[Problem], severity: str) -> list[Problem]:
    """Return problems whose severity field matches *severity* -- item 431.

    Case-sensitive match on :attr:`Problem.severity`.  Order is preserved.

    Args:
        problems: List of :class:`Problem` instances.
        severity: The severity value to filter by (case-sensitive).

    Returns:
        New list of :class:`Problem` instances with ``p.severity == severity``.
        Empty list when *problems* is empty or no match is found.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.severity == severity]


def class_severity_matrix(problems: list[Problem]) -> dict[str, dict[str, int]]:
    """Return a 2-D sparse count matrix keyed by class then severity -- item 434.

    Outer key is :attr:`Problem.problem_class`; inner key is
    :attr:`Problem.severity`.  Counts are positive integers.  Missing
    class/severity combinations are absent (sparse -- not zero-filled).

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Nested dict ``{class: {severity: count}}``.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    matrix: dict[str, dict[str, int]] = {}
    for p in problems:
        inner = matrix.setdefault(p.problem_class, {})
        inner[p.severity] = inner.get(p.severity, 0) + 1
    return matrix


def fid_severity_matrix(problems: list[Problem]) -> dict[str, dict[str, int]]:
    """Return a 2-D sparse count matrix keyed by finding_id then severity -- item 435.

    Outer key is :attr:`Problem.finding_id`; inner key is
    :attr:`Problem.severity`.  Counts are positive integers.  Missing
    fid/severity combinations are absent (sparse -- not zero-filled).

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Nested dict ``{finding_id: {severity: count}}``.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    matrix: dict[str, dict[str, int]] = {}
    for p in problems:
        inner = matrix.setdefault(p.finding_id, {})
        inner[p.severity] = inner.get(p.severity, 0) + 1
    return matrix


def severity_entropy(problems: list[Problem]) -> float:
    """Return the Shannon entropy of the severity distribution -- item 437.

    Computes ``H = -sum(p * log2(p))`` over the severity frequency
    distribution derived from *problems*.

    Special cases:

    - Empty *problems* -> 0.0
    - Single distinct severity -> 0.0 (no uncertainty)

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Shannon entropy in bits (log base 2) as a float.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    total = len(problems)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def severity_gini_impurity(problems: list[Problem]) -> float:
    """Return the Gini impurity of the severity distribution -- item 438.

    Computes ``G = 1 - sum(p^2)`` where *p* is the fraction of problems with
    each distinct severity value.

    Special cases:

    - Empty *problems* -> 0.0
    - Single distinct severity -> 0.0 (pure)
    - Two equal severities -> 0.5

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Gini impurity as a float in ``[0.0, 1.0)``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    total = len(problems)
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    return 1.0 - sum((c / total) ** 2 for c in counts.values())


def severity_balance_score(problems: list[Problem]) -> float:
    """Return the normalised severity balance score -- item 439.

    Computes ``severity_entropy / log2(num_distinct_severities)``, giving 1.0
    for perfectly uniform severity distributions and approaching 0.0 for
    maximally imbalanced ones.

    Special cases:

    - Empty *problems* -> 1.0 (vacuously balanced)
    - Single distinct severity -> 1.0 (trivially balanced)

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Normalised balance score as a float in ``[0.0, 1.0]``.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 1.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    n = len(counts)
    if n == 1:
        return 1.0
    total = len(problems)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    return entropy / math.log2(n)


def top_n_severities(problems: list[Problem], n: int) -> list[tuple[str, int]]:
    """Return the *n* most frequent severity values -- item 440.

    Results are sorted by descending count, with ties broken by ascending
    severity name (alphabetical order).

    Args:
        problems: List of :class:`Problem` instances.
        n: Maximum number of results to return.  0 returns an empty list.

    Returns:
        List of ``(severity, count)`` tuples, at most *n* entries.

    Pure (no I/O, no SurrealDB).
    """
    if not problems or n <= 0:
        return []
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]


def problems_for_severity(problems: list[Problem], severity: str) -> list[Problem]:
    """Return all problems whose severity field matches *severity* -- item 441.

    Case-sensitive match on :attr:`Problem.severity`.  Order is preserved.
    Follows the canonical ``problems_for_X`` accessor naming convention.

    Args:
        problems: List of :class:`Problem` instances.
        severity: The severity value to filter by (case-sensitive).

    Returns:
        New list of :class:`Problem` instances with ``p.severity == severity``.
        Empty list when *problems* is empty or no match is found.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.severity == severity]


def class_count_for_severity(problems: list[Problem], severity: str) -> int:
    """Return the number of distinct classes with at least one problem of *severity* -- item 442.

    Counts distinct :attr:`Problem.problem_class` values that appear in at
    least one record whose :attr:`Problem.severity` matches *severity*.

    Args:
        problems: List of :class:`Problem` instances.
        severity: The severity value to filter by (case-sensitive).

    Returns:
        Count of distinct problem classes with the given severity.
        Returns 0 when *problems* is empty or *severity* is not found.

    Pure (no I/O, no SurrealDB).
    """
    return len({p.problem_class for p in problems if p.severity == severity})


def fid_count_for_severity(problems: list[Problem], severity: str) -> int:
    """Return the number of distinct finding_ids with at least one problem of *severity* -- item 443.

    Counts distinct :attr:`Problem.finding_id` values that appear in at
    least one record whose :attr:`Problem.severity` matches *severity*.

    Args:
        problems: List of :class:`Problem` instances.
        severity: The severity value to filter by (case-sensitive).

    Returns:
        Count of distinct finding_ids with the given severity.
        Returns 0 when *problems* is empty or *severity* is not found.

    Pure (no I/O, no SurrealDB).
    """
    return len({p.finding_id for p in problems if p.severity == severity})


def severity_pair_co_occurrence(problems: list[Problem], severity_a: str, severity_b: str) -> int:
    """Return the count of distinct fids in both severity_a and severity_b -- item 444.

    Counts distinct :attr:`Problem.finding_id` values that appear in at least
    one record with *severity_a* AND in at least one record with *severity_b*.

    Args:
        problems: List of :class:`Problem` instances.
        severity_a: First severity value (case-sensitive).
        severity_b: Second severity value (case-sensitive).

    Returns:
        Count of finding_ids co-occurring in both severity groups.
        Returns 0 when *problems* is empty or either severity is not found.
        Symmetric: result is the same when *severity_a* and *severity_b* are swapped.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    fids_a: set[str] = {p.finding_id for p in problems if p.severity == severity_a}
    fids_b: set[str] = {p.finding_id for p in problems if p.severity == severity_b}
    return len(fids_a & fids_b)


def severity_pair_exclusive_fids(
    problems: list[Problem], severity_a: str, severity_b: str
) -> frozenset[str]:
    """Return finding_ids in severity_a that are NOT in severity_b -- item 445.

    Computes the set difference of fid sets filtered by severity:
    ``fids_a - fids_b`` where each fids_x is the set of distinct finding_ids
    for problems with severity x.

    Args:
        problems: List of :class:`Problem` instances.
        severity_a: The source severity (fids must appear here).
        severity_b: The exclusion severity (fids must NOT appear here).

    Returns:
        frozenset of finding_ids exclusive to *severity_a*.
        Returns ``frozenset()`` when *problems* is empty or either severity
        is not present (unanswerable query sentinel).
        Asymmetric: ``(a, b)`` differs from ``(b, a)`` in general.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return frozenset()
    severities_present = {p.severity for p in problems}
    if severity_a not in severities_present or severity_b not in severities_present:
        return frozenset()
    fids_a: frozenset[str] = frozenset(p.finding_id for p in problems if p.severity == severity_a)
    fids_b: frozenset[str] = frozenset(p.finding_id for p in problems if p.severity == severity_b)
    return fids_a - fids_b


def severity_fid_jaccard(problems: list[Problem], severity_a: str, severity_b: str) -> float:
    """Return the Jaccard similarity between severity_a and severity_b fid sets -- item 446.

    Computes ``|fids_a ∩ fids_b| / |fids_a ∪ fids_b|`` where each fids_x is
    the set of distinct :attr:`Problem.finding_id` values for records with
    severity x.

    Args:
        problems: List of :class:`Problem` instances.
        severity_a: First severity value (case-sensitive).
        severity_b: Second severity value (case-sensitive).

    Returns:
        Jaccard similarity as a float in ``[0.0, 1.0]``.
        Returns 0.0 when the union is empty (either or both severities absent,
        or *problems* is empty).

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    fids_a: set[str] = {p.finding_id for p in problems if p.severity == severity_a}
    fids_b: set[str] = {p.finding_id for p in problems if p.severity == severity_b}
    union_size = len(fids_a | fids_b)
    if union_size == 0:
        return 0.0
    return len(fids_a & fids_b) / union_size


def severity_fid_matrix(problems: list[Problem]) -> dict[str, dict[str, int]]:
    """Return a 2-D sparse count matrix keyed by severity then finding_id -- item 448.

    Outer key is :attr:`Problem.severity`; inner key is
    :attr:`Problem.finding_id`.  Counts are positive integers.  Missing
    severity/fid combinations are absent (sparse -- not zero-filled).
    Transpose of :func:`fid_severity_matrix`.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Nested dict ``{severity: {finding_id: count}}``.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    matrix: dict[str, dict[str, int]] = {}
    for p in problems:
        inner = matrix.setdefault(p.severity, {})
        inner[p.finding_id] = inner.get(p.finding_id, 0) + 1
    return matrix


def all_severities(problems: list[Problem]) -> list[str]:
    """Return a sorted list of all distinct severity values -- item 449.

    Returns ``sorted(set(p.severity for p in problems))``.  Each severity
    appears exactly once, regardless of how many records share it.  The result
    is sorted alphabetically for deterministic output.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Sorted list of distinct severity strings.  Empty list for empty input.

    Pure (no I/O, no SurrealDB).
    """
    return sorted({p.severity for p in problems})


def severity_labelling_ratio(problems: list[Problem]) -> float:
    """Return the fraction of Problem records with a non-empty severity -- item 451.

    Counts the number of records whose :attr:`Problem.severity` field is
    non-empty (a labelled record) and divides by the total record count.
    Distinct from :func:`severity_coverage_ratio` which returns a
    ``dict[str, float]`` of class coverage per severity.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Scalar ``float`` in ``[0.0, 1.0]``.  ``0.0`` for empty input or
        when all records are unlabelled.  ``1.0`` when all records are labelled.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    labelled = sum(1 for p in problems if p.severity)
    return labelled / len(problems)


def rarest_severity(problems: list[Problem]) -> str | None:
    """Return the severity value with the fewest Problem records -- item 453.

    Returns the anti-mode of the severity distribution.  When multiple
    severities share the minimum count, the alphabetically smallest value
    is returned (deterministic tie-breaking).

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        The least-frequent severity string, or ``None`` for empty input.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return None
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    return min(counts, key=lambda sev: (counts[sev], sev))


def severity_rank(problems: list[Problem], severity: str) -> int:
    """Return the 1-based dense rank of *severity* by descending record count -- item 454.

    Rank 1 is the most common severity.  Severities with equal counts share
    the same rank (dense rank: no gaps between adjacent ranks).  Returns 0
    if *severity* is not found in *problems* or if *problems* is empty.

    Args:
        problems: List of :class:`Problem` instances.
        severity: The severity value to rank.

    Returns:
        1-based integer rank.  ``0`` when *severity* is absent or input
        is empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    if severity not in counts:
        return 0
    # Dense rank: rank = number of distinct counts strictly greater than this one, plus 1
    my_count = counts[severity]
    distinct_higher = len({c for c in counts.values() if c > my_count})
    return distinct_higher + 1


def severity_percentile(problems: list[Problem], severity: str) -> float:
    """Return the percentile rank of *severity* in the count distribution -- item 455.

    Uses the formula ``100.0 * (n - rank) / (n - 1)`` where ``n`` is the
    number of distinct severities and ``rank`` is the 1-based dense rank
    (most common = rank 1).  Special cases:

    - Empty *problems* or absent *severity* → ``0.0``
    - Single distinct severity → ``100.0`` (trivially the most common)

    Args:
        problems: List of :class:`Problem` instances.
        severity: The severity value whose percentile to compute.

    Returns:
        Float in ``[0.0, 100.0]``.  ``100.0`` for the most common severity;
        ``0.0`` for the rarest or when absent/empty.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    if severity not in counts:
        return 0.0
    n = len(counts)
    if n == 1:
        return 100.0
    my_count = counts[severity]
    distinct_higher = len({c for c in counts.values() if c > my_count})
    rank = distinct_higher + 1
    return 100.0 * (n - rank) / (n - 1)


def severity_z_score(problems: list[Problem], severity: str) -> float:
    """Return the z-score of *severity*'s count relative to all severity counts -- item 456.

    Computes ``(count[severity] - mean_count) / stdev_count`` using population
    standard deviation.  Returns ``0.0`` when:

    - *problems* is empty
    - *severity* is not found in *problems*
    - Standard deviation is zero (all severities have equal count)

    A negative z-score means the severity is below the mean count (rarer than
    average); a positive z-score means above average.

    Args:
        problems: List of :class:`Problem` instances.
        severity: The severity value whose z-score to compute.

    Returns:
        Float z-score.  ``0.0`` for edge cases described above.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    if severity not in counts:
        return 0.0
    values = list(counts.values())
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    stdev = variance**0.5
    if stdev == 0.0:
        return 0.0
    return (counts[severity] - mean) / stdev


def severity_iqr(problems: list[Problem]) -> float:
    """Return the interquartile range of severity counts -- item 457.

    Computes Q3 - Q1 over the sorted list of per-severity record counts.
    Uses the inclusive (Tukey hinges / median-of-halves) quartile method
    via :func:`statistics.quantiles`.

    Special cases:
    - Empty *problems* → ``0.0``
    - Single distinct severity → ``0.0`` (no spread)
    - All severities with equal counts → ``0.0`` (Q1 == Q3)

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Non-negative float.  ``Q3 - Q1`` of the severity count distribution.

    Pure (no I/O, no SurrealDB).
    """
    import statistics

    if not problems:
        return 0.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    if len(counts) <= 1:
        return 0.0
    sorted_counts = sorted(counts.values())
    quartiles = statistics.quantiles(sorted_counts, n=4, method="inclusive")
    return float(quartiles[2] - quartiles[0])


def severity_cv(problems: list[Problem]) -> float:
    """Return the coefficient of variation of severity counts -- item 458.

    CV = population_stdev / mean over the per-severity record counts.
    A dimensionless measure of relative spread in the count distribution.

    Special cases:
    - Empty *problems* → ``0.0``
    - Single distinct severity → ``0.0`` (stdev is 0; no spread to measure)
    - All severities with equal counts → ``0.0`` (stdev == 0)

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Non-negative float.  ``population_stdev / mean`` of severity counts.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    if len(counts) <= 1:
        return 0.0
    values = list(counts.values())
    n = len(values)
    mean = sum(values) / n
    if mean == 0.0:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / n
    stdev = variance**0.5
    return stdev / mean


def severity_mean_count(problems: list[Problem]) -> float:
    """Return the mean record count per distinct severity -- item 459.

    Computes the arithmetic mean of the per-severity record counts:
    ``total_records / distinct_severity_count``.

    Special cases:
    - Empty *problems* → ``0.0``

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Non-negative float.  Arithmetic mean of all per-severity counts.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0.0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    return float(sum(counts.values()) / len(counts))


def severity_min_count(problems: list[Problem]) -> int:
    """Return the minimum record count across all distinct severities -- item 460.

    Equivalent to ``min(per_severity_counts)``.

    Special cases:
    - Empty *problems* → ``0``

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Non-negative int.  Smallest per-severity record count.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    return min(counts.values())


def severity_max_count(problems: list[Problem]) -> int:
    """Return the maximum record count across all distinct severities -- item 461.

    Equivalent to ``max(per_severity_counts)``.

    Special cases:
    - Empty *problems* → ``0``

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Non-negative int.  Largest per-severity record count.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    return max(counts.values())


def severity_count_range(problems: list[Problem]) -> int:
    """Return the range of per-severity record counts -- item 462.

    Computes ``max(counts) - min(counts)``.  When all severities have equal
    counts the range is 0.

    Special cases:
    - Empty *problems* → ``0``
    - Single distinct severity → ``0`` (min == max)

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Non-negative int.  ``max_count - min_count`` of severity counts.

    Pure (no I/O, no SurrealDB).
    """
    if not problems:
        return 0
    counts: dict[str, int] = {}
    for p in problems:
        counts[p.severity] = counts.get(p.severity, 0) + 1
    vals = counts.values()
    return max(vals) - min(vals)


def fids_with_severity(problems: list[Problem], severity: str) -> list[str]:
    """Return sorted finding_ids that have at least one problem at *severity* -- item 464.

    Symmetric complement to :func:`classes_with_severity` on the finding_id axis.

    Args:
        problems: List of :class:`Problem` instances.
        severity: Target severity string.  Unknown values return ``[]``.

    Returns:
        Sorted :class:`list` of distinct ``finding_id`` strings.  Empty when
        *problems* is empty or no record matches *severity*.

    Pure (no I/O, no SurrealDB).
    """
    return sorted({p.finding_id for p in problems if p.severity == severity})


def dominant_severity_for_class(problems: list[Problem], problem_class: str) -> str | None:
    """Return the most common severity within *problem_class* -- item 465.

    Counts per-severity records for problems whose ``problem_class`` matches
    exactly.  Returns the severity with the highest count.  Tie-break: the
    alphabetically-first severity wins, ensuring a deterministic result.

    Special cases:
    - Empty *problems* or absent *problem_class* → ``None``

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: Target class to filter on.

    Returns:
        The dominant severity string, or ``None`` when the class is absent.

    Pure (no I/O, no SurrealDB).
    """
    counts: dict[str, int] = {}
    for p in problems:
        if p.problem_class == problem_class:
            counts[p.severity] = counts.get(p.severity, 0) + 1
    if not counts:
        return None
    return min(counts, key=lambda s: (-counts[s], s))


def dominant_severity_for_fid(problems: list[Problem], finding_id: str) -> str | None:
    """Return the most common severity for *finding_id* -- item 466.

    Counts per-severity records for problems whose ``finding_id`` matches
    exactly, across all classes.  Returns the severity with the highest count.
    Tie-break: the alphabetically-first severity wins.

    Special cases:
    - Empty *problems* or absent *finding_id* → ``None``

    Args:
        problems: List of :class:`Problem` instances.
        finding_id: Target finding_id to filter on.

    Returns:
        The dominant severity string, or ``None`` when the fid is absent.

    Pure (no I/O, no SurrealDB).
    """
    counts: dict[str, int] = {}
    for p in problems:
        if p.finding_id == finding_id:
            counts[p.severity] = counts.get(p.severity, 0) + 1
    if not counts:
        return None
    return min(counts, key=lambda s: (-counts[s], s))


def dominant_class_for_severity(problems: list[Problem], severity: str) -> str | None:
    """Return the problem_class most associated with *severity* -- item 467.

    Counts per-class records for problems whose ``severity`` matches exactly.
    Returns the class with the highest count.  Tie-break: alphabetically first.

    Special cases:
    - Empty *problems* or absent *severity* → ``None``

    Args:
        problems: List of :class:`Problem` instances.
        severity: Target severity to filter on.

    Returns:
        The dominant class string, or ``None`` when the severity is absent.

    Pure (no I/O, no SurrealDB).
    """
    class_counts: dict[str, int] = {}
    for p in problems:
        if p.severity == severity:
            class_counts[p.problem_class] = class_counts.get(p.problem_class, 0) + 1
    if not class_counts:
        return None
    return min(class_counts, key=lambda c: (-class_counts[c], c))


def dominant_fid_for_severity(problems: list[Problem], severity: str) -> str | None:
    """Return the finding_id most associated with *severity* -- item 468.

    Counts per-fid records for problems whose ``severity`` matches exactly.
    Returns the fid with the highest count.  Tie-break: alphabetically first.

    Special cases:
    - Empty *problems* or absent *severity* -> ``None``

    Args:
        problems: List of :class:`Problem` instances.
        severity: Target severity to filter on.

    Returns:
        The dominant fid string, or ``None`` when the severity is absent.

    Pure (no I/O, no SurrealDB).
    """
    fid_counts: dict[str, int] = {}
    for p in problems:
        if p.severity == severity:
            fid_counts[p.finding_id] = fid_counts.get(p.finding_id, 0) + 1
    if not fid_counts:
        return None
    return min(fid_counts, key=lambda f: (-fid_counts[f], f))


def severity_count_for_class(problems: list[Problem], problem_class: str, severity: str) -> int:
    """Return count of records matching both *problem_class* and *severity* -- item 469.

    The raw intersection count at the (class, severity) cell of the 2-D
    count matrix.

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: Target class to filter on.
        severity: Target severity to filter on.

    Returns:
        Non-negative int.  0 when either axis value is absent.

    Pure (no I/O, no SurrealDB).
    """
    return sum(1 for p in problems if p.problem_class == problem_class and p.severity == severity)


def severity_count_for_fid(problems: list[Problem], finding_id: str, severity: str) -> int:
    """Return the count of problems matching BOTH finding_id AND severity -- item 470.

    Symmetric complement to :func:`severity_count_for_class` on the fid axis.

    Special cases:
    - Empty *problems*, absent *finding_id*, or absent *severity* → ``0``

    Args:
        problems: List of :class:`Problem` instances.
        finding_id: Target finding_id to filter on.
        severity: Target severity to filter on.

    Returns:
        Non-negative int.  Count of records matching both filters.

    Pure (no I/O, no SurrealDB).
    """
    return sum(1 for p in problems if p.finding_id == finding_id and p.severity == severity)


def problem_count_for_class_fid_pair(
    problems: list[Problem], problem_class: str, finding_id: str
) -> int:
    """Return count of records matching BOTH *problem_class* AND *finding_id* -- item 471.

    The raw intersection count at the (class, fid) cell of the 2-D count matrix.
    Completes the 3-axis cross-product triangle: class×severity (469),
    fid×severity (470), class×fid (471).

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: Target class to filter on.
        finding_id: Target finding_id to filter on.

    Returns:
        Non-negative int.  0 when either axis value is absent.

    Pure (no I/O, no SurrealDB).
    """
    return sum(
        1 for p in problems if p.problem_class == problem_class and p.finding_id == finding_id
    )


def class_fid_matrix(problems: list[Problem]) -> dict[str, dict[str, int]]:
    """Return 2-D count matrix of class × finding_id co-occurrences -- item 472.

    ``matrix[cls][fid]`` is the count of records matching both *problem_class* == cls
    and *finding_id* == fid.  Sparse: absent pairs are not present as keys.
    Complements ``class_severity_matrix`` on the fid dimension.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Nested dict ``dict[str, dict[str, int]]``.  Empty dict for empty input.

    Pure (no I/O, no SurrealDB).
    """
    matrix: dict[str, dict[str, int]] = {}
    for p in problems:
        row = matrix.setdefault(p.problem_class, {})
        row[p.finding_id] = row.get(p.finding_id, 0) + 1
    return matrix


def three_axis_count(
    problems: list[Problem],
    problem_class: str,
    finding_id: str,
    severity: str,
) -> int:
    """Return count of records matching ALL THREE axes -- item 473.

    Full 3-axis intersection: *problem_class* AND *finding_id* AND *severity*
    must all match.  Completes the cross-product triangle (items 469/470/471
    cover 2-axis joins; this exposes the 3-axis point query).

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: Target class to filter on.
        finding_id: Target finding_id to filter on.
        severity: Target severity to filter on.

    Returns:
        Non-negative int.  0 when any axis value is absent.

    Pure (no I/O, no SurrealDB).
    """
    return sum(
        1
        for p in problems
        if p.problem_class == problem_class
        and p.finding_id == finding_id
        and p.severity == severity
    )


def three_axis_matrix(
    problems: list[Problem],
) -> dict[str, dict[str, dict[str, int]]]:
    """Return 3-D sparse count tensor: class x fid x severity -- item 474.

    ``tensor[cls][fid][sev]`` is the count of records matching all three axes.
    Sparse: absent triples are not present as keys.
    Generalises the 2-D matrices (items 472/fid_severity_matrix) to 3 dimensions.

    Args:
        problems: List of :class:`Problem` instances.

    Returns:
        Three-level nested dict.  Empty dict for empty input.

    Pure (no I/O, no SurrealDB).
    """
    tensor: dict[str, dict[str, dict[str, int]]] = {}
    for p in problems:
        fid_row = tensor.setdefault(p.problem_class, {})
        sev_row = fid_row.setdefault(p.finding_id, {})
        sev_row[p.severity] = sev_row.get(p.severity, 0) + 1
    return tensor


def problems_at_triple(
    problems: list[Problem],
    problem_class: str,
    finding_id: str,
    severity: str,
) -> list[Problem]:
    """Return Problem records matching ALL three axes -- item 475.

    Filter complement to :func:`three_axis_count`: returns the actual
    :class:`Problem` objects (not just the count) for the given
    (class, fid, severity) triple.  Preserves insertion order.

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: Target class to filter on.
        finding_id: Target finding_id to filter on.
        severity: Target severity to filter on.

    Returns:
        List of matching :class:`Problem` objects.
        Empty list when the triple is absent.

    Pure (no I/O, no SurrealDB).
    """
    return [
        p
        for p in problems
        if p.problem_class == problem_class
        and p.finding_id == finding_id
        and p.severity == severity
    ]


def problems_for_fid(
    problems: list[Problem],
    finding_id: str,
) -> list[Problem]:
    """Return Problem records matching *finding_id* -- item 477.

    Symmetric to :func:`problems_for_class` on the finding_id axis.
    Preserves insertion order of matching records.

    Args:
        problems: List of :class:`Problem` instances.
        finding_id: Target finding_id.

    Returns:
        List of :class:`Problem` instances.  Empty list when absent.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.finding_id == finding_id]


def problems_matching_class_and_severity(
    problems: list[Problem],
    problem_class: str,
    severity: str,
) -> list[Problem]:
    """Return Problem records matching BOTH problem_class AND severity -- item 479.

    Complements :func:`severity_count_for_class` (returns list, not int).
    Preserves insertion order of matching records.

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: Target problem_class.
        severity: Target severity.

    Returns:
        List of :class:`Problem` instances.  Empty list when absent pair.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.problem_class == problem_class and p.severity == severity]


def problems_matching_fid_and_severity(
    problems: list[Problem],
    finding_id: str,
    severity: str,
) -> list[Problem]:
    """Return Problem records matching BOTH finding_id AND severity -- item 480.

    Symmetric to :func:`problems_matching_class_and_severity` on the fid axis.
    Complements :func:`severity_count_for_fid` (returns list, not int).
    Preserves insertion order of matching records.

    Args:
        problems: List of :class:`Problem` instances.
        finding_id: Target finding_id.
        severity: Target severity.

    Returns:
        List of :class:`Problem` instances.  Empty list when absent pair.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.finding_id == finding_id and p.severity == severity]


def problems_matching_class_and_fid(
    problems: list[Problem],
    problem_class: str,
    finding_id: str,
) -> list[Problem]:
    """Return Problem records matching BOTH problem_class AND finding_id -- item 481.

    Completes the 3-pair symmetric filter set alongside
    :func:`problems_matching_class_and_severity` and
    :func:`problems_matching_fid_and_severity`.
    Complements :func:`problem_count_for_class_fid_pair` (returns list, not int).
    Preserves insertion order of matching records.

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: Target problem_class.
        finding_id: Target finding_id.

    Returns:
        List of :class:`Problem` instances.  Empty list when absent pair.

    Pure (no I/O, no SurrealDB).
    """
    return [p for p in problems if p.problem_class == problem_class and p.finding_id == finding_id]


def class_total_severity_score(
    problems: list[Problem],
    problem_class: str,
    weights: dict[str, float],
) -> float:
    """Return the aggregate severity score for *problem_class* using *weights* -- item 482.

    For each :class:`Problem` in *problem_class*, adds ``weights.get(p.severity, 0.0)``
    to the running total.  Unrecognised severities contribute 0.  Returns 0.0 when
    *problem_class* is absent or *weights* is empty.

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: Target problem_class.
        weights: Mapping of severity label to score (e.g. ``{"HIGH": 3.0, "LOW": 1.0}``).

    Returns:
        float.  Non-negative when all weights are non-negative.

    Pure (no I/O, no SurrealDB).
    """
    return float(
        sum(weights.get(p.severity, 0.0) for p in problems if p.problem_class == problem_class)
    )


def fid_total_severity_score(
    problems: list[Problem],
    finding_id: str,
    weights: dict[str, float],
) -> float:
    """Return the aggregate severity score for *finding_id* using *weights* -- item 483.

    Symmetric to :func:`class_total_severity_score` on the finding_id axis.
    For each :class:`Problem` with *finding_id*, adds ``weights.get(p.severity, 0.0)``
    to the running total.  Unrecognised severities contribute 0.

    Args:
        problems: List of :class:`Problem` instances.
        finding_id: Target finding_id.
        weights: Mapping of severity label to score.

    Returns:
        float.  0.0 when *finding_id* is absent or *weights* is empty.

    Pure (no I/O, no SurrealDB).
    """
    return float(sum(weights.get(p.severity, 0.0) for p in problems if p.finding_id == finding_id))


def all_severity_scores(
    problems: list[Problem],
    weights: dict[str, float],
) -> dict[str, float]:
    """Return total severity score for every class using *weights* -- item 484.

    Bulk form of :func:`class_total_severity_score`: returns a mapping from
    every class present in *problems* to its total weighted severity score.
    Classes whose problems all have unrecognised severities score 0.0 but
    are still included (non-sparse by class: every class that appears).

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.  Unrecognised
            severity labels contribute 0.0.

    Returns:
        ``{class_name: total_score}`` for each unique class in *problems*.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    scores: dict[str, float] = {}
    for p in problems:
        if p.problem_class not in scores:
            scores[p.problem_class] = 0.0
        scores[p.problem_class] += weights.get(p.severity, 0.0)
    return scores


def all_fid_severity_scores(
    problems: list[Problem],
    weights: dict[str, float],
) -> dict[str, float]:
    """Return total severity score for every finding_id using *weights* -- item 485.

    Bulk form of :func:`fid_total_severity_score` and the fid-axis symmetric
    complement to :func:`all_severity_scores`.  Every fid present in *problems*
    appears in the result, including those whose records all have unrecognised
    severities (score 0.0).

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.  Unrecognised
            severity labels contribute 0.0.

    Returns:
        ``{finding_id: total_score}`` for each unique fid in *problems*.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    scores: dict[str, float] = {}
    for p in problems:
        if p.finding_id not in scores:
            scores[p.finding_id] = 0.0
        scores[p.finding_id] += weights.get(p.severity, 0.0)
    return scores


def top_n_classes_by_score(
    problems: list[Problem],
    weights: dict[str, float],
    n: int,
) -> list[str]:
    """Return the top-*n* class names ranked by total severity score -- item 486.

    Builds the per-class weighted score (same logic as
    :func:`all_severity_scores`) then returns the *n* class names with the
    highest score, sorted descending by score with an alphabetical tie-break.
    Classes whose problems all have unrecognised severities score 0.0 and
    appear in the ranking as normal.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        n: Maximum number of class names to return.  ``n=0`` returns ``[]``.

    Returns:
        ``list[str]`` of at most *n* class names, descending by score,
        alphabetical tie-break.  Empty list when ``n=0`` or *problems* is
        empty.

    Pure (no I/O, no SurrealDB).
    """
    if n <= 0:
        return []
    scores: dict[str, float] = {}
    for p in problems:
        if p.problem_class not in scores:
            scores[p.problem_class] = 0.0
        scores[p.problem_class] += weights.get(p.severity, 0.0)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [cls for cls, _ in ranked[:n]]


def top_n_fids_by_score(
    problems: list[Problem],
    weights: dict[str, float],
    n: int,
) -> list[str]:
    """Return the N finding_ids with the highest total severity score -- item 487.

    Symmetric to :func:`top_n_classes_by_score` on the fid axis.  Scoring is
    identical to :func:`all_fid_severity_scores`: each matching record
    contributes ``weights.get(p.severity, 0.0)`` to the fid total.

    Ordering: descending by score; alphabetical (ascending) tie-break.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        n: Maximum number of fid names to return.  ``n=0`` returns ``[]``.

    Returns:
        ``list[str]`` of at most *n* finding_id strings, descending by score,
        alphabetical tie-break.  Empty list when ``n=0`` or *problems* is
        empty.

    Pure (no I/O, no SurrealDB).
    """
    if n <= 0:
        return []
    scores: dict[str, float] = {}
    for p in problems:
        if p.finding_id not in scores:
            scores[p.finding_id] = 0.0
        scores[p.finding_id] += weights.get(p.severity, 0.0)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [fid for fid, _ in ranked[:n]]


def classes_above_score_threshold(
    problems: list[Problem],
    weights: dict[str, float],
    threshold: float,
) -> frozenset[str]:
    """Return class names whose total weighted severity score STRICTLY exceeds threshold -- item 489.

    Scoring mirrors :func:`all_severity_scores`: each record contributes
    ``weights.get(p.severity, 0.0)`` to its class total.  Only classes with
    ``score > threshold`` (strict) are included; classes at exactly *threshold*
    are excluded.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        threshold: Score boundary (exclusive upper bound for exclusion).

    Returns:
        ``frozenset[str]`` of class names with total score strictly above
        *threshold*.  ``frozenset()`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    scores: dict[str, float] = {}
    for p in problems:
        if p.problem_class not in scores:
            scores[p.problem_class] = 0.0
        scores[p.problem_class] += weights.get(p.severity, 0.0)
    return frozenset(cls for cls, score in scores.items() if score > threshold)


def fids_above_score_threshold(
    problems: list[Problem],
    weights: dict[str, float],
    threshold: float,
) -> frozenset[str]:
    """Return fid names whose total weighted severity score STRICTLY exceeds threshold -- item 490.

    Symmetric to :func:`classes_above_score_threshold` on the fid axis.
    Scoring mirrors :func:`all_fid_severity_scores`: each record contributes
    ``weights.get(p.severity, 0.0)`` to its fid total.  Only fids with
    ``score > threshold`` (strict) are included; fids at exactly *threshold*
    are excluded.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        threshold: Score boundary (exclusive upper bound for exclusion).

    Returns:
        ``frozenset[str]`` of finding_id strings with total score strictly
        above *threshold*.  ``frozenset()`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    scores: dict[str, float] = {}
    for p in problems:
        if p.finding_id not in scores:
            scores[p.finding_id] = 0.0
        scores[p.finding_id] += weights.get(p.severity, 0.0)
    return frozenset(fid for fid, score in scores.items() if score > threshold)


def score_delta_between_snapshots(
    before: list[Problem],
    after: list[Problem],
    problem_class: str,
    weights: dict[str, float],
) -> float:
    """Return signed score change for *problem_class* between two snapshots -- item 491.

    Computes ``class_total_severity_score(after, cls, w)``
    minus ``class_total_severity_score(before, cls, w)``.

    Positive delta = score increased (class has more/higher-weighted problems
    in *after* than in *before*).  Negative delta = score decreased (improvement).
    When the class is absent in both snapshots the delta is 0.0.

    Args:
        before: Problem list from the earlier scan.
        after:  Problem list from the more recent scan.
        problem_class: The class to measure.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``float`` signed score delta.  0.0 when *problem_class* is absent in
        both snapshots.

    Pure (no I/O, no SurrealDB).
    """
    score_before = sum(
        weights.get(p.severity, 0.0) for p in before if p.problem_class == problem_class
    )
    score_after = sum(
        weights.get(p.severity, 0.0) for p in after if p.problem_class == problem_class
    )
    return float(score_after - score_before)


def all_score_deltas_between_snapshots(
    before: list[Problem],
    after: list[Problem],
    weights: dict[str, float],
) -> dict[str, float]:
    """Return per-class signed score deltas between two snapshots -- item 492.

    Computes ``score_after[cls] - score_before[cls]`` for every class in the
    UNION of *before* and *after*.  Classes present only in *after* contribute
    a positive delta (their full after score); classes present only in *before*
    contribute a negative delta (their before score negated).

    Args:
        before: Problem list from the earlier scan.
        after:  Problem list from the more recent scan.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``dict[str, float]`` mapping each class to its signed score change.
        Empty dict when both *before* and *after* are empty.

    Pure (no I/O, no SurrealDB).
    """
    scores_before: dict[str, float] = {}
    for p in before:
        scores_before[p.problem_class] = scores_before.get(p.problem_class, 0.0) + weights.get(
            p.severity, 0.0
        )
    scores_after: dict[str, float] = {}
    for p in after:
        scores_after[p.problem_class] = scores_after.get(p.problem_class, 0.0) + weights.get(
            p.severity, 0.0
        )
    all_classes = scores_before.keys() | scores_after.keys()
    return {
        cls: float(scores_after.get(cls, 0.0) - scores_before.get(cls, 0.0)) for cls in all_classes
    }


def regressing_classes(
    before: list[Problem],
    after: list[Problem],
    weights: dict[str, float],
) -> frozenset[str]:
    """Return class names whose weighted severity score INCREASED between snapshots -- item 493.

    A class is *regressing* when its total severity score is strictly higher in
    *after* than in *before* (delta > 0).  Improving classes (delta < 0) and
    stable classes (delta == 0) are excluded.  New classes that appear only in
    *after* with a positive score are considered regressing (score 0 → positive).

    Args:
        before: Problem list from the earlier scan.
        after:  Problem list from the more recent scan.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``frozenset[str]`` of class names with strictly positive score delta.
        ``frozenset()`` when both *before* and *after* are empty.

    Pure (no I/O, no SurrealDB).
    """
    deltas = all_score_deltas_between_snapshots(before, after, weights)
    return frozenset(cls for cls, delta in deltas.items() if delta > 0.0)


def improving_classes(
    before: list[Problem],
    after: list[Problem],
    weights: dict[str, float],
) -> frozenset[str]:
    """Return class names whose weighted severity score DECREASED between snapshots -- item 494.

    A class is *improving* when its total severity score is strictly lower in
    *after* than in *before* (delta < 0).  Worsening classes (delta > 0) and
    stable classes (delta == 0) are excluded.  A class that disappears entirely
    from *after* has score 0, which is lower than any positive *before* score,
    so it is considered improving.

    Args:
        before: Problem list from the earlier scan.
        after:  Problem list from the more recent scan.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``frozenset[str]`` of class names with strictly negative score delta.
        ``frozenset()`` when both *before* and *after* are empty.

    Pure (no I/O, no SurrealDB).
    """
    deltas = all_score_deltas_between_snapshots(before, after, weights)
    return frozenset(cls for cls, delta in deltas.items() if delta < 0.0)


def largest_regression(
    before: list[Problem],
    after: list[Problem],
    weights: dict[str, float],
) -> tuple[str, float] | None:
    """Return the (class, delta) pair for the class with the biggest positive delta -- item 496.

    Scans all per-class score deltas and returns the class whose score
    increased the most (highest positive delta).  Tie-break: alphabetically
    ascending class name.  Returns ``None`` when no class has a positive
    delta (i.e. all classes are stable or improving).

    Args:
        before: Problem list from the earlier scan.
        after:  Problem list from the more recent scan.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``(class_name, delta)`` tuple for the highest positive delta, or
        ``None`` if no class regressed.

    Pure (no I/O, no SurrealDB).
    """
    deltas = all_score_deltas_between_snapshots(before, after, weights)
    positive = [(cls, delta) for cls, delta in deltas.items() if delta > 0.0]
    if not positive:
        return None
    return max(positive, key=lambda kv: (kv[1], [-ord(c) for c in kv[0]]))


def largest_improvement(
    before: list[Problem],
    after: list[Problem],
    weights: dict[str, float],
) -> tuple[str, float] | None:
    """Return the (class, delta) pair for the class with the most negative delta -- item 497.

    Symmetric to :func:`largest_regression` for improving classes.  Scans all
    per-class score deltas and returns the class whose score decreased the most
    (lowest/most-negative delta).  Tie-break: alphabetically ascending class name.
    Returns ``None`` when no class has a negative delta (all stable or worsening).

    The ``delta`` in the returned tuple is negative (it represents the score
    decrease, not the absolute magnitude).

    Args:
        before: Problem list from the earlier scan.
        after:  Problem list from the more recent scan.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``(class_name, delta)`` tuple where delta is negative, for the class
        that improved the most.  ``None`` if no class improved.

    Pure (no I/O, no SurrealDB).
    """
    deltas = all_score_deltas_between_snapshots(before, after, weights)
    negative = [(cls, delta) for cls, delta in deltas.items() if delta < 0.0]
    if not negative:
        return None
    # min delta (most negative) = most improved; tie-break alpha ascending
    # Use min() with key: (delta ascending, name ascending for ties)
    return min(negative, key=lambda kv: (kv[1], kv[0]))


def score_summary(
    problems: list[Problem],
    problem_class: str,
    weights: dict[str, float],
) -> dict[str, float]:
    """Return a scoring statistics summary for *problem_class* -- item 498.

    Computes three scalar statistics for the class in a single pass:

    * ``total`` — sum of ``weights.get(p.severity, 0.0)`` for all matching records.
    * ``mean``  — ``total / count`` (0.0 when the class is absent or has no records).
    * ``max_single`` — maximum per-record weight (0.0 when the class is absent).

    All three keys are always present in the returned dict.  Unknown severities
    (not in *weights*) contribute 0 to all three statistics.

    Args:
        problems: List of :class:`Problem` instances.
        problem_class: The class to summarise.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``dict[str, float]`` with keys ``"total"``, ``"mean"``, ``"max_single"``.

    Pure (no I/O, no SurrealDB).
    """
    matching_scores = [
        weights.get(p.severity, 0.0) for p in problems if p.problem_class == problem_class
    ]
    count = len(matching_scores)
    if count == 0:
        return {"total": 0.0, "mean": 0.0, "max_single": 0.0}
    total = sum(matching_scores)
    return {
        "total": float(total),
        "mean": float(total / count),
        "max_single": float(max(matching_scores)),
    }


def all_score_summaries(
    problems: list[Problem],
    weights: dict[str, float],
) -> dict[str, dict[str, float]]:
    """Return per-class score summaries for every class in problems -- item 499.

    Bulk version of :func:`score_summary`.  Computes ``total``, ``mean``,
    and ``max_single`` for every distinct ``problem_class`` in *problems*.

    Each inner dict has exactly the three keys:
    * ``"total"`` — sum of ``weights.get(p.severity, 0.0)`` for class records.
    * ``"mean"``  — ``total / count`` (0.0 when count is 0, but that cannot
      occur here since a class only appears when it has ≥1 record).
    * ``"max_single"`` — maximum per-record weight for the class.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``dict[str, dict[str, float]]`` keyed by class name.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).
    """
    # Collect per-class score lists in one pass
    class_scores: dict[str, list[float]] = {}
    for p in problems:
        score = weights.get(p.severity, 0.0)
        if p.problem_class not in class_scores:
            class_scores[p.problem_class] = []
        class_scores[p.problem_class].append(score)
    result: dict[str, dict[str, float]] = {}
    for cls, scores in class_scores.items():
        total = sum(scores)
        result[cls] = {
            "total": float(total),
            "mean": float(total / len(scores)),
            "max_single": float(max(scores)),
        }
    return result


def problems_with_max_severity_score(
    problems: list[Problem],
    weights: dict[str, float],
) -> list[Problem]:
    """Return all Problem records whose per-record severity weight equals the global maximum.

    Computes the maximum per-record weight across *all* problems, then returns
    every record whose weight equals that maximum.  All ties are included.
    Insertion order is preserved.  When *problems* is empty, returns ``[]``.

    When every record has an unknown severity (not in *weights*), each record
    receives weight ``0.0`` which becomes the global maximum, so ALL records are
    returned — consistent with the contract that 0.0 IS the max in that case.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``list[Problem]`` of all records at the global maximum weight.
        Empty list when *problems* is empty.

    Pure (no I/O, no SurrealDB).  Item 500.
    """
    if not problems:
        return []
    record_weights = [weights.get(p.severity, 0.0) for p in problems]
    max_weight = max(record_weights)
    return [p for p, w in zip(problems, record_weights) if w == max_weight]


def classes_by_total_score(
    problems: list[Problem],
    weights: dict[str, float],
) -> list[str]:
    """Return ALL class names sorted descending by total weighted severity score.

    This is the full-ranking complement to :func:`top_n_classes_by_score`: it
    returns every class rather than capping at *n*.  Alphabetical tie-break.
    Empty *problems* returns ``[]``.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``list[str]`` of all class names, highest total score first.
        Alphabetical tie-break.  Empty list when *problems* is empty.

    Pure (no I/O, no SurrealDB).  Item 501.
    """
    scores: dict[str, float] = {}
    for p in problems:
        scores[p.problem_class] = scores.get(p.problem_class, 0.0) + weights.get(p.severity, 0.0)
    return sorted(scores.keys(), key=lambda cls: (-scores[cls], cls))


def fids_by_total_score(
    problems: list[Problem],
    weights: dict[str, float],
) -> list[str]:
    """Return ALL finding IDs sorted descending by total weighted severity score.

    The fid-axis counterpart of :func:`classes_by_total_score`.  A finding_id
    that appears in multiple records across different classes accumulates its
    weighted score.  Alphabetical tie-break.  Empty *problems* returns ``[]``.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``list[str]`` of all finding IDs, highest total score first.
        Alphabetical tie-break.  Empty list when *problems* is empty.

    Pure (no I/O, no SurrealDB).  Item 502.
    """
    scores: dict[str, float] = {}
    for p in problems:
        scores[p.finding_id] = scores.get(p.finding_id, 0.0) + weights.get(p.severity, 0.0)
    return sorted(scores.keys(), key=lambda fid: (-scores[fid], fid))


def weighted_problem_count(
    problems: list[Problem],
    weights: dict[str, float],
) -> float:
    """Return the total weighted severity score across ALL Problem records.

    This is the global scalar cost of the entire scan — the sum of
    ``weights.get(p.severity, 0.0)`` for every record regardless of class or
    finding_id.  Unknown severities contribute ``0.0``.  Empty → ``0.0``.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``float`` total weighted count.  ``0.0`` when *problems* is empty.

    Pure (no I/O, no SurrealDB).  Item 503.
    """
    return float(sum(weights.get(p.severity, 0.0) for p in problems))


def weighted_problem_count_by_class(
    problems: list[Problem],
    weights: dict[str, float],
) -> dict[str, float]:
    """Return the total weighted severity score for EACH class as a flat dict.

    The per-class decomposition of :func:`weighted_problem_count`.  Returns
    ``{class_name: total_weighted_score}`` for every class in *problems*.
    Classes whose records all have unknown severities map to ``0.0`` (not
    omitted).  Empty *problems* returns ``{}``.

    This is the scalar-only alternative to :func:`all_score_summaries`; use
    this when the caller only needs the total per class, not ``mean`` or
    ``max_single``.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``dict[str, float]`` mapping class name → total weighted score.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).  Item 504.
    """
    scores: dict[str, float] = {}
    for p in problems:
        scores[p.problem_class] = scores.get(p.problem_class, 0.0) + weights.get(p.severity, 0.0)
    return scores


def weighted_problem_count_by_fid(
    problems: list[Problem],
    weights: dict[str, float],
) -> dict[str, float]:
    """Return the total weighted severity score for EACH finding_id as a flat dict.

    The fid-axis counterpart of :func:`weighted_problem_count_by_class`.  A
    finding_id that appears in multiple records across different classes
    accumulates its weighted score.  Unknown severities contribute ``0.0``
    and the fid is still included in the result.  Empty *problems* returns
    ``{}``.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``dict[str, float]`` mapping finding_id → total weighted score.
        Empty dict when *problems* is empty.

    Pure (no I/O, no SurrealDB).  Item 505.
    """
    scores: dict[str, float] = {}
    for p in problems:
        scores[p.finding_id] = scores.get(p.finding_id, 0.0) + weights.get(p.severity, 0.0)
    return scores


def score_rank_of_class(
    problems: list[Problem],
    weights: dict[str, float],
    problem_class: str,
) -> int | None:
    """Return the 1-based dense rank of *problem_class* by total weighted score.

    Rank 1 = highest-scoring class.  Tied classes receive the same rank
    (dense rank, not standard/Olympic rank).  Returns ``None`` when
    *problem_class* is absent from *problems* or *problems* is empty.

    Examples:
        scores = {A: 5.0, B: 5.0, C: 1.0} → rank(A)=1, rank(B)=1, rank(C)=2.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        problem_class: The class name to look up.

    Returns:
        ``int`` 1-based dense rank, or ``None`` if class is absent/empty.

    Pure (no I/O, no SurrealDB).  Item 506.
    """
    if not problems:
        return None
    # Compute per-class totals
    class_totals: dict[str, float] = {}
    for p in problems:
        class_totals[p.problem_class] = (
            class_totals.get(p.problem_class, 0.0) + weights.get(p.severity, 0.0)
        )
    if problem_class not in class_totals:
        return None
    target_score = class_totals[problem_class]
    # Dense rank: count how many DISTINCT scores are strictly higher
    distinct_higher = len({s for s in class_totals.values() if s > target_score})
    return distinct_higher + 1


def score_percentile_of_class(
    problems: list[Problem],
    weights: dict[str, float],
    problem_class: str,
) -> float | None:
    """Return the [0.0, 1.0] percentile position of *problem_class* by total score.

    Percentile = (number of OTHER classes with a STRICTLY lower total score)
                 / (total number of classes - 1).

    * Single class → ``0.0`` (not ``None`` — the class exists, the denominator
      is ``max(1, total-1) = 1``, and 0 strictly-lower / 1 = 0.0).
    * Absent class → ``None``.
    * Empty *problems* → ``None``.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        problem_class: The class name to look up.

    Returns:
        ``float`` in [0.0, 1.0], or ``None`` if class is absent/empty.

    Pure (no I/O, no SurrealDB).  Item 507.
    """
    if not problems:
        return None
    class_totals: dict[str, float] = {}
    for p in problems:
        class_totals[p.problem_class] = (
            class_totals.get(p.problem_class, 0.0) + weights.get(p.severity, 0.0)
        )
    if problem_class not in class_totals:
        return None
    target_score = class_totals[problem_class]
    n = len(class_totals)
    if n == 1:
        return 0.0
    strictly_lower = sum(1 for s in class_totals.values() if s < target_score)
    return float(strictly_lower / (n - 1))


def classes_in_score_band(
    problems: list[Problem],
    weights: dict[str, float],
    lo: float,
    hi: float,
) -> frozenset[str]:
    """Return classes whose total weighted score falls within the inclusive band [lo, hi].

    ``lo > hi`` → ``frozenset()`` (empty by contract, no raise).
    Empty *problems* → ``frozenset()``.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        lo: Inclusive lower bound.
        hi: Inclusive upper bound.

    Returns:
        ``frozenset[str]`` of class names with ``lo <= total_score <= hi``.

    Pure (no I/O, no SurrealDB).  Item 508.
    """
    if lo > hi or not problems:
        return frozenset()
    class_totals: dict[str, float] = {}
    for p in problems:
        class_totals[p.problem_class] = (
            class_totals.get(p.problem_class, 0.0) + weights.get(p.severity, 0.0)
        )
    return frozenset(cls for cls, score in class_totals.items() if lo <= score <= hi)


def score_spread(
    problems: list[Problem],
    weights: dict[str, float],
) -> float:
    """Return the spread (max − min) of total class scores.

    Computes the total weighted severity score for each class, then returns
    ``max(totals) - min(totals)``.  Returns ``0.0`` when *problems* is empty
    or when only one distinct class exists.  Returns ``0.0`` when all classes
    have the same total (max == min).

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``float`` non-negative spread.  ``0.0`` for empty or single class.

    Pure (no I/O, no SurrealDB).  Item 509.
    """
    if not problems:
        return 0.0
    class_totals: dict[str, float] = {}
    for p in problems:
        class_totals[p.problem_class] = (
            class_totals.get(p.problem_class, 0.0) + weights.get(p.severity, 0.0)
        )
    totals = list(class_totals.values())
    if len(totals) < 2:
        return 0.0
    return float(max(totals) - min(totals))


def top_class_by_score(
    problems: list[Problem],
    weights: dict[str, float],
) -> str | None:
    """Return the single class name with the highest total weighted severity score.

    Alphabetical tie-break when multiple classes share the top score.
    Returns ``None`` when *problems* is empty.

    This is the ``str | None`` single-return convenience accessor over
    :func:`classes_by_total_score`, safe to use without indexing the list.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``str`` class name with the highest total score, or ``None`` if empty.

    Pure (no I/O, no SurrealDB).  Item 510.
    """
    if not problems:
        return None
    ranked = classes_by_total_score(problems, weights)
    return ranked[0] if ranked else None


def bottom_class_by_score(
    problems: list[Problem],
    weights: dict[str, float],
) -> str | None:
    """Return the single class name with the LOWEST total weighted severity score.

    Alphabetical tie-break when multiple classes share the bottom score.
    Returns ``None`` when *problems* is empty.

    The complement of :func:`top_class_by_score`.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``str`` class name with the lowest total score, or ``None`` if empty.

    Pure (no I/O, no SurrealDB).  Item 512.
    """
    if not problems:
        return None
    class_totals: dict[str, float] = {}
    for p in problems:
        class_totals[p.problem_class] = (
            class_totals.get(p.problem_class, 0.0) + weights.get(p.severity, 0.0)
        )
    min_score = min(class_totals.values())
    # Among classes tied at min_score, return alphabetically first
    return min(cls for cls, score in class_totals.items() if score == min_score)


def classes_tied_at_score(
    problems: list[Problem],
    weights: dict[str, float],
    target_score: float,
) -> frozenset[str]:
    """Return frozenset of class names whose total weighted score equals target_score exactly.

    Float equality is used (no epsilon).  Empty input or no match -> frozenset().

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        target_score: The exact total score to match against.

    Returns:
        ``frozenset[str]`` of class names whose accumulated score equals
        ``target_score``.  Empty frozenset when no class matches or input is empty.

    Pure (no I/O, no SurrealDB).  Item 513.
    """
    if not problems:
        return frozenset()
    class_totals: dict[str, float] = {}
    for p in problems:
        class_totals[p.problem_class] = (
            class_totals.get(p.problem_class, 0.0) + weights.get(p.severity, 0.0)
        )
    return frozenset(cls for cls, score in class_totals.items() if score == target_score)


def top_fid_by_score(
    problems: list[Problem],
    weights: dict[str, float],
) -> str | None:
    """Return the single finding_id with the highest total weighted severity score.

    Alphabetical tie-break (ascending) among fids that share the top score.
    Returns ``None`` for empty input.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``str`` finding_id with the highest total score, or ``None`` if empty.

    Pure (no I/O, no SurrealDB).  Item 517.
    """
    if not problems:
        return None
    ranked = fids_by_total_score(problems, weights)
    return ranked[0] if ranked else None


def bottom_fid_by_score(
    problems: list[Problem],
    weights: dict[str, float],
) -> str | None:
    """Return the single finding_id with the lowest total weighted severity score.

    Alphabetical tie-break (ascending) among fids that share the bottom score.
    Returns ``None`` for empty input.

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.

    Returns:
        ``str`` finding_id with the lowest total score, or ``None`` if empty.

    Pure (no I/O, no SurrealDB).  Item 518.
    """
    if not problems:
        return None
    fid_totals: dict[str, float] = {}
    for p in problems:
        fid_totals[p.finding_id] = (
            fid_totals.get(p.finding_id, 0.0) + weights.get(p.severity, 0.0)
        )
    min_score = min(fid_totals.values())
    # Among fids tied at min_score, return alphabetically first
    return min(fid for fid, score in fid_totals.items() if score == min_score)


def fids_tied_at_score(
    problems: list[Problem],
    weights: dict[str, float],
    target_score: float,
) -> frozenset[str]:
    """Return frozenset of finding_ids whose total weighted score equals target_score exactly.

    Float equality is used (no epsilon).  Empty input or no match -> frozenset().

    Args:
        problems: List of :class:`Problem` instances.
        weights: Mapping of severity label to numeric score.
        target_score: The exact total score to match against.

    Returns:
        ``frozenset[str]`` of finding_ids whose accumulated score equals
        ``target_score``.  Empty frozenset when no fid matches or input is empty.

    Pure (no I/O, no SurrealDB).  Item 519.
    """
    if not problems:
        return frozenset()
    fid_totals: dict[str, float] = {}
    for p in problems:
        fid_totals[p.finding_id] = (
            fid_totals.get(p.finding_id, 0.0) + weights.get(p.severity, 0.0)
        )
    return frozenset(fid for fid, score in fid_totals.items() if score == target_score)
