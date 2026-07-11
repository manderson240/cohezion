"""Unit tests for the cockpit daemon-state layer — all seams mocked, no live services."""

from __future__ import annotations

import inspect
import json
import subprocess

from cohezion.cockpit import daemon_state as ds


# --- read_task_queue -------------------------------------------------------
def test_read_task_queue_shape(tmp_path):
    tasks = [
        {"id": 1, "prompt": "a", "done": True, "source_item_id": "wq1"},
        {"id": 2, "prompt": "b", "done": False, "source_item_id": "wq2"},
        {"id": 3, "prompt": "c", "done": False},  # manual task: no source_item_id
    ]
    f = tmp_path / "tasks.json"
    f.write_text(json.dumps(tasks))

    out = ds.read_task_queue(path=f)

    assert out["total"] == 3
    assert out["done"] == 1
    assert isinstance(out["pending"], list) and len(out["pending"]) == 2
    # each pending item exposes id/source_item_id/prompt; manual task -> source_item_id None
    manual = next(p for p in out["pending"] if p["id"] == 3)
    assert manual["source_item_id"] is None
    assert manual["prompt"] == "c"


def test_read_task_queue_missing_file(tmp_path):
    out = ds.read_task_queue(path=tmp_path / "nope.json")
    assert out == {"total": 0, "done": 0, "pending": []}


# --- read_graph_counts -----------------------------------------------------
def test_read_graph_counts_parses_surreal_shape():
    calls: list[str] = []

    def fake_sql(query: str):
        calls.append(query)
        # SurrealDB HTTP returns [{"result": [{"count": N}], "status": "OK"}]
        return [{"result": [{"count": 7}], "status": "OK"}]

    out = ds.read_graph_counts(sql_fn=fake_sql)
    assert out == {"compound_loop": 7, "yielded": 7, "spawned": 7, "agent_journey": 7}
    assert len(calls) == 4  # one query per table


def test_read_graph_counts_failsoft_on_error():
    def boom(query: str):
        raise OSError("surreal down")

    assert ds.read_graph_counts(sql_fn=boom) == {
        "compound_loop": 0,
        "yielded": 0,
        "spawned": 0,
        "agent_journey": 0,
    }


# --- read_work_queue -------------------------------------------------------
def test_read_work_queue_breakdown():
    def fake_fetch(base: str):
        return {
            "total": 3,
            "items": [
                {"status": "actioned", "relevance": "APPLY"},
                {"status": "actioned", "relevance": "IGNORE"},
                {"status": "pending_review", "relevance": "APPLY"},
            ],
        }

    out = ds.read_work_queue(fetch=fake_fetch)
    assert out["total"] == 3
    assert out["by_status"] == {"actioned": 2, "pending_review": 1}
    assert out["by_relevance"] == {"APPLY": 2, "IGNORE": 1}


def test_read_work_queue_failsoft():
    def boom(base: str):
        raise OSError("api down")

    assert ds.read_work_queue(fetch=boom) == {"total": 0, "by_status": {}, "by_relevance": {}}


# --- read_gap_analysis -----------------------------------------------------
def test_read_gap_analysis_maps_gaps():
    class FakeGap:
        def __init__(self, tt, score, action):
            self.task_type = tt
            self.best_available_score = score
            self.suggested_action = action

    class FakeMatrix:
        def run_gap_analysis(self):
            return [FakeGap("reason", 0.25, "scout"), FakeGap("code", 0.55, "finetune")]

    out = ds.read_gap_analysis(matrix_factory=FakeMatrix)
    assert out == [
        {"task_type": "reason", "score": 0.25, "action": "scout"},
        {"task_type": "code", "score": 0.55, "action": "finetune"},
    ]


def test_read_gap_analysis_failsoft():
    def boom():
        raise RuntimeError("no matrix")

    assert ds.read_gap_analysis(matrix_factory=boom) == []


# --- read_lemonade_health --------------------------------------------------
def test_read_lemonade_health_shape():
    def fake_fetch(base: str):
        return {"status": "ok", "all_models_loaded": ["Gemma-4-E4B-it-GGUF", "llama3.2-1b-FLM"]}

    out = ds.read_lemonade_health(fetch=fake_fetch)
    assert out["status"] == "ok"
    assert out["loaded"] == ["Gemma-4-E4B-it-GGUF", "llama3.2-1b-FLM"]


def test_read_lemonade_health_down():
    def boom(base: str):
        raise OSError("router down")

    assert ds.read_lemonade_health(fetch=boom) == {"status": "down", "loaded": []}


# --- tail_daemon_log -------------------------------------------------------
def test_tail_daemon_log(tmp_path):
    log = tmp_path / "d.log"
    log.write_text("\n".join(f"line{i}" for i in range(50)))
    out = ds.tail_daemon_log(path=log, n=5)
    assert out.splitlines() == ["line45", "line46", "line47", "line48", "line49"]


def test_tail_daemon_log_missing(tmp_path):
    assert ds.tail_daemon_log(path=tmp_path / "absent.log") == ""


# --- run_feeder ------------------------------------------------------------
def test_run_feeder_parses_json():
    def fake_run(cmd):
        assert cmd[-2:] == ["--limit", "5"]
        return subprocess.CompletedProcess(
            cmd, 0, stdout=json.dumps({"fed": 2, "skipped": 1, "candidates": 3, "task_ids": [4, 5]})
        )

    out = ds.run_feeder(limit=5, run=fake_run)
    assert out["ok"] is True
    assert out["returncode"] == 0
    assert out["summary"]["fed"] == 2
    assert out["summary"]["task_ids"] == [4, 5]


def test_run_feeder_unparseable_output():
    def fake_run(cmd):
        return subprocess.CompletedProcess(cmd, 1, stdout="Traceback: boom")

    out = ds.run_feeder(run=fake_run)
    assert out["ok"] is False
    assert "raw" in out


# --- add_manual_task -------------------------------------------------------
def test_add_manual_task_appends_pending(tmp_path):
    tasks_file = tmp_path / "tasks.json"
    lock_file = tmp_path / "tasks.lock"
    existing = [{"id": 1, "prompt": "old", "priority": 2, "done": True}]
    tasks_file.write_text(json.dumps(existing))

    out = ds.add_manual_task("do the thing", priority=2, tasks_file=tasks_file, lock_file=lock_file)

    on_disk = json.loads(tasks_file.read_text())
    # existing task preserved
    assert on_disk[0] == {"id": 1, "prompt": "old", "priority": 2, "done": True}
    # new task appended with daemon schema {id: max+1, prompt, priority, done:False}
    assert on_disk[1] == {"id": 2, "prompt": "do the thing", "priority": 2, "done": False}
    assert out["added"]["id"] == 2
    assert out["total"] == 2


def test_add_manual_task_empty_file(tmp_path):
    tasks_file = tmp_path / "tasks.json"
    lock_file = tmp_path / "tasks.lock"
    out = ds.add_manual_task("first", tasks_file=tasks_file, lock_file=lock_file)
    assert out["added"]["id"] == 1
    assert json.loads(tasks_file.read_text()) == [
        {"id": 1, "prompt": "first", "priority": 2, "done": False}
    ]


def test_add_manual_task_is_flock_guarded():
    # V-model structural invariant: the write path must take the daemon's flock.
    src = inspect.getsource(ds.add_manual_task)
    assert "fcntl.flock" in src
    assert "LOCK_EX" in src


# --- ask_local_advisor -----------------------------------------------------
def test_advisor_body_omits_temperature():
    # F0/F1 lesson: temp=0.0 on Gemma yields empty output — body must OMIT it.
    body = ds._build_advisor_body("hello state")
    assert "temperature" not in body
    assert body["model"] == ds.ADVISOR_MODEL
    assert body["messages"][0]["content"] == "hello state"


def test_ask_local_advisor_uses_injected_chat():
    seen: list[str] = []

    def fake_chat(prompt: str):
        seen.append(prompt)
        return "  It is compounding fine. No concerns. Keep feeding.  "

    out = ds.ask_local_advisor("summary here", chat_fn=fake_chat)
    assert out == "It is compounding fine. No concerns. Keep feeding."
    assert "summary here" in seen[0]


def test_ask_local_advisor_failsoft_on_exception():
    def boom(prompt: str):
        raise OSError("router down")

    out = ds.ask_local_advisor("s", chat_fn=boom)
    assert out.startswith("(advisor unavailable")


def test_ask_local_advisor_failsoft_on_empty():
    out = ds.ask_local_advisor("s", chat_fn=lambda p: "")
    assert out == "(advisor returned no content)"
