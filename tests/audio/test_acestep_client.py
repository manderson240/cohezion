"""Tests for AceStepClient — thin wrapper on lemonade v11 :13305/v1/audio/generations.
Endpoint contract PROVEN live 2026-07-15: POST {model,prompt,duration,audio_format} ->
raw WAV bytes (Content-Type audio/wav), ~5s for 8s clip."""
from unittest.mock import patch, MagicMock
import pytest
from cohezion.audio.acestep_client import AceStepClient, coherence_to_prompt


def test_coherence_to_prompt_maps_hiho_to_consonance():
    # HIHO optimum (0.5) -> calm/consonant; extremes -> tense/dissonant (4x(1-x) peaks at 0.5)
    calm = coherence_to_prompt(0.5)
    tense_low = coherence_to_prompt(0.05)
    assert "calm" in calm.lower() or "consonant" in calm.lower() or "stable" in calm.lower()
    assert calm != tense_low  # discriminating: a constant-prompt impl fails this


def test_coherence_to_prompt_bounds():
    # any coherence in [0,1] yields a non-empty prompt string
    for c in (0.0, 0.25, 0.5, 0.75, 1.0):
        assert isinstance(coherence_to_prompt(c), str) and coherence_to_prompt(c)


def test_generate_posts_correct_payload_and_returns_bytes():
    fake = MagicMock()
    fake.read.return_value = b"RIFF$(#\x00WAVEfake-audio-bytes" * 100
    fake.headers = {"Content-Type": "audio/wav"}
    fake.__enter__.return_value = fake
    with patch("cohezion.audio.acestep_client.urllib.request.urlopen", return_value=fake) as uo:
        c = AceStepClient()
        data = c.generate("gentle pad", duration=8)
    assert data[:4] == b"RIFF"  # real WAV magic
    # discriminating: the request body must carry model+prompt (a stub ignoring args fails)
    sent = uo.call_args[0][0].data.decode()
    assert "ACE-Step-Music" in sent and "gentle pad" in sent


def test_generate_fail_open_returns_none_on_error():
    with patch("cohezion.audio.acestep_client.urllib.request.urlopen", side_effect=OSError("down")):
        assert AceStepClient().generate("x") is None  # never raises into the caller
