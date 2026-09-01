"""Proxy-layer tests for the admission gate (2026-09-01) — the HTTP half.

The decision core is covered in test_admission_gate.py; these prove the ASGI layer
CONSUMES it correctly (consumption, not declaration): a refusing gate turns into a 503
before any upstream contact, an allowing gate forwards body/headers/status faithfully,
and the status endpoint exposes what telemetry needs.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from cohezion.platform.admission_gate import AdmissionGate, GateConfig
from cohezion.platform.admission_proxy import build_app


def _gate(available_gb: float, resident: list[str] | None = None, enforce: bool = True):
    entries = [{"model_name": n, "checkpoint": ""} for n in (resident or [])]
    return AdmissionGate(
        config=GateConfig(floor_gb=16.0, enforce=enforce),
        read_available_gb=lambda: available_gb,
        read_resident=lambda: entries,
    )


def _upstream(recorder: list[httpx.Request]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        recorder.append(request)
        return httpx.Response(200, json={"upstream": "ok", "path": request.url.path})

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://upstream.test"
    )


class TestRefusalPath:
    def test_overbudget_load_returns_503_and_never_reaches_upstream(self) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(available_gb=10.4), client=_upstream(seen))
        with TestClient(app) as c:
            r = c.post(
                "/api/v1/chat/completions",
                json={"model": "Qwen3.6-35B-A3B-GGUF", "messages": []},
            )
        assert r.status_code == 503
        assert r.json()["error"]["type"] == "admission_refused"
        assert "floor" in r.json()["error"]["message"].lower()
        assert seen == []  # the refused request MUST NOT touch lemond

    def test_shadow_mode_forwards_but_counts(self) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(available_gb=10.4, enforce=False), client=_upstream(seen))
        with TestClient(app) as c:
            r = c.post("/api/v1/chat/completions", json={"model": "Qwen3.6-35B-A3B-GGUF"})
            assert r.status_code == 200
            status = c.get("/admission/status").json()
        assert len(seen) == 1  # forwarded in shadow mode
        assert status["counters"]["shadow_refusals"] == 1


class TestForwardPath:
    def test_no_model_request_forwards_untouched(self) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(available_gb=5.0), client=_upstream(seen))
        with TestClient(app) as c:
            r = c.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["path"] == "/api/v1/health"
        assert len(seen) == 1

    def test_resident_model_forwards_with_body_intact(self) -> None:
        seen: list[httpx.Request] = []
        app = build_app(
            _gate(available_gb=10.4, resident=["Bonsai-8B-gguf"]), client=_upstream(seen)
        )
        with TestClient(app) as c:
            r = c.post(
                "/v1/chat/completions",
                json={"model": "Bonsai-8B-gguf", "messages": [{"role": "user", "content": "x"}]},
            )
        assert r.status_code == 200
        assert b"Bonsai-8B-gguf" in seen[0].content  # body forwarded verbatim

    def test_non_json_body_is_not_gated(self) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(available_gb=5.0), client=_upstream(seen))
        with TestClient(app) as c:
            r = c.post("/api/v1/something", content=b"\x00binary")
        assert r.status_code == 200
        assert len(seen) == 1


class TestStatusEndpoint:
    def test_status_reports_config_and_counters(self) -> None:
        app = build_app(_gate(available_gb=50.0), client=_upstream([]))
        with TestClient(app) as c:
            s = c.get("/admission/status").json()
        assert s["config"]["floor_gb"] == 16.0
        assert s["config"]["enforce"] is True
        assert set(s["counters"]) == {"forwarded", "refused", "shadow_refusals"}


@pytest.mark.parametrize("method", ["GET", "DELETE"])
def test_bodyless_methods_forward(method: str) -> None:
    seen: list[httpx.Request] = []
    app = build_app(_gate(available_gb=5.0), client=_upstream(seen))
    with TestClient(app) as c:
        r = c.request(method, "/api/v1/models")
    assert r.status_code == 200
    assert len(seen) == 1


class TestStreamingBranch:
    """MockTransport materializes responses, leaving the StreamingResponse branch — the
    proxy's entire purpose for chat completions — untested (review 2026-09-01, F7).
    A genuinely-streaming ASGI upstream exercises it."""

    @staticmethod
    def _streaming_upstream() -> httpx.AsyncClient:
        async def asgi(scope, receive, send):  # a minimal chunked-SSE-ish upstream
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/event-stream")],
                }
            )
            for chunk in (b"data: one\n\n", b"data: two\n\n"):
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=asgi), base_url="http://upstream.test"
        )

    def test_streamed_upstream_body_arrives_intact(self) -> None:
        app = build_app(_gate(available_gb=50.0), client=self._streaming_upstream())
        with TestClient(app) as c:
            r = c.post("/v1/chat/completions", json={"model": "Bonsai-8B-gguf"})
        assert r.status_code == 200
        assert r.content == b"data: one\n\ndata: two\n\n"
        assert r.headers["content-type"].startswith("text/event-stream")


class TestUpstreamDown:
    def test_connect_error_returns_clean_502(self) -> None:
        def refuse(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = httpx.AsyncClient(
            transport=httpx.MockTransport(refuse), base_url="http://upstream.test"
        )
        app = build_app(_gate(available_gb=50.0), client=client)
        with TestClient(app) as c:
            r = c.get("/api/v1/health")
        assert r.status_code == 502
        assert r.json()["error"]["type"] == "upstream_unreachable"


class TestSelfProbeRegression:
    def test_default_residency_probe_targets_upstream_not_own_port(self) -> None:
        # F1 regression (review 2026-09-01): after cutover the module-default
        # LEMONADE_BASE is the proxy's OWN port — the gate's default residency probe
        # must aim at config.upstream_base or it deadlocks probing itself.
        from unittest.mock import patch

        from cohezion.platform.admission_gate import GateConfig

        cfg = GateConfig(floor_gb=16.0, upstream_base="http://127.0.0.1:13315")
        with patch("cohezion.platform.admission_gate.fetch_loaded_models", return_value=[]) as m:
            g = AdmissionGate(config=cfg, read_available_gb=lambda: 50.0)
            g.decide("Bonsai-8B-gguf")
        assert m.call_args.kwargs["base_url"] == "http://127.0.0.1:13315"


class TestControlSurfaceNotProxied:
    def test_post_to_admission_path_is_never_forwarded(self) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(available_gb=50.0), client=_upstream(seen))
        with TestClient(app) as c:
            r = c.post("/admission/status", json={"x": 1})
        assert r.status_code == 404
        assert seen == []


class TestMultipartGating:
    def test_multipart_model_field_is_gated(self) -> None:
        # MED-5 regression: transcription requests carry `model` as a form field.
        seen: list[httpx.Request] = []
        app = build_app(_gate(available_gb=10.4), client=_upstream(seen))
        with TestClient(app) as c:
            r = c.post(
                "/v1/audio/transcriptions",
                files={"file": ("a.wav", b"RIFF....", "audio/wav")},
                data={"model": "Whisper-Large-v3-Turbo"},
            )
        assert r.status_code == 503
        assert seen == []
