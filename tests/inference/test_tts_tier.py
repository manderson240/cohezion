"""Live-validation tests for DirectLemonadeTTSTier (kokoro-v1 on :13305).

These hit the real lemonade kokoro recipe. Marked as live; skip in CI without
lemonade on :13305. Run with:  .venv/bin/python -m pytest tests/inference/test_tts_tier.py -v
"""

from __future__ import annotations

import socket

import httpx
import pytest

from cohezion.inference.tts_tier import (
    DirectLemonadeTTSTier,
    TTSRequest,
)


def lemonade_kokoro_reachable(host: str = "localhost", port: int = 13305) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def _kokoro_produces_audio(port: int = 13305) -> bool:
    """Probe whether kokoro-v1 is actually loaded and emitting non-empty audio.

    A bare socket check is insufficient: the OmniRouter accepts connections and
    returns 200 OK with an EMPTY body when the TTS model is not loaded, which
    makes the live synthesis tests fail instead of skip. This does a tiny real
    synthesis and requires non-empty audio bytes back.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"http://localhost:{port}/v1/audio/speech",
                json={
                    "model": "kokoro-v1",
                    "input": "hi",
                    "voice": "default",
                    "response_format": "mp3",
                    "speed": 1.0,
                },
            )
            return resp.status_code == 200 and len(resp.content) > 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not lemonade_kokoro_reachable(),
    reason="kokoro-v1 not loaded on :13305 (run lemonade load kokoro-v1 first)",
)

# Stronger guard for tests that require kokoro to actually emit audio. The
# OmniRouter being reachable does not mean kokoro-v1 is loaded — when it is not,
# /v1/audio/speech returns 200 with an empty body. These tests skip (not fail)
# in that state.
KOKORO_LIVE = pytest.mark.skipif(
    not _kokoro_produces_audio(),
    reason="kokoro-v1 not emitting audio on :13305 (200 OK but empty body — model not loaded)",
)


@KOKORO_LIVE
@pytest.mark.asyncio
async def test_tts_default_voice_mp3() -> None:
    tier = DirectLemonadeTTSTier(port=13305)
    r = await tier.speak(TTSRequest(text="The voice loop is now closed."))
    assert r.ok, f"render failed: {r.error}"
    assert r.audio[:3] == b"ID3" or r.audio[:2] == b"\xff\xfb", "not a valid MP3"
    assert r.mime_type == "audio/mpeg"
    assert r.bytes_per_char > 100  # 79 chars -> 52k bytes -> 660 bpc
    assert r.latency_ms < 5000  # generous for CPU


@KOKORO_LIVE
@pytest.mark.asyncio
async def test_tts_af_sky_voice() -> None:
    tier = DirectLemonadeTTSTier(port=13305)
    r = await tier.speak(
        TTSRequest(
            text="Compound engineering: each output should make the next cheaper.", voice="af_sky"
        )
    )
    assert r.ok
    assert r.voice == "af_sky"
    assert len(r.audio) > 1000


@KOKORO_LIVE
@pytest.mark.asyncio
async def test_tts_wav_format() -> None:
    tier = DirectLemonadeTTSTier(port=13305)
    r = await tier.speak(TTSRequest(text="Half in, half out.", response_format="wav"))
    assert r.ok
    assert r.audio[:4] == b"RIFF", "not a valid WAV"
    assert r.mime_type == "audio/wav"


@pytest.mark.asyncio
async def test_tts_error_path() -> None:
    bad = DirectLemonadeTTSTier(port=9999)  # nothing on 9999
    r = await bad.speak(TTSRequest(text="should fail"))
    assert not r.ok
    assert r.error is not None
    assert "Connect" in r.error or "connect" in r.error


@KOKORO_LIVE
@pytest.mark.asyncio
async def test_tts_is_alive() -> None:
    tier = DirectLemonadeTTSTier(port=13305)
    assert await tier.is_alive()


def test_dataclass_voice_type() -> None:
    req = TTSRequest(text="x", voice="am_michael")
    assert req.voice == "am_michael"
    # Type guard: VoiceID is a Literal; a bad voice would be a type error.
