"""JourneyNexus service — orchestration façade for FLUME/Quadrature/Omni.

Exports consumed by:
  - tests/api/test_journey_nexus.py
  - tests/api/test_journey_nexus_router.py

Implemented 2026-07-08 against the pre-existing service test contract
(tests-as-spec). Method bodies drafted by Qwen3-Coder-30B on the local CPU
lane; dataclass surface and signatures restored to the original contract by
the orchestrating model.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import numpy as np


@dataclass
class EVOEvent:
    """A single event in an EVO stream."""

    id: str
    timestamp: float
    z_256: list[float]
    state_12d: list[float]
    kind: str
    voice: str
    score: float
    journey_id: str


@dataclass
class QuadratureOutcome:
    """Result of a Quadrature Nexus consensus vote."""

    approved: bool
    consensus_score: float
    alignment_score: float
    voice_responses: list[Any] = field(default_factory=list)
    rejection_reason: str | None = None


@dataclass
class OmniChatOutcome:
    """Result of an Omni chat completion."""

    text: str
    model: str = ""
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    tool_calls: list[Any] = field(default_factory=list)
    images_b64: list[str] = field(default_factory=list)
    audio_b64: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class NarrateResult:
    """Result of a journey narration (text + audio + optional image)."""

    journey_id: str
    text: str
    audio_b64: str
    coherence: float
    image_b64: str | None = None


def _encode_journey_text(text: str) -> np.ndarray:
    """Text → 256D FLUME latent.

    Real path: nomic-embed-text-v2-moe via the Lemonade OmniRouter (:13305),
    subsampled to the 256D FLUME contract by LemonadeEmbedBridge. Offline
    fallback: FlumeVAEEncoder's deterministic hash encode (never raises).
    """
    from cohezion.inference.lemonade_embed_bridge import LemonadeEmbedBridge

    bridge = LemonadeEmbedBridge()
    if bridge.is_available():
        z = bridge.encode(text)
        if float(np.linalg.norm(z)) > 1e-8:
            return z
    from cohezion.flume.vae_encoder import get_encoder

    return get_encoder().encode(text)


class _ImageTierAdapter:
    """Placeholder image tier — the omni image pipeline is not wired yet."""

    async def render(self, *, prompt: str, journey_id: str) -> Any:
        raise NotImplementedError("image rendering requires the omni image pipeline")


class _OmniFacade:
    """Composite Omni tier: real TTS lane + placeholder image/run surfaces."""

    def __init__(self) -> None:
        from cohezion.inference.tts_tier import build_tts_tier

        self.tts_tier = build_tts_tier()
        self.image_tier = _ImageTierAdapter()

    async def run(self, req: Any) -> Any:
        raise NotImplementedError("omni run() requires the full Omni pipeline")


class JourneyNexus:
    """Orchestration façade for FLUME VAE, Quadrature Nexus, and Omni Tier."""

    def __init__(self) -> None:
        self._events: list[EVOEvent] = []
        self._omni_tier: Any = None
        self._quadrature_nexus: Any = None

    def add_event(self, event: EVOEvent) -> None:
        """Append *event* to the in-memory EVO stream."""
        self._events.append(event)

    def stream_snapshot(self) -> list[EVOEvent]:
        """Return a copy of all events currently in the stream."""
        return list(self._events)

    async def subscribe(
        self,
        *,
        journey_id: str | None = None,
    ) -> AsyncIterator[EVOEvent]:
        """Yield events, optionally filtered by *journey_id*."""
        for e in self._events:
            if journey_id is None or e.journey_id == journey_id:
                yield e

    # ----- lazy singletons ---------------------------------------------------

    def _get_quadrature_nexus(self) -> Any:
        if self._quadrature_nexus is None:
            from cohezion.swarm.quadrature_nexus import QuadratureNexus

            self._quadrature_nexus = QuadratureNexus()
        return self._quadrature_nexus

    def _get_omni_tier(self) -> Any:
        if self._omni_tier is None:
            self._omni_tier = _OmniFacade()
        return self._omni_tier

    # ----- orchestration -----------------------------------------------------

    async def quadrature(self, journey_id: str, *, mode: str = "preflight") -> QuadratureOutcome:
        """Run a 4-voice Quadrature Nexus consensus vote on a journey."""
        from cohezion.api.services import journey_loader
        from cohezion.swarm.quadrature_nexus import QuadratureProposal

        journey = journey_loader.load_journey(journey_id)
        proposal = QuadratureProposal(
            action="interpret_journey",
            description=journey["intent"],
            context={
                "journey_id": journey_id,
                "initial_12d": journey.get("initial_axiomatic", []),
                "mode": mode,
            },
            submitted_by="journey_nexus",
        )
        # QuadratureNexus.deliberate is async — await directly, never to_thread.
        result = await self._get_quadrature_nexus().deliberate(proposal)
        return QuadratureOutcome(
            approved=result.approved,
            consensus_score=result.consensus_score,
            alignment_score=result.alignment_score,
            voice_responses=[
                {
                    "voice": vr.voice.value,
                    "approval_score": vr.approval_score,
                    "concerns": vr.concerns,
                    "recommendations": vr.recommendations,
                    "score": vr.approval_score,
                }
                for vr in result.responses
            ],
            rejection_reason=result.rejection_reason,
        )

    async def narrate(self, journey_id: str, *, with_image: bool = False) -> NarrateResult:
        """Narrate a journey: FLUME-encode the text, speak it, optionally render."""
        from cohezion.api.services import flume, journey_loader

        journey = journey_loader.load_journey(journey_id)
        intent = journey.get("intent", "")
        text = f"Journey {journey_id}: {intent}. The manifold remembers."
        z = _encode_journey_text(text)
        # compute_coherence measures chunk-mean balance around the HIHO center
        # (0.5); embeddings are zero-centered, so shift into the HIHO frame.
        coherence = float(min(1.0, max(0.0, flume.compute_coherence([0.5 + float(v) for v in z]))))
        from cohezion.inference.tts_tier import TTSRequest

        omni = self._get_omni_tier()
        tts = await omni.tts_tier.speak(TTSRequest(text=text, voice="am_michael"))
        audio_b64 = base64.b64encode(tts.audio).decode("ascii") if tts.audio else ""
        image_b64: str | None = None
        if with_image:
            img = await omni.image_tier.render(prompt=intent, journey_id=journey_id)
            image_b64 = img.image_b64
        return NarrateResult(
            journey_id=journey_id,
            text=text,
            audio_b64=audio_b64,
            coherence=coherence,
            image_b64=image_b64,
        )

    async def omni_chat(self, journey_id: str, *, message: str) -> OmniChatOutcome:
        """Route *message* through the Omni Tier with journey context."""
        from cohezion.api.services import journey_loader

        journey = journey_loader.load_journey(journey_id)
        intent = journey.get("intent", "")
        req = SimpleNamespace(
            prompt=f"Journey context: {intent}\nUser: {message}",
            journey_id=journey_id,
        )
        result = await self._get_omni_tier().run(req)
        images_b64 = (
            [base64.b64encode(b).decode("ascii") for b in result.images] if result.images else []
        )
        audio_b64 = base64.b64encode(result.audio).decode("ascii") if result.audio else ""
        tool_calls = [
            {
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
                "artefact_kind": tc.artefact_kind,
            }
            for tc in result.tool_calls
        ]
        return OmniChatOutcome(
            text=result.text,
            images_b64=images_b64,
            audio_b64=audio_b64,
            tool_calls=tool_calls,
        )
