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


def least_frequent_class(problems: list[Problem]) -> str | None:
    """Return the ``problem_class`` with the lowest finding count — item 197.

    Symmetric complement of :func:`most_frequent_class` for tail-class
    analysis.  On ties the class whose LAST appearance is latest in
    *problems* wins (most-recently-seen rarest class)::

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
        last_seen[p.problem_class] = i
    min_count = min(counts.values())
    # Among tied-minimum classes, return the one whose last appearance is latest.
    candidates = [cls for cls, cnt in counts.items() if cnt == min_count]
    return max(candidates, key=lambda cls: last_seen[cls])
