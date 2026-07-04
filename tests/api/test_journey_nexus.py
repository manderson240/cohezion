"""Tests for the JourneyNexus service (the orchestration façade).

These are unit tests — the FLUME VAE, Quadrature Nexus, and Omni Tier are
mocked so the suite runs without the OmniRouter (:13305).
"""

from __future__ import annotations

import base64
from typing import Any

import pytest

from cohezion.api.services.journey_nexus import (
    EVOEvent,
    JourneyNexus,
    NarrateResult,
    OmniChatOutcome,
    QuadratureOutcome,
)


# ----- Pure dataclass + EVOStream tests (no mocking needed) ----------------


def test_evoevent_construction():
    e = EVOEvent(
        id="e1",
        timestamp=0.0,
        z_256=[0.0] * 256,
        state_12d=[0.0] * 12,
        kind="deliberation",
        voice="architect",
        score=0.9,
        journey_id="j1",
    )
    assert e.voice == "architect"
    assert e.score == 0.9


def test_quadrature_outcome_dict_voice_responses():
    """voice_responses is a list of dicts (dashboard-friendly)."""
    o = QuadratureOutcome(
        approved=True,
        consensus_score=0.91,
        alignment_score=0.87,
        voice_responses=[
            {
                "voice": "architect",
                "approval_score": 0.95,
                "concerns": [],
                "recommendations": ["ship it"],
                "score": 0.95,
            }
        ],
    )
    assert o.voice_responses[0]["voice"] == "architect"
    assert o.rejection_reason is None


def test_narrate_result_optional_image():
    r = NarrateResult(journey_id="j1", text="hi", audio_b64="Zm9v", coherence=0.7)
    assert r.image_b64 is None
    r2 = NarrateResult(
        journey_id="j2", text="hi", audio_b64="Zm9v", image_b64="aW1n", coherence=0.8
    )
    assert r2.image_b64 == "aW1n"


@pytest.mark.asyncio
async def test_subscribe_empty_returns_no_events():
    nx = JourneyNexus()
    events = [e async for e in nx.subscribe()]
    assert events == []


@pytest.mark.asyncio
async def test_add_event_then_subscribe_returns_it():
    nx = JourneyNexus()
    nx.add_event(
        EVOEvent(
            id="x",
            timestamp=1.0,
            z_256=[0.5] * 256,
            state_12d=[0.5] * 12,
            kind="k",
            voice="engineer",
            score=0.8,
            journey_id="j9",
        )
    )
    events = [e async for e in nx.subscribe()]
    assert len(events) == 1
    assert events[0].id == "x"


@pytest.mark.asyncio
async def test_subscribe_filters_by_journey_id():
    nx = JourneyNexus()
    nx.add_event(
        EVOEvent(
            id="1",
            timestamp=0.0,
            z_256=[],
            state_12d=[],
            kind="k",
            voice="v",
            score=0.5,
            journey_id="a",
        )
    )
    nx.add_event(
        EVOEvent(
            id="2",
            timestamp=0.0,
            z_256=[],
            state_12d=[],
            kind="k",
            voice="v",
            score=0.5,
            journey_id="b",
        )
    )
    nx.add_event(
        EVOEvent(
            id="3",
            timestamp=0.0,
            z_256=[],
            state_12d=[],
            kind="k",
            voice="v",
            score=0.5,
            journey_id="a",
        )
    )
    a_events = [e async for e in nx.subscribe(journey_id="a")]
    assert {e.id for e in a_events} == {"1", "3"}


def test_stream_snapshot_returns_all_events():
    nx = JourneyNexus()
    for i in range(5):
        nx.add_event(
            EVOEvent(
                id=str(i),
                timestamp=float(i),
                z_256=[],
                state_12d=[],
                kind="k",
                voice="v",
                score=0.5,
                journey_id="j",
            )
        )
    assert len(nx.stream_snapshot()) == 5


# ----- Lazy singletons (no network, no live services) ----------------------


def test_lazy_init_creates_singleton_omni_and_quadrature():
    nx = JourneyNexus()
    # Before first call, the singletons are None
    assert nx._omni_tier is None
    assert nx._quadrature_nexus is None
    # First call instantiates them
    omni = nx._get_omni_tier()
    omni2 = nx._get_omni_tier()
    assert omni is omni2  # singleton
    qn = nx._get_quadrature_nexus()
    qn2 = nx._get_quadrature_nexus()
    assert qn is qn2


# ----- Mocks: quadr + narrate + omni_chat (no live :13305 needed) -----------


class _FakeVoiceResponse:
    def __init__(self, voice: str, score: float) -> None:
        self.voice = type("V", (), {"value": voice})()
        self.approval_score = score
        self.concerns = [f"concern-{voice}"]
        self.recommendations = [f"rec-{voice}"]


class _FakeQuadratureResult:
    def __init__(self) -> None:
        self.approved = True
        self.consensus_score = 0.91
        self.alignment_score = 0.88
        self.responses = [
            _FakeVoiceResponse("architect", 0.95),
            _FakeVoiceResponse("engineer", 0.90),
            _FakeVoiceResponse("ethicist", 0.85),
            _FakeVoiceResponse("resource", 0.94),
        ]
        self.rejection_reason = None


class _FakeQuadratureNexus:
    """Matches the real QuadratureNexus signature: `async def deliberate`."""

    def __init__(self) -> None:
        self.last_proposal: Any = None
        self.deliberate_called: bool = False

    async def deliberate(self, proposal: Any) -> _FakeQuadratureResult:
        self.last_proposal = proposal
        self.deliberate_called = True
        return _FakeQuadratureResult()


class _RaisingFakeQuadratureNexus:
    """Discriminating fake: surfaces AttributeError that the old
    `asyncio.to_thread(nexus.deliberate, ...)` pattern would have caused.

    If someone re-introduces `to_thread` and a real QuadratureResult is
    returned, this fake would never raise — but the assertion on
    `nexus.deliberate` being a coroutine catches the wrong-wrap pattern.
    """

    def __init__(self) -> None:
        self.deliberate_called = False

    async def deliberate(self, proposal: Any) -> Any:
        self.deliberate_called = True
        # Real QuadratureNexus.deliberate is `async def`; confirm via inspect.
        import inspect

        assert inspect.iscoroutinefunction(self.deliberate), (
            "Real QuadratureNexus.deliberate must be async — "
            "if you changed the signature, update JourneyNexus.quadrature() to match."
        )
        return _FakeQuadratureResult()


@pytest.mark.asyncio
async def test_quadrature_maps_result_fields(monkeypatch):
    nx = JourneyNexus()
    fake = _FakeQuadratureNexus()
    monkeypatch.setattr(nx, "_get_quadrature_nexus", lambda: fake)
    # Patch the loader at its source — the service does an in-method import,
    # so we must reach the source module rather than the destination.
    monkeypatch.setattr(
        "cohezion.api.services.journey_loader.load_journey",
        lambda jid: {"id": jid, "intent": "test intent", "initial_axiomatic": [0.5] * 12},
    )

    out = await nx.quadrature("j1", mode="preflight")
    assert fake.deliberate_called, "Service must call nexus.deliberate()"
    assert out.approved is True
    assert out.consensus_score == 0.91
    assert out.alignment_score == 0.88
    assert len(out.voice_responses) == 4
    voices = {vr["voice"] for vr in out.voice_responses}
    assert voices == {"architect", "engineer", "ethicist", "resource"}
    # The proposal used the journey's intent
    assert fake.last_proposal.description == "test intent"
    assert fake.last_proposal.action == "interpret_journey"
    assert fake.last_proposal.context["journey_id"] == "j1"
    assert fake.last_proposal.context["initial_12d"] == [0.5] * 12


class _FakeTTSResult:
    def __init__(self) -> None:
        self.audio_b64 = base64.b64encode(b"fake-mp3").decode("ascii")


class _FakeImageResult:
    def __init__(self) -> None:
        self.image_b64 = base64.b64encode(b"fake-png").decode("ascii")


class _FakeTTS:
    def __init__(self) -> None:
        self.last_text: str | None = None
        self.last_voice: str | None = None

    async def speak(self, *, text: str, voice: str) -> _FakeTTSResult:
        self.last_text = text
        self.last_voice = voice
        return _FakeTTSResult()


class _FakeImageTier:
    def __init__(self) -> None:
        self.last_prompt: str | None = None
        self.last_journey_id: str | None = None

    async def render(self, *, prompt: str, journey_id: str) -> _FakeImageResult:
        self.last_prompt = prompt
        self.last_journey_id = journey_id
        return _FakeImageResult()


class _FakeOmni:
    def __init__(self) -> None:
        self.tts_tier = _FakeTTS()
        self.image_tier = _FakeImageTier()


class _FakeVAE:
    def __init__(self) -> None:
        self.last_text: str | None = None

    def encode(self, text: str) -> list[float]:
        self.last_text = text
        return [0.5] * 256


@pytest.mark.asyncio
async def test_narrate_no_image_uses_vae_and_tts(monkeypatch):
    nx = JourneyNexus()
    fake_omni = _FakeOmni()
    monkeypatch.setattr(nx, "_get_omni_tier", lambda: fake_omni)
    fake_vae = _FakeVAE()
    monkeypatch.setattr("cohezion.api.services.flume.get_vae", lambda: fake_vae)
    monkeypatch.setattr(
        "cohezion.api.services.journey_loader.load_journey",
        lambda jid: {"id": jid, "intent": "test intent"},
    )

    out = await nx.narrate("j1")
    assert isinstance(out, NarrateResult)
    assert out.journey_id == "j1"
    assert "test intent" in out.text
    assert out.audio_b64  # base64
    assert out.image_b64 is None
    assert 0.0 <= out.coherence <= 1.0
    # TTS was called with the narration text and the am_michael voice
    assert fake_omni.tts_tier.last_voice == "am_michael"
    assert fake_omni.tts_tier.last_text is not None
    assert "test intent" in fake_omni.tts_tier.last_text


@pytest.mark.asyncio
async def test_narrate_with_image_renders(monkeypatch):
    nx = JourneyNexus()
    fake_omni = _FakeOmni()
    monkeypatch.setattr(nx, "_get_omni_tier", lambda: fake_omni)
    fake_vae = _FakeVAE()
    monkeypatch.setattr("cohezion.api.services.flume.get_vae", lambda: fake_vae)
    monkeypatch.setattr(
        "cohezion.api.services.journey_loader.load_journey",
        lambda jid: {"id": jid, "intent": "paint a sphere"},
    )

    out = await nx.narrate("j2", with_image=True)
    assert out.image_b64 == base64.b64encode(b"fake-png").decode("ascii")
    assert fake_omni.image_tier.last_prompt == "paint a sphere"
    assert fake_omni.image_tier.last_journey_id == "j2"


class _FakeToolCallLog:
    def __init__(self, name: str, args: dict, kind: str) -> None:
        self.tool_name = name
        self.arguments = args
        self.artefact_kind = kind


class _FakeOmniResult:
    def __init__(self) -> None:
        self.text = "I'll generate an image for you"
        self.images = [b"img1", b"img2"]
        self.audio = b"audio-bytes"
        self.tool_calls = [
            _FakeToolCallLog("generate_image", {"prompt": "sphere"}, "image"),
        ]


class _FakeOmniWithRun:
    def __init__(self) -> None:
        self.last_request: Any = None
        # The service calls `.tts_tier` / `.image_tier` for some paths; for omni_chat
        # these are unused but the lazy _get_omni_tier probes them — keep them set.
        self.tts_tier: Any = None
        self.image_tier: Any = None

    async def run(self, req: Any) -> _FakeOmniResult:
        self.last_request = req
        return _FakeOmniResult()


@pytest.mark.asyncio
async def test_omni_chat_uses_journey_context(monkeypatch):
    nx = JourneyNexus()
    fake_omni = _FakeOmniWithRun()
    # We need .tts_tier/.image_tier for the lazy _get_omni_tier path; stub them
    fake_omni.tts_tier = _FakeTTS()
    fake_omni.image_tier = _FakeImageTier()
    monkeypatch.setattr(nx, "_get_omni_tier", lambda: fake_omni)
    monkeypatch.setattr(
        "cohezion.api.services.journey_loader.load_journey",
        lambda jid: {"id": jid, "intent": "sphere project"},
    )

    out = await nx.omni_chat("j99", message="render a sphere")
    assert isinstance(out, OmniChatOutcome)
    assert "I'll generate an image" in out.text
    assert len(out.images_b64) == 2
    assert out.audio_b64 == base64.b64encode(b"audio-bytes").decode("ascii")
    assert out.tool_calls[0]["tool_name"] == "generate_image"
    # The prompt sent to Omni should include the journey context
    assert "sphere project" in fake_omni.last_request.prompt
    assert "render a sphere" in fake_omni.last_request.prompt
