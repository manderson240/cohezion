"""Entry point for the Google Sheets research pipeline daemon."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from .config import ServerConfig
from .sheets_bridge import SheetsBridge
from .sheets_research_daemon import SheetsResearchDaemon
from .vault_ops import VaultOps


logger = logging.getLogger("sheets-research")

# Global daemon instance for CLI commands
_daemon_instance = None


def _load_oauth_token() -> str | None:
    """Read access token from Claude Code's credentials file."""
    creds_path = Path.home() / ".claude" / ".credentials.json"
    try:
        data = json.loads(creds_path.read_text())
        return data["claudeAiOauth"]["accessToken"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


async def run_research_daemon(config: ServerConfig):
    """Run the sheets research daemon."""
    if not config.sheets_research_enabled:
        logger.info("Sheets research daemon is disabled")
        return

    # Initialize vault and sheets bridge
    vault = VaultOps(config.vault_path)
    sheets = SheetsBridge(
        spreadsheet_id=config.sheets_spreadsheet_id,
        quota_project=config.sheets_quota_project,
    )

    # Initialize daemon
    daemon = SheetsResearchDaemon(
        config=config,
        sheets_bridge=sheets,
        vault_ops=vault,
    )

    logger.info("Sheets research daemon initialized")

    # Run daemon
    await daemon.run()


async def _init_daemon(config: ServerConfig) -> SheetsResearchDaemon:
    """Initialize daemon without running it."""
    vault = VaultOps(config.vault_path)
    sheets = SheetsBridge(
        spreadsheet_id=config.sheets_spreadsheet_id,
        quota_project=config.sheets_quota_project,
    )
    return SheetsResearchDaemon(
        config=config,
        sheets_bridge=sheets,
        vault_ops=vault,
    )


def cmd_dlq(daemon: SheetsResearchDaemon):
    """List dead letter queue entries."""
    entries = daemon.get_dlq_entries()
    if not entries:
        print("Dead letter queue is empty")
        return
    print(f"Dead Letter Queue ({len(entries)} entries):")
    print("-" * 100)
    for entry in entries:
        print(f"Row {entry['row']}: {entry['link'][:60]}")
        print(f"  Reason: {entry['reason']}")
        print(f"  Failures: {entry['failure_count']}")
        print(f"  Last attempt: {entry['last_attempt']}")
        print()


def cmd_retry(daemon: SheetsResearchDaemon, row_number: int):
    """Retry a specific DLQ row."""
    if daemon.retry_dlq_row(row_number):
        print(f"Row {row_number} queued for retry")
    else:
        print(f"Row {row_number} not found in DLQ")
        sys.exit(1)


def cmd_mark_inaccessible(daemon: SheetsResearchDaemon, row_number: int):
    """Mark a DLQ row as permanently inaccessible."""
    if daemon.mark_dlq_inaccessible(row_number):
        print(f"Row {row_number} marked as inaccessible and removed from DLQ")
    else:
        print(f"Row {row_number} not found in DLQ")
        sys.exit(1)


def cmd_status(daemon: SheetsResearchDaemon):
    """Get daemon status."""
    status = daemon.get_status()
    print(json.dumps(status, indent=2))


def main():
    """Entry point for the sheets-research-daemon command."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Google Sheets research daemon")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Daemon command (default)
    subparsers.add_parser("start", help="Start the daemon (default)")

    # DLQ commands
    dlq_parser = subparsers.add_parser("dlq", help="Show dead letter queue")
    retry_parser = subparsers.add_parser("retry", help="Retry a failed row")
    retry_parser.add_argument("row", type=int, help="Row number to retry")

    inaccessible_parser = subparsers.add_parser(
        "mark-inaccessible",
        help="Mark a row as permanently inaccessible",
    )
    inaccessible_parser.add_argument("row", type=int, help="Row number to mark")

    status_parser = subparsers.add_parser("status", help="Get daemon status")

    args = parser.parse_args()
    config = ServerConfig.from_env()

    # Handle non-daemon commands
    if args.command in ("dlq", "retry", "mark-inaccessible", "status"):

        async def run_command():
            daemon = await _init_daemon(config)
            if args.command == "dlq":
                cmd_dlq(daemon)
            elif args.command == "retry":
                cmd_retry(daemon, args.row)
            elif args.command == "mark-inaccessible":
                cmd_mark_inaccessible(daemon, args.row)
            elif args.command == "status":
                cmd_status(daemon)

        asyncio.run(run_command())
        sys.exit(0)

    # Default: start daemon
    if not config.sheets_research_enabled:
        logger.warning("SHEETS_RESEARCH_ENABLED is false, daemon disabled")
        sys.exit(0)

    logger.info("Starting sheets research daemon")
    logger.info(f"Vault path: {config.vault_path}")
    logger.info(f"Poll interval: {config.sheets_research_poll_interval}s")
    logger.info(f"Batch size: {config.sheets_research_batch_size}")
    logger.info(f"Max agents: {config.sheets_research_max_concurrent_agents}")
    logger.info(f"Work queue DB: {config.sheets_research_work_queue_db}")

    try:
        asyncio.run(run_research_daemon(config))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception:
        logger.exception("Daemon crashed")
        sys.exit(1)


if __name__ == "__main__":
    main()
