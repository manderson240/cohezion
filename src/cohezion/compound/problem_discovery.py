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
