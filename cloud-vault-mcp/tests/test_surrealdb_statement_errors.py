"""SurrealDB answers HTTP 200 with per-statement ``status: "ERR"``; the client
must not read that as success (measured 2026-09-19: ``track_session`` reported
success for a CREATE that never landed). HTTP 4xx must surface the SurrealQL
error body, not just the status code."""

from unittest.mock import MagicMock

import pytest

from mcp_server.surrealdb_sync import SurrealQLError, _checked_statements


def _resp(status_code, payload=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload
    r.text = text
    return r


def test_ok_statements_pass_through():
    payload = [{"status": "OK", "result": [{"id": "agent_session:x"}]}]
    assert _checked_statements(_resp(200, payload)) == payload


def test_statement_level_err_raises_with_the_db_message():
    payload = [
        {"status": "OK", "result": None},
        {"status": "ERR", "result": "The table 'agent_session' does not exist"},
    ]
    with pytest.raises(SurrealQLError, match="agent_session"):
        _checked_statements(_resp(200, payload))


def test_http_400_raises_with_body_not_just_code():
    with pytest.raises(SurrealQLError, match="Parse error at line 3"):
        _checked_statements(
            _resp(400, text='{"code":400,"details":"Parse error at line 3"}')
        )


def test_track_session_reports_failure_when_statement_errs():
    """Consumption check: the tool's success envelope follows the DB's verdict."""
    from mcp_server.agent_context import AgentContextOps

    db = MagicMock()
    db._execute_query.side_effect = SurrealQLError(
        "The table 'agent_session' does not exist"
    )
    mgr = AgentContextOps(db)
    out = mgr.track_session(agent_id="probe", goals=["g"])
    assert out["success"] is False
    assert "agent_session" in out["error"]
