"""genesis_persistence: the journey writer is REACHED, and its verdict is READ.

Measured 2026-09-20 (ns cohezion, db genesis AND db main): the ``journey_transitions``
table this module writes and reads did not exist. Cause: the only intended caller,
``flume.trajectory_capture._async_persist``, imported ``store_journey_transition`` -- a name
this module never defined -- inside a try/except that swallowed the ImportError. The real
writer, ``persist_journey_transition``, had zero callers. Independently, ``_execute_surql``
returned an HTTP-200 body carrying ``status: "ERR"`` as success. Existing tests mocked the
persist and the reader wholesale, so neither defect could surface.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from cohezion.persistence import genesis_persistence as gp


class _Resp:
    def __init__(self, body, status=200):
        self._body, self.status_code, self.text = body, status, json.dumps(body)

    def json(self):
        return self._body


def _client(body, status=200):
    client = MagicMock()
    client.post = AsyncMock(return_value=_Resp(body, status))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestExecutorReadsTheVerdict:
    @pytest.mark.asyncio
    async def test_DISCRIMINATING_err_statement_is_none_not_success(self, caplog):
        body = [{"status": "ERR", "result": "The table 'journey_transitions' does not exist"}]
        with (
            patch("httpx.AsyncClient", return_value=_client(body)),
            caplog.at_level("WARNING", logger="cohezion.persistence.genesis_persistence"),
        ):
            out = await gp._execute_surql("SELECT 1;")
        assert out is None
        assert any("does not exist" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_ok_statements_pass_through(self):
        body = [{"status": "OK", "result": [{"id": "x:1"}]}]
        with patch("httpx.AsyncClient", return_value=_client(body)):
            assert await gp._execute_surql("SELECT 1;") == body

    @pytest.mark.asyncio
    async def test_http_error_is_none(self):
        with patch("httpx.AsyncClient", return_value=_client({"details": "parse"}, 400)):
            assert await gp._execute_surql("bad") is None

    @pytest.mark.asyncio
    async def test_persist_returns_false_on_err(self):
        body = [{"status": "ERR", "result": "boom"}]
        with patch("httpx.AsyncClient", return_value=_client(body)):
            ok = await gp.persist_journey_transition("j", 0, np.zeros(12), np.zeros(12), 1.0)
        assert ok is False


class TestTrajectoryCaptureReachesTheWriter:
    """CONSUMPTION: capture_trajectory's exit persists through the REAL writer."""

    @pytest.mark.asyncio
    async def test_DISCRIMINATING_every_point_becomes_a_create(self):
        from cohezion.flume.trajectory_capture import TrajectoryRecorder, _async_persist

        rec = TrajectoryRecorder(domain="aimo", agent_id="solver-1")
        rec.record(state={"difficulty": 5}, action="solve", reward=1.0)
        rec.record(state={"difficulty": 8}, action="verify", reward=0.0)

        sent: list[str] = []

        async def fake_exec(q: str):
            sent.append(q)
            return [{"status": "OK", "result": [{}]}]

        with patch.object(gp, "_execute_surql", side_effect=fake_exec):
            await _async_persist(rec)

        # The phantom-import version of the caller produced ZERO of these.
        assert len(sent) == 2
        assert all(q.startswith("CREATE journey_transitions SET ") for q in sent)
        assert "t = 0," in sent[0] and "t = 1," in sent[1]
        assert f"journey_id = '{rec.trajectory_id}'" in sent[0]
        assert 'metadata = {"domain": "aimo", "agent_id": "solver-1"' in sent[0]
        assert 'action = "solve"' in sent[0]

    @pytest.mark.asyncio
    async def test_writer_failure_never_escapes_the_capture(self):
        from cohezion.flume.trajectory_capture import TrajectoryRecorder, _async_persist

        rec = TrajectoryRecorder(domain="aimo", agent_id="s")
        rec.record(state={"difficulty": 5}, action="solve", reward=1.0)
        with patch.object(gp, "_execute_surql", side_effect=RuntimeError("down")):
            await _async_persist(rec)  # must not raise


class TestWriterFields:
    @pytest.mark.asyncio
    async def test_action_and_json_safe_metadata_are_written(self):
        sent: list[str] = []

        async def fake_exec(q: str):
            sent.append(q)
            return [{"status": "OK", "result": [{}]}]

        with patch.object(gp, "_execute_surql", side_effect=fake_exec):
            ok = await gp.persist_journey_transition(
                "j",
                3,
                np.zeros(12),
                np.ones(12),
                0.5,
                action="solve",
                metadata={"k": 1, "bad": object()},
            )
        assert ok is True
        assert 'action = "solve"' in sent[0]
        assert 'metadata = {"k": 1}' in sent[0]
