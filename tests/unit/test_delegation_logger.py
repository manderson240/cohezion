"""Unit tests for DelegationLogger."""

import json
import tempfile
import threading
import unittest.mock
from pathlib import Path

import pytest

from cohezion.agi import dream_rsi
from cohezion.inference.delegation_logger import DelegationEvent, DelegationLogger


def test_delegation_event_to_dict() -> None:
    event = DelegationEvent(
        task_name="coding",
        task_importance=0.9,
        quality_gap=0.3,
        escalation_cost=0.25,
        evi_score=1.08,
        source_tier=1,
        target_tier=2,
        escalated=True,
        model_selected="qwen3.5:397b-cloud",
        reason="Tier 2 escalation",
    )
    data = event.to_dict()
    assert data["task_name"] == "coding"
    assert data["evi_score"] == 1.08
    assert data["source_tier"] == 1
    assert data["target_tier"] == 2
    assert data["escalated"] is True


def test_delegation_logger_fallback_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "delegation_log.jsonl"
        # Unreachable SurrealDB URL: forces get_recent_events down the JSONL
        # fallback path (the primary read hits the live delegation_log table).
        logger = DelegationLogger(surreal_url="http://localhost:59999")
        logger.fallback_path = log_path

        event1 = DelegationEvent(
            task_name="reasoning",
            task_importance=0.8,
            quality_gap=0.2,
            escalation_cost=0.25,
            evi_score=0.64,
            source_tier=1,
            target_tier=1,
            escalated=False,
            model_selected="deepseek-r1-0528-8b-FLM",
            reason="Tier 1 selected",
        )

        logger.log_delegation(event1)
        assert log_path.exists()

        events = logger.get_recent_events(limit=5)
        assert len(events) == 1
        assert events[0]["task_name"] == "reasoning"
        assert events[0]["model_selected"] == "deepseek-r1-0528-8b-FLM"


# ── log_outcome: outcome telemetry write path (Dream-RSI) ──────────────────


class _FakeResponse:
    """Minimal urlopen stand-in: context manager returning a canned body."""

    def __init__(self, payload: bytes) -> None:
        self._buf = payload

    def read(self) -> bytes:
        return self._buf

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _capture_outcome_post(http_calls: list, payload: bytes):
    """Source-level urlopen stub capturing (url, data) for the outcome pass."""

    def _fake(req, timeout=None):
        http_calls.append({"url": req.full_url, "data": req.data.decode("utf-8")})
        return _FakeResponse(payload)

    return unittest.mock.patch("cohezion.inference.delegation_logger.urllib.request.urlopen", _fake)


def _make_logger() -> DelegationLogger:
    return DelegationLogger(surreal_url="http://localhost:59999")


_OK_BODY = json.dumps([{"status": "OK", "result": []}]).encode()


class TestLogOutcome:
    def test_merges_outcome_columns_on_existing_row(self) -> None:
        """UPDATE ... MERGE on the record id — no second row is inserted."""
        calls: list = []
        logger = _make_logger()
        with _capture_outcome_post(calls, _OK_BODY):
            ok = logger.log_outcome(
                "abc123",
                quality_score=0.87,
                cost_seconds=12.5,
                succeeded=True,
                error=None,
            )
        assert ok is True
        assert len(calls) == 1
        assert calls[0]["url"].endswith("/sql")
        sql = calls[0]["data"]
        assert sql.startswith("UPDATE delegation_log:abc123 MERGE ")
        fields = json.loads(sql[len("UPDATE delegation_log:abc123 MERGE ") : -1])
        assert fields["metrics"] == {"score": 0.87}
        assert fields["cost"] == 12.5
        assert fields["succeeded"] is True
        assert "error" not in fields

    def test_noop_when_nothing_to_record_makes_no_http(self) -> None:
        calls: list = []
        logger = _make_logger()
        with _capture_outcome_post(calls, _OK_BODY):
            ok = logger.log_outcome("delegation_log:abc123")
        assert ok is True
        assert calls == []  # no-op-safe: zero HTTP when there is nothing to write

    def test_fail_open_when_surrealdb_down(self) -> None:
        """A dead SurrealDB must warn and return False, never raise."""
        calls: list = []

        def _boom(req, timeout=None):
            calls.append(req)
            raise OSError("connection refused")

        logger = _make_logger()
        with unittest.mock.patch(
            "cohezion.inference.delegation_logger.urllib.request.urlopen", _boom
        ):
            ok = logger.log_outcome("delegation_log:abc123", quality_score=0.5)
        assert ok is False and len(calls) == 1

    def test_db_error_status_returns_false(self) -> None:
        calls: list = []
        bad_body = json.dumps([{"status": "ERR", "result": "no such record"}]).encode()
        logger = _make_logger()
        with _capture_outcome_post(calls, bad_body):
            ok = logger.log_outcome("delegation_log:abc123", succeeded=False, error="oom")
        assert ok is False

    def test_backtick_quoting_for_non_alphanumeric_id(self) -> None:
        calls: list = []
        logger = _make_logger()
        with _capture_outcome_post(calls, _OK_BODY):
            logger.log_outcome("row-with-dash", quality_score=1.0)
        assert "UPDATE delegation_log:`row-with-dash` MERGE" in calls[0]["data"]

    def test_error_lands_as_outcome_error_column(self) -> None:
        calls: list = []
        logger = _make_logger()
        with _capture_outcome_post(calls, _OK_BODY):
            logger.log_outcome("delegation_log:x", error="inference timeout")
        fields = json.loads(calls[0]["data"].split("MERGE ")[1].rstrip(";"))
        assert fields["outcome_error"] == "inference timeout"


class TestLogOutcomeRowShapeForDreamRsi:
    """Row-shape contract: dream_rsi._record_from_row must read the new columns
    as outcome_metrics['score'] / cost / succeeded — never as decision context."""

    def _record_from_merged_row(self, fields: dict):
        row = {
            "id": "delegation_log:abc123",
            "task_name": "coding",
            "model_selected": "qwen3.5:397b-cloud",
            "timestamp": 1789123456.0,
        }
        row.update(fields)
        return dream_rsi._record_from_row("delegation_log", row)

    def test_score_lands_in_outcome_metrics_via_metrics_mapping(self) -> None:
        rec = self._record_from_merged_row(
            {"metrics": {"score": 0.87}, "cost": 12.5, "succeeded": True}
        )
        assert rec is not None
        assert rec.cost == 12.5
        assert rec.succeeded is True
        # OUTCOME_KEYS resolves the score directly from outcome_metrics.
        assert dream_rsi._outcome_value(rec) == pytest.approx(0.87)

    def test_score_never_lands_in_policy_context(self) -> None:
        rec = self._record_from_merged_row({"metrics": {"score": 0.87}})
        assert rec is not None
        assert "score" not in rec.policy_context
        assert "metrics" not in rec.policy_context

    def test_cost_maps_to_record_cost_not_context(self) -> None:
        rec = self._record_from_merged_row({"cost": 3.25})
        assert rec is not None
        assert rec.cost == pytest.approx(3.25)
        assert "cost" not in rec.policy_context

    def test_succeeded_false_yields_zero_reward(self) -> None:
        rec = self._record_from_merged_row({"succeeded": False})
        assert rec is not None and rec.succeeded is False
        assert dream_rsi._outcome_value(rec) == 0.0

    def test_round_trip_through_log_outcome_write_shape(self) -> None:
        """End-to-end shape check: the exact MERGE payload log_outcome sends,
        replayed as a SurrealDB row, is readable by the dream loader."""
        calls: list = []
        logger = _make_logger()
        with _capture_outcome_post(calls, _OK_BODY):
            logger.log_outcome(
                "delegation_log:abc123",
                quality_score=0.42,
                cost_seconds=7.75,
                succeeded=True,
                error="",
            )
        fields = json.loads(calls[0]["data"].split("MERGE ")[1].rstrip(";"))
        rec = self._record_from_merged_row(fields)
        assert rec is not None
        assert dream_rsi._outcome_value(rec) == pytest.approx(0.42)
        assert rec.cost == pytest.approx(7.75)
        assert rec.succeeded is True


class TestLogDelegationUnchanged:
    """The existing decision-write paths must be untouched by log_outcome."""

    def test_log_delegation_still_writes_jsonl_and_does_not_use_outcome_pass(
        self, tmp_path: Path
    ) -> None:
        log_path = tmp_path / "delegation_log.jsonl"
        logger = DelegationLogger(surreal_url="http://localhost:59999")
        logger.fallback_path = log_path

        calls: list = []
        event = DelegationEvent(
            task_name="coding",
            task_importance=0.9,
            quality_gap=0.3,
            escalation_cost=0.25,
            evi_score=1.08,
            source_tier=1,
            target_tier=2,
            escalated=True,
            model_selected="qwen3.5:397b-cloud",
            reason="Tier 2 escalation",
        )
        with _capture_outcome_post(calls, _OK_BODY):
            logger.log_delegation(event)  # must not raise, must stay fire-and-forget
            threading.Event().wait(0.3)  # let the daemon thread run

        assert log_path.exists()
        row = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert row["task_name"] == "coding"
        assert "metrics" not in row and "cost" not in row  # decision row, not outcome
        # log_delegation never calls the log_outcome HTTP pass.
        assert all("MERGE" not in c["data"] for c in calls)

    def test_log_outcome_signature_keyword_only(self) -> None:
        logger = _make_logger()
        try:
            logger.log_outcome("x", 0.5)  # type: ignore[misc]
        except TypeError:
            pass  # positional quality_score is rejected — keyword-only contract
        else:  # pragma: no cover
            raise AssertionError("log_outcome must be keyword-only after delegation_id")
