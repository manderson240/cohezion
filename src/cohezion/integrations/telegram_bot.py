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
from typing import Any

import httpx


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

    async def _select_model(self) -> str | None:
        """Selects the best available local model for chat."""
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
        """Handles general text input by querying local Ollama model."""
        model = await self._select_model()
        if not model:
            await self._send_msg(
                "⚠️ <b>Ollama Offline or No Models Found</b>\n"
                "Please ensure Ollama is running (<code>ollama serve</code>) and at least one model is pulled."
            )
            return

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
                if r.status_code == 200:
                    reply = r.json().get("message", {}).get("content", "").strip()
                    if reply:
                        # Append assistant reply to history
                        self.conversation_history.append({"role": "assistant", "content": reply})
                        await self._send_msg(reply, parse_mode=None)
                    else:
                        await self._send_msg("⚠️ Received empty response from local model.")
                else:
                    await self._send_msg(
                        f"⚠️ Ollama error (HTTP {r.status_code}): {safe_html(r.text)}"
                    )
        except Exception as e:
            logger.error("Failed to call local model: %s", e)
            await self._send_msg(
                f"⚠️ Failed to communicate with local model: <code>{safe_html(str(e))}</code>"
            )

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
    hub = TelegramCommunicationHub()
    if not hub.is_configured():
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment.")
        sys.exit(1)

    try:
        asyncio.run(hub.start())
    except KeyboardInterrupt:
        asyncio.run(hub.stop())
