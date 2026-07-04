"""Tests for DirectLemonadeSTTTier (Whisper-Large-v3-Turbo on OmniRouter :13305).

Live tests hit the real OmniRouter and skip cleanly when :13305 is down.
Mocked tests use httpx stubs and always run.

To run live:
    .venv/bin/python -m pytest tests/inference/test_stt_tier.py -v
"""

from __future__ import annotations

import io
import socket
import wave

import pytest

from cohezion.inference.stt_tier import (
    DirectLemonadeSTTTier,
    Segment,
    STTRequest,
    STTResult,
    _detect_ext,
    _read_audio,
    build_stt_tier,
)


def lemonade_reachable(host: str = "localhost", port: int = 13305) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


# ----- Pure-logic tests (no network) ----------------------------------------


def test_default_port_is_13305():
    """The 2026-06-10 design rule: only the OmniRouter. No per-lane ports."""
    assert DirectLemonadeSTTTier.DEFAULT_PORT == 13305
    assert DirectLemonadeSTTTier.DEFAULT_MODEL == "Whisper-Large-v3-Turbo"


def test_stt_request_defaults():
    req = STTRequest(audio=b"\x00")
    assert req.model == "Whisper-Large-v3-Turbo"
    assert req.response_format == "json"
    assert req.language is None
    assert req.temperature == 0.0
    assert req.prompt is None


def test_stt_result_ok_when_text_present():
    r = STTResult(
        text="hello world",
        mime_type="audio/mpeg",
        audio_bytes=1024,
        duration_s=1.0,
        language="english",
        segments=[],
        response_format="json",
        latency_ms=200.0,
        bytes_per_sec=1024.0,
        model="Whisper-Large-v3-Turbo",
        port=13305,
    )
    assert r.ok
    assert r.error is None
    assert r.word_count == 2


def test_stt_result_not_ok_when_empty():
    r = STTResult(
        text="",
        mime_type="",
        audio_bytes=0,
        duration_s=None,
        language=None,
        segments=[],
        response_format="json",
        latency_ms=10.0,
        bytes_per_sec=0.0,
        model="Whisper-Large-v3-Turbo",
        port=13305,
        error="boom",
    )
    assert not r.ok
    assert r.error == "boom"
    assert r.word_count == 0


def test_segment_from_api_parses_fields():
    raw = {
        "id": 0,
        "start": 0.0,
        "end": 1.5,
        "text": " hello ",
        "tokens": [1, 2, 3],
        "temperature": 0.0,
        "avg_logprob": -0.25,
        "compression_ratio": 1.5,
        "no_speech_prob": 0.01,
    }
    s = Segment.from_api(raw)
    assert s.id == 0
    assert s.start == 0.0
    assert s.end == 1.5
    assert s.text == " hello "
    assert s.tokens == [1, 2, 3]
    assert s.avg_logprob == -0.25


def test_segment_from_api_tolerates_missing_fields():
    s = Segment.from_api({"id": 1, "text": "x"})
    assert s.start == 0.0
    assert s.end == 0.0
    assert s.tokens == []


def test_detect_ext_bytes_defaults_to_mp3():
    assert _detect_ext(b"\x00") == "mp3"


def test_detect_ext_path_suffix():
    assert _detect_ext("/tmp/clip.wav") == "wav"
    assert _detect_ext("/tmp/clip.MP3") == "mp3"
    assert _detect_ext("/tmp/noext") == "mp3"


def test_read_audio_from_path(tmp_path):
    p = tmp_path / "x.wav"
    p.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    data, name, mime = _read_audio(str(p))
    assert data == b"RIFF\x00\x00\x00\x00WAVE"
    assert name == "x.wav"
    assert mime == "audio/wav"


def test_read_audio_from_bytes():
    data, name, mime = _read_audio(b"\xff\xfb\x90\x00")
    assert data == b"\xff\xfb\x90\x00"
    assert name == "audio.mp3"
    assert mime == "audio/mpeg"


def test_build_stt_tier_factory():
    t = build_stt_tier()
    assert isinstance(t, DirectLemonadeSTTTier)
    assert t.port == 13305
    t2 = build_stt_tier(port=9000)
    assert t2.port == 9000


# ----- Mocked test (always runs) --------------------------------------------


@pytest.mark.asyncio
async def test_stt_transcribe_mocked_json(monkeypatch):
    """Verify the request shape and response parsing without hitting the router."""
    import httpx

    captured = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"text": " half in half out "}

        def raise_for_status(self):
            pass

        content = b""

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *, files, data):
            captured["url"] = url
            captured["files"] = files
            captured["data"] = data
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    tier = DirectLemonadeSTTTier(port=13305)
    r = await tier.transcribe(
        STTRequest(
            audio=b"\xff\xfb\x90\x00" * 100,
            response_format="json",
        )
    )
    assert r.ok
    assert r.text == " half in half out "
    assert captured["url"] == "http://localhost:13305/v1/audio/transcriptions"
    # Multipart fields
    assert "file" in captured["files"]
    fname, fbytes, fmime = captured["files"]["file"]
    assert fname == "audio.mp3"
    assert fbytes == b"\xff\xfb\x90\x00" * 100
    assert fmime == "audio/mpeg"
    # Form data
    assert captured["data"]["model"] == "Whisper-Large-v3-Turbo"
    # response_format is the default ("json"), so should be omitted
    assert "response_format" not in captured["data"]


@pytest.mark.asyncio
async def test_stt_transcribe_mocked_verbose_json(monkeypatch):
    """verbose_json should populate language/duration/segments."""

    payload = {
        "task": "transcribe",
        "language": "english",
        "duration": 6.26,
        "text": " Half in, half out.",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 1.2,
                "text": " Half in,",
                "tokens": [1, 2, 3],
                "temperature": 0.0,
                "avg_logprob": -0.3,
                "compression_ratio": 1.4,
                "no_speech_prob": 0.01,
            },
            {
                "id": 1,
                "start": 1.2,
                "end": 6.26,
                "text": " half out.",
                "tokens": [4, 5, 6],
                "temperature": 0.0,
                "avg_logprob": -0.3,
                "compression_ratio": 1.4,
                "no_speech_prob": 0.01,
            },
        ],
    }

    class _Resp:
        status_code = 200

        def json(self):
            return payload

        def raise_for_status(self):
            pass

        content = b""

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *, files, data):
            return _Resp()

    import cohezion.inference.stt_tier as stt_mod

    monkeypatch.setattr(stt_mod.httpx, "AsyncClient", _Client)

    # 1 second of silence * 16000 samples/sec
    silence = b"\x00\x00" * 16000
    tier = DirectLemonadeSTTTier(port=13305)
    r = await tier.transcribe(
        STTRequest(
            audio=silence,
            response_format="verbose_json",
            language="en",
        )
    )
    assert r.ok
    assert r.text == " Half in, half out."
    assert r.language == "english"
    assert r.duration_s == 6.26
    assert len(r.segments) == 2
    assert r.segments[0].text == " Half in,"
    assert r.segments[1].end == 6.26


@pytest.mark.asyncio
async def test_stt_transcribe_mocked_text_format(monkeypatch):
    """text response_format: server returns plain text body."""

    class _Resp:
        status_code = 200

        def json(self):
            raise AssertionError("json() should not be called for text")

        def raise_for_status(self):
            pass

        content = b"the quick brown fox"

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *, files, data):
            return _Resp()

    import cohezion.inference.stt_tier as stt_mod

    monkeypatch.setattr(stt_mod.httpx, "AsyncClient", _Client)

    tier = DirectLemonadeSTTTier(port=13305)
    r = await tier.transcribe(STTRequest(audio=b"\xff\xfb", response_format="text"))
    assert r.ok
    assert r.text == "the quick brown fox"


@pytest.mark.asyncio
async def test_stt_transcribe_error_path():
    """No service on port 9999 -> error populated, ok=False."""
    tier = DirectLemonadeSTTTier(port=9999)
    r = await tier.transcribe(STTRequest(audio=b"\xff\xfb"))
    assert not r.ok
    assert r.error is not None
    assert "Connect" in r.error or "connect" in r.error or "refused" in r.error.lower()


# ----- Live tests against :13305 (skipped if router down) ------------------


LIVE = pytest.mark.skipif(
    not lemonade_reachable(),
    reason="lemonade OmniRouter not reachable on :13305",
)


def _make_silence_wav(duration_s: float = 0.5, sample_rate: int = 16000) -> bytes:
    """A real WAV in memory (1 channel, 16-bit PCM silence)."""
    n = int(duration_s * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n)
    return buf.getvalue()


def _fetch_tts_mp3() -> bytes:
    """Ask the OmniRouter :13305 for a real MP3 we can transcribe back.

    As of 2026-06-10, the kokoro TTS server is dispatched through the
    OmniRouter (:13305), not on the legacy :8008 port. The 13305 router
    handles the model load + dispatch transparently.
    """
    import json as _json
    import urllib.request as _ur

    tts_body = _json.dumps(
        {
            "model": "kokoro-v1",
            "input": "Half in, half out. Compound engineering means each output should make the next cheaper.",
            "voice": "am_michael",
            "response_format": "mp3",
            "speed": 1.0,
        }
    ).encode()
    req = _ur.Request(
        "http://localhost:13305/v1/audio/speech",
        data=tts_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _ur.urlopen(req, timeout=30) as resp:  # noqa: S310 (test hits localhost:13305)
        return resp.read()


@LIVE
@pytest.mark.asyncio
async def test_stt_transcribe_silence_live():
    """Silence transcribes without raising. text may be empty; ok must be True."""
    tier = DirectLemonadeSTTTier(port=13305)
    wav = _make_silence_wav(duration_s=0.5)
    r = await tier.transcribe(STTRequest(audio=wav, response_format="json"))
    assert r.error is None, f"unexpected error: {r.error}"
    assert r.model == "Whisper-Large-v3-Turbo"
    assert r.port == 13305
    assert r.audio_bytes == len(wav)


@LIVE
@pytest.mark.asyncio
async def test_stt_transcribe_tts_roundtrip_live():
    """End-to-end: kokoro MP3 -> whisper text. The whole local voice loop."""
    mp3 = _fetch_tts_mp3()
    assert len(mp3) > 1000, f"TTS produced suspiciously small MP3: {len(mp3)} bytes"
    tier = DirectLemonadeSTTTier(port=13305)
    r = await tier.transcribe(STTRequest(audio=mp3, response_format="json"))
    assert r.ok, f"transcribe failed: {r.error}"
    # The recognized text should at least contain "half" (case-insensitive).
    assert "half" in r.text.lower(), f"unexpected transcription: {r.text!r}"
    assert r.latency_ms < 30_000, f"unexpectedly slow: {r.latency_ms}ms"


@LIVE
@pytest.mark.asyncio
async def test_stt_transcribe_verbose_live():
    """verbose_json returns language + duration + segments."""
    mp3 = _fetch_tts_mp3()
    tier = DirectLemonadeSTTTier(port=13305)
    r = await tier.transcribe(STTRequest(audio=mp3, response_format="verbose_json"))
    assert r.ok, f"transcribe failed: {r.error}"
    assert r.language is not None, "verbose_json should set language"
    assert r.duration_s is not None and r.duration_s > 0
    assert r.duration_s < 60, f"duration looks wrong: {r.duration_s}s"


@LIVE
@pytest.mark.asyncio
async def test_stt_is_alive_live():
    tier = DirectLemonadeSTTTier(port=13305)
    assert await tier.is_alive()
