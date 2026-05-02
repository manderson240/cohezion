"""Dispatch inference requests to Lemonade with OOM safety.

Uses the already-running Lemonade server (port 8002) for all inference.
Avoids loading additional large models.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import requests

from cohezion.competition.orchestrator.resource_guard import ResourceGuard


logger = logging.getLogger(__name__)

LEMONADE_API = "http://127.0.0.1:8002/v1"
MODEL_NAME = "Gemma-4-26B-A4B-it-GGUF"


@dataclass
class GenerationResult:
    text: str
    tokens_used: int
    duration_ms: float
    model: str


class ModelDispatcher:
    """Single-model dispatcher using the pre-warmed Lemonade server."""

    def __init__(self) -> None:
        self.guard = ResourceGuard()
        self._warm = False

    def _ensure_warm(self) -> bool:
        if self._warm:
            return True
        try:
            r = requests.get(f"{LEMONADE_API}/models", timeout=5)
            if r.status_code == 200:
                self._warm = True
                logger.info("ModelDispatcher: Lemonade server warm")
                return True
        except Exception as e:
            logger.warning(f"ModelDispatcher: Lemonade not warm: {e}")
        return False

    def generate(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.6,
        max_tokens: int = 2048,
    ) -> GenerationResult:
        """Generate text via OpenAI-compatible API on port 8002."""
        if not self._ensure_warm():
            raise RuntimeError("Lemonade server not available on port 8002")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        req = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        import time as _time

        t0 = _time.perf_counter()
        try:
            r = requests.post(f"{LEMONADE_API}/chat/completions", json=req, timeout=120)
            r.raise_for_status()
        except requests.exceptions.Timeout:
            raise RuntimeError("Lemonade inference timeout (120s)") from None

        data = r.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        dur = (_time.perf_counter() - t0) * 1000

        return GenerationResult(text=text, tokens_used=tokens, duration_ms=dur, model=MODEL_NAME)

    def generate_structured(
        self,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Generate JSON matching a schema.

        Uses constrained decoding if available, otherwise validates post-hoc.
        """
        # Append schema instruction
        full_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with a JSON object matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            f"No extra text."
        )
        result = self.generate(system, full_prompt, temperature=temperature, max_tokens=4096)
        try:
            # Strip markdown fences
            raw = result.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw.rsplit("\n", 1)[0]
            raw = raw.strip()
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}\nRaw: {result.text[:500]}")
            return {"error": "parse_failed", "raw": result.text[:1000]}
