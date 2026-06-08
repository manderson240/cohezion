"""Qwen API provider for Cohezion Portfolio — Track 4 submission bridge.

When QWEN_API_KEY is set, portfolio agent requests route to Alibaba Cloud's
Qwen API (OpenAI-compatible endpoint) instead of local Triune inference.
This satisfies the Qwen Track 4 "Autopilot Agent" requirement for Alibaba
Cloud deployment proof while keeping local inference as the default.

Usage (local inference, default)::

    agent = PortfolioAgent()   # uses Triune if available

Usage (Qwen API, Track 4 submission)::

    export QWEN_API_KEY=sk-...
    agent = PortfolioAgent(provider=QwenProvider())
"""

from __future__ import annotations

import logging
import os
from typing import Any


logger = logging.getLogger(__name__)

_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_QWEN_MODEL = "qwen-plus"


class QwenProvider:
    """Thin wrapper around Qwen's OpenAI-compatible API.

    Falls back gracefully when openai package is missing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _QWEN_MODEL,
        base_url: str = _QWEN_BASE_URL,
    ) -> None:
        self._api_key = api_key or os.environ.get("QWEN_API_KEY", "")
        self._model = model
        self._base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        except ImportError:
            raise RuntimeError(
                "openai package required for QwenProvider. Install with: uv pip install openai"
            )
        return self._client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def complete(self, prompt: str, max_tokens: int = 512) -> str:
        """Synchronous completion via Qwen API."""
        if not self._api_key:
            raise RuntimeError("QWEN_API_KEY not set — cannot use QwenProvider")
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""


def get_provider() -> QwenProvider | None:
    """Return a QwenProvider if QWEN_API_KEY is set, else None (use local inference)."""
    api_key = os.environ.get("QWEN_API_KEY", "")
    if not api_key:
        return None
    provider = QwenProvider(api_key=api_key)
    logger.info("QwenProvider active (model=%s)", provider._model)
    return provider
