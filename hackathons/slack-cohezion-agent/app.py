#!/usr/bin/env python3
"""Cohezion Intelligence Agent for Slack.

Powered by AMD silicon compound AI — $0 per query on local hardware.
Uses MCP server integration (required technology for Slack Agent Builder Challenge).

Start:
    python mcp_server.py &   # start MCP server
    python app.py            # start Slack bot

Slash commands:
    /cohezion ask <question>      — Q&A via compound loop
    /cohezion review <task>       — 3-agent code review
    /cohezion search <query>      — semantic vault search
    /cohezion status              — AMD silicon health
    /cohezion help                — show commands
"""

import os
import sys
import time

_REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _REPO)

from dotenv import load_dotenv
load_dotenv()

try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    HAS_SLACK = True
except ImportError:
    HAS_SLACK = False
    App = None  # type: ignore[misc,assignment]
    SocketModeHandler = None  # type: ignore[misc,assignment]

from shared.cohezion_mcp_client import CohezionMCPClient
from handlers.ask_handler import handle_ask
from handlers.review_handler import handle_review
from handlers.search_handler import handle_search
from handlers.status_handler import handle_status

_mcp = CohezionMCPClient()

_HELP_TEXT = """\
*Cohezion Intelligence — Compound AI for your Slack workspace*

Powered by AMD silicon at $0/query. MCP-backed.

*Commands:*
• `/cohezion ask <question>` — Q&A via NPU→iGPU→CPU routing
• `/cohezion review <task>` — 3-agent code review pipeline
• `/cohezion search <query>` — FLUME VAE semantic search
• `/cohezion status` — AMD silicon health check

*Examples:*
• `/cohezion ask How do I add rate limiting to FastAPI?`
• `/cohezion review Add OAuth2 PKCE to our auth service`
• `/cohezion search Redis caching patterns`

_Runs on AMD Ryzen AI MAX+ Strix Halo — NPU (42 TPS) + iGPU + CPU + SemanticCache_
"""


# ── Slack App ─────────────────────────────────────────────────────────────────

def build_app() -> "App":
    if not HAS_SLACK:
        raise RuntimeError("slack_bolt not installed. Run: uv pip install slack-bolt")

    app = App(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    )

    # ── /cohezion slash command ───────────────────────────────────────────
    @app.command("/cohezion")
    def handle_cohezion_command(ack, command, say, client):
        ack()

        text = (command.get("text") or "").strip()
        parts = text.split(None, 1)
        subcommand = parts[0].lower() if parts else "help"
        args = parts[1] if len(parts) > 1 else ""

        channel = command["channel_id"]
        user = command["user_id"]

        if subcommand == "help" or not subcommand:
            say(text=_HELP_TEXT, channel=channel)

        elif subcommand == "ask":
            if not args:
                say(text="Usage: `/cohezion ask <your question>`", channel=channel)
                return
            # Post "thinking" message first
            thinking = say(text=f"<@{user}> :brain: Routing to AMD silicon...", channel=channel)
            result = handle_ask(question=args, user_id=user)
            tier = result["tier_used"]
            cost = result["cost_usd"]
            latency = result["latency_ms"]
            local = result["local_silicon"]
            tier_icon = ":zap:" if local else ":cloud:"
            footer = f"_{tier_icon} {tier.upper()} · {latency}ms · ${cost:.4f}_"
            # Update with answer
            try:
                client.chat_update(
                    channel=channel,
                    ts=thinking["ts"],
                    text=f"{result['answer']}\n\n{footer}",
                )
            except Exception:  # noqa: BLE001
                say(text=f"{result['answer']}\n\n{footer}", channel=channel)

        elif subcommand == "review":
            if not args:
                say(text="Usage: `/cohezion review <task description>`", channel=channel)
                return
            # Post thread starter
            start_msg = say(
                text=f"<@{user}> :mag: Starting Cohezion 3-agent code review...",
                channel=channel,
            )
            thread_ts = start_msg.get("ts")

            def post_progress(stage: str, msg: str) -> None:
                icon = {"orchestrator": ":gear:", "analyst": ":microscope:", "engineer": ":hammer:"}.get(stage, ":arrow_right:")
                try:
                    client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"{icon} *{stage.title()}*: {msg}",
                    )
                except Exception:  # noqa: BLE001
                    pass

            result = handle_review(task=args, progress_callback=post_progress)

            # Post final summary to thread
            impl = result.get("implementation", {})
            patches = impl.get("code_patches", [])
            confidence = impl.get("confidence_score", 0)

            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": result["summary"]},
                },
            ]

            if patches:
                patch = patches[0]
                blocks.append({"type": "divider"})
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Top Patch: `{patch.get('file', 'unknown')}`*\n_{patch.get('description', '')}_",
                    },
                })
                code = patch.get("code", "")[:800]
                if code:
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"```{code}```"},
                    })

            try:
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    blocks=blocks,
                    text=result["summary"],
                )
            except Exception:  # noqa: BLE001
                say(text=result["summary"], channel=channel)

        elif subcommand == "search":
            if not args:
                say(text="Usage: `/cohezion search <query>`", channel=channel)
                return
            result = handle_search(query=args)
            say(text=result["formatted"], channel=channel)

        elif subcommand == "status":
            result = handle_status()
            try:
                say(blocks=result["blocks"], text=result["text"], channel=channel)
            except Exception:  # noqa: BLE001
                say(text=result["text"], channel=channel)

        else:
            say(
                text=f"Unknown subcommand `{subcommand}`. Try `/cohezion help`",
                channel=channel,
            )

    # ── @Cohezion app mentions ────────────────────────────────────────────
    @app.event("app_mention")
    def handle_mention(event, say):
        text = event.get("text", "")
        # Strip the bot mention
        import re  # noqa: PLC0415
        question = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
        if not question:
            say(text=_HELP_TEXT, thread_ts=event.get("ts"))
            return

        result = handle_ask(question=question, user_id=event.get("user", ""))
        tier = result["tier_used"]
        cost = result["cost_usd"]
        local = result["local_silicon"]
        tier_icon = ":zap:" if local else ":cloud:"
        footer = f"_{tier_icon} {tier.upper()} · ${cost:.4f}_"
        say(
            text=f"{result['answer']}\n\n{footer}",
            thread_ts=event.get("ts"),
        )

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not HAS_SLACK:
        print("ERROR: slack_bolt not installed.")
        print("Run: uv pip install slack-bolt slack-sdk")
        sys.exit(1)

    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        print("ERROR: SLACK_APP_TOKEN not set (needed for Socket Mode).")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    print("[Cohezion Slack Agent] Starting in Socket Mode...")
    slack_app = build_app()
    handler = SocketModeHandler(slack_app, app_token)
    print("[Cohezion Slack Agent] Connected. Waiting for events...")
    handler.start()
