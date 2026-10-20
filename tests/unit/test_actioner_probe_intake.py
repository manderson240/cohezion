"""Capped research cards reach the actioner through the experiment lane only (C6).

The honesty gate (``card_honesty.gate_relevance``) caps a research card claiming APPLY at
MONITOR until it links a probe result, and nothing wrote ``probe_ref`` -- while the
actioner polled only ``relevance=APPLY``. New research cards could therefore never be
actioned. Resolution without weakening the gate: the actioner also takes those capped
cards, runs them ONLY through the experiment lane (the experiment is the probe), and
records the experiment artifact as ``probe_ref``. It never re-asserts APPLY itself.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from cohezion.actioner import engine
from cohezion.actioner.engine import WorkQueueAPI, run_batch


CAPPED_EXPERIMENT = {
    "id": "cap000000001",
    "type": "research",
    "title": "A new benchmark for agent evals",
    "relevance": "MONITOR",
    "relevance_claimed": "APPLY",
    "probe_ref": "",
    "created_at": "2026-09-01",
}
CAPPED_IMPLEMENT = {**CAPPED_EXPERIMENT, "id": "cap000000002", "title": "MCP routing cache"}
PLAIN_MONITOR = {**CAPPED_EXPERIMENT, "id": "mon000000003", "relevance_claimed": ""}
APPLY_ITEM = {
    "id": "app000000004",
    "type": "improvement",
    "title": "agent routing cache",
    "relevance": "APPLY",
    "created_at": "2026-09-05",
}


class FakeQueue(WorkQueueAPI):
    """Answers the same GETs the real API serves; records every PATCH body."""

    def __init__(self, items):
        super().__init__("http://fake")
        self.items = items
        self.patches: list[tuple[str, dict]] = []

    def _request(self, method, path, body=None):
        if method == "PATCH":
            self.patches.append((path.rsplit("/", 1)[-1], body))
            return {}
        query = dict(kv.split("=") for kv in path.split("?", 1)[1].split("&"))
        rows = [
            i
            for i in self.items
            if i.get("relevance") == query["relevance"]
            and i.get("status", "reviewed") == query["status"]
        ]
        return {"items": rows}


class OkExecutor:
    def __init__(self):
        self.calls = 0

    def execute_task(self, task_description, skill_name, operation_type, execute_fn):
        self.calls += 1
        out, _ = execute_fn("")
        return SimpleNamespace(success=True, output=out, metrics={})


def _run(api, tmp_path, **kw):
    raw = json.dumps({"proposal": "p", "falsifiable_step": "s"})
    return run_batch(
        OkExecutor(),
        api,
        lambda p: raw,
        proposals_path=tmp_path / "p.jsonl",
        vault_dir=tmp_path / "v",
        **kw,
    )


def test_capped_research_card_is_actioned_as_an_experiment_with_a_probe_ref(tmp_path):
    api = FakeQueue([CAPPED_EXPERIMENT])
    s = _run(api, tmp_path)
    assert s["actioned"] == [{"id": CAPPED_EXPERIMENT["id"], "route": "experiment"}]
    (item_id, body) = api.patches[0]
    assert item_id == CAPPED_EXPERIMENT["id"]
    assert body["status"] == "actioned" and body["action_route"] == "experiment"
    assert body["probe_ref"].endswith(".md") and (tmp_path / "v") in _parents(body["probe_ref"])
    assert "relevance" not in body  # never re-asserts APPLY; the gate stays the judge


def test_capped_card_that_triages_to_implement_is_not_actioned(tmp_path):
    api = FakeQueue([CAPPED_IMPLEMENT])
    s = _run(api, tmp_path)
    assert s["actioned"] == [] and api.patches == []
    assert s["skipped_needs_probe"] == [CAPPED_IMPLEMENT["id"]]
    # not a triage miss: its relevance may change, so it must not be ledgered away
    assert not (tmp_path / engine.MISSES_FILENAME).exists()


def test_genuine_monitor_card_is_left_alone(tmp_path):
    api = FakeQueue([PLAIN_MONITOR])
    s = _run(api, tmp_path)
    assert s["processed"] == 0 and api.patches == []


def test_apply_cards_come_before_capped_cards(tmp_path):
    api = FakeQueue([CAPPED_EXPERIMENT, APPLY_ITEM])  # capped card is OLDER
    s = _run(api, tmp_path, batch_size=1)
    assert [a["id"] for a in s["actioned"]] == [APPLY_ITEM["id"]]


def test_crash_replay_of_a_capped_card_still_records_the_probe(tmp_path):
    _run(FakeQueue([CAPPED_EXPERIMENT]), tmp_path)
    api = FakeQueue([CAPPED_EXPERIMENT])  # PATCH was lost; the card is still MONITOR
    s = _run(api, tmp_path)
    assert s["deduped"] == [CAPPED_EXPERIMENT["id"]]
    assert api.patches[0][1]["probe_ref"].endswith(".md")


def test_probe_gated_types_match_the_gate():
    from cohezion.api.card_honesty import RESEARCH_TYPES

    assert engine.PROBE_GATED_TYPES == RESEARCH_TYPES


def _parents(path_str):
    from pathlib import Path

    return list(Path(path_str).parents)
