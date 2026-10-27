"""Dream-RSI discovery-replay self-improvement evaluator (arXiv:2609.14858).

Implements, as deterministic zero-cost analysis over Cohezion's own decision
history, the replay-simulator meta-exploration framework of:

    Tong Zheng, Xidong Wu, Zheng Zhang, Zhankui He, Chaoyi Zhang,
    Benjamin Coleman, Ruoqiao Wei, Di Bai, Haolin Liu, Rui Liu, Xue Wang,
    Yue Zhuan, Wang-Cheng Kang, Renkai Xiang, Heng Huang, Xinwu Cheng,
    Yunsong Guo.
    "Dream-RSI: Recursive Self-Improvement through Evolving Worlds."
    arXiv:2609.14858 (v1, 2026-09-14). https://dream-rsi.com/

Paper mechanism -> this module:

* **Lightweight orchestration layer.** The paper makes exploration explicit by
  separating an *exploration policy* (code that chooses branching, parallel
  batches, and stopping) from a *fixed coding agent + evaluator*. Here the
  policy is any callable ``DiscoveryRecord -> action-or-None`` (e.g. an
  NPU-first vs iGPU-first routing rule); no agent, model, or evaluator is
  touched. Only the policy code changes — exactly the paper's invariant.
* **Discovery trees.** Paper nodes record an attempt's inherited workspace,
  generated artifact, evaluation diagnostics, and score ``s_v`` under a fixed
  task-scoring protocol (larger = better). Our flattened equivalent is
  :class:`DiscoveryRecord`: one past decision point with its policy context
  (model / tier / EVI / file-scope strategy), realized action, outcome metrics,
  and cost, ingested from ``delegation_log`` / ``experiment_run`` /
  ``learning`` / vault retros.
* **Replay simulator + dreaming.** In the paper, replay walks a candidate
  policy through a *recorded* discovery tree, deterministically revealing
  stored outcomes instead of re-executing anything ("no outcomes beyond the
  tree are generated"). :func:`replay_dream` is the flattened form: at each
  historical decision point we ask what the candidate policy WOULD have chosen,
  score agreement against the realized choice, and estimate the counterfactual
  outcome purely from *other recorded branches* that actually took that action
  (mean realized outcome of the same-context pool). Unrecorded branches are
  unscoreable — we return ``None`` rather than inventing an outcome, the
  fail-closed analogue of the paper's ``Child(v) = ∅`` rule.
* **Replay objective (paper Eq. 1).** ``V = max_v s_v − β1·N + β2·N/max{1,k}``
  balances discovery quality, execution cost, and a parallelism bonus.
  :func:`replay_objective` implements it directly over a record set.
* **Policy improvement + loop closure.** The paper evaluates M candidate
  versions on the fixed history, selects ``m* = argmax V^m`` (candidate set
  includes the incumbent, so the winner is never worse on replay), then
  redeploys online to grow the simulator pool. :func:`refine_policy` is that
  selection step: rank candidates by :class:`PolicyScore` and return the winner
  with a rationale. The 'dream' runs between campaigns at zero inference cost
  instead of re-running expensive online trials.

Wire-in (deliberately NOT wired here): the perpetual loop and retrospective
extraction (``cohezion.agi.recursive_learning``) are the consumers — after each
retrospective lands in SurrealDB/vault, the loop calls ``refine_policy`` over
the refreshed history and adopts the winning routing/exploration policy for
the next campaign. This module is a self-contained pure-stdlib library like
``kst_eval.py``: no cohezion imports, no model loads, all I/O offline-mockable.
The SurrealDB reader mirrors the auth pattern of
``cohezion.data_mesh.kanban_bridge`` (env-var credentials, never hardcoded).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cohezion.storage.surreal_http import checked_statements


__all__ = [
    "DiscoveryRecord",
    "DiscoveryTree",
    "PolicyRefinement",
    "PolicyScore",
    "candidate_from_context",
    "load_from_surrealdb",
    "load_from_vault_retros",
    "refine_policy",
    "replay_dream",
    "replay_objective",
]

logger = logging.getLogger(__name__)

#: Policy callable: given a historical decision point, return the action the
#: candidate policy WOULD take, or ``None`` when the policy does not apply to
#: that context (excluded from scoring, counted against coverage). Raising is
#: also treated as not-applicable — replay never propagates policy bugs.
Policy = Callable[["DiscoveryRecord"], "str | None"]

#: Context keys defining the "realized search space" pool for counterfactual
#: lookups: records sharing these context values are treated as branches of the
#: same discovery tree (the paper's replay world).
DEFAULT_CONTEXT_KEYS: tuple[str, ...] = ("model", "tier", "task")

#: Outcome-metric keys consulted (in order) when distilling a scalar score.
OUTCOME_KEYS: tuple[str, ...] = ("score", "reward", "quality", "value", "success_rate")

_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_NS = "cohezion"
_SURREAL_DB = "main"
_VAULT_RETROS = Path.home() / "vaults" / "cohezion-vault" / "retros"
_RE_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")


# --------------------------------------------------------------------------
# Discovery record — one historical decision point (paper's tree node, flat)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DiscoveryRecord:
    """A past decision point from Cohezion's own history.

    Flattened counterpart of a Dream-RSI discovery-tree node: the paper's node
    records the attempt's workspace, artifact, diagnostics, and score ``s_v``;
    here we keep the decision-level essentials so any logged choice can be
    replayed counterfactually.

    Attributes:
        id: Stable record id (table row id or vault note stem).
        timestamp: ISO-8601 instant of the decision (adapters normalize epochs).
        policy_context: Policy state at decision time — e.g. ``model`` chosen,
            ``tier``, ``evi`` threshold, ``file_scope`` strategy, ``task``.
        action: The action actually taken (e.g. ``"npu_first"``,
            ``"igpu_first"``, ``"cloud_escalate"``). ``None`` = unrecorded.
        outcome_metrics: Realized outcomes; ``score`` (or another
            :data:`OUTCOME_KEYS` entry) is the replay reward, larger = better.
        cost: Realized execution cost of the decision (agent calls, seconds,
            or dollars — one consistent unit per history).
        source_table: Provenance (``delegation_log`` | ``experiment_run`` |
            ``learning`` | ``vault_retro`` | custom).
        succeeded: Optional boolean verdict when the source records one.
    """

    id: str
    timestamp: str
    policy_context: Mapping[str, Any] = field(default_factory=dict)
    action: str | None = None
    outcome_metrics: Mapping[str, Any] = field(default_factory=dict)
    cost: float | None = None
    source_table: str = "manual"
    succeeded: bool | None = None


@dataclass(frozen=True, slots=True)
class DiscoveryTree:
    """An ordered, deduplicated set of decision points — one replay world.

    The paper's replay simulator is the recorded discovery tree; Cohezion's
    accumulated history is a flat set of decision points, which this class
    orders deterministically (timestamp, then id) so every replay is
    reproducible.
    """

    records: tuple[DiscoveryRecord, ...]
    name: str = "default"

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self) -> tuple[DiscoveryRecord, ...]:  # type: ignore[override]
        return self.records

    @classmethod
    def from_records(
        cls,
        records: Iterable[DiscoveryRecord],
        name: str = "default",
    ) -> DiscoveryTree:
        """Build a tree, deduplicating by id and ordering deterministically."""
        seen: dict[str, DiscoveryRecord] = {}
        for rec in records:
            seen.setdefault(rec.id, rec)
        ordered = tuple(sorted(seen.values(), key=lambda r: (r.timestamp, r.id)))
        return cls(records=ordered, name=name)


@dataclass(frozen=True, slots=True)
class PolicyScore:
    """Off-policy ('dream') evaluation of one candidate policy over a history.

    Attributes:
        policy_name: Label of the evaluated candidate.
        n_decision_points: Total historical decision points considered.
        n_applicable: Points where the candidate returned an action.
        n_scored: Points where a counterfactual gain was actually computable
            (realized outcome and a recorded counterfactual branch both exist).
        agreement_rate: Share of applicable points (with a known realized
            action) where the candidate would have chosen the same action.
            ``None`` when no agreement is measurable.
        counterfactual_gain_estimate: Mean over scored points of
            ``(counterfactual outcome) − (realized outcome)``; agreed points
            contribute exactly 0.0 (the incumbent baseline). ``None`` when no
            point is scoreable — never a fabricated number.
        coverage: ``n_applicable / n_decision_points`` (0.0 for empty history):
            the share of decision points where the policy is even applicable.
        cost_delta: Mean over scored points of counterfactual-minus-realized
            cost; negative = the candidate would have been cheaper. ``None``
            when no cost comparison is computable.
    """

    policy_name: str
    n_decision_points: int
    n_applicable: int
    n_scored: int
    agreement_rate: float | None
    counterfactual_gain_estimate: float | None
    coverage: float
    cost_delta: float | None

    def ranking_key(self) -> tuple[float, float, float, str]:
        """Deterministic descending-sort key: gain, agreement, cheaper cost, name."""
        gain = self.counterfactual_gain_estimate
        agreement = self.agreement_rate
        cost = self.cost_delta
        return (
            -(gain if gain is not None else float("-inf")),
            -(agreement if agreement is not None else 0.0),
            cost if cost is not None else 0.0,
            self.policy_name,
        )


@dataclass(frozen=True, slots=True)
class PolicyRefinement:
    """Winner of the offline 'dream' selection step (paper §3, policy selection)."""

    winner_name: str
    winner_policy: Policy
    scores: tuple[PolicyScore, ...]  # best-first by PolicyScore.ranking_key
    rationale: str
    history_size: int


# --------------------------------------------------------------------------
# Outcome / cost distillation (fixed task-scoring protocol, paper §3)
# --------------------------------------------------------------------------


def _outcome_value(record: DiscoveryRecord) -> float | None:
    """Distill a scalar reward from ``outcome_metrics`` (larger = better).

    Priority: the first :data:`OUTCOME_KEYS` hit, then the ``succeeded`` flag
    mapped to 1.0/0.0. Records with neither carry no replayable outcome.
    """
    metrics = record.outcome_metrics or {}
    for key in OUTCOME_KEYS:
        value = metrics.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    if record.succeeded is not None:
        return 1.0 if record.succeeded else 0.0
    return None


def _context_signature(
    record: DiscoveryRecord,
    context_keys: Sequence[str],
) -> tuple[Any, ...]:
    """Context fingerprint grouping records into one realized search space."""
    ctx = record.policy_context or {}
    return tuple(ctx.get(k) for k in context_keys)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


# --------------------------------------------------------------------------
# Replay (dreaming): off-policy counterfactual evaluation — paper §3 offline
# --------------------------------------------------------------------------


def replay_dream(
    records: Sequence[DiscoveryRecord] | DiscoveryTree,
    candidate_policy: Policy,
    *,
    policy_name: str = "candidate",
    context_keys: Sequence[str] = DEFAULT_CONTEXT_KEYS,
) -> PolicyScore:
    """Evaluate a candidate exploration policy against recorded history.

    For each historical decision point the candidate returns its hypothetical
    action (or ``None``/raises = not applicable). When it disagrees with the
    realized action, the counterfactual outcome is read from the recorded
    branches that actually took the candidate's action within the same context
    signature (same ``context_keys`` values) — the paper's deterministic
    reveal of stored children, never a re-execution. Missing evidence yields
    ``None`` aggregates, not guesses; policy exceptions are contained.

    Returns a :class:`PolicyScore`; for an empty history every estimate is
    ``None`` with ``coverage == 0.0``.
    """
    tree = records if isinstance(records, DiscoveryTree) else DiscoveryTree.from_records(records)
    points = tree.records

    # Counterfactual pools: context signature -> action -> (outcomes, costs)
    pools: dict[tuple[Any, ...], dict[str, tuple[list[float], list[float]]]] = {}
    for rec in points:
        sig = _context_signature(rec, context_keys)
        action = rec.action
        if action is None:
            continue
        value = _outcome_value(rec)
        cost = rec.cost
        if value is None and cost is None:
            continue
        per_action = pools.setdefault(sig, {})
        outcomes, costs = per_action.setdefault(action, ([], []))
        if value is not None:
            outcomes.append(value)
        if cost is not None:
            costs.append(cost)

    n_applicable = 0
    n_agreeable = 0
    n_agree = 0
    gains: list[float] = []
    cost_deltas: list[float] = []

    for point in points:
        try:
            cf_action = candidate_policy(point)
        except Exception as exc:
            logger.debug("dream_rsi: policy %s failed on %s: %s", policy_name, point.id, exc)
            continue
        if not isinstance(cf_action, str) or not cf_action:
            continue
        n_applicable += 1

        sig = _context_signature(point, context_keys)
        pool = pools.get(sig, {}).get(cf_action, ([], []))
        cf_outcome = _mean(pool[0]) if pool[0] else None
        cf_cost = _mean(pool[1]) if pool[1] else None
        realized_outcome = _outcome_value(point)

        if point.action is not None:
            n_agreeable += 1
            if cf_action == point.action:
                n_agree += 1
                # Identical choice => the counterfactual IS the realized path.
                if realized_outcome is not None:
                    gains.append(0.0)
                if point.cost is not None:
                    cost_deltas.append(0.0)
                continue

        # Disagreed (or realized action unrecorded): score against recorded
        # branches of the counterfactual action; unrecorded branches are
        # unscoreable (paper's Child(v) = ∅ fail-closed rule).
        if cf_outcome is not None and realized_outcome is not None:
            gains.append(cf_outcome - realized_outcome)
        if cf_cost is not None and point.cost is not None:
            cost_deltas.append(cf_cost - point.cost)

    total = len(points)
    return PolicyScore(
        policy_name=policy_name,
        n_decision_points=total,
        n_applicable=n_applicable,
        n_scored=len(gains),
        agreement_rate=(n_agree / n_agreeable) if n_agreeable else None,
        counterfactual_gain_estimate=_mean(gains) if gains else None,
        coverage=(n_applicable / total) if total else 0.0,
        cost_delta=_mean(cost_deltas) if cost_deltas else None,
    )


def replay_objective(
    records: Sequence[DiscoveryRecord] | DiscoveryTree,
    *,
    beta1: float = 0.0,
    beta2: float = 0.0,
    n_rounds: int | None = None,
) -> float | None:
    """Paper Eq. 1 replay score over a record set: quality − β1·N + β2·N/max{1,k}.

    ``N`` counts scored decision points (generation–evaluation attempts the
    trajectory represents); ``k`` is the caller-supplied decision-round count.
    With ``k=None`` the trajectory is assumed fully sequential (``k = N``),
    the conservative case where the parallelism bonus degrades to β2.
    Returns ``None`` when no record carries a replayable outcome.
    """
    tree = records if isinstance(records, DiscoveryTree) else DiscoveryTree.from_records(records)
    outcomes = [v for rec in tree.records if (v := _outcome_value(rec)) is not None]
    if not outcomes:
        return None
    n = len(outcomes)
    k = n_rounds if n_rounds is not None else n
    quality = max(outcomes)
    return quality - beta1 * n + beta2 * n / max(1, k)


# --------------------------------------------------------------------------
# Policy improvement: offline selection (paper §3) — the 'dream' step
# --------------------------------------------------------------------------


def refine_policy(
    history: Sequence[DiscoveryRecord] | DiscoveryTree,
    candidates: Mapping[str, Policy],
    *,
    context_keys: Sequence[str] = DEFAULT_CONTEXT_KEYS,
) -> PolicyRefinement | None:
    """Rank candidate policies by dream score; return the winner + rationale.

    Mirrors the paper's offline phase: every candidate is evaluated on the same
    fixed history, the incumbent-class policy (perfect agreement) is the
    natural baseline, and selection is deterministic — highest counterfactual
    gain, then agreement, then cheaper cost, then name. Returns ``None``
    (never raises) when the history is empty, no candidates are given, or no
    candidate is applicable anywhere.
    """
    tree = history if isinstance(history, DiscoveryTree) else DiscoveryTree.from_records(history)
    if not tree.records or not candidates:
        return None

    scored = [
        replay_dream(tree, policy, policy_name=name, context_keys=context_keys)
        for name, policy in candidates.items()
    ]
    scored = [s for s in scored if s.coverage > 0.0]
    if not scored:
        return None
    scored.sort(key=PolicyScore.ranking_key)
    best = scored[0]
    runner_up = scored[1] if len(scored) > 1 else None

    parts = [
        f"Selected {best.policy_name!r}: counterfactual gain "
        f"{best.counterfactual_gain_estimate:+.4f}"
        if best.counterfactual_gain_estimate is not None
        else f"Selected {best.policy_name!r}: counterfactual gain unavailable "
        f"(no scoreable decision points)",
    ]
    agreement = best.agreement_rate
    parts.append(
        f"agreement {agreement:.2%}" if agreement is not None else "agreement unmeasurable",
    )
    parts.append(f"coverage {best.coverage:.0%} of {best.n_decision_points} decision points")
    if best.cost_delta is not None:
        parts.append(f"cost delta {best.cost_delta:+.4f}")
    if runner_up is not None:
        runner_gain = runner_up.counterfactual_gain_estimate
        parts.append(
            f"runner-up {runner_up.policy_name!r} (gain {runner_gain:+.4f})"
            if runner_gain is not None
            else f"runner-up {runner_up.policy_name!r} (gain unavailable)",
        )
    parts.append("off-policy replay over accumulated history; no online trial was run")

    return PolicyRefinement(
        winner_name=best.policy_name,
        winner_policy=candidates[best.policy_name],
        scores=tuple(scored),
        rationale="; ".join(parts),
        history_size=len(tree.records),
    )


# --------------------------------------------------------------------------
# Candidate-policy builders (pluggable routing rules)
# --------------------------------------------------------------------------


def candidate_from_context(
    match: Mapping[str, Any],
    action: str,
    otherwise: str | None = None,
) -> Policy:
    """Build a policy that picks ``action`` when context matches ``match``.

    Example: ``candidate_from_context({"tier": "npu"}, "npu_first",
    otherwise="igpu_first")`` — an NPU-first routing rule. Context keys absent
    from the record count as non-matching (fail-closed applicability); pass
    ``otherwise=None`` to make non-matching contexts not-applicable.
    """
    required = dict(match)

    def policy(record: DiscoveryRecord) -> str | None:
        ctx = record.policy_context or {}
        for key, expected in required.items():
            if ctx.get(key) != expected:
                return otherwise
        return action

    return policy


# --------------------------------------------------------------------------
# Loaders — SurrealDB (kanban_bridge auth pattern) and vault retros
# --------------------------------------------------------------------------


def _surreal_basic_auth() -> str:
    """Raw b64 credential for Basic auth (env override, kanban_bridge pattern)."""
    user = os.environ.get("SURREAL_USER", "root")
    password = os.environ.get("SURREAL_PASS", "root")
    return base64.b64encode(f"{user}:{password}".encode()).decode()


def _surreal_sql_post(url: str, ns: str, db: str, surql: str, timeout_s: float) -> bytes:
    """POST one read-only SurQL statement; returns the raw response body."""
    req = urllib.request.Request(  # noqa: S310
        url,
        data=surql.encode(),
        headers={
            "surreal-ns": ns,
            "surreal-db": db,
            "Content-Type": "text/plain",
            "Authorization": f"Basic {_surreal_basic_auth()}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
        return resp.read()


def _iso_timestamp(row: Mapping[str, Any]) -> str:
    """Normalize a row's timestamp field (epoch float, ISO str, or date str)."""
    for key in ("timestamp", "created_at", "date", "time"):
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(float(value), tz=UTC).isoformat()
        if isinstance(value, str) and value:
            return value
    return ""


_SCALAR_CONTEXT_EXCLUDE = {
    "id",
    "timestamp",
    "created_at",
    "date",
    "time",
    "action",
    "cost",
    "score",
    "reward",
    "quality",
    "value",
    "success",
    "success_rate",
    "metrics",
    "outcome",
    "succeeded",
}


def _record_from_row(table: str, row: Mapping[str, Any]) -> DiscoveryRecord | None:
    """Adapt one SurrealDB row (any of the history tables) to a DiscoveryRecord."""
    rec_id = row.get("id")
    if not rec_id:
        return None
    action = row.get("action")
    if not isinstance(action, str) or not action:
        for key in ("verdict", "status", "pattern", "name", "kind"):
            value = row.get(key)
            if isinstance(value, str) and value:
                action = value
                break
    cost = row.get("cost")
    cost_f = float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None
    metrics_raw = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    outcome_metrics: dict[str, Any] = dict(metrics_raw)
    for key, value in row.items():
        if key in _SCALAR_CONTEXT_EXCLUDE:
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            outcome_metrics.setdefault(key, value)
    succeeded = row.get("succeeded")
    if not isinstance(succeeded, bool):
        status = row.get("status")
        if isinstance(status, str):
            succeeded = status.lower() in {"completed", "merged", "passed", "success"}
        else:
            succeeded = None
    context: dict[str, Any] = {}
    for key, value in row.items():
        if key in _SCALAR_CONTEXT_EXCLUDE or isinstance(value, (list, dict, Mapping)):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            context[key] = value
    return DiscoveryRecord(
        id=str(rec_id),
        timestamp=_iso_timestamp(row),
        policy_context=context,
        action=action,
        outcome_metrics=outcome_metrics,
        cost=cost_f,
        source_table=table,
        succeeded=succeeded,
    )


def load_from_surrealdb(
    *,
    url: str = _SURREAL_URL,
    ns: str = _SURREAL_NS,
    db: str = _SURREAL_DB,
    tables: Sequence[str] = ("delegation_log", "experiment_run", "learning"),
    limit_per_table: int = 500,
    timeout_s: float = 3.0,
) -> tuple[list[DiscoveryRecord], list[str]]:
    """Read decision history from SurrealDB (read-only, kanban_bridge auth).

    Credentials come from ``SURREAL_USER``/``SURREAL_PASS`` env (dev default
    ``root:root``), never hardcoded. Each table is queried independently;
    failures are logged and collected in the returned ``errors`` list rather
    than raised (fail-open, mirroring ``kanban_bridge``). Unit tests mock
    ``urllib.request.urlopen`` at source level; this function is never hit
    offline in tests.
    """
    records: list[DiscoveryRecord] = []
    errors: list[str] = []
    for table in tables:
        surql = f"SELECT * FROM {table} LIMIT {int(limit_per_table)};"
        try:
            body = _surreal_sql_post(url, ns, db, surql, timeout_s)
            results: Any = json.loads(body)
            # SurrealDB /sql returns a list of per-statement results; tolerate a
            # bare dict response shape from proxies. SurrealDB answers HTTP 200
            # even when a statement failed, so the parsed body goes through the
            # shared checker: an ERR statement is a failed read for this table.
            if isinstance(results, Mapping):
                results = [results]
            results = checked_statements(results)
            rows: list[Any] = []
            for entry in results:
                result = entry.get("result") if isinstance(entry, dict) else None
                if isinstance(result, list):
                    rows.extend(result)
            for row in rows:
                if isinstance(row, Mapping):
                    rec = _record_from_row(table, row)
                    if rec is not None:
                        records.append(rec)
        except Exception as exc:
            logger.warning("dream_rsi: SurrealDB read failed for %s: %s", table, exc)
            errors.append(f"{table}: {exc}")
    return records, errors


def load_from_vault_retros(retro_dir: Path | str | None = None) -> list[DiscoveryRecord]:
    """Ingest vault markdown retros as one decision point per note.

    Timestamp comes from a ``date:`` frontmatter line or the ``YYYY-MM-DD``
    filename prefix; the action is the first ``# `` heading (falling back to
    the filename stem). Retros carry no numeric outcome or cost, so those stay
    unknown and such points are replayable only for agreement/coverage.
    A missing or unreadable directory yields an empty list, never an error.
    """
    directory = Path(retro_dir) if retro_dir is not None else _VAULT_RETROS
    records: list[DiscoveryRecord] = []
    try:
        paths = sorted(directory.glob("*.md"))
    except OSError as exc:
        logger.warning("dream_rsi: cannot list retro dir %s: %s", directory, exc)
        return []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("dream_rsi: cannot read retro %s: %s", path, exc)
            continue
        date_match = re.search(r"^date:\s*(\S+)", text, re.MULTILINE)
        if date_match:
            timestamp = date_match.group(1)
        else:
            stem_match = _RE_DATE_PREFIX.match(path.stem)
            timestamp = stem_match.group(1) if stem_match else ""
        heading = None
        for line in text.splitlines():
            if line.startswith("# ") and not line.startswith("## "):
                heading = line[2:].strip()
                break
        records.append(
            DiscoveryRecord(
                id=path.stem,
                timestamp=timestamp,
                policy_context={"source": "vault_retro"},
                action=heading or path.stem,
                outcome_metrics={},
                cost=None,
                source_table="vault_retro",
            )
        )
    return records
