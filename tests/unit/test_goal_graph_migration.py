"""R1/R2/R3: one goal/loop graph -- mapping per old table, idempotent migration,
derived_from edges, and the single write path.

Fixtures = one REAL row per old table, captured from the 2026-09-18 census
(``goal_loop_fixtures/goal_loop_census_rows.json``). Integration tests run un-mocked against
SurrealDB in the scratch db ``tgl_test_migrate`` and SKIP (not pass) when it is down.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cohezion.flume.goal_graph import (
    apply_plan,
    discover_domains,
    map_autonomous_row,
    map_goal_row,
    map_loop_row,
    plan_migration,
)
from cohezion.flume.loop_goal_refactor_engine import (
    DurableSurrealGoalPersistence,
    GoalSpecification,
    LoopSpec,
    TraceGoalRefactorPipeline,
    record_ref,
)
from cohezion.flume.trace_goal_sources import sql


FIXTURE = json.loads((Path(__file__).parent / "goal_loop_fixtures" / "goal_loop_census_rows.json").read_text())
SCRATCH = "tgl_test_migrate"


def _read(table: str) -> list[dict]:
    return FIXTURE.get(table, [])


def _plan():
    domains = discover_domains(lambda: list(FIXTURE))
    return domains, plan_migration(domains, _read)


def test_discover_domains_excludes_traces_and_handles_missing_half() -> None:
    domains, _ = _plan()
    assert set(domains) == {
        "doctor", "kaggle", "kg", "metrics", "quadrature_nexus", "smith", "twin", "verification",
    }  # fmt: skip
    assert "compound" not in domains and "autonomous" not in domains  # traces are not copied
    assert discover_domains(lambda: ["compound_loop", "autonomous_loop", "goal", "loop"]) == []


@pytest.mark.parametrize("table", [t for t in FIXTURE if t.endswith("_goal")])
def test_goal_row_maps_with_provenance_and_domain(table: str) -> None:
    domain = table.removesuffix("_goal")
    for row in FIXTURE[table]:
        key, f = map_goal_row(domain, row)
        assert key.startswith(f"{domain}__")
        assert f["domain"] == domain and f["source_table"] == table
        assert f["source_id"] == row["id"] and f["title"]


@pytest.mark.parametrize(
    "table", [t for t in FIXTURE if t.endswith("_loop") and t != "autonomous_loop"]
)
def test_loop_row_maps_with_provenance_and_domain(table: str) -> None:
    domain = table.removesuffix("_loop")
    for row in FIXTURE[table]:
        key, f = map_loop_row(domain, row)
        assert key.startswith(f"{domain}__")
        assert f["domain"] == domain and f["source_table"] == table
        assert f["source_id"] == row["id"] and f["name"]
        assert f["rung"] is None or isinstance(f["rung"], int)


def test_autonomous_loop_keeps_convergence_data() -> None:
    row = FIXTURE["autonomous_loop"][0]
    _, f = map_autonomous_row(row)
    assert f["domain"] == "autonomous" and f["rung"] == 1
    assert f["stop_when"] == row["exit_predicate"]
    assert f["meta"]["converged"] == row["converged"]
    assert f"iterations={row['iteration_count']}" in f["note"]


def test_migration_counts_per_domain_equal_the_old_tables() -> None:
    """DISCRIMINATING (mutation: drop `domain` from the mapper -> counts collapse)."""
    _, plan = _plan()
    counts = plan.counts()
    for table, rows in FIXTURE.items():
        if table == "serves":
            continue
        if table == "autonomous_loop":
            assert counts["autonomous"]["loop"] == len(rows)
            continue
        domain, _, kind = table.rpartition("_")
        assert counts[domain][kind] == len(rows), table


def test_plan_is_deterministic_so_a_rerun_writes_the_same_ids() -> None:
    _, a = _plan()
    _, b = _plan()
    assert list(a.goals) == list(b.goals) and list(a.loops) == list(b.loops)
    assert a.edges == b.edges


def test_serves_edge_becomes_a_pursues_edge_and_docs_become_mirrors() -> None:
    _, plan = _plan()
    pursues = [e for e in plan.edges if e[0] == "pursues"]
    assert ("pursues", "kaggle__sept_build_gate", "kaggle__G1_kaggriculture", "kaggle") in pursues
    mirrors = [e for e in plan.edges if e[0] == "mirrors"]
    assert mirrors and all(e[2].endswith(".md") for e in mirrors)
    assert any(e[3] == "metrics" for e in mirrors)  # metrics_goal.doc -> references/*.md


def test_record_ref_and_relate_refuse_unsafe_input() -> None:
    with pytest.raises(ValueError):
        record_ref("goal", "bad`key")
    with pytest.raises(ValueError):
        DurableSurrealGoalPersistence().relate("bogus", "loop:`a`", "goal:`b`")


# -- un-mocked, scratch db ---------------------------------------------------------


@pytest.fixture()
def scratch() -> DurableSurrealGoalPersistence:
    p = DurableSurrealGoalPersistence(database=SCRATCH, timeout=10.0)
    try:
        DurableSurrealGoalPersistence(database="main", timeout=3.0)._sql(
            f"DEFINE DATABASE IF NOT EXISTS {SCRATCH};"
        )
    except Exception as exc:
        pytest.skip(f"SurrealDB not reachable: {exc}")
    for stmt in (
        "DEFINE TABLE IF NOT EXISTS goal SCHEMALESS; DEFINE TABLE IF NOT EXISTS loop SCHEMALESS;",
        "REMOVE TABLE IF EXISTS goal_graph;",
        "DELETE goal;",
        "DELETE loop;",
    ):
        p._sql(stmt)
    yield p
    for stmt in ("REMOVE TABLE IF EXISTS goal_graph;", "DELETE goal;", "DELETE loop;"):
        p._sql(stmt)


def _count(table: str, where: str = "") -> int:
    rows = sql(f"SELECT count() AS n FROM {table} {where} GROUP ALL;", SCRATCH)
    return rows[0]["n"] if rows else 0


def test_live_migration_is_idempotent_and_goal_graph_has_kind_and_domain(scratch) -> None:
    _, plan = _plan()
    apply_plan(plan, scratch)
    first = (_count("goal"), _count("loop"), _count("goal_graph"))
    assert first[0] == len(plan.goals) and first[1] == len(plan.loops)
    assert _count("goal_graph", "WHERE kind = 'pursues'") >= 1  # R1 falsifier
    fields = sql("INFO FOR TABLE goal_graph;", SCRATCH)[0]["fields"]
    assert "kind" in fields and "domain" in fields  # R1 falsifier
    apply_plan(plan, scratch)  # R2: second run adds ZERO rows
    assert (_count("goal"), _count("loop"), _count("goal_graph")) == first
    per_domain = {
        r["domain"]: r["n"]
        for r in sql("SELECT domain, count() AS n FROM loop GROUP BY domain;", SCRATCH)
    }
    assert per_domain == {d: c["loop"] for d, c in plan.counts().items() if c["loop"]}


def test_live_derived_from_edge_carries_source_db(scratch) -> None:
    goal = GoalSpecification("g_df", "Stabilize: x", "error_rate", 0.05, direction="at_most")
    refs = [
        {"source_db": "vault", "source_table": "event_log", "source_id": "event_log:vv1"},
        {"source_db": SCRATCH, "source_table": "event_log", "source_id": "event_log:mm1"},
    ]
    scratch.persist_goal(goal, domain="trace", session="t", derived_from=refs)
    scratch.persist_goal(goal, domain="trace", session="t", derived_from=refs)  # idempotent
    edges = sql("SELECT * FROM goal_graph WHERE kind = 'derived_from' ORDER BY source_db;", SCRATCH)
    assert len(edges) == 2
    by_db = {e["source_db"]: e for e in edges}
    assert str(by_db["vault"]["out"]).startswith("trace_ref:")  # cross-db: placeholder + fields
    assert by_db["vault"]["source_id"] == "event_log:vv1"
    assert str(by_db[SCRATCH]["out"]) == "event_log:mm1"  # same db: the real record id
    assert all(str(e["in"]) == "goal:g_df" for e in edges)


def test_live_refactor_writes_a_loop_row_and_a_pursues_edge(scratch) -> None:
    """R1: `pursues > 0` from a REAL executed loop, not only from migrated `serves`."""
    pipeline = TraceGoalRefactorPipeline(persistence=scratch)
    trace = [{"type": "JOURNEY_STEP", "source": "s", "payload": {"msg": "error"}}]
    goal, _ = pipeline.refactor(
        trace,
        step_fn=lambda it, s: (s, 0.9, "m"),
        max_iterations=1,
        domain="trace",
        session="t",
    )
    assert goal is not None
    loops = sql("SELECT * FROM loop;", SCRATCH)
    assert len(loops) == 1 and loops[0]["domain"] == "trace" and loops[0]["rung"] == 1
    pur = sql("SELECT * FROM goal_graph WHERE kind = 'pursues';", SCRATCH)
    assert len(pur) == 1 and str(pur[0]["out"]) == f"goal:{goal.goal_id}"


def test_loopspec_is_the_template_fields() -> None:
    fields = set(LoopSpec.__dataclass_fields__)
    assert {"goal", "each_iteration", "verify", "stop_when", "bound", "on_stop", "rung",
            "cadence", "domain", "session"} <= fields  # fmt: skip
