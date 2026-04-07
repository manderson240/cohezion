"""Gemma 4 model provider implementation (Ollama-backed with thinking mode)."""

from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from cohezion.swarm.providers.model_provider import (
    GenerationResult,
    register_model_provider,
)
from cohezion.swarm.providers.ollama_provider import OllamaProvider


logger = logging.getLogger(__name__)


import yaml
from pathlib import Path


class Gemma4Provider(OllamaProvider):
    """Gemma 4 provider specializing in reasoning and native tool-calling.

    Features:
    - Dual-routing support for Local Lemonade (NPU/GPU) and Cloud endpoints.
    - Hardware-targeted dispatch based on Model tier.
    - Regime-aware routing (Sensing, Calculation, Synthesis, Steering).
    """

    def __init__(self, config: dict[str, Any] | None = None):
        gemma_config = {
            "timeout": 300,
            "thinking_mode": True,
            "context_window": 256000,
        }
        if config:
            gemma_config.update(config)

        super().__init__(gemma_config)

        self.thinking_mode = self.config.get("thinking_mode", True)
        self.context_window = self.config.get("context_window", 256000)

        # Load Lemonade Hardware Mapping
        self.hw_config = self._load_hw_config()

    def _load_hw_config(self) -> Dict[str, Any]:
        """Load the Lemonade silicon mapping config."""
        config_path = Path("src/cohezion/swarm/lemonade_config.yaml")
        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        return {}

    def _get_target_url(self, model: str) -> str:
        """Routes a model to the correct silicon endpoint (NPU, GPU, or Cloud)."""
        affinity = self.hw_config.get("model_affinity", {}).get(model)
        if not affinity:
            return self.base_url  # Fallback to default

        targets = self.hw_config.get("hardware_targets", {})
        target = targets.get(affinity)
        if not target:
            return self.base_url

        return target.get("endpoint", self.base_url)

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        """Generate response using Gemma 4.
        Symphony-Optimized: Routes between local Lemonade (NPU/GPU) and Cloud providers.
        """
        regime = kwargs.get("regime", "general")

        # SYMPHONY-ANCHORING: If a la-phase anchor is provided, we use it to reduce token overhead
        anchor_id = kwargs.get("anchor_id")

        # Context-Sensing Guard: Prevent local OOM for huge contexts
        current_ctx = len(prompt) // 4
        if current_ctx > 64000 and "cloud" not in model:
            logger.warning(
                "Massive context detected (%d tokens). Suggesting cloud routing.", current_ctx
            )

        target_url = self._get_target_url(model)

        session = await self._get_session()
        start_time = time.time()

        actual_thinking = self.thinking_mode
        actual_temp = temperature

        if regime == "CALCULATION":
            actual_thinking = True
            actual_temp = 0.1
        elif regime == "SENSING":
            actual_thinking = False
            actual_temp = 0.8

        # Prepare payload for Chat API
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": kwargs.get("format", ""),
            "options": {
                "num_predict": max_tokens,
                "temperature": actual_temp,
                "num_ctx": self.context_window,
                "thinking": actual_thinking,
                **kwargs.get("options", {}),
            },
        }

        # Symphony Anchor: If we have a cached cloud context, we tell the provider to use it
        if anchor_id:
            payload["anchor_id"] = anchor_id

        if self.keep_alive:
            payload["keep_alive"] = self.keep_alive

        try:
            async with session.post(
                f"{target_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Gemma 4 API error {response.status}: {error_text}")

                data = await response.json()
                message = data.get("message", {})
                response_text = message.get("content", "")

                thinking_text = message.get("thinking", "") or data.get("thinking", "")
                if thinking_text:
                    response_text = f"<thought>\n{thinking_text}\n</thought>\n\n{response_text}"

                tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                latency_ms = (time.time() - start_time) * 1000
                confidence = 0.95 if actual_thinking else 0.85

                return GenerationResult(
                    response=response_text,
                    model=model,
                    provider="gemma4",
                    confidence=confidence,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata={
                        "total_duration": data.get("total_duration", 0),
                        "thinking_enabled": actual_thinking,
                        "context_window": self.context_window,
                        "regime": regime,
                        "hardware_target": target_url,
                        "anchor_id": anchor_id,
                    },
                )

        except Exception as e:
            logger.exception(f"Gemma 4 generation failed for model {model}")
            raise RuntimeError(f"Gemma 4 generation error: {e}")


# Auto-register Gemma 4 provider
register_model_provider("gemma4", Gemma4Provider)
