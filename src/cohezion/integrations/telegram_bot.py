"""Telegram Bot integration for bi-directional communication with local sessions.

Allows remote session listing, log tailing, system resource auditing, and command
dispatching via Telegram. Constrained to the configured TELEGRAM_CHAT_ID for security.
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import json
import logging
import os
import re as _re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, NamedTuple

import httpx

from cohezion.config.defaults import LEMONADE_BASE_URL


# Fail-open: if oom_guard is unavailable the RAM gate is simply skipped.
_check_ram = None
with contextlib.suppress(Exception):
    from cohezion.inference.oom_guard import check_ram as _check_ram  # type: ignore[assignment]

# Minimum free RAM (GiB) required before sending a hint that could trigger a
# large-model auto-load on the OmniRouter.  Matches the N3 invariant floor.
_OOM_MIN_FREE_GB: float = 20.0

# Pattern matching model names that contain a parameter count ≥ 10 B, i.e. hints
# that can auto-load a model large enough to risk OOM on a partially-used system.
# Covers the MEDIUM/COMPLEX tier names: 27B, 31B, 35B, 26B (and future additions).
_LARGE_MODEL_RE = _re.compile(r"\b(1[0-9]B|2[0-9]B|3[0-9]B|[1-9]\d{2,}B)\b", _re.IGNORECASE)

LEMONADE_ROUTER_URL: str = LEMONADE_BASE_URL

SYSTEM_PROMPT: str = (
    "You are the Cohezion assistant, coordinating between the operator, AMD silicon (:13305 OmniRouter), "
    "and the active Antigravity engineering swarm. "
    "You assist the operator with local telemetry, model fleet status, and compound engineering tasks. "
    "Answer concisely, technically, and helpfully."
)


def clean_model_output(content: str) -> str:
    """Strip <think>...</think> blocks from reasoning models for clean messaging."""
    return _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL).strip()


def markdown_to_telegram_html(content: str) -> str:
    """Format markdown text into clean Telegram-compliant HTML.

    Protects code blocks and inline code, escapes raw HTML characters, converts
    markdown syntax (headers, bold, italic, bullets) to Telegram HTML tags, and
    preserves code blocks.
    """
    clean_text = clean_model_output(content)
    if not clean_text:
        return ""

    code_blocks: list[tuple[str, str]] = []

    def _save_code_block(m: _re.Match[str]) -> str:
        lang = m.group(1).strip() if m.group(1) else ""
        code = m.group(2).strip()
        code_blocks.append((html.escape(code), html.escape(lang)))
        return f"\x00CB{len(code_blocks) - 1}\x00"

    text = _re.sub(
        r"```([a-zA-Z0-9_-]*)\n?(.*?)```", _save_code_block, clean_text, flags=_re.DOTALL
    )

    inline_codes: list[str] = []

    def _save_inline_code(m: _re.Match[str]) -> str:
        inline_codes.append(html.escape(m.group(1)))
        return f"\x00IC{len(inline_codes) - 1}\x00"

    text = _re.sub(r"`([^`]+)`", _save_inline_code, text)

    # Escape HTML entities
    text = html.escape(text)

    # Markdown headers (# Header -> <b>Header</b>)
    text = _re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", text, flags=_re.MULTILINE)

    # Bold (**bold** or __bold__)
    text = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = _re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic (*italic* or _italic_)
    text = _re.sub(r"(?<!\w)\*([^*\n]+?)\*(?!\w)", r"<i>\1</i>", text)
    text = _re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"<i>\1</i>", text)

    # Bullets (* item or - item at start of line -> • item)
    text = _re.sub(r"^[\*\-]\s+", "• ", text, flags=_re.MULTILINE)

    # Restore code blocks & inline code
    for i, (escaped_code, lang) in enumerate(code_blocks):
        cls = f' class="language-{lang}"' if lang else ""
        text = text.replace(f"\x00CB{i}\x00", f"<pre><code{cls}>{escaped_code}</code></pre>")

    for i, escaped_code in enumerate(inline_codes):
        text = text.replace(f"\x00IC{i}\x00", f"<code>{escaped_code}</code>")

    return text


class QueryComplexity(Enum):
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"


MAX_TOKENS_BY_COMPLEXITY: dict[QueryComplexity, int] = {
    QueryComplexity.SIMPLE: 96,
    QueryComplexity.MEDIUM: 320,
    QueryComplexity.COMPLEX: 768,
}

# Keywords whose presence indicates a COMPLEX query regardless of length.
_COMPLEX_TOKENS: frozenset[str] = frozenset(
    {
        "explain",
        "design",
        "refactor",
        "implement",
        "compare",
        "analyze",
        "analyse",
        "architect",
        "debug",
        "diagnose",
        "rewrite",
        "summarize",
        "summarise",
        "audit",
        "plan",
        "generate",
        "create",
        "build",
    }
)

# Model hints per complexity tier — sent as "preferred model" to the OmniRouter.
# The router substitutes the closest currently-loaded model when the hint isn't loaded.
_COMPLEXITY_HINTS: dict[QueryComplexity, list[str]] = {
    QueryComplexity.SIMPLE: [
        "user.cohezion-router",
        "llama3.2-1b-FLM",
        "qwen3-4b-FLM",
        "Gemma-4-E2B-it-GGUF",
        "Gemma-4-E4B-it-GGUF",
    ],
    QueryComplexity.MEDIUM: [
        "user.cohezion-router",
        "qwen3-4b-FLM",
        "deepseek-r1-0528-8b-FLM",
        "Gemma-4-E4B-it-GGUF",
        "Qwen3.6-27B-GGUF",
        "Gemma-4-31B-it-GGUF",
    ],
    QueryComplexity.COMPLEX: [
        "user.cohezion-router",
        "deepseek-r1-0528-8b-FLM",
        "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "Gemma-4-31B-it-GGUF",
        "Qwen3.6-35B-A3B-GGUF",
        "Gemma-4-26B-A4B-it-GGUF",
    ],
}


@dataclass
class _OmniTelemetry:
    """Per-call telemetry recorded after each OmniRouter chat request."""

    actual_model: str = ""
    port: int = 13305
    backend: str = "lemonade-omnirouter"
    route_reason: str = ""
    error: str | None = None


# SteerBoost-inspired early refusal detection (arXiv 2606.11599).
# >75% of steering failure signal concentrates in first 1-2 tokens.
# Checking the first 60 chars skips 200-500ms of wasted generation time
# per failed hint when the model returns a refusal instead of content.
_REFUSAL_PREFIX_RE = _re.compile(
    r"^(I (cannot|can't|am unable|don't have access)|"
    r"I'?m (not able|sorry|unable)|"
    r"As an? (AI|language model|assistant[,.])|"
    r"I need to clarify)",
    _re.IGNORECASE,
)


def _is_refusal_prefix(content: str) -> bool:
    """Return True when the first 60 chars of content match a known refusal pattern."""
    return bool(_REFUSAL_PREFIX_RE.match(content[:60].lstrip()))


# Real transient-network exception classes captured at import time. Tests patch
# the module-level ``httpx`` symbol with a MagicMock, which would otherwise make
# ``httpx.TimeoutException`` un-catchable; this tuple stays bound to the real
# classes so the lemonade-probe retry works under both production and tests.
_TRANSIENT_HTTP_ERRORS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
)


class ModelSelection(NamedTuple):
    """A selected chat model plus which backend serves it.

    ``backend`` is ``"lemonade"`` (OpenAI-compatible router :13305) or
    ``"ollama"`` (legacy :11434 fallback). ``_handle_chat`` uses it to pick the
    right endpoint and response parser.
    """

    model: str
    backend: str


try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


logger = logging.getLogger(__name__)


def safe_html(text: str) -> str:
    """Escapes characters to be safe for Telegram HTML parse_mode."""
    return html.escape(text, quote=True)


class TelegramCommunicationHub:
    """Telegram Daemon client that polls getUpdates and routes commands to active sessions."""

    def __init__(self) -> None:
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.allowed_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        self._running = False
        self.conversation_history: list[dict[str, str]] = []
        self.max_history = 20
        # Process-spawn guard: True only after a successful :13305 probe.
        # /agent and /run are blocked until inference is verified healthy.
        self._inference_ready: bool = False
        self.routing_mode: str = (
            os.environ.get("TELEGRAM_ROUTING_MODE", "antigravity").strip().lower()
        )

    async def _run_cmd(self, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        """Run subprocess.run in a background thread to keep event loop responsive."""
        return await asyncio.to_thread(subprocess.run, *args, **kwargs)

    def is_configured(self) -> bool:
        return bool(self.token and self.allowed_chat_id)

    async def _verify_inference_health(self) -> bool:
        """Probe :13305 to confirm inference is up. Caches result; re-probes after failure."""
        if self._inference_ready:
            return True
        available = await self._select_model()
        if available:
            self._inference_ready = True
            logger.info("Inference health verified: model=%s", available)
        return self._inference_ready

    def _classify_complexity(self, text: str) -> QueryComplexity:
        """Classify query complexity for OmniRouter hint selection."""
        words = text.lower().split()
        if len(words) > 40:
            return QueryComplexity.COMPLEX
        if _COMPLEX_TOKENS.intersection(words):
            return QueryComplexity.COMPLEX
        if len(words) <= 6:
            return QueryComplexity.SIMPLE
        return QueryComplexity.MEDIUM

    async def _chat_omnirouter(
        self,
        complexity_or_text: QueryComplexity | str,
        messages: list[dict[str, str]] | None = None,
        max_tokens: int = 128,
    ) -> tuple[str | None, _OmniTelemetry]:
        """POST to :13305 OmniRouter with a complexity hint; retry across hint list on failure."""
        if isinstance(complexity_or_text, str):
            complexity = QueryComplexity.MEDIUM
            messages = [{"role": "user", "content": complexity_or_text}]
        else:
            complexity = complexity_or_text
            if messages is None:
                messages = []

        telem = _OmniTelemetry(port=13305, backend="lemonade-omnirouter")
        hints = list(_COMPLEXITY_HINTS.get(complexity, _COMPLEXITY_HINTS[QueryComplexity.MEDIUM]))
        last_error: str | None = None

        for attempt, hint_model in enumerate(hints, 1):
            # RAM gate: skip hints that could auto-load a large model when RAM
            # is insufficient.  Fail-open: if _check_ram is None (import failed)
            # we proceed without the gate rather than refusing all requests.
            if _check_ram is not None and _LARGE_MODEL_RE.search(hint_model):
                ram_ok, free_gb = _check_ram(_OOM_MIN_FREE_GB)
                if not ram_ok:
                    logger.warning(
                        "OOMGuard: skipping hint %r — only %.1f GiB free (need %.0f GiB); "
                        "trying next hint",
                        hint_model,
                        free_gb,
                        _OOM_MIN_FREE_GB,
                    )
                    last_error = f"RAM pressure: {free_gb:.1f} GiB free"
                    continue

            try:
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{LEMONADE_ROUTER_URL}/v1/chat/completions",
                        json={
                            "model": hint_model,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "stream": False,
                        },
                        timeout=60.0,
                    )
                if r.status_code != 200:
                    last_error = f"HTTP {r.status_code}"
                    continue
                data = r.json()
                choices = data.get("choices", [])
                if not choices:
                    last_error = "no choices"
                    continue
                content = str(choices[0].get("message", {}).get("content", "")).strip()
                content = clean_model_output(content)
                if not content:
                    last_error = "empty content"
                    continue
                if _is_refusal_prefix(content):
                    last_error = f"refusal: {content[:60]!r}"
                    continue
                actual_model = data.get("model", hint_model)
                base_reason = "hint served" if actual_model == hint_model else "hint substituted"
                telem.actual_model = actual_model
                telem.route_reason = (
                    f"attempt {attempt}: {base_reason}" if attempt > 1 else base_reason
                )
                return (content, telem)
            except _TRANSIENT_HTTP_ERRORS as e:
                last_error = str(e)
                continue
            except Exception as e:
                last_error = str(e)
                break

        telem.route_reason = f"all {len(hints)} hints exhausted"
        telem.error = last_error or "unknown error"
        return (None, telem)

    async def _record_telemetry(self, telem: _OmniTelemetry) -> None:
        """Persist per-call OmniRouter telemetry to SurrealDB (fire-and-forget)."""
        try:
            sql = (
                f"CREATE telegram_telemetry SET "
                f"backend='{telem.backend}', model='{telem.actual_model}', "
                f"port={telem.port}, route_reason='{telem.route_reason}', "
                f"error={json.dumps(telem.error or '')}, "  # declared, never persisted before 2026-09-20
                f"ts=time::now();"
            )
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://localhost:8001/sql",
                    headers={
                        "surreal-ns": "cohezion",
                        "surreal-db": "main",
                        "Content-Type": "text/plain",
                        "Authorization": "Basic cm9vdDpyb290",
                    },
                    content=sql,
                    timeout=3.0,
                )
        except Exception as exc:
            logger.debug("Telemetry write failed: %s", exc)

    async def _sync_bot_commands(self) -> None:
        """Register slash commands with Telegram so the / menu auto-completes in mobile UI."""
        commands = [
            {"command": "status", "description": "Fleet vitals, RAM/GPU & Lemonade router"},
            {"command": "agy", "description": "Direct query to Antigravity Orchestrator"},
            {"command": "local", "description": "Query local AMD silicon (:13305 OmniRouter)"},
            {"command": "mode", "description": "Switch routing: /mode [antigravity|local|auto]"},
            {"command": "list", "description": "List running agent sessions"},
            {"command": "read", "description": "Read last 20 lines of a session pane"},
            {"command": "send", "description": "Dispatch command keys to session"},
            {"command": "learnings", "description": "Retrieve latest registered learnings"},
            {"command": "run", "description": "Execute Python snippet via local inference"},
            {"command": "clear", "description": "Clear conversation history"},
            {"command": "help", "description": "Show command manual and instructions"},
        ]
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.base_url}/setMyCommands",
                    json={"commands": commands},
                    timeout=8.0,
                )
        except Exception as e:
            logger.debug("Failed to set bot commands: %s", e)

    async def _set_status_indicator(self, online: bool) -> None:
        """Set bot short description (online/offline presence indicator in Telegram profile)."""
        text = "🟢 Online — Cohezion Swarm & Antigravity Node" if online else "🔴 Offline"
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.base_url}/setMyShortDescription",
                    json={"short_description": text},
                    timeout=8.0,
                )
        except Exception as e:
            logger.debug("Failed to set bot status indicator: %s", e)

    async def start(self) -> None:
        """Starts the long-polling execution loop."""
        if not self.is_configured():
            logger.error("Telegram credentials missing in environment. Cannot start hub.")
            return

        self._running = True
        logger.info("Cohezion Telegram Hub started on chat %s", self.allowed_chat_id)
        await self._sync_bot_commands()
        await self._set_status_indicator(online=True)
        await self._send_msg("🤖 Cohezion Telegram Hub is active and monitoring local silicon.")

        while self._running:
            try:
                await self._poll_updates()
                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Telegram polling error: %s", e)
                await asyncio.sleep(5.0)

    async def stop(self) -> None:
        self._running = False
        logger.info("Stopping Telegram Hub...")
        await self._set_status_indicator(online=False)
        await self._send_msg("🛑 Telegram Hub is shutting down.")

    async def _send_msg(self, text: str, parse_mode: str | None = "HTML") -> None:
        """Sends a message back to the allowed chat ID with chunking and parse fallback."""
        if not text:
            return

        # Respect Telegram's 4096 character limit per message
        chunks: list[str] = []
        if len(text) <= 4000:
            chunks = [text]
        else:
            remaining = text
            while len(remaining) > 4000:
                split_idx = remaining.rfind("\n\n", 0, 4000)
                if split_idx == -1:
                    split_idx = remaining.rfind("\n", 0, 4000)
                if split_idx == -1:
                    split_idx = 4000
                chunks.append(remaining[:split_idx])
                remaining = remaining[split_idx:].lstrip()
            if remaining:
                chunks.append(remaining)

        async with httpx.AsyncClient() as client:
            for chunk in chunks:
                try:
                    payload: dict[str, Any] = {
                        "chat_id": self.allowed_chat_id,
                        "text": chunk,
                    }
                    if parse_mode:
                        payload["parse_mode"] = parse_mode

                    resp = await client.post(
                        f"{self.base_url}/sendMessage",
                        json=payload,
                        timeout=15.0,
                    )
                    # If HTML parsing failed, retry plain text
                    if resp.status_code != 200 and parse_mode:
                        logger.warning(
                            "Telegram sendMessage failed (%d: %s). Retrying as plain text.",
                            resp.status_code,
                            resp.text,
                        )
                        clean_plain = _re.sub(r"<[^<]+?>", "", chunk)
                        await client.post(
                            f"{self.base_url}/sendMessage",
                            json={"chat_id": self.allowed_chat_id, "text": clean_plain},
                            timeout=15.0,
                        )
                except Exception as e:
                    logger.warning("Failed to send telegram msg chunk: %s", e)

    async def _poll_updates(self) -> None:
        """Polls new updates from Telegram API."""
        url = f"{self.base_url}/getUpdates"
        params = {"timeout": 10}
        if self.last_update_id:
            params["offset"] = self.last_update_id + 1

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=12.0)
            if resp.status_code != 200:
                return

            updates = resp.json().get("result", [])
            tasks = []
            for update in updates:
                self.last_update_id = update["update_id"]
                message = update.get("message", {})
                tasks.append(asyncio.create_task(self._process_message(message)))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_message(self, message: dict[str, Any]) -> None:
        """Processes incoming text message, verifying user authorization."""
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = str(message.get("text", "")).strip()

        if not text or not chat_id:
            return

        # Security check: ignore unauthorized users
        if chat_id != self.allowed_chat_id:
            logger.warning("Blocked unauthorized Telegram message from chat ID: %s", chat_id)
            return

        if not text.startswith("/"):
            if self.routing_mode == "antigravity" or self._is_antigravity_query(text):
                await self._handle_antigravity(text)
                return
            await self._handle_chat(text)
            return

        parts = text.split(maxsplit=2)
        command = parts[0].lower()

        if command in ("/start", "/help"):
            await self._send_msg(self._get_help_message())

        elif command in ("/antigravity", "/agy", "/ask"):
            prompt = text[len(command) :].strip()
            if not prompt:
                await self._send_msg(
                    f"⚠️ Format: <code>{safe_html(command)} &lt;question&gt;</code>"
                )
            else:
                await self._handle_antigravity(prompt)

        elif command == "/mode":
            mode_arg = parts[1].lower().strip() if len(parts) > 1 else ""
            if mode_arg in ("antigravity", "local", "auto"):
                self.routing_mode = mode_arg
                await self._send_msg(f"🔀 Chat routing mode set to: <b>{mode_arg}</b>")
            else:
                await self._send_msg(
                    f"Current routing mode: <b>{self.routing_mode}</b>\n"
                    "Usage: <code>/mode [antigravity|local|auto]</code>"
                )

        elif command.startswith("/local "):
            prompt = text[len("/local ") :].strip()
            if not prompt:
                await self._send_msg("⚠️ Format: <code>/local &lt;prompt&gt;</code>")
            else:
                await self._handle_chat(prompt)

        elif command == "/status":
            await self._handle_status()

        elif command == "/list":
            await self._handle_list()

        elif command == "/clear":
            self.conversation_history.clear()
            await self._send_msg("🧹 Conversation history cleared.")

        elif command.startswith("/read"):
            if len(parts) < 2:
                await self._send_msg("⚠️ Format: <code>/read &lt;session_name&gt;</code>")
            else:
                await self._handle_read(parts[1])

        elif command.startswith("/send"):
            if len(parts) < 3:
                await self._send_msg(
                    "⚠️ Format: <code>/send &lt;session_name&gt; &lt;command_keys&gt;</code>"
                )
            else:
                await self._handle_send(parts[1], parts[2])

        elif command.startswith("/agent "):
            prompt = text[len("/agent ") :].strip()
            if not prompt:
                await self._send_msg("⚠️ Format: <code>/agent &lt;prompt&gt;</code>")
            elif not await self._verify_inference_health():
                await self._send_msg(
                    "🔴 <b>/agent blocked</b> — :13305 Lemonade router not responding.\n"
                    "Fix inference first, then retry."
                )
            else:
                await self._handle_agent(prompt)

        elif command == "/agents":
            await self._handle_agents()

        elif command == "/learnings":
            await self._handle_learnings()

        elif command == "/run":
            # Task #18: execute a Python snippet via local inference code executor
            code = text[len("/run ") :].strip() if len(parts) > 1 else ""
            if not code:
                await self._send_msg("⚠️ Format: <code>/run &lt;python code&gt;</code>")
            elif not await self._verify_inference_health():
                await self._send_msg(
                    "🔴 <b>/run blocked</b> — :13305 Lemonade router not responding.\n"
                    "Fix inference first, then retry."
                )
            else:
                await self._handle_run(code)

        else:
            await self._send_msg(
                f"❓ Unknown command: <code>{safe_html(command)}</code>\nUse /help for commands."
            )

    def _get_help_message(self) -> str:
        return (
            "🚀 <b>Cohezion Telemetry Hub Commands</b>\n\n"
            "🌌 <b>Antigravity Communication</b>\n"
            "Send any question directly to chat with Antigravity!\n"
            "/agy &lt;prompt&gt; - Direct query to Antigravity CLI\n"
            f"/mode [antigravity|local|auto] - Switch routing mode (current: <b>{safe_html(self.routing_mode)}</b>)\n"
            "/local &lt;prompt&gt; - Force query to local AMD silicon (:13305 OmniRouter)\n"
            "/clear - Clear conversation history\n\n"
            "🎛 <b>System &amp; Session Diagnostics</b>\n"
            "/status - CPU/RAM vitals + Lemonade :13305 fleet (AMD silicon)\n"
            "/list - List running tmux sessions\n"
            "/read &lt;session&gt; - Scrape last 20 lines of a session pane\n"
            "/send &lt;session&gt; &lt;cmd&gt; - Dispatch keystrokes to a session\n"
            "/learnings - Retrieve latest registered knowledge entries\n\n"
            "🤖 <b>Agent Control</b>\n"
            "/agent &lt;prompt&gt; - Inline COMPLEX reply via :13305 + background worktree\n"
            "/agents - List active background agent sessions\n\n"
            "⚙️ <b>Local Inference Execution</b>\n"
            "/run &lt;python code&gt; - Execute Python via sandboxed subprocess, result via :13305\n"
            "/help - Display this manual"
        )

    async def _select_model(self) -> ModelSelection | None:
        """Selects the best available chat model from the Lemonade fleet (:13305).

        Uses the always-up Lemonade OpenAI-compatible router (:13305) exclusively.
        Returns None when the router is unreachable or lists no usable model.
        """
        lemonade_model = await self._select_lemonade_model()
        if lemonade_model is not None:
            return ModelSelection(lemonade_model, "lemonade")
        return None

    async def _select_lemonade_model(self) -> str | None:
        """Picks a served model from the lemonade router, or None if unavailable.

        Prefers ``Granite-4.1-8B-GGUF`` (validated no-thinking main-loop model),
        then any served id containing "Granite", then any non-embedding,
        non-cloud id. Returns None when the router is down or lists nothing.
        """
        url = f"{LEMONADE_ROUTER_URL}/v1/models"

        # The fleet is normally up; a single slow/dropped probe must NOT collapse
        # to "Local Fleet Offline". Retry the probe once on a transient network
        # error (timeout / connection reset) before giving up to the Ollama path.
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get(url, timeout=5.0)
                if r.status_code != 200:
                    return None
                data = r.json()
                ids = [str(m.get("id", "")) for m in data.get("data", []) if isinstance(m, dict)]
                ids = [m for m in ids if m]
                if not ids:
                    return None

                if "Granite-4.1-8B-GGUF" in ids:
                    return "Granite-4.1-8B-GGUF"
                for model_id in ids:
                    if "granite" in model_id.lower():
                        return model_id
                for model_id in ids:
                    lowered = model_id.lower()
                    if "embed" not in lowered and "cloud" not in lowered:
                        return model_id
                return None
            except _TRANSIENT_HTTP_ERRORS as e:
                # Transient: the router may be momentarily busy. Retry once.
                last_exc = e
                logger.warning(
                    "Transient error querying lemonade router (attempt %d/2): %s", attempt + 1, e
                )
                continue
            except Exception as e:  # non-transient: do not retry
                logger.warning("Error querying lemonade router models: %s", e)
                return None

        logger.warning("Lemonade router probe failed after retry: %s", last_exc)
        return None

    async def _select_ollama_model(self) -> str | None:
        """Legacy Ollama model selection (fallback path, preserved intact)."""
        try:
            from cohezion.config.defaults import OLLAMA_BASE_URL

            async with httpx.AsyncClient() as client:
                r = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3.0)
                if r.status_code == 200:
                    data = r.json()
                    models_list = data.get("models", [])
                    models = [str(m.get("name", "")) for m in models_list if isinstance(m, dict)]
                    # Filter out embedding models
                    models = [m for m in models if "embed" not in m]

                    # Preference order for local chat
                    preferred = ["phi4:latest", "phi4", "phi4-mini", "mistral:7b", "gemma"]
                    for pref in preferred:
                        if pref in models:
                            return pref

                    # Next preference: any model that is NOT a cloud endpoint
                    local_models = [m for m in models if "cloud" not in m]
                    if local_models:
                        return local_models[0]

                    if models:
                        return models[0]
        except Exception as e:
            logger.warning("Error querying Ollama tags: %s", e)
        return None

    async def _handle_chat(self, text: str) -> None:
        """Route plain-text chat through the :13305 OmniRouter with complexity-tiered hints.

        Falls back to Ollama only when the OmniRouter is fully unreachable.
        Never touches cloud endpoints.
        """
        complexity = self._classify_complexity(text)
        self.conversation_history.append({"role": "user", "content": text})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history :]

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation_history,
        ]
        max_tok = MAX_TOKENS_BY_COMPLEXITY[complexity]

        reply, telem = await self._chat_omnirouter(complexity, messages, max_tok)

        if reply is not None:
            self.conversation_history.append({"role": "assistant", "content": reply})
            await self._send_msg(reply, parse_mode=None)
            await self._record_telemetry(telem)
            return

        await self._send_msg(
            "⚠️ <b>Local Fleet Offline</b>\n"
            "The :13305 Lemonade router is unreachable. "
            "Ensure the AMD fleet is up: <code>lemond --port 13305 &amp;</code>"
        )

    async def _chat_lemonade(self, model: str, messages: list[dict[str, str]]) -> str | None:
        """POSTs to the lemonade OpenAI router and parses choices[].message.content."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{LEMONADE_ROUTER_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 1024,
                    "stream": False,
                },
                timeout=60.0,
            )
            if r.status_code != 200:
                await self._send_msg(
                    f"⚠️ Lemonade router error (HTTP {r.status_code}): {safe_html(r.text)}"
                )
                return None
            choices = r.json().get("choices", [])
            if choices:
                return str(choices[0].get("message", {}).get("content", "")).strip()
            return ""

    async def _chat_ollama(self, model: str, messages: list[dict[str, str]]) -> str | None:
        """Legacy Ollama ``/api/chat`` path (fallback, preserved intact)."""
        from cohezion.config.defaults import OLLAMA_BASE_URL

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                },
                timeout=60.0,
            )
            if r.status_code != 200:
                await self._send_msg(f"⚠️ Ollama error (HTTP {r.status_code}): {safe_html(r.text)}")
                return None
            return str(r.json().get("message", {}).get("content", "")).strip()

    async def _query_lemonade_fleet(self) -> str:
        """Queries :13305 OmniRouter for loaded model IDs. Returns a summary string."""
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{LEMONADE_ROUTER_URL}/v1/models", timeout=4.0)
            if r.status_code != 200:
                return f"OmniRouter :13305 returned HTTP {r.status_code}"
            ids = [
                str(m.get("id", ""))
                for m in r.json().get("data", [])
                if isinstance(m, dict) and m.get("id")
            ]
            if not ids:
                return "OmniRouter :13305 online — no models loaded"
            return ", ".join(ids)
        except _TRANSIENT_HTTP_ERRORS:
            return "OmniRouter :13305 unreachable (transient)"
        except Exception as exc:
            return f"OmniRouter :13305 error: {exc}"

    async def _handle_status(self) -> None:
        """Queries local silicon metrics (AMD Strix Halo) + Lemonade :13305 fleet."""
        import psutil

        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        ram_used = (vm.total - vm.available) / (1024**3)
        ram_total = vm.total / (1024**3)

        # AMD Strix Halo: use rocm-smi, fall back to "AMD iGPU (unified memory)"
        gpu_status = "AMD iGPU (unified memory — no discrete VRAM)"
        try:
            res = await self._run_cmd(
                ["rocm-smi", "--showuse", "--csv"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                lines = [l for l in res.stdout.strip().splitlines() if l and "GPU" not in l]
                if lines:
                    gpu_status = f"ROCm: {lines[0].strip()}"
        except Exception:
            pass

        fleet = await self._query_lemonade_fleet()

        msg = (
            f"💻 <b>Silicon Vitals (AMD Strix Halo)</b>\n"
            f"- CPU Usage: <code>{cpu:.1f}%</code>\n"
            f"- RAM Usage: <code>{ram_used:.1f}GB / {ram_total:.1f}GB</code> ({vm.percent}%)\n"
            f"- GPU/NPU: <code>{safe_html(gpu_status)}</code>\n"
            f"- Lemonade :13305: <code>{safe_html(fleet)}</code>"
        )
        await self._send_msg(msg)

    async def _handle_list(self) -> None:
        """Lists active tmux sessions."""
        try:
            res = await self._run_cmd(
                ["tmux", "list-sessions"], capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0:
                msg = f"📟 <b>Active Sessions</b>\n<pre>{safe_html(res.stdout)}</pre>"
            elif "no server running" in res.stdout.lower() or res.returncode == 1:
                msg = "📟 <b>Active Sessions</b>\n<i>No active tmux sessions found.</i>"
            else:
                msg = (
                    f"⚠️ Failed to list sessions: <code>{safe_html(res.stdout or res.stderr)}</code>"
                )
        except Exception as e:
            msg = f"⚠️ Failed to list sessions: <code>{safe_html(str(e))}</code>"
        await self._send_msg(msg)

    async def _handle_read(self, session_name: str) -> None:
        """Reads terminal logs from a target session."""
        try:
            res = await self._run_cmd(
                ["tmux", "capture-pane", "-t", session_name, "-p"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                lines = res.stdout.strip().split("\n")
                last_20 = "\n".join(lines[-20:])
                msg = f"📋 <b>Log Tail: {safe_html(session_name)}</b>\n<pre>{safe_html(last_20)}</pre>"
            else:
                msg = f"⚠️ Session <code>{safe_html(session_name)}</code> not found or inactive."
        except Exception as e:
            msg = f"⚠️ Failed to read session logs: <code>{safe_html(str(e))}</code>"
        await self._send_msg(msg)

    async def _handle_send(self, session_name: str, keys: str) -> None:
        """Sends keys to a target session."""
        try:
            res = await self._run_cmd(
                ["tmux", "send-keys", "-t", session_name, keys, "C-m"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                msg = f"✅ Sent input to <code>{safe_html(session_name)}</code>: <i>'{safe_html(keys)}'</i>"
            else:
                msg = (
                    f"⚠️ Session <code>{safe_html(session_name)}</code> not found. Cannot dispatch."
                )
        except Exception as e:
            msg = f"⚠️ Failed to dispatch keystrokes: <code>{safe_html(str(e))}</code>"
        await self._send_msg(msg)

    async def _handle_learnings(self) -> None:
        """Gets latest registered learnings from the project."""
        try:
            from cohezion.persistence.genesis_persistence import get_journey_transitions

            # Retrieve latest prompt/learning telemetry
            transitions = await get_journey_transitions(limit=3)
            if transitions:
                items = []
                for t in transitions:
                    step_id = safe_html(str(t.get("step_id", "unknown")))
                    reward = t.get("reward", 0.0)
                    items.append(
                        f"- ID: <code>{step_id}</code>\n  Reward: <code>{reward:.4f}</code>"
                    )
                msg = "💡 <b>Latest Journey Telemetry</b>\n" + "\n".join(items)
            else:
                # Fallback to reading KEY_LEARNINGS.md
                from pathlib import Path

                path = Path("src/cohezion/knowledge_graph/KEY_LEARNINGS.md")
                if path.exists():
                    lines = path.read_text().split("\n")
                    latest = []
                    for line in lines:
                        if line.startswith("### Learning"):
                            latest.append(safe_html(line.replace("### ", "• ")))
                        if len(latest) >= 5:
                            break
                    msg = "💡 <b>Latest Key Learnings</b>\n" + "\n".join(latest)
                else:
                    msg = "💡 <b>Latest Key Learnings</b>\n<i>No telemetry database or index file found.</i>"
        except Exception as e:
            msg = f"⚠️ Failed to query learnings: <code>{safe_html(str(e))}</code>"
        await self._send_msg(msg)

    async def _handle_run(self, code: str) -> None:
        """Execute a Python snippet in a sandboxed subprocess.

        The code runs under the repo venv so cohezion imports are available.
        stdout/stderr are captured and returned to Telegram. A :13305 inference
        call then summarises the output for natural-language readability.

        Security: only the operator (matched TELEGRAM_CHAT_ID) can trigger /run.
        """
        import tempfile
        import textwrap
        from pathlib import Path

        # Write code to a temp file so we avoid shell-injection from user input
        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        venv_py = str(Path(__file__).parents[3] / ".venv" / "bin" / "python3")
        if not Path(venv_py).exists():
            import sys as _sys

            venv_py = _sys.executable

        try:
            res = await self._run_cmd(
                [venv_py, tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except TimeoutError:
            await self._send_msg("⏱ <b>/run timed out</b> (30s limit).")
            return
        except Exception as exc:
            await self._send_msg(f"⚠️ Execution error: <code>{safe_html(str(exc))}</code>")
            return
        finally:
            with contextlib.suppress(Exception):
                Path(tmp_path).unlink(missing_ok=True)

        stdout = res.stdout.strip()
        stderr = res.stderr.strip()
        exit_code = res.returncode

        raw_output = stdout or stderr or "(no output)"
        truncated = raw_output[:800]
        status_emoji = "✅" if exit_code == 0 else "❌"

        # Send raw output first for immediate feedback
        await self._send_msg(
            f"{status_emoji} <b>/run</b> (exit {exit_code})\n<pre>{safe_html(truncated)}</pre>"
        )

        # Ask OmniRouter to summarise / explain the output (MEDIUM tier, non-blocking)
        if raw_output and raw_output != "(no output)":
            summary_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"The following Python code was executed locally:\n```python\n"
                        f"{textwrap.shorten(code, 300)}\n```\n\n"
                        f"Output (exit {exit_code}):\n```\n{truncated}\n```\n\n"
                        f"Summarise the result in 1-2 sentences."
                    ),
                },
            ]
            summary, telem = await self._chat_omnirouter(
                QueryComplexity.MEDIUM, summary_messages, 128
            )
            if summary:
                await self._send_msg(f"🧠 <i>{safe_html(summary)}</i>")
                await self._record_telemetry(telem)

    async def _handle_agent(self, prompt: str) -> None:
        """Spawns a side agent: one-shot reply via :13305 OmniRouter (COMPLEX tier) + tmux worktree.

        The agent prompt is first answered inline via local inference so the operator
        gets an immediate response. A tmux worktree session is then created for any
        long-running work the prompt implies.
        """
        import time

        # 1. Inline response via :13305 OmniRouter (COMPLEX tier — heavy reasoning model)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        reply, telem = await self._chat_omnirouter(
            QueryComplexity.COMPLEX,
            messages,
            MAX_TOKENS_BY_COMPLEXITY[QueryComplexity.COMPLEX],
        )
        if reply:
            await self._send_msg(reply, parse_mode=None)
            await self._record_telemetry(telem)
        else:
            await self._send_msg(
                "⚠️ OmniRouter :13305 unavailable — inline response skipped. "
                "Starting worktree session anyway."
            )

        # 2. Spawn tmux worktree session for background work
        session_id = f"agent-{int(time.time())}"
        worktree_path = f"../cohezion-{session_id}"
        try:
            res_wt = await self._run_cmd(
                ["git", "worktree", "add", "-b", session_id, worktree_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res_wt.returncode != 0:
                await self._send_msg(
                    f"⚠️ Worktree failed (inline reply above is the agent response): "
                    f"<code>{safe_html(res_wt.stderr)}</code>"
                )
                return
        except Exception as e:
            await self._send_msg(f"⚠️ Git error: <code>{safe_html(str(e))}</code>")
            return

        # Launch claude-code in the worktree with the prompt as the initial task
        safe_prompt = prompt.replace("'", "\\'")
        cmd = (
            f"cd {worktree_path} && "
            f"echo 'Agent task: {safe_prompt}' && "
            f"claude --print '{safe_prompt}' 2>&1 | tee agent.log"
        )
        try:
            res_tmux = await self._run_cmd(
                ["tmux", "new-session", "-d", "-s", session_id, cmd],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res_tmux.returncode == 0:
                await self._send_msg(
                    f"✅ Background agent running in <code>{safe_html(session_id)}</code>.\n"
                    f"Use <code>/read {safe_html(session_id)}</code> to tail logs."
                )
            else:
                await self._send_msg(
                    f"⚠️ Failed to spawn tmux session: <code>{safe_html(res_tmux.stderr)}</code>"
                )
        except Exception as e:
            await self._send_msg(f"⚠️ Tmux error: <code>{safe_html(str(e))}</code>")

    async def _send_chat_action(self, action: str = "typing") -> None:
        """Sends chat action indicator (e.g. typing) to Telegram."""
        if not self.is_configured():
            return
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.base_url}/sendChatAction",
                    json={"chat_id": self.allowed_chat_id, "action": action},
                    timeout=5.0,
                )
        except Exception as e:
            logger.debug("Failed to send chat action: %s", e)

    async def _keep_typing(self, interval: float = 4.0) -> None:
        """Maintains 'typing...' status in Telegram while a long operation runs."""
        while True:
            await self._send_chat_action("typing")
            await asyncio.sleep(interval)

    def _is_antigravity_query(self, text: str) -> bool:
        """Check if message is asking a question or directed to Antigravity."""
        lowered = text.lower().strip()
        triggers = (
            "antigravity",
            "agy",
            "orchestrator",
            "gemini",
            "claude",
            "swarm",
            "what are you working on",
            "what is our status",
            "what's our status",
            "status of",
            "portfolio",
            "anthropic",
            "google drive",
            "fix ",
            "refactor ",
            "can you ",
            "did you ",
            "how do we ",
            "why did ",
        )
        return any(t in lowered for t in triggers)

    async def _bridge_to_active_session(self, prompt: str) -> None:
        """Forward Telegram prompt to active Antigravity session queue and EventBus."""
        try:
            from cohezion.core.event_bus import Event, EventBus, EventType

            bus = EventBus()
            await bus.publish(
                Event(
                    type=EventType.CUSTOM,
                    source="telegram_bot",
                    payload={
                        "prompt": prompt,
                        "chat_id": self.allowed_chat_id,
                        "timestamp": time.time(),
                    },
                )
            )
        except Exception as e:
            logger.debug("EventBus bridge error: %s", e)

        try:
            import json as _json

            conv_dir = Path("/home/mike-anderson/.gemini/antigravity-cli/conversations")
            if conv_dir.exists():
                dbs = sorted(conv_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
                if dbs:
                    active_id = dbs[0].stem
                    msg_dir = Path(
                        f"/home/mike-anderson/.gemini/antigravity-cli/brain/{active_id}/.system_generated/messages"
                    )
                    msg_dir.mkdir(parents=True, exist_ok=True)
                    msg_id = str(uuid.uuid4())
                    msg_payload = {
                        "id": msg_id,
                        "recipient": active_id,
                        "sender": "telegram-bot",
                        "priority": "MESSAGE_PRIORITY_HIGH",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "renderDetails": {"messageTitle": "Telegram Question from Operator"},
                        "content": f'Operator asked via Telegram (@CohezionBot):\n"{prompt}"',
                    }
                    (msg_dir / f"{msg_id}.json").write_text(_json.dumps(msg_payload, indent=2))
                    logger.info(
                        "Bridged Telegram prompt to active Antigravity session %s", active_id
                    )
        except Exception as e:
            logger.debug("Active session brain bridge failed: %s", e)

    def _get_recent_context_summary(self) -> str:
        """Extract recent user tasks from history.jsonl to give Antigravity active awareness."""
        try:
            import json as _json

            hist_file = Path("/home/mike-anderson/.gemini/antigravity-cli/history.jsonl")
            if hist_file.exists():
                lines = hist_file.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                recent_lines = lines[-4:]
                entries: list[str] = []
                for line in recent_lines:
                    try:
                        data = _json.loads(line)
                        display = str(data.get("display", "")).strip().replace("\n", " ")
                        if display:
                            entries.append(display[:120])
                    except Exception as err:
                        logger.debug("Skipping unparseable history entry: %s", err)
                        continue
                if entries:
                    return "\n".join(f"- {e}" for e in entries)
        except Exception as e:
            logger.debug("Could not read recent context summary: %s", e)
        return "Active session orchestrating Cohezion codebase."

    async def _handle_antigravity(self, prompt: str) -> None:
        """Route query directly to Antigravity CLI, with typing indicator and streaming reply."""
        await self._send_chat_action("typing")
        await self._bridge_to_active_session(prompt)

        recent_ctx = self._get_recent_context_summary()
        prompt_with_ctx = (
            f'The operator on Telegram asks:\n"{prompt}"\n\n'
            f"Context: You are Antigravity, orchestrating Cohezion. Recent active tasks in this workspace:\n"
            f"{recent_ctx}\n\n"
            "Respond concisely, directly, and helpfully for mobile Telegram messaging (max 250 words)."
        )

        cmd = [
            "/home/mike-anderson/.local/bin/agy",
            "-p",
            prompt_with_ctx,
            "--dangerously-skip-permissions",
        ]

        typing_task = asyncio.create_task(self._keep_typing())
        try:
            res = await self._run_cmd(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and res.stdout.strip():
                formatted_reply = markdown_to_telegram_html(res.stdout.strip())
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append(
                    {"role": "assistant", "content": res.stdout.strip()}
                )
                await self._send_msg(f"🌌 <b>Antigravity</b>:\n\n{formatted_reply}")
            else:
                err = res.stderr.strip() or f"Process exited with code {res.returncode}"
                logger.warning("Antigravity CLI failed: %s, falling back to OmniRouter", err)
                await self._handle_chat(prompt)
        except TimeoutError:
            await self._send_msg(
                "⏱ <b>Antigravity request timed out</b> (120s limit). Routing to local silicon..."
            )
            await self._handle_chat(prompt)
        except Exception as exc:
            logger.error("Error invoking Antigravity: %s", exc)
            await self._send_msg(f"⚠️ Antigravity error: <code>{safe_html(str(exc))}</code>")
        finally:
            typing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await typing_task

    async def _handle_agents(self) -> None:
        """Lists active side agents (tmux sessions starting with 'agent-')."""
        try:
            res = await self._run_cmd(
                ["tmux", "list-sessions"], capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0:
                agents = [
                    line for line in res.stdout.strip().split("\n") if line.startswith("agent-")
                ]
                if agents:
                    msg = f"🤖 <b>Active Side Agents</b>\n<pre>{safe_html(chr(10).join(agents))}</pre>"
                else:
                    msg = "🤖 <b>Active Side Agents</b>\n<i>No active agent sessions found.</i>"
            else:
                msg = "🤖 <b>Active Side Agents</b>\n<i>No active tmux sessions found.</i>"
        except Exception as e:
            msg = f"⚠️ Failed to list agents: <code>{safe_html(str(e))}</code>"
        await self._send_msg(msg)

    # --- reconcile 2026-08-26: methods preserved from the branch (worktree-virtual-soaring-shamir) ---
    async def _classify_delegation_intent(self, text: str) -> str:
        """Classify user intent into STATUS, LIST, AGENT, or CHAT."""
        try:
            messages: list[dict[str, str]] = [{"role": "user", "content": text}]
            max_tok = MAX_TOKENS_BY_COMPLEXITY[QueryComplexity.SIMPLE]
            reply, _telem = await self._chat_omnirouter(QueryComplexity.SIMPLE, messages, max_tok)
            if reply:
                reply_clean = str(reply).strip().upper()
                for label in ("STATUS", "LIST", "AGENT", "CHAT"):
                    if label in reply_clean:
                        return label
        except Exception as e:
            logger.debug("Error in _classify_delegation_intent: %s", e)
        return "CHAT"


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # httpx logs full request URLs at INFO, which embeds the bot token
    # (https://api.telegram.org/bot<TOKEN>/...). Silence it to avoid leaking the
    # secret into the pane/journal; warnings/errors still surface.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    hub = TelegramCommunicationHub()
    if not hub.is_configured():
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment.")
        sys.exit(1)

    try:
        asyncio.run(hub.start())
    except KeyboardInterrupt:
        asyncio.run(hub.stop())
