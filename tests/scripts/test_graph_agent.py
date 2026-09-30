"""The agent's tools and oracle are deterministic; only the model in the middle is not."""

import importlib.util
import sys
from pathlib import Path


_ops = Path(__file__).resolve().parents[2] / "scripts/ops"
sys.path.insert(0, str(_ops))
_spec = importlib.util.spec_from_file_location("graph_agent", _ops / "graph_agent.py")
ga = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ga)
import memory_entities as me


FILES = {"src/a/hotswap.py", "docs/AGENTS.md"}


def _res():
    return me.Resolver({"note-one"}, set(), FILES)


def _db(rows):
    return lambda q: [{"status": "OK", "result": rows}]


def test_ga1_who_mentions_counts_distinct_notes_and_reports_unresolved():
    rows = [{"note": "memory:note_a"}, {"note": "memory:note_a"}, {"note": "memory:note_b"}]
    out = ga.who_mentions_impl("hotswap.py", _res(), db=_db(rows))
    assert out["count"] == 2 and out["notes"] == ["note_a", "note_b"] and out["resolved"]
    miss = ga.who_mentions_impl("nope.xyz", _res(), db=_db(rows))
    assert miss == {"token": "nope.xyz", "resolved": False, "notes": [], "count": 0}


def test_ga2_entities_in_note_uses_the_indexer_id_rule():
    seen = []
    ga.entities_in_note_impl("SESSION-29-X", db=lambda q: seen.append(q) or [{"result": []}])
    assert "memory:SESSION_29_X" in seen[0]  # case preserved, same rule as index_memory.py


def test_ga3_score_needs_a_standalone_number_not_a_substring():
    assert ga.score("There are 4 notes.", {"4"})
    assert not ga.score("There are 14 notes.", {"4"})  # '14' contains '4' — must not pass
    assert not ga.score("Version 1.4 of it", {"4"})  # '.4' is part of a version, not the answer
    assert not ga.score("I do not know", {"4"})


def test_ga4_build_questions_ground_truth_comes_from_the_rows_not_a_model():
    def db(q):
        if "graph_entity" in q:
            return [
                {
                    "result": [
                        {
                            "id": "graph_entity:file_x",
                            "canonical": "src/a/hotswap.py",
                            "kind": "file",
                        }
                    ]
                }
            ]
        return [
            {"result": [{"out": "graph_entity:file_x", "in": f"memory:n{i}"} for i in range(3)]}
        ]

    qs = ga.build_questions(2, _res(), db=db)
    count = next(q for q in qs if q["kind"] == "count")
    assert count["expected"] == {"3"} and "hotswap.py" in count["q"]
