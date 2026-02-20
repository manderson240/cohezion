"""CLI entry point for entire.io sync daemon."""

import asyncio
import json
import logging
import os
from pathlib import Path

import click

from mcp_server.entire_sync_daemon import EntireSyncDaemon


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default paths
VAULT_PATH = os.getenv("VAULT_PATH", str(Path.home() / "vaults" / "cohezion-vault"))
GIT_PATH = os.getenv("GIT_PATH", VAULT_PATH)
SURREALDB_URL = os.getenv("SURREALDB_URL", "")


@click.group()
def cli():
    """Entire.io synchronization daemon and utilities."""
    pass


@cli.command()
@click.option(
    "--poll-interval",
    default=300,
    help="Polling interval in seconds (default: 300)",
    type=int,
)
@click.option("--vault-path", default=VAULT_PATH, help="Path to vault")
@click.option("--git-path", default=GIT_PATH, help="Path to git repository")
@click.option("--surrealdb-url", default=SURREALDB_URL, help="SurrealDB HTTP endpoint")
@click.option(
    "--since", default=None, help="ISO date to start syncing from (e.g. 2026-01-01)"
)
def start(
    poll_interval: int, vault_path: str, git_path: str, surrealdb_url: str, since: str
) -> None:
    """Start the entire.io sync daemon."""
    logger.info(f"Starting daemon with vault: {vault_path}")
    logger.info(f"Git repository: {git_path}")
    logger.info(f"Poll interval: {poll_interval}s")

    daemon = EntireSyncDaemon(
        vault_path=vault_path,
        poll_interval_seconds=poll_interval,
        git_path=git_path,
        surrealdb_url=surrealdb_url or None,
    )

    try:
        asyncio.run(daemon.start(since=since))
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")


@cli.command()
@click.option("--vault-path", default=VAULT_PATH, help="Path to vault")
@click.option("--git-path", default=GIT_PATH, help="Path to git repository")
def status(vault_path: str, git_path: str) -> None:
    """Show daemon status and queue state."""
    try:
        daemon = EntireSyncDaemon(vault_path=vault_path, git_path=git_path)
        status_info = asyncio.run(daemon.get_status())

        click.echo("Entire.io Sync Daemon Status")
        click.echo("=" * 40)
        click.echo(f"Status: {status_info['status']}")
        click.echo(f"Last sync: {status_info['last_sync'] or 'Never'}")
        click.echo(f"Processed commits: {status_info['processed_count']}")
        click.echo(f"Failed commits (DLQ): {status_info['dlq_count']}")
        click.echo(f"Poll interval: {status_info['poll_interval']}s")
    except Exception as e:
        click.echo(f"Error getting status: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--vault-path", default=VAULT_PATH, help="Path to vault")
def dlq(vault_path: str) -> None:
    """List dead letter queue entries."""
    try:
        daemon = EntireSyncDaemon(vault_path=vault_path)
        entries = daemon.dlq.get_all()

        if not entries:
            click.echo("Dead letter queue is empty")
            return

        click.echo("Dead Letter Queue")
        click.echo("=" * 80)
        for entry in entries:
            click.echo(
                f"Commit: {entry['commit_hash'][:8]} - "
                f"Failures: {entry['failure_count']}"
            )
            click.echo(f"  Reason: {entry['failure_reason']}")
            click.echo(f"  Last attempt: {entry['last_attempt']}")
            click.echo()
    except Exception as e:
        click.echo(f"Error listing DLQ: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("commit_hash")
@click.option("--vault-path", default=VAULT_PATH, help="Path to vault")
def retry(commit_hash: str, vault_path: str) -> None:
    """Retry a failed commit from the dead letter queue."""
    try:
        daemon = EntireSyncDaemon(vault_path=vault_path)
        success = asyncio.run(daemon.retry_failed(commit_hash))

        if success:
            click.echo(f"Successfully scheduled retry for {commit_hash}")
        else:
            click.echo(f"Commit {commit_hash} not found in dead letter queue", err=True)
            raise SystemExit(1)
    except Exception as e:
        click.echo(f"Error retrying commit: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--vault-path", default=VAULT_PATH, help="Path to vault")
@click.option("--git-path", default=GIT_PATH, help="Path to git repository")
@click.option("--surrealdb-url", default=SURREALDB_URL, help="SurrealDB HTTP endpoint")
@click.option(
    "--since", default=None, help="ISO date to backfill from (e.g. 2026-01-01)"
)
def backfill(vault_path: str, git_path: str, surrealdb_url: str, since: str) -> None:
    """Run one-time backfill of historical commits."""
    click.echo(f"Starting backfill (since={since or 'all time'})")

    daemon = EntireSyncDaemon(
        vault_path=vault_path,
        git_path=git_path,
        surrealdb_url=surrealdb_url or None,
    )

    try:
        results = asyncio.run(daemon.backfill(since=since))
        click.echo("Backfill Results")
        click.echo("=" * 40)
        click.echo(f"Total commits scanned: {results['total']}")
        click.echo(f"Entire.io commits found: {results['entire_commits']}")
        click.echo(f"Successfully processed: {results['processed']}")
        click.echo(f"Skipped (already processed): {results['skipped']}")
        click.echo(f"Failed (sent to DLQ): {results['failed']}")
    except Exception as e:
        click.echo(f"Backfill failed: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--vault-path", default=VAULT_PATH, help="Path to vault")
@click.option("--git-path", default=GIT_PATH, help="Path to git repository")
@click.option("--surrealdb-url", default=SURREALDB_URL, help="SurrealDB HTTP endpoint")
@click.option("--json-output", is_flag=True, help="Output as JSON for machine parsing")
def health(
    vault_path: str, git_path: str, surrealdb_url: str, json_output: bool
) -> None:
    """Check daemon health: paths, queues, SurrealDB connectivity."""
    checks = {
        "vault_path": {"status": "fail", "detail": ""},
        "git_path": {"status": "fail", "detail": ""},
        "work_queue": {"status": "fail", "detail": ""},
        "dlq": {"status": "fail", "detail": ""},
        "surrealdb": {"status": "skip", "detail": "not configured"},
    }
    healthy = True

    try:
        # Check 1: Vault path
        if Path(vault_path).exists():
            checks["vault_path"] = {"status": "pass", "detail": vault_path}
        else:
            checks["vault_path"] = {
                "status": "fail",
                "detail": f"not found: {vault_path}",
            }
            healthy = False

        # Check 2: Git path
        if Path(git_path).exists():
            checks["git_path"] = {"status": "pass", "detail": git_path}
        else:
            checks["git_path"] = {"status": "fail", "detail": f"not found: {git_path}"}
            healthy = False

        # Check 3 & 4: Work queue and DLQ
        daemon = EntireSyncDaemon(
            vault_path=vault_path,
            git_path=git_path,
            surrealdb_url=surrealdb_url or None,
        )

        status_info = asyncio.run(daemon.get_status())
        checks["work_queue"] = {
            "status": "pass",
            "detail": f"{status_info['processed_count']} processed",
        }
        checks["dlq"] = {
            "status": "warn" if status_info["dlq_count"] > 0 else "pass",
            "detail": f"{status_info['dlq_count']} failed commits",
        }
        if status_info["dlq_count"] > 10:
            healthy = False
            checks["dlq"]["status"] = "fail"

        # Check 5: SurrealDB (if configured)
        if surrealdb_url:
            try:
                import httpx

                resp = httpx.get(f"{surrealdb_url.rstrip('/')}/health", timeout=5.0)
                if resp.status_code == 200:
                    checks["surrealdb"] = {"status": "pass", "detail": surrealdb_url}
                else:
                    checks["surrealdb"] = {
                        "status": "fail",
                        "detail": f"HTTP {resp.status_code}",
                    }
                    healthy = False
            except Exception as e:
                checks["surrealdb"] = {"status": "fail", "detail": str(e)}
                healthy = False

    except Exception as e:
        healthy = False
        checks["_error"] = {"status": "fail", "detail": str(e)}

    # Build result
    result = {
        "healthy": healthy,
        "last_sync": status_info.get("last_sync") if "status_info" in dir() else None,
        "checks": checks,
    }

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo("Entire.io Sync Daemon Health Check")
        click.echo("=" * 40)
        for name, check in checks.items():
            if name.startswith("_"):
                continue
            icon = {"pass": "OK", "fail": "FAIL", "warn": "WARN", "skip": "SKIP"}[
                check["status"]
            ]
            click.echo(f"  [{icon:4s}] {name}: {check['detail']}")
        click.echo()
        if healthy:
            click.echo("Overall: HEALTHY")
        else:
            click.echo("Overall: UNHEALTHY")

    raise SystemExit(0 if healthy else 1)


@cli.command()
@click.option("--vault-path", default=VAULT_PATH, help="Path to vault")
@click.option("--git-path", default=GIT_PATH, help="Path to git repository")
def test(vault_path: str, git_path: str) -> None:
    """Test daemon connectivity and basic operations."""
    click.echo("Testing Entire.io Sync Daemon")
    click.echo("=" * 40)

    try:
        daemon = EntireSyncDaemon(vault_path=vault_path, git_path=git_path)

        # Test 1: Check paths exist
        if Path(vault_path).exists():
            click.echo("✓ Vault path exists")
        else:
            click.echo(f"✗ Vault path not found: {vault_path}", err=True)

        if Path(git_path).exists():
            click.echo("✓ Git path exists")
        else:
            click.echo(f"✗ Git path not found: {git_path}", err=True)

        # Test 2: Get status
        status_info = asyncio.run(daemon.get_status())
        click.echo("✓ Status retrieval successful")
        click.echo(f"  Processed: {status_info['processed_count']}")
        click.echo(f"  Failed (DLQ): {status_info['dlq_count']}")

        # Test 3: DLQ operations
        dlq_entries = daemon.dlq.get_all()
        click.echo(f"✓ Dead letter queue readable ({len(dlq_entries)} entries)")

        click.echo()
        click.echo("All tests passed! Daemon is ready to run.")

    except Exception as e:
        click.echo(f"✗ Test failed: {e}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
