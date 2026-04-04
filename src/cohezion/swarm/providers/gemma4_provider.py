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


class Gemma4Provider(OllamaProvider):
    """Gemma 4 provider specializing in reasoning and native tool-calling.

    Features:
    - Native "Thinking Mode" support for deep reasoning
    - 256K token context window support (31B/26B)
    - Optimized for local UMA hardware (AMD ROCm)
    - Structured JSON output integration

    Configuration:
        base_url: Ollama API URL (default: http://localhost:11434)
        thinking_mode: Enable Gemma 4 reasoning (default: True)
        context_window: Default context window size (default: 256000)
        timeout: Request timeout in seconds (default: 120)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize Gemma 4 provider.

        Args:
            config: Optional configuration override
        """
        # Default Gemma 4 config
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

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        """Generate response using Gemma 4 via Ollama Chat API.

        Specialized for Gemma 4's reasoning and multimodal capabilities.
        """
        session = await self._get_session()
        start_time = time.time()

        # Prepare payload for Chat API
        message_content = {"role": "user", "content": prompt}
        
        # Support multimodal inputs (base64 encoded images)
        if "images" in kwargs:
            message_content["images"] = kwargs["images"]

        payload = {
            "model": model,
            "messages": [message_content],
            "stream": False,
            "format": kwargs.get("format", ""),
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "num_ctx": self.context_window,
                "thinking": self.thinking_mode,
                **kwargs.get("options", {}),
            },
        }

        # Add keep_alive if specified
        if self.keep_alive:
            payload["keep_alive"] = self.keep_alive

        try:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Gemma 4 API error {response.status}: {error_text}")

                data = await response.json()

                # Extract message content
                message = data.get("message", {})
                response_text = message.get("content", "")
                
                # Check for thinking field
                thinking_text = message.get("thinking", "") or data.get("thinking", "")
                if thinking_text:
                    response_text = f"<thought>\n{thinking_text}\n</thought>\n\n{response_text}"

                tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                latency_ms = (time.time() - start_time) * 1000

                confidence = 0.95 if self.thinking_mode else 0.85

                return GenerationResult(
                    response=response_text,
                    model=model,
                    provider="gemma4",
                    confidence=confidence,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata={
                        "total_duration": data.get("total_duration", 0),
                        "thinking_enabled": self.thinking_mode,
                        "context_window": self.context_window,
                    },
                )

        except TimeoutError:
            raise RuntimeError(f"Gemma 4 request timed out after {self.timeout}s")

        except Exception as e:
            logger.exception(f"Gemma 4 generation failed for model {model}")
            raise RuntimeError(f"Gemma 4 generation error: {e}")


# Auto-register Gemma 4 provider
register_model_provider("gemma4", Gemma4Provider)
