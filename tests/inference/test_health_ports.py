"""FT4: fleet health must probe the OmniRouter, not the dead per-device ports.

Measured 2026-08-12 before the fix — `check_fleet()` against a healthy box:

    npu down / igpu_rocwmma down / igpu_unified down / cpu down / ollama up

All four LOCAL lanes reported DOWN because they were probed at :13306-:13309,
which have no listener (invariant N1). This is not cosmetic: `fleet.route()`
skips any local candidate whose lane is not UP —

    if lane_key in health.lanes and health.lanes[lane_key].status != LaneStatus.UP:
        attempts.append(f"{candidate.model_id}(lane-down)")
        continue

— so every local model was being skipped and routing fell through toward Ollama
and cloud. That inverts the Quarter-on-a-String local-first protocol and spends
real money for work the NPU/iGPU could do at $0.

Lemonade's OmniRouter (:13305) serves ALL devices on demand, so a local lane is
up exactly when the router is reachable. Device occupancy is a separate signal
(`LemonadeHealth.devices`, FT1) and must not be confused with lane availability:
a device with no resident model is still available, because lemonade loads on
demand.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from cohezion.inference.health import LaneStatus, check_fleet


LOCAL_LANES = ("npu", "igpu_rocwmma", "igpu_unified", "cpu")
DEAD_PORTS = (13306, 13307, 13308, 13309)


class _Resp:
    def __init__(self, code: int, payload: dict | None = None):
        self.status_code = code
        self._payload = payload or {"data": [{"id": "llama3.2-1b-FLM"}]}

    def json(self) -> dict:
        return self._payload


@pytest.fixture(autouse=True)
def _clear_health_cache():
    """check_fleet() is single-flight cached for 30 s — reset between tests."""
    import cohezion.inference.health as mod

    mod._LAST_CHECK_AT = 0.0
    mod._LAST_RESULT = None
    yield
    mod._LAST_CHECK_AT = 0.0
    mod._LAST_RESULT = None


class TestLocalLanesUseOmniRouter:
    """FT4 — local lane health derives from :13305 only."""

    def test_local_lanes_up_when_only_omnirouter_answers(self, monkeypatch):
        """DISCRIMINATING: dead-port impl reports all four DOWN here.

        Only :13305 answers; every other port raises ConnectError, exactly as on
        the real box.
        """
        import httpx

        import cohezion.inference.health as mod

        def _fake_get(url: str, *_a, **_k):
            if "13305" in url:
                return _Resp(200)
            raise httpx.ConnectError(f"no listener: {url}")

        monkeypatch.setattr(mod.httpx, "get", _fake_get)

        health = check_fleet(force=True)
        for lane in LOCAL_LANES:
            assert health.lanes[lane].status == LaneStatus.UP, (
                f"{lane} reported {health.lanes[lane].status} though the OmniRouter is up"
            )
        assert health.any_local_up is True
        assert health.local_lanes_up == 4

    def test_local_lanes_down_when_omnirouter_is_down(self, monkeypatch):
        """Inverse: a genuinely dead router must still report DOWN (no fake-up)."""
        import httpx

        import cohezion.inference.health as mod

        def _fake_get(url: str, *_a, **_k):
            raise httpx.ConnectError(f"no listener: {url}")

        monkeypatch.setattr(mod.httpx, "get", _fake_get)

        health = check_fleet(force=True)
        for lane in LOCAL_LANES:
            assert health.lanes[lane].status == LaneStatus.DOWN
        assert health.any_local_up is False


class TestNoDeadPortsInHealthModule:
    """FT4b — the dead-port literals must not reappear."""

    def test_no_dead_port_literals_in_executable_code(self):
        import cohezion.inference.health as mod

        tree = ast.parse(Path(mod.__file__).read_text())
        docstring_ids = {
            id(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        }
        bad_ints = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, int)
        } & set(DEAD_PORTS)
        bad_strs = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
            and any(str(p) in node.value for p in DEAD_PORTS)
        ]
        assert not bad_ints, f"N1: dead port int literal(s) {sorted(bad_ints)}"
        assert not bad_strs, f"N1: dead port in string literal(s) {bad_strs}"

    def test_module_docstring_does_not_advertise_dead_ports(self):
        """The docstring is the thing that taught readers the wrong topology."""
        import cohezion.inference.health as mod

        doc = mod.__doc__ or ""
        for port in DEAD_PORTS:
            assert str(port) not in doc, (
                f":{port} is offline under N1 — the module docstring must not list it"
            )
