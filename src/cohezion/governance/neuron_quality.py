"""Neuron-store deposit-quality audit (item 52, 2026-06-06) — report-only.

Prompted by arXiv 2605.31075 (TaskMem) — its memory-quality REWARD TAXONOMY
(non-redundancy / accuracy / format), NOT its RL-on-30B-VL method (off-stack/off-modality). Measures
those three dimensions over DEPOSITED neurons (items 15/16/24): the FleetHealthSpecialist (item 36)
COUNTS deposits but never assesses QUALITY — this closes that gap. Read-only complement to item-51's
write-time dedup; operates on an injected neuron list, so it never reads SurrealDB under pytest.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


# A well-formed neuron must carry these (country+name for addressing, tags for recall — item 29
# recall_neurons filters by tags, so an untagged neuron is unrecallable = format-invalid).
_REQUIRED_FIELDS = ("country", "name", "tags")

_NEURON_COUNTRIES = ("inference", "skill", "cerebellum")
# A neuron's tags mix the task_class with structural labels and the lane (schemas differ per country:
# inference=[lane,"rewarded",task_class], skill=["skill",skill_name], cerebellum=[country,"procedural",
# task_class,lane]). The task_class is read from the tags by EXCLUDING this structural/lane denylist.
# Documented limitation: a task_class that collides with a structural/lane token would be excluded
# (rare; a coverage list is a smell, not a verdict).
_STRUCTURAL_TAGS = frozenset(
    {
        "inference",
        "skill",
        "cerebellum",  # country labels
        "procedural",
        "rewarded",
        "distilled",  # deposit structural labels
        "npu",
        "igpu",
        "cpu",
        "igpu_unified",
        "igpu_rocwmma",
        "cloud",
        "cli",  # lane vocabulary
    }
)


def _task_classes_of(neuron: dict) -> set[str]:
    """The task_class tag(s) of a neuron = its tags minus the structural/lane denylist."""
    return {str(t) for t in (neuron.get("tags") or []) if str(t) not in _STRUCTURAL_TAGS}


def memory_coverage(store: Iterable[object]) -> dict[str, set[str]]:
    """Per neuron country, the SET of task classes the fleet has procedural memory for (item 55).

    "What does the fleet remember?" — the observability complement to item-37's per-task recall.
    Reads the task_class from each neuron's TAGS (not its name) via ``_task_classes_of``. Always
    returns exactly the three country keys; a country with no neurons maps to an empty set. Pure —
    read-only over the injected ``store`` (no SurrealDB), non-dict entries ignored.
    """
    coverage: dict[str, set[str]] = {c: set() for c in _NEURON_COUNTRIES}
    for neuron in store:
        if not isinstance(neuron, dict):
            continue
        country = str(neuron.get("country", ""))
        if country in coverage:
            coverage[country] |= _task_classes_of(neuron)
    return coverage


@dataclass(frozen=True)
class DepositQualityReport:
    """TaskMem-style quality over deposited neurons. All three views are report-only."""

    redundant: dict[str, int]  # name -> count, for names deposited more than once
    low_evidence: list[str]  # neuron names whose reward is strictly below the evidence floor
    format_invalid: list[str]  # neuron names missing a required field (or "<unnamed>")


def deposit_quality_report(
    neurons: Iterable[object],
    *,
    evidence_floor: float = 0.5,
) -> DepositQualityReport:
    """Audit a neuron list on TaskMem's 3 dimensions (item 52). Pure — no SurrealDB, no writes.

    - **non-redundancy**: ``{name: count}`` for names deposited >1 time (the duplicates item-51's
      ``deposit_cerebellum_if_novel`` prevents at write time — this finds any already present).
    - **evidence**: neuron names whose ``reward`` is strictly ``< evidence_floor`` (weak evidence).
    - **format**: neuron names missing any of country/name/tags (an untagged neuron is unrecallable).

    Non-dict entries are ignored (fail-soft). A clean store yields all-empty views.
    """
    dicts = [n for n in neurons if isinstance(n, dict)]

    counts = Counter(str(n["name"]) for n in dicts if n.get("name"))
    redundant = {name: c for name, c in counts.items() if c >= 2}

    low_evidence = sorted(
        str(n.get("name", "<unnamed>"))
        for n in dicts
        if float(n.get("reward", 1.0)) < evidence_floor
    )

    format_invalid = sorted(
        str(n.get("name", "<unnamed>"))
        for n in dicts
        if any(not n.get(field) for field in _REQUIRED_FIELDS)
    )

    return DepositQualityReport(
        redundant=redundant,
        low_evidence=low_evidence,
        format_invalid=format_invalid,
    )


def memory_gaps(
    store: Iterable[object], *, task_classes: Iterable[str] | None = None
) -> dict[str, set[str]]:
    """Per neuron country, the task classes the fleet handles but has NO procedural memory for.

    The actionable complement to item-55 :func:`memory_coverage`: ``wanted - covered`` per country,
    where ``wanted`` is the task-class set of interest (default: the FleetRegistry ``Task`` names).
    An empty store → every country has ALL ``task_classes`` as gaps (NOT an empty dict — the three
    country keys are always present). Report-only, pure — injected ``task_classes`` means no registry
    read under pytest.
    """
    if task_classes is None:
        from cohezion.inference.registry import Task

        wanted = {t.value for t in Task}
    else:
        wanted = {str(t) for t in task_classes}
    coverage = memory_coverage(store)
    return {country: wanted - covered for country, covered in coverage.items()}


def memory_gap_priority(
    store: Iterable[object],
    routing_records: Iterable[Mapping[str, object]],
    *,
    task_classes: Iterable[str] | None = None,
) -> list[tuple[str, int]]:
    """Rank cerebellum (procedural-memory) gaps by routing frequency — fill the busiest first (item 129).

    Item-75 :func:`memory_gaps` says WHERE memory is missing; this says WHICH gap to grow FIRST. Of
    the *cerebellum* gaps, rank the gap task_classes by how OFTEN the fleet routes them (count in
    ``routing_records``, each ``{"task_class", "lane", ...}``) — the most-routed UNREMEMBERED task is
    the highest-value memory to deposit. A COVERED task (not a gap) is EXCLUDED even if routed often;
    a gap never routed has no traffic and is EXCLUDED. Returns ``[(task_class, route_count)]``
    descending (ties broken by name). Report-only, pure — the deposit is the gated action.
    """
    gaps = memory_gaps(store, task_classes=task_classes).get("cerebellum", set())
    counts: dict[str, int] = {}
    for rec in routing_records:
        if not isinstance(rec, Mapping):
            continue
        task_class = rec.get("task_class")
        if task_class is not None and str(task_class) in gaps:
            counts[str(task_class)] = counts.get(str(task_class), 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


@dataclass(frozen=True)
class DepositQualityDelta:
    """Signed change in neuron-store quality across two snapshots (item 74). Negative = improving."""

    redundancy_delta: int  # change in # of duplicate-named neurons
    low_evidence_delta: int  # change in # of below-floor-reward neurons
    format_invalid_delta: int  # change in # of malformed neurons


def deposit_quality_delta(
    before: DepositQualityReport, after: DepositQualityReport
) -> DepositQualityDelta:
    """Quality-trend monitor: is the growing neuron store getting BETTER or WORSE? (item 74).

    Returns the SIGNED change in each problem count (``len(after.*) - len(before.*)``) — mirroring
    the harness-blessed :meth:`DegradationDetector.diff_snapshots` (CB11) pure-delta pattern.
    Negative = fewer problems = improving; positive = degrading. NOT clamped (an honest -1 for a
    redundancy drop, not 0). Pure — no I/O, operates on two injected reports.
    """
    return DepositQualityDelta(
        redundancy_delta=len(after.redundant) - len(before.redundant),
        low_evidence_delta=len(after.low_evidence) - len(before.low_evidence),
        format_invalid_delta=len(after.format_invalid) - len(before.format_invalid),
    )


@dataclass(frozen=True)
class ProblemChurn:
    """Name-level churn for ONE problem class between two snapshots. Report-only."""

    newly: list[
        str
    ]  # names in `after` but NOT `before` (a neuron that just entered the problem set)
    resolved: list[str]  # names in `before` but NOT `after` (a fix that landed)


@dataclass(frozen=True)
class DepositQualityChurn:
    """WHICH neurons entered/left each problem set (item 128) — the name-level dual of item-74."""

    redundant: ProblemChurn
    low_evidence: ProblemChurn
    format_invalid: ProblemChurn


def _problem_churn(before_names: Iterable[str], after_names: Iterable[str]) -> ProblemChurn:
    before_set, after_set = set(before_names), set(after_names)
    return ProblemChurn(
        newly=sorted(after_set - before_set), resolved=sorted(before_set - after_set)
    )


def deposit_quality_churn(
    before: DepositQualityReport, after: DepositQualityReport
) -> DepositQualityChurn:
    """WHICH neuron names entered/left each problem set across two snapshots (item 128). Report-only.

    The name-level dual of item-74 ``deposit_quality_delta`` (which gives only the COUNT change):
    per problem class (redundant / low_evidence / format_invalid), ``newly`` = names in ``after`` not
    ``before`` (a neuron that just became problematic — fix THIS), ``resolved`` = names in ``before``
    not ``after`` (a fix that landed). A name in BOTH snapshots is in NEITHER list (compared by NAME,
    not by count — a ``redundant`` neuron whose count merely changed is unchanged churn). Identical
    snapshots → all-empty. Pure (two injected reports, no I/O). ``redundant`` is a dict; its churn is
    over its KEYS (the neuron names).
    """
    return DepositQualityChurn(
        redundant=_problem_churn(before.redundant, after.redundant),
        low_evidence=_problem_churn(before.low_evidence, after.low_evidence),
        format_invalid=_problem_churn(before.format_invalid, after.format_invalid),
    )


# The memory LAYERS for the distillation ratio: raw = the undistilled journey-point firehose;
# distilled = the reusable-memory layers it should be compounded into.
_RAW_LAYER = "journey_point"
_DISTILLED_LAYERS = ("neuron", "learnings", "compound_learnings", "mem0")


@dataclass(frozen=True)
class MemoryUtilization:
    """Per-layer fill status + the raw->distilled distillation ratio (item 106). Report-only."""

    layer_status: dict[str, str]  # layer -> "dormant" | "sparse" | "healthy"
    raw_count: int  # journey_point — the undistilled firehose
    distilled_count: int  # neuron + learnings + compound_learnings + mem0 (present layers)
    distillation_ratio: float | None  # raw / distilled; None when distilled == 0
    under_distilled: bool  # raw dwarfs distilled — the distillation bottleneck


def memory_utilization(
    layer_counts: Mapping[str, int],
    *,
    sparse_floor: int = 100,
    under_distilled_ratio: float = 100.0,
) -> MemoryUtilization:
    """Are we LEVERAGING our memory? Per-layer fill + the raw:distilled ratio (item 106). Report-only.

    Over injected per-layer record counts (e.g. ``{journey_point, neuron, learnings,
    compound_learnings, mem0, vault_notes}``), classify each layer as ``dormant`` (count == 0),
    ``sparse`` (``0 < count < sparse_floor``), or ``healthy`` (``>= sparse_floor``), and compute the
    DISTILLATION RATIO = raw / distilled where raw = ``journey_point`` and distilled = the sum of the
    present ``{neuron, learnings, compound_learnings, mem0}`` layers. A huge ratio means the firehose
    of raw journey points is barely being distilled into reusable memory (the 2026-06-06 ~15000:1
    bottleneck). ``under_distilled`` is True when raw > 0 AND either nothing is distilled (ratio
    undefined → maximal bottleneck) OR ratio > ``under_distilled_ratio``. Empty input → all-empty.
    Pure (injected counts; no SurrealDB read under pytest), composes item-52/55 neuron-quality.
    """
    layer_status = {
        layer: ("dormant" if count == 0 else "sparse" if count < sparse_floor else "healthy")
        for layer, count in layer_counts.items()
    }
    raw_count = int(layer_counts.get(_RAW_LAYER, 0))
    distilled_count = sum(int(layer_counts.get(layer, 0)) for layer in _DISTILLED_LAYERS)
    if distilled_count == 0:
        distillation_ratio: float | None = None
        under_distilled = raw_count > 0  # raw exists but nothing distilled → maximal bottleneck
    else:
        distillation_ratio = raw_count / distilled_count
        under_distilled = distillation_ratio > under_distilled_ratio
    return MemoryUtilization(
        layer_status=layer_status,
        raw_count=raw_count,
        distilled_count=distilled_count,
        distillation_ratio=distillation_ratio,
        under_distilled=under_distilled,
    )
