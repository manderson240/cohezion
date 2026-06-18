#!/usr/bin/env python3
"""Demo runner — simulate Slack commands without live credentials.

Usage:
    python demo/slack_demo.py ask "How do I add rate limiting to FastAPI?"
    python demo/slack_demo.py review "Add OAuth2 PKCE to our auth service"
    python demo/slack_demo.py search "Redis caching patterns"
    python demo/slack_demo.py status
    python demo/slack_demo.py all   # run all demo commands
"""

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from shared.cohezion_bridge import CohezionBridge
from handlers.ask_handler import handle_ask
from handlers.review_handler import handle_review
from handlers.search_handler import handle_search
from handlers.status_handler import handle_status

try:
    from rich.console import Console
    from rich.rule import Rule
    from rich.panel import Panel
    console = Console()
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False


def _header(text: str) -> None:
    if HAS_RICH and console is not None:
        console.rule(f"[bold cyan]{text}[/bold cyan]")
    else:
        print(f"\n{'='*60}\n  {text}\n{'='*60}")


def _print(text: str, style: str = "") -> None:
    if HAS_RICH and console is not None:
        console.print(f"[{style}]{text}[/{style}]" if style else text)
    else:
        print(text)


def demo_ask(question: str) -> None:
    _header(f"/cohezion ask")
    _print(f"  Question: {question}", "dim")
    print()

    t0 = time.time()
    result = handle_ask(question=question)
    elapsed = time.time() - t0

    tier_icon = "⚡" if result["local_silicon"] else "☁"
    _print(f"{result['answer']}", "green")
    print()
    _print(f"  {tier_icon} {result['tier_used'].upper()} · {result['latency_ms']}ms · ${result['cost_usd']:.4f}", "dim")


def demo_review(task: str) -> None:
    _header("/cohezion review")
    _print(f"  Task: {task}", "dim")
    print()

    updates = []

    def progress(stage: str, msg: str) -> None:
        icons = {"orchestrator": "⚙", "analyst": "🔬", "engineer": "🔨"}
        icon = icons.get(stage, "→")
        line = f"  {icon} {stage.title()}: {msg}"
        updates.append(line)
        _print(line, "yellow")

    result = handle_review(task=task, progress_callback=progress)
    print()
    _print(result["summary"], "bold green")

    impl = result.get("implementation", {})
    patches = impl.get("code_patches", [])
    if patches:
        p = patches[0]
        print()
        _print(f"Top patch: {p.get('file', 'unknown')}", "bold")
        _print(f"  {p.get('description', '')}", "dim")
        code = p.get("code", "")[:400]
        if code:
            _print(f"\n```\n{code}\n```", "cyan")


def demo_search(query: str) -> None:
    _header("/cohezion search")
    result = handle_search(query=query)
    _print(result["formatted"], "green")


def demo_status() -> None:
    _header("/cohezion status")
    result = handle_status()
    _print(result["text"], "green")


def demo_all() -> None:
    _header("Cohezion Intelligence Agent for Slack — Full Demo")
    _print("  Track: New Slack Agent (MCP server integration)", "dim")
    _print("  Prize: $42,000 · Deadline: July 13, 2026", "dim")
    print()

    bridge = CohezionBridge()
    status = bridge.get_status()
    npu = "✓" if status.get("lemonade_npu") else "✗"
    igpu = "✓" if status.get("lemonade_igpu") else "✗"
    cpu = "✓" if status.get("lemonade_cpu") else "✗"
    _print(f"  AMD Silicon: NPU [{npu}]  iGPU [{igpu}]  CPU [{cpu}]", "yellow")
    print()

    demo_ask("How do I implement rate limiting middleware in FastAPI with Redis?")
    print()
    demo_search("Redis caching patterns")
    print()
    demo_review("Add OAuth2 PKCE flow to authentication service — 847 lines changed, security-sensitive")
    print()
    demo_status()

    print()
    _header("Demo Complete")
    _print("  Start the full Slack agent:", "dim")
    _print("    python mcp_server.py &   # MCP integration server", "dim")
    _print("    python app.py            # Slack bot", "dim")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cohezion Slack Agent Demo")
    parser.add_argument("subcommand", choices=["ask", "review", "search", "status", "all"])
    parser.add_argument("args", nargs="*", help="Command arguments")
    parsed = parser.parse_args()

    arg_text = " ".join(parsed.args)

    if parsed.subcommand == "ask":
        question = arg_text or "How do I add rate limiting to a FastAPI application?"
        demo_ask(question)
    elif parsed.subcommand == "review":
        task = arg_text or "Add OAuth2 PKCE to authentication service"
        demo_review(task)
    elif parsed.subcommand == "search":
        query = arg_text or "Redis caching"
        demo_search(query)
    elif parsed.subcommand == "status":
        demo_status()
    elif parsed.subcommand == "all":
        demo_all()

    return 0


if __name__ == "__main__":
    sys.exit(main())
