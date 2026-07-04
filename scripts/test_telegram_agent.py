"""End-user simulation agent for TelegramCommunicationHub.

Runs an interactive REPL that mimics a Telegram user — no real Telegram token
or internet connection required. Bot replies print to stdout; all business logic
(OmniRouter routing, command dispatch, tmux queries) runs unchanged against the
live local services.

Usage:
    # Interactive REPL (type messages, see bot replies):
    uv run python scripts/test_telegram_agent.py

    # Automated smoke-test (exit 0 on pass, exit 1 on failure):
    uv run python scripts/test_telegram_agent.py --smoke

Smoke-test checks:
    /help        → help text present
    /clear       → clears history, acks
    /status      → shows CPU/RAM + Lemonade fleet
    /list        → tmux session list (any response)
    /agents      → agent list (any response)
    chat msg     → non-empty reply via :13305 (or fleet-offline notice)
    /unknown     → unknown command notice
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

# Provide dummy credentials so is_configured() returns True even without env vars
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat")

from cohezion.integrations.telegram_bot import TelegramCommunicationHub  # noqa: E402


class LocalTestAgent(TelegramCommunicationHub):
    """Telegram hub with I/O swapped for local testing.

    _send_msg   → appends to self.sent_messages AND prints to stdout
    _run_cmd    → unchanged (real subprocess, reads tmux/git if present)
    Telegram    → bypassed entirely; messages injected via inject_message()
    """

    def __init__(self) -> None:
        super().__init__()
        # Override chat_id to match the fake env var so auth check passes
        self.allowed_chat_id = os.environ["TELEGRAM_CHAT_ID"]
        self.sent_messages: list[str] = []

    async def _send_msg(self, text: str, parse_mode: str | None = "HTML") -> None:
        """Print to stdout instead of sending to Telegram."""
        import html

        if parse_mode == "HTML":
            # Strip HTML tags for readable terminal output
            import re

            clean = re.sub(r"<[^>]+>", "", text)
            clean = html.unescape(clean)
        else:
            clean = text
        print(f"\n[BOT] {clean}\n")
        self.sent_messages.append(text)

    async def inject_message(self, text: str) -> None:
        """Simulate a user sending `text` in the Telegram chat."""
        fake_message: dict[str, Any] = {
            "chat": {"id": self.allowed_chat_id},
            "text": text,
        }
        self.sent_messages.clear()
        await self._process_message(fake_message)


async def _repl(agent: LocalTestAgent) -> None:
    print("=" * 60)
    print("  Cohezion Telegram Hub — Local Test REPL")
    print("  Commands: /help /status /list /clear /agents")
    print("  /read <session>  /send <session> <keys>")
    print("  /agent <prompt>  — or type any text to chat")
    print("  Ctrl-C or /quit to exit")
    print("=" * 60)
    print()

    while True:
        try:
            text = await asyncio.to_thread(input, "YOU > ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in ("/quit", "/exit"):
            print("Bye.")
            break
        await agent.inject_message(text)


async def _smoke_test(agent: LocalTestAgent) -> bool:
    """Run a predefined set of test cases. Returns True if all pass."""
    failures: list[str] = []

    async def check(label: str, message: str, must_contain: str) -> None:
        await agent.inject_message(message)
        combined = " ".join(agent.sent_messages)
        if not agent.sent_messages:
            failures.append(f"FAIL [{label}]: no reply")
        elif must_contain.lower() not in combined.lower():
            short = combined[:120].replace("\n", " ")
            failures.append(f"FAIL [{label}]: '{must_contain}' not in reply. Got: {short}")
        else:
            print(f"  PASS [{label}]")

    print("\n=== Cohezion Telegram Hub Smoke Tests ===\n")

    await check("/help", "/help", "help")
    await check("/clear", "/clear", "clear")
    await check("/status", "/status", "CPU")
    await check("/list", "/list", "")  # any non-empty reply
    await check("/agents", "/agents", "")  # any non-empty reply
    await check("/unknown", "/xyzzy", "Unknown command")
    # Chat: either a real reply or the fleet-offline notice
    await check(
        "chat→:13305",
        "What is the current RSI threshold for oversold signals?",
        "",  # any non-empty reply
    )

    print()
    if failures:
        for f in failures:
            print(f"  {f}")
        print(f"\n{len(failures)} test(s) FAILED.\n")
        return False
    print(f"All {7} tests PASSED.\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Telegram Hub locally")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run automated smoke tests (exit 0=pass, 1=fail)",
    )
    args = parser.parse_args()

    agent = LocalTestAgent()

    if args.smoke:
        ok = asyncio.run(_smoke_test(agent))
        sys.exit(0 if ok else 1)
    else:
        asyncio.run(_repl(agent))


if __name__ == "__main__":
    main()
