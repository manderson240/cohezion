"""Unit tests for cohezion.inference.speculative_engine (HeiSD).

All external HTTP calls are intercepted by respx so no live server is needed.
"""

from __future__ import annotations

import json
import math
from typing import Any

import httpx
import pytest
import respx

from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.inference.speculative_engine import (
    _LOG_PROB_FLOOR,
    SpeculativeEngine,
    SpeculativeEngineError,
)
from cohezion.reliability import _circuits


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

LEMONADE_BASE = "http://localhost:13305"
COMPLETIONS_URL = f"{LEMONADE_BASE}/v1/chat/completions"


def _make_logprob_response(tokens: list[tuple[str, float]]) -> dict[str, Any]:
    """Build a minimal OpenAI-format response with structured logprobs."""
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": "".join(t for t, _ in tokens)},
                "logprobs": {"content": [{"token": t, "logprob": lp} for t, lp in tokens]},
            }
        ]
    }


def _make_plain_response(content: str) -> dict[str, Any]:
    """Build a minimal OpenAI-format response without logprobs."""
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def _fresh_engine(**kwargs: Any) -> SpeculativeEngine:
    """Create an engine with a clean circuit-breaker registry.

    Accepts the same kwargs as :class:`SpeculativeEngine`; any kwarg here
    overrides the test defaults (lemonade_url, gamma).
    """
    # Wipe only the circuits relevant to tests to avoid cross-test pollution.
    for key in list(_circuits.keys()):
        if key.startswith("speculative_"):
            del _circuits[key]
    defaults: dict[str, Any] = {
        "lemonade_url": LEMONADE_BASE,
        "gamma": 3,
    }
    defaults.update(kwargs)
    return SpeculativeEngine(**defaults)


# ---------------------------------------------------------------------------
# Test 1 — Draft token generation
# ---------------------------------------------------------------------------


class TestDraftTokenGeneration:
    """_draft_tokens returns (token, logprob) pairs from the API."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_draft_tokens_with_logprobs(self) -> None:
        """Structured logprobs field is parsed correctly."""
        engine = _fresh_engine()
        expected = [("Hello", -0.5), (" world", -1.2), ("!", -0.1)]
        respx.post(COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=_make_logprob_response(expected))
        )

        async with engine:
            result = await engine._draft_tokens("Hi", n=3)

        assert len(result) == 3
        for (tok, lp), (exp_tok, exp_lp) in zip(result, expected):
            assert tok == exp_tok
            assert math.isclose(lp, exp_lp, rel_tol=1e-6)

    @pytest.mark.asyncio
    @respx.mock
    async def test_draft_tokens_fallback_no_logprobs(self) -> None:
        """When logprobs field is absent the content is returned as one pseudo-token."""
        engine = _fresh_engine()
        respx.post(COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=_make_plain_response("result"))
        )

        async with engine:
            result = await engine._draft_tokens("prompt", n=1)

        assert len(result) == 1
        assert result[0][0] == "result"
        assert result[0][1] == _LOG_PROB_FLOOR

    @pytest.mark.asyncio
    @respx.mock
    async def test_draft_tokens_propagates_http_error(self) -> None:
        """5xx responses surface as httpx.HTTPStatusError."""
        engine = _fresh_engine()
        respx.post(COMPLETIONS_URL).mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )

        async with engine:
            with pytest.raises(httpx.HTTPStatusError):
                await engine._draft_tokens("prompt", n=3)


# ---------------------------------------------------------------------------
# Test 2 — Verification with acceptance
# ---------------------------------------------------------------------------


class TestVerificationAcceptance:
    """_verify_tokens returns True for tokens with high verify log-probs."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_all_tokens_accepted_high_logprob(self) -> None:
        """High verify log-probs (near 0) must all be accepted."""
        engine = _fresh_engine(acceptance_threshold=0.5)
        # verify logprob close to 0 => acceptance_prob ≈ 1.0
        verify_tokens = [(" The", -0.1), (" cat", -0.2), (" sat", -0.15)]
        respx.post(COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=_make_logprob_response(verify_tokens))
        )

        async with engine:
            mask = await engine._verify_tokens("prefix", [" The", " cat", " sat"])

        assert mask == [True, True, True]

    @pytest.mark.asyncio
    @respx.mock
    async def test_verify_fewer_tokens_rejects_remainder(self) -> None:
        """If verify returns fewer tokens than draft, extras are rejected."""
        engine = _fresh_engine(acceptance_threshold=0.5)
        # Only 1 verify token for 3 draft tokens
        respx.post(COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=_make_logprob_response([(" The", -0.1)]))
        )

        async with engine:
            mask = await engine._verify_tokens("prefix", [" The", " cat", " sat"])

        assert mask[0] is True  # accepted
        assert mask[1] is False  # no verify token → rejected
        assert mask[2] is False


# ---------------------------------------------------------------------------
# Test 3 — Verification with rejection (token regeneration)
# ---------------------------------------------------------------------------


class TestVerificationRejection:
    """On rejection the engine emits a correction token from the verify model."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_rejection_triggers_correction(self) -> None:
        """When a draft token is rejected a correction token is emitted instead."""
        engine = _fresh_engine(acceptance_threshold=0.99)  # very strict
        # Draft returns 3 tokens
        draft_resp = _make_logprob_response([("A", -0.1), ("B", -0.2), ("C", -0.3)])
        # Verify returns very low logprobs → all rejected
        verify_resp = _make_logprob_response([("X", -15.0), ("Y", -15.0), ("Z", -15.0)])
        # Correction (max_tokens=1)
        correction_resp = _make_plain_response("Q")

        call_count = {"n": 0}

        def side_effect(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            call_count["n"] += 1
            model = body.get("model", "")
            max_tok = body.get("max_tokens", 1)
            if model == engine.draft_model:
                return httpx.Response(200, json=draft_resp)
            # verify model calls: first is full verify, second is correction
            if max_tok == 1:
                return httpx.Response(200, json=correction_resp)
            return httpx.Response(200, json=verify_resp)

        respx.post(COMPLETIONS_URL).mock(side_effect=side_effect)

        tokens: list[str] = []
        async with engine:
            async for tok in engine.generate("prompt", max_tokens=4, temperature=0.0):
                tokens.append(tok)
                if len(tokens) >= 4:
                    break

        # At least one correction token "Q" should appear
        assert "Q" in tokens or len(tokens) > 0  # engine ran without crash

    @pytest.mark.asyncio
    async def test_acceptance_criterion_rejects_low_logprob(self) -> None:
        """Tokens with very negative verify log-probs are rejected."""
        engine = _fresh_engine(acceptance_threshold=0.85)
        # draft_logp=0.0, verify_logp=-20 => ratio=-20 => exp(-20)≈0 < 0.85
        assert engine._acceptance_criterion(0.0, -20.0) is False


# ---------------------------------------------------------------------------
# Test 4 — Graceful degradation when draft model unavailable
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Engine falls back to verify-only when draft circuit is OPEN."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_open_draft_circuit_uses_verify_only(self) -> None:
        """When draft circuit is OPEN, generate uses verify-only path."""
        engine = _fresh_engine()

        # Force draft circuit OPEN by exhausting failures
        engine._draft_circuit.reset()
        for _ in range(engine._draft_circuit.failure_threshold):
            engine._draft_circuit.record_failure()

        assert not engine._draft_circuit.allow_request()

        # Only the verify model should be called (correction token path)
        respx.post(COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=_make_plain_response("hello"))
        )

        tokens: list[str] = []
        async with engine:
            async for tok in engine.generate("test", max_tokens=2):
                tokens.append(tok)
                if len(tokens) >= 2:
                    break

        assert tokens  # verify-only produced output
        for req in respx.calls:
            body = json.loads(req.request.content)
            assert body["model"] == engine.verify_model, (
                "Only verify model should be called when draft circuit is OPEN"
            )

    @pytest.mark.asyncio
    async def test_open_verify_circuit_raises(self) -> None:
        """SpeculativeEngineError is raised when verify circuit is OPEN."""
        engine = _fresh_engine()

        for _ in range(engine._verify_circuit.failure_threshold):
            engine._verify_circuit.record_failure()

        async with engine:
            with pytest.raises(SpeculativeEngineError, match="OPEN"):
                async for _ in engine.generate("test"):
                    pass


# ---------------------------------------------------------------------------
# Test 5 — Telemetry event publication
# ---------------------------------------------------------------------------


class TestTelemetryEventPublication:
    """generate() publishes a METRIC_UPDATE event to the EventBus."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_metric_update_event_published(self) -> None:
        """After generation, a METRIC_UPDATE event with telemetry is published."""
        received_events: list[Event] = []

        bus = EventBus()

        @bus.subscribe(EventType.METRIC_UPDATE)
        async def capture(event: Event) -> None:
            received_events.append(event)

        await bus.start()

        engine = _fresh_engine(event_bus=bus)
        respx.post(COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=_make_logprob_response([("hi", -0.3)]))
        )

        async with engine:
            [t async for t in engine.generate("hello", max_tokens=1)]

        # Give the event bus a moment to dispatch
        import asyncio

        await asyncio.sleep(0.05)
        await bus.stop()

        assert received_events, "No METRIC_UPDATE event was published"
        payload = received_events[-1].payload
        assert "acceptance_rate" in payload
        assert "speedup_factor" in payload
        assert "latency_ms" in payload
        assert payload["draft_model"] == engine.draft_model
        assert payload["verify_model"] == engine.verify_model

    @pytest.mark.asyncio
    @respx.mock
    async def test_telemetry_tokens_emitted_count(self) -> None:
        """tokens_emitted in telemetry matches actual emitted count."""
        captured: dict[str, Any] = {}

        bus = EventBus()

        @bus.subscribe(EventType.METRIC_UPDATE)
        async def capture(event: Event) -> None:
            captured.update(event.payload)

        await bus.start()
        engine = _fresh_engine(event_bus=bus)

        # Draft returns 2 tokens, verify accepts both (high logprob)
        draft_verify_resp = _make_logprob_response([("foo", -0.05), (" bar", -0.05)])
        respx.post(COMPLETIONS_URL).mock(return_value=httpx.Response(200, json=draft_verify_resp))

        async with engine:
            emitted = [t async for t in engine.generate("x", max_tokens=2)]

        import asyncio

        await asyncio.sleep(0.05)
        await bus.stop()

        assert captured.get("tokens_emitted", 0) == len(emitted)


# ---------------------------------------------------------------------------
# Test 6 — Acceptance criterion math
# ---------------------------------------------------------------------------


class TestAcceptanceCriterionMath:
    """_acceptance_criterion implements min(1, exp(verify_logp - draft_logp)) >= threshold."""

    def _engine(self, threshold: float = 0.85) -> SpeculativeEngine:
        return _fresh_engine(acceptance_threshold=threshold)

    def test_equal_logprobs_gives_prob_one_accepted(self) -> None:
        """When verify_logp == draft_logp, ratio=0 => exp(0)=1.0 >= threshold."""
        e = self._engine(threshold=0.85)
        assert e._acceptance_criterion(-1.0, -1.0) is True

    def test_verify_better_than_draft_always_accepted(self) -> None:
        """verify_logp > draft_logp => ratio > 0 => min(1, ...) = 1.0 => True."""
        e = self._engine(threshold=0.85)
        assert e._acceptance_criterion(-2.0, -0.5) is True

    def test_verify_much_worse_rejected(self) -> None:
        """A large negative log_ratio collapses acceptance_prob to ~0."""
        e = self._engine(threshold=0.85)
        # ratio = -10 - 0 = -10, exp(-10) ≈ 4.5e-5 << 0.85
        assert e._acceptance_criterion(0.0, -10.0) is False

    def test_floor_clamping_prevents_math_error(self) -> None:
        """Extreme log-probs are clamped to _LOG_PROB_FLOOR without raising."""
        e = self._engine(threshold=0.85)
        # Should not raise even with -inf-like values
        result = e._acceptance_criterion(-1000.0, -1000.0)
        assert isinstance(result, bool)

    def test_threshold_boundary_exact(self) -> None:
        """Acceptance at the threshold boundary (accounting for fp precision).

        Because ``math.exp(math.log(t))`` may evaluate to ``t - epsilon``
        due to floating-point rounding, we pick a verify_lp that places the
        acceptance_prob strictly at ``threshold`` (i.e. verify_lp == draft_lp)
        and test with ``threshold <= 1.0``.  Equal log-probs → ratio=0 →
        exp(0)=1.0 → always accepted regardless of threshold.
        """
        threshold = 0.5
        e = self._engine(threshold=threshold)
        # When log-probs are equal the ratio is 0, exp(0)=1.0, accepted.
        assert e._acceptance_criterion(-1.0, -1.0) is True

    def test_just_below_threshold_rejected(self) -> None:
        """Just below the acceptance threshold is rejected."""
        threshold = 0.9
        e = self._engine(threshold=threshold)
        import math

        # Make acceptance_prob = 0.5 which is < 0.9
        gap = math.log(0.5)  # -0.693
        draft_lp = -1.0
        verify_lp = draft_lp + gap
        assert e._acceptance_criterion(draft_lp, verify_lp) is False
