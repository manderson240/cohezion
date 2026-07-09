"""Telegram notifications for compound loop milestones via Cohezion bot.

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment.
All functions are fire-and-forget: they silently no-op when credentials
are absent or when the Telegram API is unreachable.

The compound loop never blocks on notification failures.
"""

from __future__ import annotations

import logging
import os

import httpx


logger = logging.getLogger(__name__)


def _creds() -> tuple[str, str] | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return (token, chat) if token and chat else None


def _redact(text: str) -> str:
    """Redact credential patterns before sending. Non-blocking on import failure."""
    try:
        from cohezion.inference.security_spec import redact_credentials

        return redact_credentials(text)
    except Exception:
        return text


def notify(message: str, parse_mode: str = "HTML") -> None:
    """Send a Telegram message. No-ops silently if credentials missing.

    Automatically redacts credential patterns before transmission —
    prevents API keys, passwords, or tokens from leaking via the bot.
    """
    creds = _creds()
    if creds is None:
        return
    token, chat_id = creds
    safe_message = _redact(message)
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": safe_message, "parse_mode": parse_mode},
            timeout=5.0,
        )
    except Exception as exc:
        logger.debug("Telegram notify failed (non-blocking): %s", exc)


# Milestone helpers wired into CompoundExecutor hooks


def notify_tier_escalation(from_tier: str, to_tier: str, task: str) -> None:
    notify(f"<b>Tier escalation</b>: {from_tier} → {to_tier}\n<code>{task[:140]}</code>")


def notify_task_complete(task: str, model: str, latency_ms: float) -> None:
    notify(
        f"<b>Task done</b> via <code>{model}</code> ({latency_ms:.0f} ms)\n"
        f"<code>{task[:140]}</code>"
    )


def notify_lemonade_offline(port: int) -> None:
    notify(
        f"<b>OOM guard</b>: Lemonade port {port} unreachable.\n"
        f"Local silicon skipped — falling back to caller execute_fn."
    )


def notify_compound_error(task: str, error: str) -> None:
    notify(f"<b>Compound error</b>\n<code>{task[:80]}</code>\n{error[:200]}")
