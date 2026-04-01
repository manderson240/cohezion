#!/usr/bin/env python3
"""Autonomous Traceability Daemon - Continuous repo health monitoring.

Usage:
    uv run python -m cohezion.mcp.servers.traceability.daemon --foreground
    uv run python -m cohezion.mcp.servers.traceability.daemon --background
    uv run python -m cohezion.mcp.servers.traceability.daemon --install-hook
    uv run python -m cohezion.mcp.servers.traceability.daemon --uninstall-hook

Modes:
    - foreground: Interactive debugging (Ctrl+C to stop)
    - background: Run as systemd service (daemonize)
    - install-hook: Install git post-commit hook
    - uninstall-hook: Remove git hook
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


# Try to import schedule, fallback to simple loop if not available
try:
    import schedule

    HAS_SCHEDULED = True
except ImportError:
    HAS_SCHEDULED = False

PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
DAEMON_LOG = PROJECT_ROOT / "_bmad" / "_config" / "traceability" / "daemon.log"
GIT_HOOK_PATH = PROJECT_ROOT / ".git" / "hooks" / "post-commit"


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(DAEMON_LOG), logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("TraceabilityDaemon")


def run_health_check() -> dict:
    """Run repository health check."""
    logger = logging.getLogger("TraceabilityDaemon")
    logger.info("Running health check...")

    result = subprocess.run(
        ["uv", "run", "python", "_bmad/_config/traceability/repo_health/repo_health_engine.py"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=300,
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run_party_review() -> dict:
    """Trigger party-mode adversarial review."""
    logger = logging.getLogger("TraceabilityDaemon")
    logger.info("Triggering party review...")

    result = subprocess.run(
        ["uv", "run", "python", "_bmad/_config/traceability/workflows/run_party_review.py"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=600,
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run_recursive_loop() -> dict:
    """Run full recursive improvement loop."""
    logger = logging.getLogger("TraceabilityDaemon")
    logger.info("Running recursive loop...")

    result = subprocess.run(
        ["uv", "run", "python", "_bmad/_config/traceability/recursive_loop.py"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=600,
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def install_git_hook():
    """Install git post-commit hook."""
    logger = logging.getLogger("TracequalityDaemon")

    hook_script = """#!/bin/bash
# Auto-trigger traceability health check on every commit
echo "$(date): Git commit detected, running health check..." >> .git/traceability.log
uv run python -m cohezion.mcp.servers.traceability.daemon --git-hook 2>&1 | tee -a .git/traceability.log
"""

    GIT_HOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    GIT_HOOK_PATH.write_text(hook_script)
    GIT_HOOK_PATH.chmod(0o755)

    logger.info(f"Git hook installed at {GIT_HOOK_PATH}")


def uninstall_git_hook():
    """Remove git post-commit hook."""
    logger = logging.getLogger("TraceabilityDaemon")

    if GIT_HOOK_PATH.exists():
        GIT_HOOK_PATH.unlink()
        logger.info(f"Git hook removed from {GIT_HOOK_PATH}")
    else:
        logger.info("Git hook not found")


def run_git_hook():
    """Run health check triggered by git commit."""
    logger = logging.getLogger("TraceabilityDaemon")
    logger.info("Git commit hook triggered")

    result = run_health_check()

    if result["returncode"] == 0:
        logger.info("Health check completed successfully")
        # Parse score from output
        if "Overall Health Score:" in result["stdout"]:
            for line in result["stdout"].split("\n"):
                if "Overall Health Score:" in line:
                    score = line.split(":")[1].strip()
                    logger.info(f"Current health score: {score}")
    else:
        logger.error(f"Health check failed: {result['stderr']}")


def run_scheduled(interval_minutes: int = 15):
    """Run health check on schedule."""
    logger = logging.getLogger("TraceabilityDaemon")
    logger.info(f"Starting scheduled mode (every {interval_minutes} minutes)")

    if HAS_SCHEDULED:
        schedule.every(interval_minutes).minutes.do(run_health_check)

        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        # Fallback to simple loop
        while True:
            run_health_check()
            time.sleep(interval_minutes * 60)


def run_foreground():
    """Run daemon in foreground (interactive)."""
    logger = logging.getLogger("TraceabilityDaemon")
    logger.info("Starting daemon in foreground mode")

    # Signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutting down daemon...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run initial health check
    run_health_check()

    # Run scheduled checks every 15 minutes (aggressive mode until 7 AM)
    run_scheduled(interval_minutes=15)


def run_background():
    """Run daemon in background (systemd service)."""
    logger = logging.getLogger("TraceabilityDaemon")
    logger.info("Starting daemon in background mode")

    # Double fork to daemonize
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    os.setsid()

    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # Redirect stdio
    sys.stdout = open(DAEMON_LOG, "a")
    sys.stderr = sys.stdout

    # Run scheduled checks
    run_scheduled(interval_minutes=15)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Autonomous Traceability Daemon")
    parser.add_argument("--foreground", action="store_true", help="Run in foreground")
    parser.add_argument("--background", action="store_true", help="Run in background")
    parser.add_argument("--install-hook", action="store_true", help="Install git hook")
    parser.add_argument("--uninstall-hook", action="store_true", help="Remove git hook")
    parser.add_argument("--git-hook", action="store_true", help="Run from git hook")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--interval", type=int, default=15, help="Check interval (minutes)")

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("TraceabilityDaemon")

    logger.info("=" * 60)
    logger.info("Autonomous Traceability Daemon")
    logger.info(
        f"Mode: {args.foreground and 'foreground' or args.background and 'background' or 'hook'}"
    )
    logger.info(f"Interval: {args.interval} minutes")
    logger.info("=" * 60)

    if args.install_hook:
        install_git_hook()
    elif args.uninstall_hook:
        uninstall_git_hook()
    elif args.git_hook:
        run_git_hook()
    elif args.background:
        run_background()
    else:
        run_foreground()


if __name__ == "__main__":
    main()
