# src/cohezion/inference/kimi_k3_dispatcher.py
"""Fleet-level reasoning dispatcher for the Kimi K3 model.

This module provides :class:`KimiK3ReasoningDispatcher`, which routes prompts
to a Kimi K3 backend with configurable reasoning effort, maintains an optional
per-agent context cache, and publishes lifecycle events on the Cohezion
``EventBus``.

The module also exposes :func:`verify_kimi_dispatcher`, an isolated async
self-test that exercises the dispatcher without requiring a live API key.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx


# The Cohezion event bus is imported when available.  A minimal fallback is
# provided so the dispatcher and its self-test can be inspected in isolation.
try:
    from cohezion.core.bus import EventBus
except ImportError:  # pragma: no cover

    class EventBus:  # type: ignore[no-redef]
        """No-op fallback used when the real Cohezion bus is not on path."""

        @staticmethod
        async def publish(topic: str, payload: dict[str, Any]) -> None:
            logging.getLogger(__name__).debug(
                "No-op EventBus.publish(%s) payload=%r", topic, payload
            )


logger = logging.getLogger(__name__)

LLM_CALL = "LLM_CALL"
LLM_RESPONSE = "LLM_RESPONSE"
AGENT_COMPLETE = "AGENT_COMPLETE"


class DispatcherError(RuntimeError):
    """Raised when the dispatcher cannot complete an LLM request."""


class KimiK3ReasoningDispatcher:
    """Dispatch prompts to Kimi K3 with reasoning effort and context caching.

    Parameters
    ----------
    reasoning_effort:
        One of ``low``, ``medium`` (default), or ``high``.  Higher effort
        reduces sampling temperature and grants a larger token budget.
    enable_context_cache:
        If ``True`` (default), the dispatcher keeps a per-agent message
        history and includes it in subsequent requests.
    """

    DEFAULT_MODEL: str = "kimi-k3"
    DEFAULT_BASE_URL: str = "https://api.moonshot.cn/v1/chat/completions"
    TIMEOUT_SECONDS: float = 120.0
    MAX_CACHED_TURNS: int = 20

    REASONING_PRESETS: dict[str, dict[str, Any]] = {
        "low": {"temperature": 0.7, "max_tokens": 1024, "top_p": 1.0},
        "medium": {"temperature": 0.5, "max_tokens": 2048, "top_p": 1.0},
        "high": {"temperature": 0.3, "max_tokens": 4096, "top_p": 1.0},
    }

    def __init__(
        self,
        reasoning_effort: str = "medium",
        enable_context_cache: bool = True,
    ) -> None:
        self.reasoning_effort = self._validate_reasoning_effort(reasoning_effort)
        self.enable_context_cache = enable_context_cache

        self.model = os.getenv("KIMI_K3_MODEL", self.DEFAULT_MODEL)
        self.base_url = os.getenv("KIMI_BASE_URL", self.DEFAULT_BASE_URL)
        self.api_key = os.getenv("MOONSHOT_API_KEY", "")
        self.timeout = float(os.getenv("KIMI_TIMEOUT_SECONDS", self.TIMEOUT_SECONDS))

        self._reasoning_params = self.REASONING_PRESETS[self.reasoning_effort]
        self._cache: dict[str, list[dict[str, str]]] = {}
        self._event_bus: Any = EventBus
        self._system_prompt = (
            "You are Kimi K3, a capable coding assistant. Think step by step "
            "when reasoning is required and produce concise, verifiable answers."
        )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    async def dispatch(self, prompt: str, agent_id: str) -> dict[str, Any]:
        """Send ``prompt`` on behalf of ``agent_id`` and return the result.

        The following events are emitted on ``EventBus``:

        * ``LLM_CALL`` before the backend request.
        * ``LLM_RESPONSE`` after the backend response is parsed.
        * ``AGENT_COMPLETE`` after all post-processing is finished.

        Parameters
        ----------
        prompt:
            The user prompt to send.
        agent_id:
            Identifier for the calling agent.  Used for context caching and
            event attribution.

        Returns
        -------
        dict[str, Any]
            A structured result containing the response text, raw backend
            payload, latency, token usage, and dispatcher metadata.

        Raises
        ------
        ValueError
            If ``prompt`` or ``agent_id`` are empty.
        DispatcherError
            If the backend request or response parsing fails.  An
            ``AGENT_COMPLETE`` event with ``success=False`` is still emitted.
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")

        start = time.perf_counter()
        messages = self._build_messages(agent_id, prompt)

        await self._emit(
            LLM_CALL,
            {
                "agent_id": agent_id,
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
                "context_cached": self.enable_context_cache,
                "message_count": len(messages),
                "timestamp": time.time(),
            },
        )

        raw: dict[str, Any] = {}
        error: str | None = None
        response_text = ""

        try:
            raw = await self._call_kimi(messages)
            response_text = self._extract_text(raw)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logger.exception("dispatch failed for agent %s", agent_id)

        latency_ms = int((time.perf_counter() - start) * 1000)
        tokens_used = raw.get("usage", {}).get("total_tokens") if raw else None

        await self._emit(
            LLM_RESPONSE,
            {
                "agent_id": agent_id,
                "model": self.model,
                "response_text": response_text,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "error": error,
                "raw_response": raw,
                "timestamp": time.time(),
            },
        )

        await self._emit(
            AGENT_COMPLETE,
            {
                "agent_id": agent_id,
                "success": error is None,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "error": error,
                "timestamp": time.time(),
            },
        )

        if error:
            raise DispatcherError(error)

        # Keep the assistant turn in cache so follow-up prompts have context.
        if self.enable_context_cache and response_text:
            self._cache[agent_id].append({"role": "assistant", "content": response_text})

        return {
            "agent_id": agent_id,
            "prompt": prompt,
            "response_text": response_text,
            "raw_response": raw,
            "reasoning_effort": self.reasoning_effort,
            "context_cached": self.enable_context_cache,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "cached_messages": max(0, len(messages) - 2),
        }

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #

    def _validate_reasoning_effort(self, value: str) -> str:
        """Normalize and validate the ``reasoning_effort`` option."""
        normalized = (value or "medium").strip().lower()
        if normalized not in self.REASONING_PRESETS:
            raise ValueError(
                f"reasoning_effort must be one of {list(self.REASONING_PRESETS)}; got {value!r}"
            )
        return normalized

    def _build_messages(self, agent_id: str, prompt: str) -> list[dict[str, str]]:
        """Build the chat message list for ``agent_id``."""
        system_msg = {"role": "system", "content": self._system_prompt}
        user_msg = {"role": "user", "content": prompt}

        if not self.enable_context_cache:
            return [system_msg, user_msg]

        history = self._cache.setdefault(agent_id, [system_msg])
        history.append(user_msg)

        # Retain system message plus the most recent turns to bound memory.
        if len(history) > self.MAX_CACHED_TURNS + 1:
            self._cache[agent_id] = [history[0], *history[-self.MAX_CACHED_TURNS :]]

        return self._cache[agent_id]

    async def _emit(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish ``payload`` to ``topic``, tolerating sync or async buses."""
        try:
            result = self._event_bus.publish(topic, payload)
            if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                await result
        except Exception as exc:
            logger.warning("EventBus publish failed for %s: %s", topic, exc)

    async def _call_kimi(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Execute an HTTP request against the Kimi K3 chat completions endpoint."""
        if not self.api_key:
            raise DispatcherError("MOONSHOT_API_KEY is not configured in the environment")

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self._reasoning_params["temperature"],
            "max_tokens": self._reasoning_params["max_tokens"],
            "top_p": self._reasoning_params["top_p"],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=body,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise DispatcherError(
                    f"Kimi API error {response.status_code}: {response.text}"
                ) from exc

            return response.json()

    def _extract_text(self, raw: dict[str, Any]) -> str:
        """Extract the assistant message content from a completions response."""
        try:
            return str(raw["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise DispatcherError(f"Unexpected API response structure: {raw}") from exc


# ------------------------------------------------------------------------- #
# Self-verification
# ------------------------------------------------------------------------- #


async def verify_kimi_dispatcher() -> dict[str, Any]:
    """Run an isolated end-to-end sanity check of :class:`KimiK3ReasoningDispatcher`.

    This function injects a capturing event bus and a fake LLM backend, so it
    does not require network access or a live API key.

    Returns
    -------
    dict[str, Any]
        A report containing ``ok`` (overall pass/fail), per-check results,
        emitted event names, and the dispatcher result.
    """
    captured_events: list[tuple[str, dict[str, Any]]] = []

    class CapturingBus:
        @staticmethod
        async def publish(topic: str, payload: dict[str, Any]) -> None:
            captured_events.append((topic, payload))

    async def fake_call(messages: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "choices": [{"message": {"content": "Verification answer: 4"}}],
            "usage": {
                "total_tokens": 7,
                "prompt_tokens": 5,
                "completion_tokens": 2,
            },
        }

    # Test 1: basic dispatch without caching.
    dispatcher = KimiK3ReasoningDispatcher(reasoning_effort="low", enable_context_cache=False)
    dispatcher._event_bus = CapturingBus()
    dispatcher._call_kimi = fake_call

    result = await dispatcher.dispatch("What is 2 + 2?", "verify-agent")

    # Test 2: context cache grows across two calls.
    cache_dispatcher = KimiK3ReasoningDispatcher(
        reasoning_effort="medium", enable_context_cache=True
    )
    cache_dispatcher._event_bus = CapturingBus()
    cache_dispatcher._call_kimi = fake_call

    await cache_dispatcher.dispatch("First question", "cache-agent")
    cache_result = await cache_dispatcher.dispatch("Second question", "cache-agent")

    required_events = {LLM_CALL, LLM_RESPONSE, AGENT_COMPLETE}
    seen_events = {topic for topic, _ in captured_events}
    missing = required_events - seen_events

    checks = {
        "basic_result_has_agent_id": result.get("agent_id") == "verify-agent",
        "basic_result_has_response": bool(result.get("response_text")),
        "basic_latency_present": isinstance(result.get("latency_ms"), int),
        "basic_tokens_present": isinstance(result.get("tokens_used"), int),
        "all_required_events_emitted": not missing,
        "context_cache_grew": cache_result.get("cached_messages", 0) > 0,
    }

    return {
        "ok": all(checks.values()),
        "checks": checks,
        "missing_events": sorted(missing),
        "events_emitted": sorted(seen_events),
        "basic_result": result,
        "cache_result": cache_result,
    }


if __name__ == "__main__":
    import sys

    async def _main() -> None:
        outcome = await verify_kimi_dispatcher()
        print(outcome)
        sys.exit(0 if outcome["ok"] else 1)

    asyncio.run(_main())
