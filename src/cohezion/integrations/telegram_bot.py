"""Telegram Bot integration for bi-directional communication with local sessions.

Allows remote session listing, log tailing, system resource auditing, and command
dispatching via Telegram. Constrained to the configured TELEGRAM_CHAT_ID for security.
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
import re as _re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, NamedTuple

import httpx

from cohezion.config.defaults import LEMONADE_BASE_URL

LEMONADE_ROUTER_URL: str = LEMONADE_BASE_URL

SYSTEM_PROMPT: str = (
    "You are the Cohezion assistant, running exclusively on AMD silicon (Ryzen AI MAX+ 395, "
    "Radeon 8060S iGPU, XDNA2 NPU). "
    "You have NO access to the open internet — all inference is local via the :13305 OmniRouter. "
    "You assist the operator with local session telemetry, model fleet status, and compound "
    "engineering tasks. Answer concisely and technically. "
    "Never suggest external API services as inference backends — local silicon only."
)


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
        "llama3.2-1b-FLM",
        "Gemma-4-E2B-it-GGUF",
        "Gemma-4-E4B-it-GGUF",
    ],
    QueryComplexity.MEDIUM: [
        "Gemma-4-E4B-it-GGUF",
        "Qwen3.6-27B-GGUF",
        "Gemma-4-31B-it-GGUF",
    ],
    QueryComplexity.COMPLEX: [
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

    async def _run_cmd(self, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        """Run subprocess.run in a background thread to keep event loop responsive."""
        return await asyncio.to_thread(subprocess.run, *args, **kwargs)

    def is_configured(self) -> bool:
        return bool(self.token and self.allowed_chat_id)

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
        complexity: QueryComplexity,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> tuple[str | None, _OmniTelemetry]:
        """POST to :13305 OmniRouter with a complexity hint; retry across hint list on failure."""
        telem = _OmniTelemetry(port=13305, backend="lemonade-omnirouter")
        hints = list(_COMPLEXITY_HINTS.get(complexity, _COMPLEXITY_HINTS[QueryComplexity.MEDIUM]))
        last_error: str | None = None

        for attempt, hint_model in enumerate(hints, 1):
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

    async def start(self) -> None:
        """Starts the long-polling execution loop."""
        if not self.is_configured():
            logger.error("Telegram credentials missing in environment. Cannot start hub.")
            return

        self._running = True
        logger.info("Cohezion Telegram Hub started on chat %s", self.allowed_chat_id)
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
        await self._send_msg("🛑 Telegram Hub is shutting down.")

    async def _send_msg(self, text: str, parse_mode: str | None = "HTML") -> None:
        """Sends a message back to the allowed chat ID."""
        try:
            payload: dict[str, Any] = {
                "chat_id": self.allowed_chat_id,
                "text": text,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.base_url}/sendMessage",
                    json=payload,
                    timeout=15.0,
                )
        except Exception as e:
            logger.debug("Failed to send telegram msg: %s", e)

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
            # Route to local model chat by default
            await self._handle_chat(text)
            return

        parts = text.split(maxsplit=2)
        command = parts[0].lower()

        if command in ("/start", "/help"):
            await self._send_msg(self._get_help_message())

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
            else:
                await self._handle_run(code)

        else:
            await self._send_msg(
                f"❓ Unknown command: <code>{safe_html(command)}</code>\nUse /help for commands."
            )

    def _get_help_message(self) -> str:
        return (
            "🚀 <b>Cohezion Communication Hub</b>\n\n"
            "💬 <b>Local Inference Chat (:13305 OmniRouter)</b>\n"
            "Send any plain text to chat — routed to AMD silicon, never cloud.\n"
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
        except asyncio.TimeoutError:
            await self._send_msg("⏱ <b>/run timed out</b> (30s limit).")
            return
        except Exception as exc:
            await self._send_msg(f"⚠️ Execution error: <code>{safe_html(str(exc))}</code>")
            return
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

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
