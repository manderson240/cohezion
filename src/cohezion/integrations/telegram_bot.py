"""Telegram Bot integration for bi-directional communication with local sessions.

Allows remote session listing, log tailing, system resource auditing, and command
dispatching via Telegram. Constrained to the configured TELEGRAM_CHAT_ID for security.
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
import subprocess
import sys
from typing import Any, NamedTuple

import httpx


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

        else:
            await self._send_msg(
                f"❓ Unknown command: <code>{safe_html(command)}</code>\nUse /help for commands."
            )

    def _get_help_message(self) -> str:
        return (
            "🚀 <b>Cohezion Telemetry Hub Commands</b>\n\n"
            "💬 <b>Local Inference Chat</b>\n"
            "Simply send any plain text message to chat with the local model.\n"
            "/clear - Clear conversation history\n\n"
            "🎛 <b>System & Session Diagnostics</b>\n"
            "/status - View CPU/RAM/GPU vitals & active models\n"
            "/list - List running tmux sessions (claude, agy, pi, hermes)\n"
            "/read &lt;session&gt; - Scrape current terminal pane output\n"
            "/send &lt;session&gt; &lt;cmd&gt; - Dispatch keystrokes to a session\n"
            "/learnings - Retrieve latest registered knowledge entries\n"
            "/agent &lt;prompt&gt; - Spawn side agent (parallel work in tmux + worktree)\n"
            "/agents - List active side agents\n"
            "/help - Display this manual"
        )

    async def _select_model(self) -> ModelSelection | None:
        """Selects the best available chat model, preferring the lemonade fleet.

        FIRST tries the always-up lemonade OpenAI-compatible router (:13305).
        If the router is unreachable or lists no usable model, FALLS BACK to the
        legacy Ollama path (:11434), which is preserved intact.
        """
        lemonade_model = await self._select_lemonade_model()
        if lemonade_model is not None:
            return ModelSelection(lemonade_model, "lemonade")

        ollama_model = await self._select_ollama_model()
        if ollama_model is not None:
            return ModelSelection(ollama_model, "ollama")

        return None

    async def _select_lemonade_model(self) -> str | None:
        """Picks a served model from the lemonade router, or None if unavailable.

        Prefers ``Granite-4.1-8B-GGUF`` (validated no-thinking main-loop model),
        then any served id containing "Granite", then any non-embedding,
        non-cloud id. Returns None when the router is down or lists nothing.
        """
        from cohezion.config.defaults import LEMONADE_ROUTER_PORT

        url = f"http://localhost:{LEMONADE_ROUTER_PORT}/v1/models"

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
            from cohezion.config.defaults import OLLAMA_PORT

            async with httpx.AsyncClient() as client:
                r = await client.get(f"http://localhost:{OLLAMA_PORT}/api/tags", timeout=3.0)
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

                    # Next preference: any model that is NOT a cloud endpoint (doesn't contain "cloud")
                    local_models = [m for m in models if "cloud" not in m]
                    if local_models:
                        return local_models[0]

                    # Fallback to any model
                    if models:
                        return models[0]
        except Exception as e:
            logger.warning("Error querying Ollama tags: %s", e)
        return None

    async def _handle_chat(self, text: str) -> None:
        """Handles general text input via the local fleet (lemonade-first).

        Routes to the lemonade router (:13305, OpenAI format) when the selected
        model came from it; otherwise uses the legacy Ollama ``/api/chat`` path.
        """
        selection = await self._select_model()
        if not selection:
            await self._send_msg(
                "⚠️ <b>Local Fleet Offline or No Models Found</b>\n"
                "The lemonade router (:13305) and Ollama (:11434) are both unreachable. "
                "Please ensure the local AMD fleet is up (or <code>ollama serve</code>) "
                "with at least one model loaded."
            )
            return

        model = selection.model

        # Append user message to history
        self.conversation_history.append({"role": "user", "content": text})

        # Enforce history limit
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history :]

        # Add system prompt for role grounding
        system_prompt = (
            "You are the Cohezion assistant, a helpful and technical AI companion for the Cohezion platform. "
            "Cohezion is an agentic AI framework featuring FLUME methodology, compound engineering, and multi-agent swarms. "
            "Answer concisely and technically. You have access to local silicon telemetry (CPU/RAM/GPU) via the bot's status command."
        )

        messages = [{"role": "system", "content": system_prompt}, *self.conversation_history]

        try:
            if selection.backend == "lemonade":
                reply = await self._chat_lemonade(model, messages)
            else:
                reply = await self._chat_ollama(model, messages)

            if reply is None:
                return  # error already surfaced to user
            if reply:
                self.conversation_history.append({"role": "assistant", "content": reply})
                await self._send_msg(reply, parse_mode=None)
            else:
                await self._send_msg("⚠️ Received empty response from local model.")
        except Exception as e:
            logger.error("Failed to call local model: %s", e)
            await self._send_msg(
                f"⚠️ Failed to communicate with local model: <code>{safe_html(str(e))}</code>"
            )

    async def _chat_lemonade(self, model: str, messages: list[dict[str, str]]) -> str | None:
        """POSTs to the lemonade OpenAI router and parses choices[].message.content.

        Returns the (possibly empty) reply string, or None if an HTTP error was
        already surfaced to the user. ``max_tokens`` is 1024 so even a borderline
        reasoning model has headroom before its budget is consumed.
        """
        from cohezion.config.defaults import LEMONADE_ROUTER_PORT

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"http://localhost:{LEMONADE_ROUTER_PORT}/v1/chat/completions",
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
        from cohezion.config.defaults import OLLAMA_PORT

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"http://localhost:{OLLAMA_PORT}/api/chat",
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

    async def _handle_status(self) -> None:
        """Queries local silicon metrics."""
        import psutil

        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        ram_used = (vm.total - vm.available) / (1024**3)
        ram_total = vm.total / (1024**3)

        gpu_status = "Not detected / headless"
        try:
            res = await self._run_cmd(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                parts = res.stdout.strip().split(", ")
                gpu_status = f"Util: {parts[0]}%, VRAM: {parts[1]}MB / {parts[2]}MB"
        except Exception:
            pass

        # Check local model roster via Ollama tags API
        models_running = "None active"
        try:
            from cohezion.config.defaults import OLLAMA_PORT

            async with httpx.AsyncClient() as client:
                r = await client.get(f"http://localhost:{OLLAMA_PORT}/api/tags", timeout=3.0)
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    if models:
                        models_running = ", ".join(models)
        except Exception:
            try:
                # Fallback to surreal db running check
                r = await httpx.AsyncClient().get("http://localhost:8001/status", timeout=1.0)
                if r.status_code == 200:
                    models_running = "SurrealDB Active (Ollama local offline)"
            except Exception:
                pass

        msg = (
            f"💻 <b>Silicon Vitals</b>\n"
            f"- CPU Usage: <code>{cpu:.1f}%</code>\n"
            f"- RAM Usage: <code>{ram_used:.1f}GB / {ram_total:.1f}GB</code> ({vm.percent}%)\n"
            f"- GPU Status: <code>{safe_html(gpu_status)}</code>\n"
            f"- Local Models: <code>{safe_html(models_running)}</code>"
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

    async def _handle_agent(self, prompt: str) -> None:
        """Spawns a side agent (parallel work in tmux + worktree)."""
        import time

        session_id = f"agent-{int(time.time())}"
        worktree_path = f"../cohezion-{session_id}"

        # 1. Create a git worktree
        try:
            res_wt = await self._run_cmd(
                ["git", "worktree", "add", "-b", session_id, worktree_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res_wt.returncode != 0:
                await self._send_msg(
                    f"⚠️ Failed to create worktree: <code>{safe_html(res_wt.stderr)}</code>"
                )
                return
        except Exception as e:
            await self._send_msg(f"⚠️ Git error: <code>{safe_html(str(e))}</code>")
            return

        # 2. Spawn tmux session starting the antigravity-cli or gemini local command in that worktree
        try:
            cmd = f"cd {worktree_path} && echo 'Starting agent with prompt: {prompt}' && gemini chat --prompt '{prompt}'"
            res_tmux = await self._run_cmd(
                ["tmux", "new-session", "-d", "-s", session_id, cmd],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res_tmux.returncode == 0:
                await self._send_msg(
                    f"✅ Spawned side agent in session <code>{safe_html(session_id)}</code>.\nUse <code>/read {safe_html(session_id)}</code> to tail logs."
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
