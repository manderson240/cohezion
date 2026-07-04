"""OmniModel — composed multimodal coordinator for the Strix Halo fleet.

Wires together:
  task_classifier → FleetRole → RamScheduler → Lemonade OmniRouter (:13305)

Provides a single entry point for all modalities:
  generate(prompt)      → text (routes via task_classifier)
  transcribe(path)      → text (Whisper-Large-v3-Turbo, NPU-cached)
  speak(text, path)     → Path (kokoro-v1 TTS)
  generate_image(p, pth)→ Path (Flux-2-Klein-9B)
  analyze_image(img, q) → text (Gemma-4-31B or Gemma-4-E4B, best available)
  party_generate(p)     → list[str] (all text models concurrently)

Constraints:
  - NEVER use Claude API (local inference only per user directive)
  - 96 GB RAM ceiling enforced via RamScheduler
  - All large model loads go through RamScheduler.ensure_loaded() first
  - Lemonade MCP tools (mcp__lemonade__*) are for interactive sessions;
    production code calls the REST API at :13305 directly

Usage:
    from cohezion.inference.omni_model import get_omni
    omni = get_omni()
    text = await omni.generate("Prove that sqrt(2) is irrational.")
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

OMNI_URL = "http://localhost:13305"


class OmniModel:
    """Composed multimodal model coordinator."""

    def __init__(self, omni_url: str = OMNI_URL) -> None:
        self._url = omni_url
        # Lazy imports to avoid circular deps and heavy startup
        self._scheduler: Any = None
        self._fleet: Any = None

    # ── Text generation ───────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        *,
        role: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Generate text.  Route is auto-selected unless `role` is provided."""
        model_id = self._pick_model(prompt, role)
        self._maybe_load(model_id)
        return await self._chat(model_id, prompt, max_tokens=max_tokens,
                                temperature=temperature)

    async def party_generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
    ) -> list[str]:
        """Fan-out to all available text models concurrently (party mode).

        Wall-clock = slowest node, not sum.  Useful for consensus or diversity.
        Returns one response per model in fleet order.
        """
        fleet = self._get_fleet()
        text_roles = ["router", "generation", "reasoning", "code", "deep_synthesis"]
        models = []
        for role in text_roles:
            try:
                from cohezion.inference.local_fleet import FleetRole  # noqa: PLC0415
                m = fleet.get(FleetRole(role))
                models.append(m.model_id)
            except (ValueError, KeyError):
                pass

        coros = [self._chat(mid, prompt, max_tokens=max_tokens) for mid in models]
        results = await asyncio.gather(*coros, return_exceptions=True)
        return [r if isinstance(r, str) else "" for r in results]

    # ── Transcription ─────────────────────────────────────────────────────

    async def transcribe(self, audio_path: str | Path) -> str:
        """Transcribe audio file using Whisper-Large-v3-Turbo (NPU-cached)."""
        from cohezion.inference.local_fleet import FleetRole  # noqa: PLC0415

        model_id = self._get_fleet().get(FleetRole.TRANSCRIBE).model_id
        self._maybe_load(model_id)
        return await self._transcribe(model_id, str(audio_path))

    # ── TTS ───────────────────────────────────────────────────────────────

    async def speak(self, text: str, output_path: str | Path) -> Path:
        """Synthesise speech using kokoro-v1.  Returns path to audio file."""
        from cohezion.inference.local_fleet import FleetRole  # noqa: PLC0415

        model_id = self._get_fleet().get(FleetRole.TTS).model_id
        self._maybe_load(model_id)
        await self._tts(model_id, text, str(output_path))
        return Path(output_path)

    # ── Image generation ──────────────────────────────────────────────────

    async def generate_image(self, prompt: str, output_path: str | Path) -> Path:
        """Generate an image using Flux-2-Klein-9B."""
        from cohezion.inference.local_fleet import FleetRole  # noqa: PLC0415

        model_id = self._get_fleet().get(FleetRole.IMAGE_GEN).model_id
        self._maybe_load(model_id)
        await self._image_gen(model_id, prompt, str(output_path))
        return Path(output_path)

    # ── Vision / image understanding ──────────────────────────────────────

    async def analyze_image(
        self,
        image_path: str | Path,
        prompt: str = "Describe this image in detail.",
        *,
        prefer_fast: bool = False,
    ) -> str:
        """Analyze an image using the best available vision model.

        prefer_fast=True uses Gemma-4-E4B (5.97 GB, ~54 TPS).
        prefer_fast=False uses Gemma-4-31B (19.5 GB, 6 TPS) for higher quality.
        """
        from cohezion.inference.local_fleet import FleetRole  # noqa: PLC0415

        role = FleetRole.VISION_FAST if prefer_fast else FleetRole.VISION
        model_id = self._get_fleet().get(role).model_id
        self._maybe_load(model_id)
        return await self._vision(model_id, str(image_path), prompt)

    # ── Internal: model selection ─────────────────────────────────────────

    def _pick_model(self, prompt: str, role: str | None) -> str:
        """Select model_id: explicit role > task_classifier > gauntlet champion > fleet default."""
        from cohezion.inference.local_fleet import FleetRole  # noqa: PLC0415

        if role:
            try:
                return self._get_fleet().get(FleetRole(role)).model_id
            except (ValueError, KeyError):
                pass

        # Try task_classifier
        try:
            from cohezion.inference.task_classifier import classify  # noqa: PLC0415
            decision = classify(prompt)
            output_type = decision.output_type
        except Exception:
            output_type = "medium_generation"

        # Check gauntlet champion for this role mapping
        fleet = self._get_fleet()
        from cohezion.inference.local_fleet import _TYPE_TO_ROLE  # noqa: PLC0415
        fleet_role = _TYPE_TO_ROLE.get(output_type, FleetRole.GENERATION)

        try:
            from cohezion.inference.gauntlet import get_champion  # noqa: PLC0415
            champion = get_champion(fleet_role.value)
            if champion:
                return champion
        except Exception:
            pass

        return fleet.get(fleet_role).model_id

    def _maybe_load(self, model_id: str) -> list[str]:
        """Check ceiling and return eviction candidates (non-blocking — no HTTP)."""
        scheduler = self._get_scheduler()
        to_evict = scheduler.ensure_loaded(model_id)
        if to_evict:
            logger.info("OmniModel: evicting %s to load %s", to_evict, model_id)
        return to_evict

    # ── Internal: Lemonade REST calls ─────────────────────────────────────

    async def _chat(
        self,
        model_id: str,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float = 0.7,
    ) -> str:
        try:
            import httpx  # noqa: PLC0415

            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self._url}/api/v1/chat", json=payload)
                resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("OmniModel._chat(%s) failed: %s", model_id, exc)
            return ""

    async def _transcribe(self, model_id: str, audio_path: str) -> str:
        try:
            import httpx  # noqa: PLC0415

            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(audio_path, "rb") as f:
                    files = {"file": (Path(audio_path).name, f, "audio/wav")}
                    resp = await client.post(
                        f"{self._url}/api/v1/audio/transcriptions",
                        data={"model": model_id},
                        files=files,
                    )
                    resp.raise_for_status()
            return resp.json().get("text", "")
        except Exception as exc:
            logger.warning("OmniModel._transcribe failed: %s", exc)
            return ""

    async def _tts(self, model_id: str, text: str, output_path: str) -> None:
        try:
            import httpx  # noqa: PLC0415

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._url}/api/v1/audio/speech",
                    json={"model": model_id, "input": text, "voice": "default"},
                )
                resp.raise_for_status()
            Path(output_path).write_bytes(resp.content)
        except Exception as exc:
            logger.warning("OmniModel._tts failed: %s", exc)

    async def _image_gen(self, model_id: str, prompt: str, output_path: str) -> None:
        try:
            import httpx  # noqa: PLC0415

            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{self._url}/api/v1/images/generations",
                    json={"model": model_id, "prompt": prompt, "n": 1},
                )
                resp.raise_for_status()
            data = resp.json()
            # Lemonade returns base64-encoded PNG
            import base64  # noqa: PLC0415
            b64 = data["data"][0].get("b64_json", "")
            if b64:
                Path(output_path).write_bytes(base64.b64decode(b64))
        except Exception as exc:
            logger.warning("OmniModel._image_gen failed: %s", exc)

    async def _vision(self, model_id: str, image_path: str, prompt: str) -> str:
        try:
            import base64  # noqa: PLC0415
            import httpx  # noqa: PLC0415

            image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
            suffix = Path(image_path).suffix.lower().lstrip(".")
            media_type = f"image/{suffix or 'png'}"

            payload = {
                "model": model_id,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}"
                        }},
                        {"type": "text", "text": prompt},
                    ],
                }],
                "max_tokens": 512,
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self._url}/api/v1/chat", json=payload)
                resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("OmniModel._vision failed: %s", exc)
            return ""

    # ── Singleton helpers ─────────────────────────────────────────────────

    def _get_fleet(self) -> Any:
        if self._fleet is None:
            from cohezion.inference.local_fleet import get_fleet  # noqa: PLC0415
            self._fleet = get_fleet()
        return self._fleet

    def _get_scheduler(self) -> Any:
        if self._scheduler is None:
            from cohezion.inference.ram_scheduler import get_scheduler  # noqa: PLC0415
            self._scheduler = get_scheduler()
        return self._scheduler


# Module-level singleton
_omni: OmniModel | None = None


def get_omni(omni_url: str = OMNI_URL) -> OmniModel:
    global _omni
    if _omni is None:
        _omni = OmniModel(omni_url=omni_url)
    return _omni
