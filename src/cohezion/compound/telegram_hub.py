"""Fire-and-forget Telegram hub for cross-session communication with OOM-safe local inference.

All methods use a 5-second timeout and never raise — callers are never blocked.
Uses port :13305 (OmniRouter) exclusively.  SessionBus is imported lazily so this
module can be imported even before the sessions package exists.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import httpx

from cohezion.config.defaults import LEMONADE_BASE_URL

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot"
_TIMEOUT = 5.0


class TelegramOOMGuard:
    """Blocks requests to heavy models (>=26B) without ctx_size validation.

    Only models in SAFE_MODELS are allowed through; anything else is remapped
    to the always-safe NPU model so callers cannot accidentally trigger an
    auto-load of a large, unbounded-ctx model on the :13305 OmniRouter (N3).
    """

    SAFE_MODELS: frozenset[str] = frozenset(
        {"llama3.2-1b-FLM", "Gemma-4-E2B-it-GGUF", "Mellum-4b"}
    )

    @classmethod
    def is_safe(cls, model_name: str) -> bool:
        """Return True when *model_name* is on the allowlist."""
        return model_name in cls.SAFE_MODELS

    @classmethod
    def guard(cls, model_name: str) -> str:
        """Return *model_name* if safe; fall back to llama3.2-1b-FLM otherwise."""
        if cls.is_safe(model_name):
            return model_name
        return "llama3.2-1b-FLM"


class TelegramHub:
    """Central communication hub: sessions -> Telegram + Lemonade inference.

    All methods are fire-and-forget (async, 5s timeout).  Never blocks callers.
    Uses port :13305 only (the OmniRouter).  Only dispatches to safe models.

    Importable without Telegram credentials: ``is_configured()`` returns False
    and ``notify`` / ``broadcast_to_sessions`` silently no-op.
    """

    def __init__(self) -> None:
        self._token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self._chat_id: str = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self._lemonade_url: str = LEMONADE_BASE_URL

    def is_configured(self) -> bool:
        """Return True when both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set."""
        return bool(self._token and self._chat_id)

    async def notify(self, message: str, session_id: str = "") -> None:
        """Send session status to Telegram (fire-and-forget, 5s timeout).

        No-ops silently when credentials are not configured.
        """
        if not self.is_configured():
            return
        text = f"[{session_id}] {message}" if session_id else message
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{_TELEGRAM_API}{self._token}/sendMessage",
                    json={"chat_id": self._chat_id, "text": text},
                    timeout=_TIMEOUT,
                )
        except Exception as exc:
            logger.debug("TelegramHub.notify failed: %s", exc)

    async def ask_local(self, prompt: str, model: str = "llama3.2-1b-FLM") -> str:
        """Route *prompt* through OOM-guarded Lemonade inference (:13305).

        Returns the response text, or "" on any timeout or error.  Never raises.
        Only safe models (SAFE_MODELS allowlist) are forwarded; anything else is
        silently remapped to llama3.2-1b-FLM so no large-model auto-load occurs.
        """
        safe_model = TelegramOOMGuard.guard(model)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._lemonade_url}/v1/chat/completions",
                    json={
                        "model": safe_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 256,
                        "stream": False,
                    },
                    timeout=_TIMEOUT,
                )
            if response.status_code != 200:
                logger.debug(
                    "TelegramHub.ask_local: HTTP %s from OmniRouter", response.status_code
                )
                return ""
            choices = response.json().get("choices", [])
            if not choices:
                return ""
            return str(choices[0].get("message", {}).get("content", "")).strip()
        except Exception as exc:
            logger.debug("TelegramHub.ask_local failed: %s", exc)
            return ""

    async def broadcast_to_sessions(self, message: str) -> None:
        """Post an operator message to all active sessions via SessionBus.

        SessionBus is imported lazily; if the sessions package is not yet
        available this method silently no-ops rather than raising ImportError.
        """
        try:
            from cohezion.sessions.session_bus import SessionBus  # noqa: PLC0415
        except ImportError:
            logger.debug("TelegramHub.broadcast_to_sessions: sessions package not available")
            return
        try:
            bus = SessionBus()
            await bus.broadcast(message)
        except Exception as exc:
            logger.debug("TelegramHub.broadcast_to_sessions: bus error: %s", exc)


## FUTURE HOOKS
# - Wire TelegramHub.notify into CompoundExecutor milestone callbacks
#   (step 11 of the 11-step pipeline) to surface completion to operator.
# - Add TelegramOOMGuard.SAFE_MODELS sync from the live :13305 /v1/models
#   endpoint on startup so new FLM models are auto-added to the allowlist.
# - Expose broadcast_to_sessions via the Hermes MCP bridge tool
#   `cohezion_sessions_broadcast` once SCP3 is fully wired.
