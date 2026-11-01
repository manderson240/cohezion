"""The adversarial gate documents "fail-open on a transport failure"; that only holds if the
transport failure ARRIVES.  GAIA's LemonadeClient defaults to a 900 s read timeout, so a router
that accepts the connection and never answers (wedged, or mid model-load) held each of the three
perspectives for 15 minutes.  Measured 2026-10-31: test_compound_full_cycle's success test hung
>115 s inside ``refine()`` with :13305 in that state.

Neutralise either bound (drop ``timeout=`` in skill_refiner, or ignore ``_timeout`` in the shim)
and a test below fails.
"""

from __future__ import annotations

import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.skill_refiner import (
    _ADVERSARIAL_TIMEOUT_S,
    ExecutionMetrics,
    LearningSignal,
    SkillRefiner,
)
from cohezion.inference.gaia_adapter import _GaiaLLMClientShim


def test_gate_builds_its_shim_with_a_bounded_timeout() -> None:
    shim = MagicMock()
    shim.prompt.return_value = "APPROVE"
    signal = LearningSignal(
        skill_name="s",
        operation_type="generate",
        key_insight="i",
        metric_change="m",
        recommendation="r",
        confidence=0.8,
    )
    metrics = ExecutionMetrics(
        success=True,
        duration_seconds=1.0,
        tokens_used=1,
        token_efficiency=1.0,
        quality_score=0.9,
        anomaly_score=0.1,
        cached_hits=0,
    )
    with (
        patch("cohezion.compound.local_inference.lemonade_available", return_value=True),
        patch("gaia.llm.lemonade_client.LemonadeClient", MagicMock()),
        patch("cohezion.inference.gaia_adapter._GaiaLLMClientShim", return_value=shim) as ctor,
    ):
        SkillRefiner()._adversarial_review_gate(signal, "s", metrics)
    timeout = ctor.call_args.kwargs.get("timeout")
    assert timeout == _ADVERSARIAL_TIMEOUT_S
    assert 0 < _ADVERSARIAL_TIMEOUT_S <= 120


def test_shim_forwards_timeout_to_the_client() -> None:
    client = MagicMock()
    client.chat_completions.return_value = {"choices": [{"message": {"content": "APPROVE"}}]}
    _GaiaLLMClientShim(client, "m", max_tokens=8, temperature=0.0, timeout=7.0).prompt("x")
    assert client.chat_completions.call_args.kwargs["timeout"] == 7.0
    # unset -> the client's own default is untouched (no behaviour change for other callers)
    client.reset_mock()
    _GaiaLLMClientShim(client, "m", max_tokens=8, temperature=0.0).prompt("x")
    assert "timeout" not in client.chat_completions.call_args.kwargs


@pytest.fixture
def silent_server():
    """Accepts connections and never replies: the wedged-router shape."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    held: list[socket.socket] = []
    stop = threading.Event()

    def _accept() -> None:
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                held.append(srv.accept()[0])
            except OSError:
                continue

    t = threading.Thread(target=_accept, daemon=True)
    t.start()
    yield srv.getsockname()[1]
    stop.set()
    t.join(2)
    for c in held:
        c.close()
    srv.close()


def test_silent_server_fails_within_the_bound(silent_server: int) -> None:
    from gaia.llm.lemonade_client import LemonadeClient

    client = LemonadeClient(
        base_url=f"http://127.0.0.1:{silent_server}/api/v1", model="m", verbose=False
    )
    shim = _GaiaLLMClientShim(client, "m", max_tokens=8, temperature=0.0, timeout=1.0)
    t0 = time.monotonic()
    with pytest.raises(Exception):  # noqa: B017 - transport error type is the client's business
        shim.prompt("x")
    assert time.monotonic() - t0 < 20
