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


def test_driver_exit_code_is_zero_on_fetch_timeout(monkeypatch, capsys):
    script = Path(__file__).resolve().parents[2] / "scripts" / "datamesh_event_consumer.py"
    spec = importlib.util.spec_from_file_location("datamesh_event_consumer_script", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setattr(
        "cohezion.data_mesh.event_consumer._default_sql",
        lambda query, timeout=10.0: _sql_that_times_out_on_fetch(query),
    )
    monkeypatch.setattr(sys, "argv", ["datamesh_event_consumer.py"])
    assert mod.main() == 0
