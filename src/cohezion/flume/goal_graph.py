"""Migration mapping + graph reader for the ONE goal/loop graph.

Nodes ``goal`` / ``loop`` (domain as data, not a table-name prefix) and one typed
edge table ``goal_graph`` (kind: pursues | derived_from | supersedes | mirrors).
The memory graph's ``relates_to`` is the proven shape.

This module is pure mapping + reading. Writes go through
``DurableSurrealGoalPersistence`` (``upsert_node`` / ``relate``): ONE write path.
The per-domain tables are read here ONLY by the migration; every runtime reader
(`graph_status`) reads canonical tables + ``goal_graph`` and never a ``<domain>_goal``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cohezion.flume.loop_goal_refactor_engine import (
    DurableSurrealGoalPersistence,
    record_ref,
)


# `<domain>_goal` / `<domain>_loop` tables that are NOT session goal/loop pairs:
# `compound_loop` is a TRACE table (never copied); `autonomous_loop` has its own mapper.
_PAIR_RE = re.compile(r"^(?P<domain>.+)_(?P<kind>goal|loop)$")
_NOT_PAIRS = frozenset({"compound", "autonomous"})
_DOC_RE = re.compile(r"(?:[\w.\-]+/)*[\w.\-]+\.md")
_DOC_FIELDS = ("spec", "doc", "recon_doc", "mirror", "plan")

_GOAL_MAPPED = {"id", "title", "name", "goal", "status", "target", "completion", "measured",
                "actual", "note", "session", "created_at", "date"}  # fmt: skip
_LOOP_MAPPED = {"id", "name", "title", "goal", "verify", "stop_when", "stop", "cadence",
                "schedule", "rung", "impl", "lane", "note", "session", "created_at", "date",
                "spec"}  # fmt: skip


def split_rid(rid: str) -> tuple[str, str]:
    table, _, key = str(rid).partition(":")
    return table, key.strip("⟨⟩`")


def node_key(domain: str, key: str) -> str:
    return f"{domain}__{key}"


def _first(row: dict[str, Any], *names: str) -> Any:
    for n in names:
        v = row.get(n)
        if v not in (None, ""):
            return v
    return None


def _as_int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _s(v: Any) -> str | None:
    return None if v is None else str(v)


def map_goal_row(domain: str, row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    table, key = split_rid(row["id"])
    fields: dict[str, Any] = {
        "title": _s(_first(row, "title", "name", "goal")) or key,
        "status": _s(row.get("status")),
        "target": _s(_first(row, "target", "goal", "completion")),
        "measured": _s(_first(row, "measured", "actual")),
        "domain": domain,
        "session": _s(row.get("session")),
        "note": _s(row.get("note")),
        "created_at": _s(_first(row, "created_at", "date")),
        "source_table": table,
        "source_id": str(row["id"]),
        "meta": {k: v for k, v in row.items() if k not in _GOAL_MAPPED},
    }
    return node_key(domain, key), fields


def map_loop_row(domain: str, row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    table, key = split_rid(row["id"])
    fields: dict[str, Any] = {
        "name": _s(_first(row, "name", "title")) or key,
        "goal": _s(row.get("goal")),
        "verify": _s(row.get("verify")),
        "stop_when": _s(_first(row, "stop_when", "stop")),
        "cadence": _s(_first(row, "cadence", "schedule")),
        "rung": _as_int(row.get("rung")),
        "impl": _s(row.get("impl")),
        "lane": _s(row.get("lane")),
        "note": _s(row.get("note")),
        "spec": _s(row.get("spec")),
        "domain": domain,
        "session": _s(row.get("session")),
        "created_at": _s(_first(row, "created_at", "date")),
        "source_table": table,
        "source_id": str(row["id"]),
        "meta": {k: v for k, v in row.items() if k not in _LOOP_MAPPED},
    }
    return node_key(domain, key), fields


def map_autonomous_row(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """`autonomous_loop` = an executed loop's outcome: converged/iterations/exit
    predicate are kept in `note` and `meta`, it ran at least once (rung 1)."""
    table, key = split_rid(row["id"])
    meta = {k: v for k, v in row.items() if k != "id"}
    fields: dict[str, Any] = {
        "name": key,
        "stop_when": _s(row.get("exit_predicate")),
        "rung": 1,
        "note": (
            f"converged={row.get('converged')} iterations={row.get('iteration_count')} "
            f"exit={row.get('exit_predicate')}"
        ),
        "domain": "autonomous",
        "source_table": table,
        "source_id": str(row["id"]),
        "meta": meta,
    }
    return node_key("autonomous", key), fields


def doc_paths(fields: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for name in _DOC_FIELDS:
        for src in (fields.get(name), (fields.get("meta") or {}).get(name)):
            if isinstance(src, str):
                out.extend(p for p in _DOC_RE.findall(src) if p not in out)
    return out[:3]


@dataclass
class MigrationPlan:
    goals: dict[str, dict[str, Any]] = field(default_factory=dict)  # node key -> fields
    loops: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[tuple[str, str, str, str | None]] = field(
        default_factory=list
    )  # kind,in,out,domain

    def counts(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for label, nodes in (("goal", self.goals), ("loop", self.loops)):
            for f in nodes.values():
                out.setdefault(f["domain"], {"goal": 0, "loop": 0})[label] += 1
        return out


def discover_domains(read_tables: Callable[[], list[str]]) -> list[str]:
    seen: dict[str, set[str]] = {}
    for t in read_tables():
        m = _PAIR_RE.match(t)
        if m and m["domain"] not in _NOT_PAIRS:
            seen.setdefault(m["domain"], set()).add(m["kind"])
    return sorted(seen)


def plan_migration(
    domains: list[str], read: Callable[[str], list[dict[str, Any]]]
) -> MigrationPlan:
    """Pure: old per-domain rows (via ``read(table)``) -> canonical nodes + edges.

    ``read`` returns [] for a table that does not exist (e.g. ``kg_loop``).
    """
    plan = MigrationPlan()
    for domain in domains:
        for row in read(f"{domain}_goal"):
            key, fields = map_goal_row(domain, row)
            plan.goals[key] = fields
        for row in read(f"{domain}_loop"):
            key, fields = map_loop_row(domain, row)
            plan.loops[key] = fields
    for row in read("autonomous_loop"):
        key, fields = map_autonomous_row(row)
        plan.loops[key] = fields
    # Existing typed edge `serves` (loop -> goal): the only REAL loop->goal evidence in
    # the old schema (loop.goal is free text that matches no goal row).
    for row in read("serves"):
        (lt, lk), (gt, gk) = split_rid(row["in"]), split_rid(row["out"])
        lm, gm = _PAIR_RE.match(lt), _PAIR_RE.match(gt)
        if lm and gm and lm["domain"] == gm["domain"]:
            d = lm["domain"]
            if node_key(d, lk) in plan.loops and node_key(d, gk) in plan.goals:
                plan.edges.append(("pursues", node_key(d, lk), node_key(d, gk), d))
    for label, nodes in (("loop", plan.loops), ("goal", plan.goals)):
        for key, f in nodes.items():
            for path in doc_paths(f):
                plan.edges.append(("mirrors", f"{label}:{key}", path, f["domain"]))
    return plan


def apply_plan(plan: MigrationPlan, persistence: DurableSurrealGoalPersistence) -> None:
    """Idempotent: deterministic node + edge ids, so a second run adds zero rows."""
    persistence.ensure_graph_schema()
    for key, f in plan.goals.items():
        persistence.upsert_node("goal", key, f)
    for key, f in plan.loops.items():
        persistence.upsert_node("loop", key, f)
    for kind, a, b, domain in plan.edges:
        if kind == "pursues":
            persistence.relate(kind, record_ref("loop", a), record_ref("goal", b), domain=domain)
        else:  # mirrors: node -> doc path
            label, _, key = a.partition(":")
            persistence.relate(
                kind, record_ref(label, key), record_ref("doc_path", b), domain=domain
            )


# ---------------------------------------------------------------------------
# Reader: the production consumer of the graph (R4)
# ---------------------------------------------------------------------------

_NOT_LINKED_PURSUES_OUT = "(SELECT VALUE out FROM goal_graph WHERE kind = 'pursues')"
_NOT_LINKED_PURSUES_IN = "(SELECT VALUE in FROM goal_graph WHERE kind = 'pursues')"


def graph_status(read: Callable[[str], list[dict[str, Any]]]) -> dict[str, Any]:
    """Per-domain counts, unlinked goals/loops, rung histogram, newest `mirrors` targets.

    Reads ONLY canonical ``goal`` / ``loop`` nodes and ``goal_graph`` edges -- never a
    ``<domain>_goal`` / ``<domain>_loop`` table. ``read(statement)`` -> rows.
    """
    dom: dict[str, dict[str, int]] = {}

    def bucket(rows: list[dict[str, Any]], key: str) -> None:
        for r in rows:
            d = dom.setdefault(str(r["domain"]), {})
            d[key] = d.get(key, 0) + int(r["n"])

    grp = "WHERE domain != NONE GROUP BY domain"
    bucket(read(f"SELECT domain, count() AS n FROM goal {grp};"), "goals")
    bucket(read(f"SELECT domain, count() AS n FROM loop {grp};"), "loops")
    bucket(
        read(
            "SELECT domain, count() AS n FROM goal WHERE domain != NONE "
            f"AND id NOT IN {_NOT_LINKED_PURSUES_OUT} GROUP BY domain;"
        ),
        "goals_without_loops",
    )
    bucket(
        read(
            "SELECT domain, count() AS n FROM loop WHERE domain != NONE "
            f"AND id NOT IN {_NOT_LINKED_PURSUES_IN} GROUP BY domain;"
        ),
        "loops_without_goals",
    )
    return {
        "domains": dict(sorted(dom.items())),
        "edges": {
            str(r["kind"]): int(r["n"])
            for r in read("SELECT kind, count() AS n FROM goal_graph GROUP BY kind;")
        },
        "rungs": {
            str(r["rung"]): int(r["n"])
            for r in read("SELECT rung, count() AS n FROM loop WHERE rung != NONE GROUP BY rung;")
        },
        "newest_mirrors": [
            str(r["out"])
            for r in read(
                "SELECT out, in.created_at AS at FROM goal_graph WHERE kind = 'mirrors' "
                "ORDER BY at DESC LIMIT 5;"
            )
        ],
    }


def format_status(status: dict[str, Any]) -> str:
    lines = [f"{'domain':<18}{'goals':>7}{'loops':>7}{'goal-no-loop':>14}{'loop-no-goal':>14}"]
    for d, c in status["domains"].items():
        lines.append(
            f"{d:<18}{c.get('goals', 0):>7}{c.get('loops', 0):>7}"
            f"{c.get('goals_without_loops', 0):>14}{c.get('loops_without_goals', 0):>14}"
        )
    lines.append(f"{len(status['domains'])} domain(s); edges by kind: {status['edges']}")
    lines.append(f"loop rungs (0 never run .. 4 unattended): {status['rungs']}")
    lines.append("newest mirrors targets: " + (", ".join(status["newest_mirrors"]) or "(none)"))
    return "\n".join(lines)
