"""Anima Service — The system voice with 3-tier graceful degradation.

Tier 1 (Template): Always works — formats physics state into narration.
Tier 2 (MCP):      Routes questions through KnowledgeMCP for grounded answers.
Tier 3 (Voice):    Pipes text through PocketTTS for audio synthesis.

Each tier falls back gracefully to the one below it.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel


anima_router = APIRouter(tags=["anima"])
logger = logging.getLogger(__name__)


class AnimaStatusResponse(BaseModel):
    tier: str
    online: bool
    mcp_available: bool
    voice_available: bool


class NarrationResponse(BaseModel):
    text: str
    tier: str


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    tier: str
    sources: list[str]


class SpeakRequest(BaseModel):
    text: str


class SpeakResponse(BaseModel):
    audio_base64: str | None
    tier: str
    fallback_text: str


class AnimaService:
    """Three-tier Anima intelligence service."""

    def __init__(self) -> None:
        self._mcp_available = False
        self._voice_available = False
        self._detect_capabilities()

    def _detect_capabilities(self) -> None:
        # Tier 2: Check if KnowledgeMCP is reachable
        try:
            import httpx

            resp = httpx.get("http://localhost:8371/health", timeout=2.0)
            self._mcp_available = resp.status_code == 200
        except Exception:
            self._mcp_available = False

        # Tier 3: Check if pocket-tts model is available
        try:
            self._voice_available = True
        except Exception:
            self._voice_available = False

    @property
    def current_tier(self) -> str:
        if self._voice_available:
            return "voice"
        if self._mcp_available:
            return "mcp"
        return "template"

    def get_status(self) -> AnimaStatusResponse:
        return AnimaStatusResponse(
            tier=self.current_tier,
            online=True,
            mcp_available=self._mcp_available,
            voice_available=self._voice_available,
        )

    def narrate(self) -> NarrationResponse:
        """Tier 1: Template narration from current universe state."""
        from cohezion.api.services.universe import get_universe_service

        svc = get_universe_service()
        report = svc.get_report()
        return NarrationResponse(text=report.summary, tier="template")

    async def ask(self, question: str) -> AskResponse:
        """Route question through available tiers."""
        # Tier 2: Try MCP-grounded answer
        if self._mcp_available:
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "http://localhost:8371/search",
                        json={"query": question, "limit": 3},
                        timeout=5.0,
                    )
                    if resp.status_code == 200:
                        results = resp.json()
                        if results:
                            answer = "\n".join(
                                r.get("content", r.get("text", ""))[:200] for r in results[:3]
                            )
                            sources = [r.get("source", "vault") for r in results[:3]]
                            return AskResponse(answer=answer, tier="mcp", sources=sources)
            except Exception as e:
                logger.warning("MCP query failed, falling back to template: %s", e)

        # Tier 1: Template answer for common questions
        answer = self._template_answer(question)
        return AskResponse(answer=answer, tier="template", sources=["template"])

    def _template_answer(self, question: str) -> str:
        """Built-in answers for common questions about HIHO physics."""
        q_lower = question.lower()
        if "hiho" in q_lower:
            return (
                "HIHO (Half-In, Half-Out) is Cohezion's stability principle. "
                "It acts like Hooke's Law on coherence — a restoring force that "
                "keeps the system at 0.5 (the sweet spot between hallucination "
                "collapse and rigid over-fitting). The HIHOStabilizationEngine "
                "applies this as F = -k * (coherence - 0.5) every tick."
            )
        if "evo" in q_lower:
            return (
                "EVOs are Evolving Virtual Organisms — charge clusters in the "
                "12D semantic manifold. Each has charge_density, magnetic_helicity, "
                "toroidal_moment, and coherence. They're initialized by "
                "EVOInitializationFactory and stabilized by the HIHO loop."
            )
        if "ca" in q_lower or "cellular" in q_lower:
            return (
                "The Cellular Automata engine uses Rule 30 (Wolfram) on a 256-cell "
                "grid. It provides the substrate fabric that EVOs move through. "
                "CA density tracks what fraction of cells are active."
            )
        if "triune" in q_lower or "knower" in q_lower or "thinker" in q_lower or "doer" in q_lower:
            return (
                "The Triune Self is Cohezion's navigation paradigm with three "
                "cognitive modes: KNOWER (Observatory — observe physics), "
                "THINKER (Vault — search knowledge), DOER (Cockpit — act on "
                "the compound engineering loop). Each mode has ritualized "
                "transitions that deepen cognitive engagement."
            )
        return (
            "I'm Anima, Cohezion's system voice. I can answer questions about "
            "HIHO physics, EVOs, cellular automata, the Triune Self, and the "
            "compound engineering loop. Try asking about any of these topics."
        )

    async def speak(self, text: str) -> SpeakResponse:
        """Tier 3: Voice synthesis via PocketTTS."""
        if self._voice_available:
            try:
                from cloud_vault_mcp.src.mcp_server.pocket_tts import PocketTTSService

                tts = PocketTTSService()
                audio = await tts.synthesize(text)
                return SpeakResponse(audio_base64=audio, tier="voice", fallback_text=text)
            except Exception as e:
                logger.warning("TTS failed: %s", e)

        return SpeakResponse(audio_base64=None, tier="template", fallback_text=text)


# Singleton
_anima: AnimaService | None = None


def get_anima_service() -> AnimaService:
    global _anima
    if _anima is None:
        _anima = AnimaService()
    return _anima


# --- Endpoints ---


@anima_router.get("/status", response_model=AnimaStatusResponse)
async def get_anima_status() -> AnimaStatusResponse:
    """Return Anima's current tier and capability status."""
    return get_anima_service().get_status()


@anima_router.post("/narrate", response_model=NarrationResponse)
async def narrate() -> NarrationResponse:
    """Generate template narration from current universe physics state."""
    return get_anima_service().narrate()


@anima_router.post("/ask", response_model=AskResponse)
async def ask_anima(req: AskRequest) -> AskResponse:
    """Ask Anima a question — routed through available tiers."""
    return await get_anima_service().ask(req.question)


@anima_router.post("/speak", response_model=SpeakResponse)
async def speak(req: SpeakRequest) -> SpeakResponse:
    """Synthesize text to audio via PocketTTS (Tier 3)."""
    return await get_anima_service().speak(req.text)
