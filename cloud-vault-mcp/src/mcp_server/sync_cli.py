"""
CLI for entire.io sync daemon management.

Provides start/stop/status commands for daemon control.
"""

import asyncio
import sys
import signal
from typing import Optional
from pathlib import Path
import json
import logging
from .sync_daemon import SyncDaemon, SyncConfig, get_sync_daemon, reset_sync_daemon

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SyncCLI:
    """CLI interface for sync daemon."""

    def __init__(self):
        self.daemon: Optional[SyncDaemon] = None
        self._shutdown_requested = False

    def start(
        self,
        repo_path: str,
        branch: str = "main",
        poll_interval: int = 60,
        sync_direction: str = "bidirectional",
        api_url: str = "https://api.entire.io/v1",
        api_key: Optional[str] = None
    ):
        """
        Start sync daemon.

        Args:
            repo_path: Git repository path
            branch: Git branch to monitor
            poll_interval: Seconds between sync cycles
            sync_direction: bidirectional|git_to_entire|entire_to_git
            api_url: Entire.io API URL
            api_key: Entire.io API key
        """
        config = SyncConfig(
            repo_path=Path(repo_path),
            branch=branch,
            poll_interval_seconds=poll_interval,
            sync_direction=sync_direction,
            entire_api_url=api_url,
            entire_api_key=api_key
        )

        self.daemon = get_sync_daemon(config)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        print(f"Starting entire.io sync daemon...")
        print(f"  Repository: {repo_path}")
        print(f"  Branch: {branch}")
        print(f"  Direction: {sync_direction}")
        print(f"  Poll interval: {poll_interval}s")
        print()

        try:
            asyncio.run(self.daemon.start())
        except KeyboardInterrupt:
            print("\nShutdown requested via Ctrl+C")
        except Exception as e:
            logger.error(f"Daemon error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            print("Daemon stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        if not self._shutdown_requested:
            print("\nShutdown signal received...")
            self._shutdown_requested = True
            if self.daemon:
                asyncio.create_task(self.daemon.stop())

    def stop(self):
        """Stop running daemon."""
        # TODO: Implement daemon process lookup and termination
        print("Stop command not yet implemented")
        print("Use 'ps aux | grep sync_cli' and 'kill <pid>' for now")
        sys.exit(1)

    def status(self):
        """Show daemon status and statistics."""
        # TODO: Implement daemon status check via IPC or pid file
        print("Status command not yet implemented")
        print("Use 'ps aux | grep sync_cli' to check if running")
        sys.exit(1)

    def health(self, api_url: str = "https://api.entire.io/v1", api_key: Optional[str] = None):
        """
        Check entire.io API health.

        Args:
            api_url: Entire.io API URL
            api_key: Entire.io API key
        """
        from .entire_ops import get_entire_ops

        client = get_entire_ops(api_url=api_url, api_key=api_key)

        print("Checking entire.io API health...")

        try:
            health = asyncio.run(client.health_check())

            print()
            print(f"Status: {health['status']}")
            print(f"Latency: {health['latency_ms']}ms")
            print(f"Timestamp: {health['timestamp']}")

            if health["status"] == "healthy":
                print("\n✓ Entire.io API is healthy")
                sys.exit(0)
            else:
                print(f"\n✗ Entire.io API is unhealthy: {health.get('error', 'Unknown error')}")
                sys.exit(1)

        except Exception as e:
            print(f"\n✗ Health check failed: {e}")
            sys.exit(1)
        finally:
            asyncio.run(client.close())


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Entire.io sync daemon CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start daemon
  sync-cli start /path/to/repo --branch main --poll-interval 60

  # Start with API key from environment
  export ENTIRE_API_KEY=your_key_here
  sync-cli start /path/to/repo

  # Check API health
  sync-cli health

  # Check daemon status
  sync-cli status

  # Stop daemon
  sync-cli stop
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Start command
    start_parser = subparsers.add_parser("start", help="Start sync daemon")
    start_parser.add_argument(
        "repo_path",
        help="Path to git repository"
    )
    start_parser.add_argument(
        "--branch",
        default="main",
        help="Git branch to monitor (default: main)"
    )
    start_parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Seconds between sync cycles (default: 60)"
    )
    start_parser.add_argument(
        "--sync-direction",
        choices=["bidirectional", "git_to_entire", "entire_to_git"],
        default="bidirectional",
        help="Sync direction (default: bidirectional)"
    )
    start_parser.add_argument(
        "--api-url",
        default="https://api.entire.io/v1",
        help="Entire.io API URL"
    )
    start_parser.add_argument(
        "--api-key",
        help="Entire.io API key (or set ENTIRE_API_KEY env var)"
    )

    # Stop command
    subparsers.add_parser("stop", help="Stop running daemon")

    # Status command
    subparsers.add_parser("status", help="Show daemon status")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check entire.io API health")
    health_parser.add_argument(
        "--api-url",
        default="https://api.entire.io/v1",
        help="Entire.io API URL"
    )
    health_parser.add_argument(
        "--api-key",
        help="Entire.io API key (or set ENTIRE_API_KEY env var)"
    )

    args = parser.parse_args()

    # Get API key from environment if not provided
    if hasattr(args, "api_key") and args.api_key is None:
        import os
        args.api_key = os.environ.get("ENTIRE_API_KEY")

    # Execute command
    cli = SyncCLI()

    if args.command == "start":
        cli.start(
            repo_path=args.repo_path,
            branch=args.branch,
            poll_interval=args.poll_interval,
            sync_direction=args.sync_direction,
            api_url=args.api_url,
            api_key=args.api_key
        )
    elif args.command == "stop":
        cli.stop()
    elif args.command == "status":
        cli.status()
    elif args.command == "health":
        cli.health(api_url=args.api_url, api_key=args.api_key)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
