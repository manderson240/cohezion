"""Coverage batch Z41: session_tracker, mcp_shared_client, trajectory_capture."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: platform/session_tracker.py
# ---------------------------------------------------------------------------


class TestSessionTracker:
    def test_model_usage_event_creation(self):
        from cohezion.platform.session_tracker import ModelUsageEvent

        ev = ModelUsageEvent(
            session_id="s1",
            model_name="phi3:mini",
            started_at=1000.0,
            duration_s=2.5,
        )
        assert ev.model_name == "phi3:mini"
        assert ev.duration_s == pytest.approx(2.5)

    def test_session_record_add_usage(self):
        from cohezion.platform.session_tracker import SessionRecord

        rec = SessionRecord(session_id="s1")
        rec.add_usage("phi3:mini", duration_s=5.0)
        assert len(rec.model_events) == 1
        assert rec.model_events[0].model_name == "phi3:mini"

    def test_session_record_total_duration(self):
        from cohezion.platform.session_tracker import SessionRecord

        rec = SessionRecord(session_id="s1")
        rec.add_usage("phi3:mini", duration_s=3.0)
        rec.add_usage("llama3", duration_s=7.0)
        assert rec.total_duration_s() == pytest.approx(10.0)

    def test_session_record_total_duration_empty(self):
        from cohezion.platform.session_tracker import SessionRecord

        rec = SessionRecord(session_id="s1")
        assert rec.total_duration_s() == pytest.approx(0.0)

    def test_session_tracker_record_and_get_recent(self):
        from cohezion.platform.session_tracker import SessionRecord, SessionTracker

        tracker = SessionTracker()
        rec1 = SessionRecord(session_id="sess1", started_at=time.time() - 10)
        rec2 = SessionRecord(session_id="sess2", started_at=time.time())
        tracker.record_session(rec1)
        tracker.record_session(rec2)
        recent = tracker.get_recent_sessions()
        assert recent[0].session_id == "sess2"  # newest first

    def test_session_tracker_replaces_existing(self):
        from cohezion.platform.session_tracker import SessionRecord, SessionTracker

        tracker = SessionTracker()
        rec = SessionRecord(session_id="same")
        tracker.record_session(rec)
        tracker.record_session(rec)
        assert len(tracker.get_recent_sessions()) == 1

    def test_session_tracker_get_usage_histogram(self):
        from cohezion.platform.session_tracker import SessionRecord, SessionTracker

        tracker = SessionTracker()
        rec = SessionRecord(session_id="s1")
        rec.add_usage("phi3:mini", duration_s=3600.0)  # 1 hour
        tracker.record_session(rec)
        hist = tracker.get_usage_histogram(days=7)
        assert "phi3:mini" in hist
        assert hist["phi3:mini"] == pytest.approx(1.0)  # 1 hour

    def test_session_tracker_histogram_excludes_old_events(self):
        from cohezion.platform.session_tracker import ModelUsageEvent, SessionRecord, SessionTracker

        tracker = SessionTracker()
        rec = SessionRecord(session_id="s1")
        # Add old event (30 days ago)
        old_ev = ModelUsageEvent(
            session_id="s1",
            model_name="old_model",
            started_at=time.time() - 30 * 86400,
            duration_s=3600.0,
        )
        rec.model_events.append(old_ev)
        tracker.record_session(rec)
        hist = tracker.get_usage_histogram(days=7)
        assert "old_model" not in hist

    def test_session_model_usage(self):
        from cohezion.platform.session_tracker import SessionRecord, SessionTracker

        tracker = SessionTracker()
        rec = SessionRecord(session_id="s1")
        rec.add_usage("phi3:mini", duration_s=1.0)
        tracker.record_session(rec)
        usage = tracker.session_model_usage(days=7)
        assert "phi3:mini" in usage
        assert "s1" in usage["phi3:mini"]

    def test_session_tracker_get_recent_sessions_limit(self):
        from cohezion.platform.session_tracker import SessionRecord, SessionTracker

        tracker = SessionTracker()
        for i in range(5):
            rec = SessionRecord(session_id=f"s{i}", started_at=time.time() + i)
            tracker.record_session(rec)
        assert len(tracker.get_recent_sessions(limit=3)) == 3


# ---------------------------------------------------------------------------
# Module 2: mcp/shared/client.py
# ---------------------------------------------------------------------------


class TestMcpSharedClient:
    def _make_client(self, token="test-token"):
        from cohezion.mcp.shared.client import MCPClient

        with patch("cohezion.mcp.shared.client.get_current_token", return_value=token):
            client = MCPClient(base_url="http://localhost:8370")
        return client

    def test_client_init(self):
        client = self._make_client()
        assert client.base_url == "http://localhost:8370"
        assert client._token == "test-token"

    def test_client_init_no_token(self):
        from cohezion.mcp.shared.client import MCPClient

        with patch("cohezion.mcp.shared.client.get_current_token", return_value=None):
            client = MCPClient(base_url="http://localhost:8370")
        assert client._token is None

    def _make_mock_response(self, status=200, json_data=None):
        """aiohttp response is an async context manager, not a coroutine."""
        mock_response = MagicMock()
        mock_response.status = status
        mock_response.json = AsyncMock(return_value=json_data or {})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        return mock_response

    def _make_mock_session(self):
        """aiohttp session methods (post/get) return async context managers."""
        mock_session = MagicMock()  # NOT AsyncMock — post/get return CMs, not coroutines
        mock_session.closed = False
        mock_session.close = AsyncMock()
        return mock_session

    def test_call_tool_success(self):
        client = self._make_client()
        mock_response = self._make_mock_response(200, {"result": "ok"})
        mock_session = self._make_mock_session()
        mock_session.post.return_value = mock_response

        with patch("cohezion.mcp.shared.client.aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(client.call_tool("my_tool", {"param": "value"}))
        assert result == {"result": "ok"}

    def test_call_tool_401_unauthorized(self):
        client = self._make_client()
        mock_response = self._make_mock_response(401)
        mock_session = self._make_mock_session()
        mock_session.post.return_value = mock_response

        with patch("cohezion.mcp.shared.client.aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(client.call_tool("my_tool", {}))
        assert "error" in result
        assert "Unauthorized" in result["error"]

    def test_call_tool_500_error(self):
        client = self._make_client()
        mock_response = self._make_mock_response(500, {"error": "server error"})
        mock_session = self._make_mock_session()
        mock_session.post.return_value = mock_response

        with patch("cohezion.mcp.shared.client.aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(client.call_tool("my_tool", {}))
        assert "error" in result

    def test_call_tool_exception(self):
        client = self._make_client()
        mock_session = self._make_mock_session()
        mock_session.post.side_effect = Exception("connection refused")

        with patch("cohezion.mcp.shared.client.aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(client.call_tool("my_tool", {}))
        assert "error" in result
        assert "connection refused" in result["error"]

    def test_get_health_success(self):
        client = self._make_client()
        mock_response = self._make_mock_response(200, {"status": "healthy"})
        mock_session = self._make_mock_session()
        mock_session.get.return_value = mock_response

        with patch("cohezion.mcp.shared.client.aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(client.get_health())
        assert result["status"] == "healthy"

    def test_get_health_exception(self):
        client = self._make_client()
        mock_session = self._make_mock_session()
        mock_session.get.side_effect = Exception("timeout")

        with patch("cohezion.mcp.shared.client.aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(client.get_health())
        assert "error" in result

    def test_close_session(self):
        client = self._make_client()
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        client._session = mock_session

        asyncio.run(client.close())
        mock_session.close.assert_awaited_once()

    def test_close_noop_when_no_session(self):
        client = self._make_client()
        asyncio.run(client.close())  # must not raise

    def test_get_session_uses_uds_connector(self):
        from cohezion.mcp.shared.client import MCPClient

        with patch("cohezion.mcp.shared.client.get_current_token", return_value=None):
            client = MCPClient(uds_path="/tmp/test.sock")

        mock_connector = MagicMock()
        mock_session = MagicMock()

        with (
            patch(
                "cohezion.mcp.shared.client.aiohttp.UnixConnector", return_value=mock_connector
            ) as mock_uds,
            patch("cohezion.mcp.shared.client.aiohttp.ClientSession", return_value=mock_session),
        ):
            asyncio.run(client._get_session())
        mock_uds.assert_called_once_with(path="/tmp/test.sock")


# ---------------------------------------------------------------------------
# Module 3: flume/trajectory_capture.py
# ---------------------------------------------------------------------------


class TestTrajectoryCapture:
    def _make_mock_encoder(self):
        mock_enc = MagicMock()
        mock_pt = MagicMock()
        mock_pt.state_12d.tolist.return_value = [0.0] * 12
        mock_pt.action_description = "solve"
        mock_pt.reward = 1.0
        mock_pt.domain = "test"
        mock_pt.surprise = 0.1
        mock_pt.metadata = {}
        mock_enc.encode_point.return_value = mock_pt
        return mock_enc, mock_pt

    def test_trajectory_recorder_init(self):
        from cohezion.flume.trajectory_capture import TrajectoryRecorder

        mock_enc, _ = self._make_mock_encoder()
        with patch("cohezion.flume.trajectory_capture.get_encoder", return_value=mock_enc):
            rec = TrajectoryRecorder(domain="aimo", agent_id="solver-1")
        assert rec.domain == "aimo"
        assert rec.agent_id == "solver-1"
        assert len(rec._points) == 0

    def test_trajectory_recorder_record(self):
        from cohezion.flume.trajectory_capture import TrajectoryRecorder

        mock_enc, mock_pt = self._make_mock_encoder()
        with patch("cohezion.flume.trajectory_capture.get_encoder", return_value=mock_enc):
            rec = TrajectoryRecorder(domain="aimo", agent_id="solver-1")
            pt = rec.record(state={"difficulty": 7}, action="solve", reward=1.0)
        assert pt is mock_pt
        assert len(rec.points) == 1

    def test_capture_trajectory_no_persist_when_empty(self):
        from cohezion.flume.trajectory_capture import capture_trajectory

        mock_enc, _ = self._make_mock_encoder()
        with patch("cohezion.flume.trajectory_capture.get_encoder", return_value=mock_enc):
            with patch("cohezion.flume.trajectory_capture._persist_points") as mock_persist:
                with capture_trajectory("aimo") as _rec:
                    pass  # no records
        mock_persist.assert_not_called()

    def test_capture_trajectory_persists_when_has_points(self):
        from cohezion.flume.trajectory_capture import capture_trajectory

        mock_enc, mock_pt = self._make_mock_encoder()
        with patch("cohezion.flume.trajectory_capture.get_encoder", return_value=mock_enc):
            with patch("cohezion.flume.trajectory_capture._persist_points") as mock_persist:
                with capture_trajectory("aimo") as rec:
                    rec.record({"state": 1}, "action", 1.0)
        mock_persist.assert_called_once()

    def test_persist_points_no_running_loop(self):
        from cohezion.flume.trajectory_capture import TrajectoryRecorder, _persist_points

        mock_enc, mock_pt = self._make_mock_encoder()
        with patch("cohezion.flume.trajectory_capture.get_encoder", return_value=mock_enc):
            rec = TrajectoryRecorder(domain="test", agent_id="agent")
            rec._points.append(mock_pt)

        with patch("cohezion.flume.trajectory_capture.asyncio.run") as mock_run:
            _persist_points(rec)
        mock_run.assert_called_once()

    def test_persist_points_with_running_loop(self):
        from cohezion.flume.trajectory_capture import TrajectoryRecorder, _persist_points

        mock_enc, mock_pt = self._make_mock_encoder()
        with patch("cohezion.flume.trajectory_capture.get_encoder", return_value=mock_enc):
            rec = TrajectoryRecorder(domain="test", agent_id="agent")
            rec._points.append(mock_pt)

        mock_loop = MagicMock()
        with patch(
            "cohezion.flume.trajectory_capture.asyncio.get_running_loop", return_value=mock_loop
        ):
            _persist_points(rec)
        mock_loop.create_task.assert_called_once()
