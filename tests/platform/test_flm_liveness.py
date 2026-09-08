"""FLM/NPU work-path liveness probe invariants.

The blind spot this closes: lemond's BackendWatchdog probes /api/tags — a metadata
endpoint that an amdxdna-wedged backend still answers. Only a bounded generation
exercises the NPU. Discriminating: a probe that merely re-checked /api/tags (or the
health endpoint) would classify every scenario below as 'alive'.
"""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest

from cohezion.core.resource_management import session_monitor
from cohezion.platform import flm_liveness
from cohezion.platform.flm_liveness import FLMProbe, probe_flm_generation


FLM_ENTRY = {
    "model_name": "llama3.2-1b-FLM",
    "checkpoint": "llama3.2:1b",
    "recipe": "flm",
    "backend_url": "http://127.0.0.1:8005/v1",
    "is_busy": False,
}


def _probe(loaded, post_fn):
    with patch("cohezion.platform.flm_liveness.fetch_loaded_models", return_value=loaded):
        return probe_flm_generation(post_fn=post_fn)


class TestProbeClassification:
    def test_successful_generation_is_alive(self):
        got = _probe([FLM_ENTRY], post_fn=lambda url, model, t: None)
        assert got.status == "alive"
        assert got.model == "llama3.2-1b-FLM"

    def test_timeout_is_wedged_not_unreachable(self):
        # THE amdxdna signature: server up (health listed it), generation hangs.
        def hang(url, model, t):
            raise TimeoutError("read timed out")

        got = _probe([FLM_ENTRY], post_fn=hang)
        assert got.status == "wedged"

    def test_url_wrapped_timeout_is_wedged(self):
        def hang(url, model, t):
            raise urllib.error.URLError(TimeoutError("timed out"))

        assert _probe([FLM_ENTRY], post_fn=hang).status == "wedged"

    def test_http_5xx_is_wedged(self):
        # A 5xx means the server ANSWERED (lemond's /api/tags watchdog stays green)
        # but the work path failed — wedge, not unreachable.
        def boom(url, model, t):
            raise urllib.error.HTTPError(url, 500, "internal", None, None)  # type: ignore[arg-type]

        assert _probe([FLM_ENTRY], post_fn=boom).status == "wedged"

    def test_http_4xx_is_probe_error_not_wedged(self):
        # rv-flm-probe M3: a 404 from the probe's own naming mismatch must never
        # raise a false NPU-wedge alarm.
        def notfound(url, model, t):
            raise urllib.error.HTTPError(url, 404, "no such model", None, None)  # type: ignore[arg-type]

        assert _probe([FLM_ENTRY], post_fn=notfound).status == "probe_error"

    def test_connection_refused_is_unreachable(self):
        def refused(url, model, t):
            raise urllib.error.URLError(ConnectionRefusedError(111, "refused"))

        assert _probe([FLM_ENTRY], post_fn=refused).status == "unreachable"

    def test_no_flm_resident(self):
        gguf_only = [{**FLM_ENTRY, "recipe": "llamacpp"}]
        assert _probe(gguf_only, post_fn=None).status == "no_flm_resident"

    def test_busy_flm_lane_is_skipped_not_probed(self):
        # Probing a busy lane would queue behind real work and misread latency.
        busy = [{**FLM_ENTRY, "is_busy": True}]
        assert _probe(busy, post_fn=None).status == "no_flm_resident"

    def test_health_down_is_unreachable(self):
        assert _probe(None, post_fn=None).status == "unreachable"


class TestRealPostBoundary:
    """rv-flm-probe H1: the injection seam left `_post_chat` — the only code that
    builds the URL and body — permanently untested. Exercise it with a stubbed
    urlopen and assert what it actually SENDS."""

    def _capture_urlopen(self, sent: dict):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"choices": [{"message": {"content": "x"}}]}'

        def fake_urlopen(req, timeout=None):
            sent["url"] = req.full_url
            sent["body"] = json.loads(req.data.decode())
            sent["timeout"] = timeout
            return _Resp()

        return fake_urlopen

    def test_post_chat_sends_checkpoint_form_to_chat_completions(self, monkeypatch):
        sent: dict = {}
        monkeypatch.setattr(flm_liveness.urllib.request, "urlopen", self._capture_urlopen(sent))
        flm_liveness._post_chat("http://127.0.0.1:8005/v1", "llama3.2:1b", 6.0)
        # FLM backends resolve the CHECKPOINT id ('llama3.2:1b'), not the router
        # model_name ('llama3.2-1b-FLM') — verified live 2026-09-01, 0.4s completion.
        assert sent["url"] == "http://127.0.0.1:8005/v1/chat/completions"
        assert sent["body"]["model"] == "llama3.2:1b"
        assert sent["body"]["max_tokens"] == 1
        assert sent["timeout"] == 6.0

    def test_post_chat_empty_choices_raises(self, monkeypatch):
        class _Empty:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"choices": []}'

        monkeypatch.setattr(
            flm_liveness.urllib.request, "urlopen", lambda req, timeout=None: _Empty()
        )
        with pytest.raises(ValueError):
            flm_liveness._post_chat("http://127.0.0.1:8005/v1", "llama3.2:1b", 6.0)

    def test_probe_passes_checkpoint_not_model_name_to_poster(self):
        # End-to-end through probe_flm_generation: the poster must receive the
        # checkpoint form. A regression swapping in model_name passes every other
        # test in this file (their post_fns ignore the argument).
        seen: dict = {}

        def capture(url, model, t):
            seen["model"] = model

        _probe([FLM_ENTRY], post_fn=capture)
        assert seen["model"] == "llama3.2:1b"


class TestGuardWiring:
    def test_probe_fires_on_cadence_and_lands_in_record(self, monkeypatch):
        monkeypatch.setattr(session_monitor, "FLM_PROBE_EVERY_N_POLLS", 5)
        state = session_monitor.GuardState()
        with patch(
            "cohezion.platform.flm_liveness.probe_flm_generation",
            return_value=FLMProbe("wedged", model="llama3.2-1b-FLM", detail="timeout"),
        ) as probe:
            rec_on = session_monitor.poll_once(10, state=state)
            rec_off = session_monitor.poll_once(11, state=state)
        assert probe.call_count == 1  # only the cadence poll probes
        assert rec_on["flm_liveness"] == "wedged"
        assert rec_on["flm_wedge_detail"] == "timeout"
        assert "flm_liveness" not in rec_off

    def test_zero_cadence_disables_probe(self, monkeypatch):
        monkeypatch.setattr(session_monitor, "FLM_PROBE_EVERY_N_POLLS", 0)
        state = session_monitor.GuardState()
        with patch("cohezion.platform.flm_liveness.probe_flm_generation") as probe:
            session_monitor.poll_once(0, state=state)
        assert probe.call_count == 0

    def test_probe_exception_never_kills_the_poll(self, monkeypatch):
        monkeypatch.setattr(session_monitor, "FLM_PROBE_EVERY_N_POLLS", 1)
        state = session_monitor.GuardState()
        with patch(
            "cohezion.platform.flm_liveness.probe_flm_generation",
            side_effect=RuntimeError("boom"),
        ):
            rec = session_monitor.poll_once(3, state=state)
        assert "available_gb" in rec  # the poll completed
