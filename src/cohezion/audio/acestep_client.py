"""AceStepClient — generate music on the local AMD fleet via lemonade v11.

Endpoint proven live 2026-07-15: POST :13305/v1/audio/generations
{model, prompt, duration, audio_format} -> raw WAV bytes (Content-Type audio/wav),
~5s for an 8s clip on Vulkan, $0. The shared foundation every engagement surface
(compound-loop sonification, Genesis soundtrack, narrator stingers) builds on.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_ENDPOINT = "http://localhost:13305/v1/audio/generations"
_MODEL = "ACE-Step-Music"


def coherence_to_prompt(coherence: float) -> str:
    """Map a HIHO coherence signal [0,1] to a music prompt.

    HIHO optimum is 0.5 (the 4x(1-x) kernel peaks there): near 0.5 -> calm, consonant,
    stable; toward the extremes -> tense, dissonant, unstable. Distance-from-0.5 drives
    the mood so the loop's health is *audible*, not a constant backdrop.
    """
    c = max(0.0, min(1.0, coherence))
    dist = abs(c - 0.5) * 2.0  # 0 at HIHO optimum, 1 at either extreme
    if dist < 0.25:
        return "calm consonant ambient synth pad, stable and warm, slow 70 bpm"
    if dist < 0.6:
        return "gently shifting ambient texture, mild tension, moderate 90 bpm"
    return "tense dissonant drone, unstable and searching, sparse 60 bpm"


class AceStepClient:
    """Thin fail-open wrapper on the lemonade ACE-Step endpoint."""

    def __init__(self, endpoint: str = _ENDPOINT, model: str = _MODEL, timeout: float = 600.0):
        self._endpoint = endpoint
        self._model = model
        self._timeout = timeout

    def generate(
        self, prompt: str, *, duration: int = 8, audio_format: str = "wav"
    ) -> bytes | None:
        """Return raw audio bytes for ``prompt``, or None on any failure (fail-open:
        music is an enhancement, never a hard dependency of the caller)."""
        payload = json.dumps(
            {"model": self._model, "prompt": prompt, "duration": duration, "audio_format": audio_format}
        ).encode()
        req = urllib.request.Request(
            self._endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                return r.read()
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            logger.warning("AceStep generation failed (fail-open): %s", exc)
            return None
