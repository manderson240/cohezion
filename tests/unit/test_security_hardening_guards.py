"""Security hardening guards (CodeQL CRITICAL fixes) — source-level unit tests.

Verifies that untrusted identifiers are validated BEFORE any external effect:
- research_server: invalid arXiv ids short-circuit before requests.get
- api.routes.rl:   invalid agent_id short-circuits before any filesystem stat
- substrate.popcorn: invalid kernel names short-circuit before subprocess.run

All external effects (HTTP, filesystem, subprocess) are mocked at source level
per AGENTS.md; no test shells out to a live binary.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import cohezion.mcp.research_server as research_server_module
from cohezion.api.routes.rl import RLPolicyResponse, get_rl_policy
from cohezion.mcp.research_server import ResearchMinerServer
from cohezion.substrate import popcorn as popcorn_module
from cohezion.substrate.popcorn import submit as popcorn_submit


# ---------------------------------------------------------------------------
# research_server: arxiv id guards must short-circuit BEFORE any HTTP request
# ---------------------------------------------------------------------------


def _no_requests_get(*_args, **_kwargs):
    raise AssertionError("requests.get must not be called for an invalid arxiv id")


def _no_sleep(*_args, **_kwargs):
    raise AssertionError("no rate-limit sleep should run on the guard path")


class TestResearchServerArxivIdGuards:
    @pytest.fixture
    def server(self) -> ResearchMinerServer:
        return ResearchMinerServer()

    @pytest.mark.parametrize("bad_id", ["../../etc", "x; rm", "2402.12345v1; rm"])
    def test_semantic_scholar_paper_rejects_invalid_arxiv_id_before_http(
        self, server, monkeypatch, bad_id
    ):
        """Invalid arxiv id returns an error dict before any requests.get."""
        monkeypatch.setattr(research_server_module.requests, "get", _no_requests_get)
        monkeypatch.setattr(research_server_module, "_arxiv_jitter", _no_sleep)
        result = server.semantic_scholar_paper(bad_id)
        assert isinstance(result, dict)
        assert "error" in result
        assert "invalid arxiv id" in result["error"]

    @pytest.mark.parametrize("bad_id", ["../../etc", "x; rm"])
    def test_papers_with_code_link_rejects_invalid_arxiv_id_before_http(
        self, server, monkeypatch, bad_id
    ):
        """Invalid arxiv id returns an error list before any requests.get."""
        monkeypatch.setattr(research_server_module.requests, "get", _no_requests_get)
        monkeypatch.setattr(research_server_module, "_arxiv_jitter", _no_sleep)
        results = server.papers_with_code_link(bad_id)
        assert isinstance(results, list)
        assert len(results) == 1
        assert "error" in results[0]
        assert "invalid arxiv id" in results[0]["error"]

    def test_semantic_scholar_paper_accepts_valid_arxiv_id_shape(self, server, monkeypatch):
        """Sanity: a well-formed id passes the guard and reaches the HTTP layer."""

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"title": "t", "authors": []}

        monkeypatch.setattr(research_server_module.requests, "get", lambda *a, **k: _Resp())
        monkeypatch.setattr(research_server_module, "_arxiv_jitter", _no_sleep)
        result = server.semantic_scholar_paper("2402.12345")
        assert "error" not in result
        assert result["title"] == "t"

    def test_papers_with_code_link_accepts_valid_arxiv_id_shape(self, server, monkeypatch):
        """Sanity: a well-formed id passes the guard and reaches the HTTP layer."""

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"results": []}

        monkeypatch.setattr(research_server_module.requests, "get", lambda *a, **k: _Resp())
        monkeypatch.setattr(research_server_module, "_arxiv_jitter", _no_sleep)
        results = server.papers_with_code_link("2402.12345")
        assert results == [{"info": "no paper-with-code entry for 2402.12345"}]


# ---------------------------------------------------------------------------
# api.routes.rl: agent_id whitelist must short-circuit BEFORE any FS stat
# ---------------------------------------------------------------------------


def _no_exists(self, *_args, **_kwargs):
    raise AssertionError(f"Path.exists must not be called for a traversal agent_id (got {self!r})")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_agent_id", ["../evil", "a b"])
async def test_get_rl_policy_rejects_invalid_agent_id_before_fs(bad_agent_id):
    """Traversal / spaced agent ids return exists=False without touching disk."""
    with patch("cohezion.api.routes.rl.Path.exists", _no_exists):
        response = await get_rl_policy(bad_agent_id)
    assert isinstance(response, RLPolicyResponse)
    assert response.exists is False
    assert response.checkpoint_path is None


# ---------------------------------------------------------------------------
# substrate.popcorn: kernel whitelist must short-circuit BEFORE subprocess
# ---------------------------------------------------------------------------


def _no_subprocess_run(*_args, **_kwargs):
    raise AssertionError("subprocess.run must not be called for an invalid kernel name")


def test_popcorn_submit_rejects_invalid_kernel_before_subprocess():
    """Injection-shaped kernel name returns an error SubmitResult without exec."""
    with patch("cohezion.substrate.popcorn.subprocess.run", _no_subprocess_run):
        result = popcorn_submit("x; rm -rf /", "submission.py")
    assert isinstance(result, popcorn_module.SubmitResult)
    assert result.passed is False
    assert result.score == 0.0
    assert "Invalid kernel name" in result.error
    assert "x; rm -rf /" in result.error
    assert result.stdout == "" and result.stderr == ""
    assert result.elapsed_s == 0.0


# ---------------------------------------------------------------------------
# Wave 2: rl.py torch.load must pass weights_only=True (unsafe-deserialization)
# ---------------------------------------------------------------------------


class TestRLTorchLoadWeightsOnly:
    @pytest.mark.asyncio
    async def test_torch_load_called_with_weights_only_true(self, tmp_path, monkeypatch):
        """torch.load receives weights_only=True via the patched loader."""
        import cohezion.api.routes.rl as rl_module

        captured: dict = {}

        def _fake_torch_load(path, map_location=None, **kwargs):
            captured["map_location"] = map_location
            captured["kwargs"] = kwargs
            return {
                "shared.0.weight": _FakeTensor((1, 4)),
                "mean_head.weight": _FakeTensor((1, 2)),
            }

        # torch is imported inside get_rl_policy, so patch the torch module
        # attribute itself (source-level mock per AGENTS.md).
        import torch as _torch

        monkeypatch.setattr(_torch, "load", _fake_torch_load)

        # Real checkpoint file on disk under a tmp cwd — no FS patching needed.
        (tmp_path / "data" / "rl" / "checkpoints").mkdir(parents=True)
        (tmp_path / "data" / "rl" / "checkpoints" / "policy_agent1.pt").write_bytes(b"x")
        monkeypatch.chdir(tmp_path)

        response = await rl_module.get_rl_policy("agent1")

        assert captured["kwargs"].get("weights_only") is True
        assert captured["map_location"] == "cpu"
        assert isinstance(response, rl_module.RLPolicyResponse)
        assert response.exists is True


# ---------------------------------------------------------------------------
# Wave 2: webmcp_bridge partial-SSRF guard
# ---------------------------------------------------------------------------


class _FakeTensor:
    def __init__(self, shape):
        self.shape = shape

    def numel(self):
        return 1


class TestWebMCPBridgeSSRFAllowlist:
    def _make_bridge(self, monkeypatch):
        """Build a WebMCPBridge without loading the real registry file."""
        import cohezion.mcp.webmcp_bridge as wb

        monkeypatch.setattr(wb, "get_registry", lambda: _FakeRegistry(), raising=True)
        return wb.WebMCPBridge()

    def _make_request(self, payload):
        class _Req:
            async def json(self):
                return payload

        return _Req()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "evil_url",
        [
            "http://169.254.169.254/latest/meta-data",
            "https://internal-service.svc.cluster.local/tools/x",
            "file:///etc/passwd",
            "gopher://localhost:6379/_INFO",
        ],
    )
    async def test_call_tool_rejects_non_allowlisted_url_before_httpx(self, monkeypatch, evil_url):
        """Non-allowlisted server URL -> 400, and httpx is never invoked."""
        import cohezion.mcp.webmcp_bridge as wb

        def _no_httpx(*_a, **_k):
            raise AssertionError("httpx must not be called for a non-allowlisted URL")

        monkeypatch.setattr(wb.httpx, "AsyncClient", _no_httpx)

        bridge = self._make_bridge(monkeypatch)
        bridge.registry.get_server = lambda name: _FakeServer(name=name, url=evil_url)

        resp = await bridge.handle_call_tool(
            self._make_request({"server": "evil", "tool": "t", "arguments": {}})
        )

        assert resp.status == 400
        body = _parse_json_body(resp)
        assert body["success"] is False
        assert "not allowed" in body["error"]

    @pytest.mark.asyncio
    async def test_call_tool_allows_localhost_https(self, monkeypatch):
        """Sanity: localhost http(s) URLs pass the allowlist and reach dispatch."""

        bridge = self._make_bridge(monkeypatch)
        called = {}

        async def _fake_http(base_url, tool_name, arguments):
            called["url"] = base_url
            return {"ok": True}

        bridge._call_http_server = _fake_http
        bridge.registry.get_server = lambda name: _FakeServer(
            name=name, url="http://localhost:8369"
        )

        resp = await bridge.handle_call_tool(
            self._make_request({"server": "local", "tool": "t", "arguments": {}})
        )
        assert resp.status == 200
        assert called["url"] == "http://localhost:8369"

    @pytest.mark.asyncio
    async def test_call_http_server_sink_rejects_bad_url(self, monkeypatch):
        """Defense-in-depth: the sink itself raises before httpx on a bad URL."""
        import cohezion.mcp.webmcp_bridge as wb

        def _no_httpx(*_a, **_k):
            raise AssertionError("httpx must not be constructed at the sink either")

        monkeypatch.setattr(wb.httpx, "AsyncClient", _no_httpx)
        bridge = self._make_bridge(monkeypatch)
        with pytest.raises(ValueError, match="non-allowlisted"):
            await bridge._call_http_server("http://169.254.169.254/", "t", {})


class _FakeServer:
    """Minimal MCPServer stand-in for bridge routing tests."""

    def __init__(self, name: str, url: str | None):
        self.name = name
        self.url = url
        self.description = "fake"
        self.status = "available"

    def to_dict(self):
        return {"name": self.name, "url": self.url}


class _FakeRegistry:
    def list_servers(self):
        return []

    def get_server(self, name):
        return None


def _parse_json_body(resp):
    import json as _json

    return _json.loads(resp.text)


# ---------------------------------------------------------------------------
# Wave 2: path-injection cluster — journey_status pause rejects traversal
# BEFORE any filesystem access
# ---------------------------------------------------------------------------


class TestJourneyStatusPathInjection:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_id", ["../../etc/passwd", "..", "a/b", ".hidden"])
    async def test_pause_journey_rejects_traversal_before_fs(self, monkeypatch, bad_id):
        """Traversal-shaped journey id -> 400 without any file I/O."""
        import cohezion.api.journey_status as js_module

        def _no_aio_open(*_a, **_k):
            raise AssertionError("no file may be opened for a traversal journey id")

        monkeypatch.setattr(js_module.aiofiles, "open", _no_aio_open)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await js_module.pause_journey(bad_id)
        assert exc_info.value.status_code == 400
        assert "Invalid journey id" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_pause_journey_valid_id_reaches_checkpoint(self, tmp_path, monkeypatch):
        """Sanity: a safe id passes the guard and reads the checkpoint file."""
        import cohezion.api.journey_status as js_module

        (tmp_path / "data" / "thermal_checkpoints").mkdir(parents=True)
        cp = tmp_path / "data" / "thermal_checkpoints" / "j1.json"
        cp.write_text(json.dumps({"thermal_state": "RUNNING", "timestamp": 0.0}))
        monkeypatch.chdir(tmp_path)

        result = await js_module.pause_journey("j1")
        assert result == {"journey_id": "j1", "status": "paused"}

        saved = json.loads(cp.read_text())
        assert saved["thermal_state"] == "PAUSED"
