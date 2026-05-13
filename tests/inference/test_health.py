"""Fleet health probe tests — all HTTP calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from cohezion.inference.health import (
    FleetHealth,
    LaneHealth,
    LaneStatus,
    check_fleet,
    format_fleet_summary,
)


def _mock_response(status_code: int, json_payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_payload
    return resp


@pytest.fixture(autouse=True)
def clear_cache():
    """Force fresh check_fleet every test."""
    import cohezion.inference.health as mod

    mod._LAST_CHECK_AT = 0.0
    mod._LAST_RESULT = None
    yield


def test_check_fleet_all_down_returns_down_status():
    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        health = check_fleet(force=True)
    assert health.local_lanes_up == 0
    assert health.any_local_up is False
    for lane_name in ("npu", "igpu_rocwmma", "igpu_unified", "cpu", "ollama"):
        assert health.lanes[lane_name].status == LaneStatus.DOWN


def test_check_fleet_npu_up_marks_lane():
    def fake_get(url, **kwargs):
        if "13306" in url:
            return _mock_response(200, {"data": [{"id": "Gemma-4-E2B-it-GGUF"}]})
        raise httpx.ConnectError("refused")

    with patch("httpx.get", side_effect=fake_get):
        health = check_fleet(force=True)

    assert health.lanes["npu"].status == LaneStatus.UP
    assert "Gemma-4-E2B-it-GGUF" in health.lanes["npu"].models_available
    assert health.local_lanes_up == 1


def test_check_fleet_caches_between_calls():
    with patch("httpx.get", side_effect=httpx.ConnectError("refused")) as mock_get:
        check_fleet(force=True)
        first_call_count = mock_get.call_count
        check_fleet()  # no force
        assert mock_get.call_count == first_call_count, "should be cached"


def test_ollama_probe_uses_api_tags_not_v1_models():
    def fake_get(url, **kwargs):
        if "11434/api/tags" in url:
            return _mock_response(200, {"models": [{"name": "phi4:latest"}]})
        raise httpx.ConnectError("refused")

    with patch("httpx.get", side_effect=fake_get):
        health = check_fleet(force=True)

    assert health.lanes["ollama"].status == LaneStatus.UP
    assert "phi4:latest" in health.lanes["ollama"].models_available


def test_claude_and_gemini_probes_check_cli_presence():
    """All Anthropic/Gemini calls are headless CLI — probes check binary, not env var."""
    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        # shutil.which returns None → CLI not on PATH → DOWN
        with patch("shutil.which", return_value=None):
            health = check_fleet(force=True)
        assert health.lanes["claude"].status == LaneStatus.DOWN
        assert health.lanes["gemini"].status == LaneStatus.DOWN

    # shutil.which returns a path AND subprocess returns 0 → UP
    class FakeCompleted:
        returncode = 0
        stdout = "2.1.114 (Claude Code)"
        stderr = ""

    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with patch("subprocess.run", return_value=FakeCompleted()):
                health = check_fleet(force=True)
        assert health.lanes["claude"].status == LaneStatus.UP
        assert health.lanes["gemini"].status == LaneStatus.UP


def test_claude_probe_uses_live_dispatch_not_version_flag():
    """Regression: claude probe must exercise `-p ping --max-tokens 1` so a green
    probe proves auth + network + model route, not just binary presence.
    See adversarial review Edge-case #14 (ROADMAP P0)."""

    class FakeCompleted:
        returncode = 0
        stdout = "pong"
        stderr = ""

    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with patch("subprocess.run", return_value=FakeCompleted()) as mock_run:
                check_fleet(force=True)

    claude_calls = [call for call in mock_run.call_args_list if "/usr/local/bin/claude" in call.args[0]]
    assert claude_calls, "claude probe did not shell out"
    argv = claude_calls[0].args[0]
    # Must be a live -p dispatch with budget cap, not --version.
    assert argv[1] == "-p", f"claude probe must use -p (live dispatch), got argv={argv!r}"
    assert "--max-budget-usd" in argv, f"claude probe must cap spend with --max-budget-usd, got argv={argv!r}"
    assert "--version" not in argv, f"claude probe must not fall back to --version (too weak), got argv={argv!r}"


def test_format_fleet_summary_renders_all_lanes():
    health = FleetHealth(
        checked_at=0.0,
        lanes={
            "npu": LaneHealth(
                lane="npu",
                endpoint="http://localhost:13306",
                status=LaneStatus.UP,
                latency_ms=12.3,
                models_available=["Gemma-4-E2B-it-GGUF"],
            ),
            "cpu": LaneHealth(
                lane="cpu",
                endpoint="http://localhost:13309",
                status=LaneStatus.DOWN,
                detail="refused",
            ),
        },
    )
    out = format_fleet_summary(health)
    assert "npu" in out
    assert "cpu" in out
    assert "✓" in out  # up icon
    assert "✗" in out  # down icon
