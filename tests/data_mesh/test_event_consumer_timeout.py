"""A slow SurrealDB read must not make the event-consumer unit exit non-zero."""

from __future__ import annotations

import importlib.util
import sys
import urllib.error
from pathlib import Path

import pytest

from cohezion.data_mesh.event_consumer import EventConsumer


def _sql_that_times_out_on_fetch(query: str):
    if query.lstrip().upper().startswith("SELECT"):
        raise TimeoutError("The read operation timed out")
    return [{"status": "OK", "result": []}]


def test_run_once_skips_batch_on_fetch_timeout():
    summary = EventConsumer("c1", sql_fn=_sql_that_times_out_on_fetch).run_once()
    assert summary["failed"] == {}
    assert summary["fetched"] == 0
    assert "timed out" in summary["skipped"]


def test_run_once_skips_batch_on_connect_timeout():
    def sql_fn(query: str):
        raise urllib.error.URLError(TimeoutError("timed out"))

    summary = EventConsumer("c1", sql_fn=sql_fn).run_once()
    assert summary["failed"] == {}
    assert "timed out" in summary["skipped"]


def test_refused_connection_stays_loud():
    def sql_fn(query: str):
        raise urllib.error.URLError(ConnectionRefusedError("refused"))

    with pytest.raises(urllib.error.URLError):
        EventConsumer("c1", sql_fn=sql_fn).run_once()


def _load_driver():
    script = Path(__file__).resolve().parents[2] / "scripts" / "datamesh_event_consumer.py"
    spec = importlib.util.spec_from_file_location("datamesh_event_consumer_script", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def driver(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr(sys, "argv", ["datamesh_event_consumer.py"])
    return _load_driver()


def _patch_sql(monkeypatch, fn):
    monkeypatch.setattr(
        "cohezion.data_mesh.event_consumer._default_sql", lambda query, timeout=10.0: fn(query)
    )


def test_driver_exit_code_is_zero_on_fetch_timeout(monkeypatch, driver, tmp_path):
    _patch_sql(monkeypatch, _sql_that_times_out_on_fetch)
    assert driver.main() == 0
    state = list((tmp_path / "state" / "cohezion").glob("*.json"))
    assert len(state) == 1  # the count went to the tmp state dir, not the real one


def test_driver_exits_nonzero_after_three_consecutive_fetch_timeouts(monkeypatch, driver):
    _patch_sql(monkeypatch, _sql_that_times_out_on_fetch)
    assert [driver.main() for _ in range(4)] == [0, 0, 1, 1]


def test_a_pass_without_a_timeout_resets_the_count(monkeypatch, driver):
    _patch_sql(monkeypatch, _sql_that_times_out_on_fetch)
    assert [driver.main() for _ in range(2)] == [0, 0]
    _patch_sql(monkeypatch, lambda q: [{"status": "OK", "result": []}])
    assert driver.main() == 0
    _patch_sql(monkeypatch, _sql_that_times_out_on_fetch)
    assert [driver.main() for _ in range(2)] == [0, 0]  # restarted from zero, not 3


def test_permanent_claim_timeout_also_stalls_the_driver(monkeypatch, driver):
    def sql(query: str):
        q = query.lstrip().upper()
        if q.startswith("SELECT"):
            return [
                {
                    "status": "OK",
                    "result": [{"id": "data_product_event:e1", "event_type": "custom"}],
                }
            ]
        if q.startswith("UPDATE"):
            raise TimeoutError("claim timed out")
        return [{"status": "OK", "result": []}]

    _patch_sql(monkeypatch, sql)
    assert [driver.main() for _ in range(3)] == [0, 0, 1]


def test_counts_are_per_consumer(monkeypatch, driver, tmp_path):
    from cohezion.data_mesh.event_consumer import record_pass_outcome

    stalled = {"skipped": "fetch timed out"}
    for _ in range(2):
        record_pass_outcome("a", stalled, tmp_path)
    assert record_pass_outcome("b", stalled, tmp_path) == 1
    assert record_pass_outcome("a", stalled, tmp_path) == 3


def test_unwritable_state_is_logged_and_does_not_crash_the_pass(tmp_path, caplog):
    from cohezion.data_mesh.event_consumer import record_pass_outcome

    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x")
    with caplog.at_level("ERROR"):
        assert record_pass_outcome("c", {"skipped": "t"}, blocker) == 1
    assert any("stall-state write failed" in m for m in caplog.messages)


def test_corrupt_state_is_logged_and_counts_from_zero(tmp_path, caplog):
    from cohezion.data_mesh.event_consumer import _stall_state_path, record_pass_outcome

    path = _stall_state_path("d", tmp_path)
    path.write_text("{not json")
    with caplog.at_level("ERROR"):
        assert record_pass_outcome("d", {"skipped": "t"}, tmp_path) == 1
    assert any("stall-state read failed" in m for m in caplog.messages)


def test_fetched_counts_fetched_events_not_attempts():
    events = [{"id": f"data_product_event:e{i}", "event_type": "custom"} for i in range(3)]

    def sql(query: str):
        if query.lstrip().upper().startswith("SELECT"):
            return [{"status": "OK", "result": events}]
        raise TimeoutError("claim timed out")

    summary = EventConsumer("c1", sql_fn=sql).run_once()
    assert summary["fetched"] == 3  # the claim timeout ended the pass at the first event
    assert summary["claim_timed_out"] == ["data_product_event:e0"]
