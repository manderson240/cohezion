"""Entity linking is exact-match or nothing; every edge carries its evidence sentence."""

import importlib.util
import sys
from pathlib import Path


_ops = Path(__file__).resolve().parents[2] / "scripts/ops"
sys.path.insert(0, str(_ops))
_spec = importlib.util.spec_from_file_location("memory_entities", _ops / "memory_entities.py")
me = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(me)

FILES = {
    "src/cohezion/inference/hotswap.py", "src/cohezion/inference/kv_budget.py",
    "src/a/util.py", "src/b/util.py", "scripts/ops/memory_facts.py",
}  # fmt: skip


def _r():
    return me.Resolver({"fleet-index", "kv-cost-follows-architecture"}, {"cohezion-land"}, FILES)


def test_me1_exact_path_module_and_unique_basename_resolve():
    r = _r()
    assert r.resolve("src/cohezion/inference/hotswap.py") == (
        "file",
        "src/cohezion/inference/hotswap.py",
    )
    assert r.resolve("cohezion.inference.kv_budget") == (
        "module",
        "src/cohezion/inference/kv_budget.py",
    )
    assert r.resolve("memory_facts.py") == ("file", "scripts/ops/memory_facts.py")


def test_me2_ambiguous_basename_is_dropped_and_counted_never_guessed():
    r = _r()
    assert r.resolve("util.py") is None
    assert r.ambiguous == 1


def test_me3_memory_and_skill_names_match_across_dash_underscore_and_args_are_ignored():
    r = _r()
    assert r.resolve("fleet_index") == ("memory", "fleet-index")
    assert r.resolve("cohezion-land --dry-run") == ("skill", "cohezion-land")
    assert (
        r.resolve("--flag") is None and r.resolve("") is None and r.resolve("no-such-thing") is None
    )


def test_me4_edges_carry_the_sentence_and_skip_self_mentions():
    text = "The `hotswap.py` gate reads `kv_budget.py` before loading.\nSee `fleet-index` for the rest."
    m, _co = me.edges_for("kv-cost-follows-architecture", text, _r())
    assert {x["kind"] for x in m} == {"file", "memory"}
    assert all("hotswap.py" in x["sentence"] or "fleet-index" in x["sentence"] for x in m)
    assert me.edges_for("fleet-index", "It is `fleet-index` itself.", _r()) == ([], [])


def test_me5_co_mention_needs_two_distinct_resolved_entities_in_one_sentence():
    text = "The `hotswap.py` gate reads `kv_budget.py` before loading."
    _m, co = me.edges_for("some-note", text, _r())
    assert len(co) == 1 and co[0]["a"] < co[0]["b"] and "hotswap.py" in co[0]["sentence"]
    _, none = me.edges_for("some-note", "Only `hotswap.py` here, and `nothing_real` too.", _r())
    assert none == []


def test_me6_edge_keys_are_deterministic_so_writes_are_idempotent():
    assert me.edge_key("m", "a", "b", "s") == me.edge_key("m", "a", "b", "s")
    assert me.edge_key("m", "a", "b", "s") != me.edge_key("m", "a", "b", "t")


def test_me7_write_counts_statement_level_errors_not_http_status(monkeypatch):
    # SurrealDB answers HTTP 200 with a per-statement ERROR; the writer must surface it.
    monkeypatch.setattr(
        me, "surreal", lambda q: [{"status": "OK"}, {"status": "ERR", "detail": "x"}]
    )
    m = [
        {
            "source": "s",
            "entity": "graph_entity:file_x",
            "kind": "file",
            "canonical": "x",
            "sentence": "a `x` b",
        }
    ]
    assert me.write_edges(m, [], "t") == 1


def test_me8_memory_node_ids_match_index_memory_and_preserve_case():
    # SurrealDB record ids are case-sensitive; a lowercased id creates a DANGLING edge.
    assert me.node_id("SESSION-29-SUMMARY") == "SESSION_29_SUMMARY"
    assert me.node_id("20260904-loop-docs") == "20260904_loop_docs"
    assert me.entity_id("memory", "Fleet-Index") == "memory:Fleet_Index"


def test_me9_hostile_sentence_stays_inside_one_json_string_literal(monkeypatch):
    # Note text is untrusted. It reaches SurrealQL only via json.dumps, which escapes the quote
    # that would end the literal; verified live too (stored verbatim, nothing deleted).
    hostile = 'x"; DELETE mem_mentions; LET $z = "}⟩; RETURN 1; //'
    seen: list[str] = []
    monkeypatch.setattr(me, "surreal", lambda q: seen.append(q) or [{"status": "OK"}])
    edge = {"source": "s", "entity": "graph_entity:file_x", "kind": "file", "canonical": "x"}
    assert me.write_edges([{**edge, "sentence": hostile}], [], "t") == 0
    assert me.json.dumps(hostile) in seen[0]  # present only in escaped form
    assert 'x"; DELETE mem_mentions' not in seen[0]  # the raw, unescaped payload never appears
