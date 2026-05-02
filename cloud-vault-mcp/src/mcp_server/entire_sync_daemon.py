"""Async daemon for syncing entire.io commits to vault and SurrealDB."""

import asyncio
import logging
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_server.entire_ops import CommitData, EntireOps, ParsingError


logger = logging.getLogger(__name__)


class WorkQueue:
    """SQLite-backed work queue for tracking processed commits."""

    def __init__(self, db_path: str = ":memory:"):
        """Initialize work queue."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema if needed."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_commits (
                    commit_hash TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'completed'
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def mark_completed(self, commit_hash: str) -> None:
        """Mark a commit as processed."""
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now(UTC).isoformat()
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_commits (commit_hash, processed_at, status)
                VALUES (?, ?, 'completed')
                """,
                (commit_hash, now),
            )
            conn.commit()
        finally:
            conn.close()

    def is_processed(self, commit_hash: str) -> bool:
        """Check if a commit has been processed."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT 1 FROM processed_commits WHERE commit_hash = ?",
                (commit_hash,),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_pending_count(self) -> int:
        """Get count of pending commits in queue."""
        # For this implementation, we don't maintain a pending queue
        # Instead, we track processed commits and everything not processed is pending
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM processed_commits WHERE status = 'completed'"
            )
            count = cursor.fetchone()[0]
            return count
        finally:
            conn.close()


class DeadLetterQueue:
    """SQLite-backed dead letter queue for failed commits."""

    def __init__(self, db_path: str):
        """Initialize DLQ."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema if needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    commit_hash TEXT PRIMARY KEY,
                    failure_reason TEXT,
                    failure_count INTEGER DEFAULT 1,
                    last_attempt TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_dlq_created ON dead_letter_queue(created_at)
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add(self, commit_hash: str, reason: str) -> None:
        """Add failed commit to DLQ."""
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now(UTC).isoformat()
            conn.execute(
                """
                INSERT INTO dead_letter_queue
                (commit_hash, failure_reason, failure_count, last_attempt)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(commit_hash) DO UPDATE SET
                    failure_count = failure_count + 1,
                    failure_reason = excluded.failure_reason,
                    last_attempt = excluded.last_attempt
                """,
                (commit_hash, reason, now),
            )
            conn.commit()
        finally:
            conn.close()

    def get_all(self) -> list[dict[str, Any]]:
        """Get all dead letter queue entries."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT commit_hash, failure_reason, failure_count, last_attempt, created_at
                FROM dead_letter_queue
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [
                {
                    "commit_hash": row[0],
                    "failure_reason": row[1],
                    "failure_count": row[2],
                    "last_attempt": row[3],
                    "created_at": row[4],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_count(self) -> int:
        """Get count of entries in DLQ."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM dead_letter_queue")
            count = cursor.fetchone()[0]
            return count
        finally:
            conn.close()

    def retry(self, commit_hash: str) -> None:
        """Remove a commit from DLQ for retry."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "DELETE FROM dead_letter_queue WHERE commit_hash = ?", (commit_hash,)
            )
            conn.commit()
        finally:
            conn.close()


class EntireSyncDaemon:
    """Async daemon for polling and syncing entire.io commits to vault."""

    def __init__(
        self,
        vault_path: str,
        poll_interval_seconds: int = 300,
        git_path: str | None = None,
        surrealdb_url: str | None = None,
    ):
        """Initialize daemon.

        Args:
            vault_path: Path to vault directory
            poll_interval_seconds: Seconds between polls (default: 5 min)
            git_path: Path to git repository (default: same as vault_path)
            surrealdb_url: SurrealDB HTTP endpoint (optional, enables DB sync)
        """
        self.vault_path = Path(vault_path)
        self.git_path = Path(git_path or vault_path)
        self.poll_interval = poll_interval_seconds
        self.surrealdb_url = surrealdb_url

        self.entire_ops = EntireOps(str(self.vault_path))
        self.work_queue = WorkQueue(str(self.vault_path / ".entire" / "queue.db"))
        self.dlq = DeadLetterQueue(str(self.vault_path / ".entire" / "dlq.db"))

        self.last_sync_time: datetime | None = None
        self._agent_context_ops = None

        if surrealdb_url:
            self._init_surrealdb()

    def _init_surrealdb(self) -> None:
        """Initialize SurrealDB connection. Graceful fallback on failure."""
        try:
            from mcp_server.agent_context_ops import AgentContextOps

            self._agent_context_ops = AgentContextOps(
                surrealdb_url=self.surrealdb_url,
            )
            logger.info(f"SurrealDB integration enabled: {self.surrealdb_url}")
        except Exception as e:
            logger.warning(f"SurrealDB unavailable, continuing without it: {e}")
            self._agent_context_ops = None

    async def start(self, since: str | None = None) -> None:
        """Start the daemon polling loop.

        Args:
            since: ISO date string to start syncing from (e.g. '2026-01-01').
                   If provided, sets last_sync_time for initial backfill.
        """
        if since:
            self.last_sync_time = datetime.fromisoformat(since)
            logger.info(f"Starting with backfill from: {since}")

        logger.info(
            f"Starting Entire.io sync daemon (poll interval: {self.poll_interval}s)"
        )
        while True:
            try:
                await self.poll_and_sync()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("Daemon shutdown requested")
                break
            except Exception as e:
                logger.error(f"Polling error: {e}", exc_info=True)
                await asyncio.sleep(30)  # Backoff on error

    async def backfill(self, since: str | None = None) -> dict[str, Any]:
        """Run a one-time backfill of historical commits.

        Args:
            since: ISO date string to backfill from. If None, processes all commits.

        Returns:
            Dict with backfill results (total, processed, skipped, failed)
        """
        if since:
            self.last_sync_time = datetime.fromisoformat(since)
        else:
            self.last_sync_time = None  # Get all commits

        logger.info(f"Starting backfill (since={since or 'all time'})")

        commits = await self._get_new_commits()
        entire_commits = [c for c in commits if self._is_entire_commit(c)]

        results = {
            "total": len(commits),
            "entire_commits": len(entire_commits),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
        }

        for commit in entire_commits:
            commit_hash = commit["hash"]
            if self.work_queue.is_processed(commit_hash):
                results["skipped"] += 1
                continue
            try:
                commit_data = self.entire_ops.parse_commit_metadata(
                    commit_hash=commit_hash,
                    commit_author=commit["author"],
                    commit_date=commit["date"],
                    commit_body=commit["body"],
                )
                await self._create_vault_note(commit_data)
                await self._sync_to_surrealdb(commit_data)
                self.work_queue.mark_completed(commit_hash)
                results["processed"] += 1
            except Exception as e:
                logger.warning(f"Backfill failed for {commit_hash[:8]}: {e}")
                self.dlq.add(commit_hash, str(e))
                results["failed"] += 1

        self.last_sync_time = datetime.now(UTC)
        logger.info(f"Backfill complete: {results}")
        return results

    async def poll_and_sync(self) -> None:
        """Poll git log for new commits and sync to vault."""
        try:
            # Get commits since last sync
            commits = await self._get_new_commits()
            logger.info(f"Found {len(commits)} new commits to process")

            # Filter for entire.io markers
            entire_commits = [c for c in commits if self._is_entire_commit(c)]
            logger.info(f"Filtered to {len(entire_commits)} entire.io commits")

            # Process each commit
            for commit in entire_commits:
                await self._process_commit(commit)

            # Update last sync time
            self.last_sync_time = datetime.now(UTC)

        except Exception as e:
            logger.error(f"Error in poll_and_sync: {e}", exc_info=True)

    async def _get_new_commits(self) -> list[dict[str, str]]:
        """Get new commits from git log.

        Returns:
            List of dicts with keys: hash, author, date, body
        """
        try:
            # Build git log command with proper formatting
            git_cmd = [
                "git",
                "-C",
                str(self.git_path),
                "log",
                "--format=%H%n%an <%ae>%n%aI%n%b%n---END---",
                "--all",
            ]

            # If we have a last sync time, only get newer commits
            if self.last_sync_time:
                git_cmd.insert(4, f"--since={self.last_sync_time.isoformat()}")

            result = subprocess.run(
                git_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git command failed: {result.stderr}")

            # Parse git log output
            commits = []
            entries = result.stdout.split("---END---")

            for entry in entries:
                entry = entry.strip()
                if not entry:
                    continue

                lines = entry.split("\n")
                if len(lines) >= 3:
                    commit = {
                        "hash": lines[0],
                        "author": lines[1],
                        "date": lines[2],
                        "body": "\n".join(lines[3:]),
                    }
                    commits.append(commit)

            return commits

        except Exception as e:
            logger.error(f"Failed to get commits: {e}")
            return []

    def _is_entire_commit(self, commit: dict[str, str]) -> bool:
        """Check if commit is from entire.io (has markers in body)."""
        body = commit.get("body", "").lower()
        # Look for entire.io markers
        markers = [
            "entire.io",
            "entire-checkpoint",
            "session summary",
            "outcomes achieved",
        ]
        return any(marker in body for marker in markers)

    async def _process_commit(self, commit: dict[str, str]) -> None:
        """Process a single entire.io commit.

        Args:
            commit: Dict with hash, author, date, body
        """
        commit_hash = commit["hash"]

        # Skip if already processed
        if self.work_queue.is_processed(commit_hash):
            logger.debug(f"Commit {commit_hash[:8]} already processed, skipping")
            return

        try:
            # Parse commit metadata
            commit_data = self.entire_ops.parse_commit_metadata(
                commit_hash=commit_hash,
                commit_author=commit["author"],
                commit_date=commit["date"],
                commit_body=commit["body"],
            )

            # Create vault note
            await self._create_vault_note(commit_data)

            # Sync to SurrealDB (optional, graceful fallback)
            await self._sync_to_surrealdb(commit_data)

            # Mark as processed
            self.work_queue.mark_completed(commit_hash)
            logger.info(f"Successfully synced commit {commit_hash[:8]}")

        except ParsingError as e:
            logger.warning(f"Failed to parse commit {commit_hash[:8]}: {e}")
            self.dlq.add(commit_hash, str(e))
        except Exception as e:
            logger.error(
                f"Error processing commit {commit_hash[:8]}: {e}", exc_info=True
            )
            self.dlq.add(commit_hash, str(e))

    async def _sync_to_surrealdb(self, commit_data: CommitData) -> None:
        """Sync parsed commit data to SurrealDB as session + outcome.

        Gracefully skips if SurrealDB is not configured or unavailable.

        Args:
            commit_data: Parsed commit data
        """
        if not self._agent_context_ops:
            return

        try:
            # Calculate approximate duration from commit metadata (default 0)
            duration_ms = 0

            # Track as a session
            session_id = self._agent_context_ops.track_session(
                agent_names=[commit_data.agent_id],
                duration_ms=duration_ms,
                status="completed",
            )

            # Record outcome with metrics
            summary_parts = []
            if commit_data.outcomes:
                summary_parts.append(f"{len(commit_data.outcomes)} outcomes")
            if commit_data.next_actions:
                summary_parts.append(f"{len(commit_data.next_actions)} next actions")
            summary = f"Checkpoint {commit_data.commit_hash[:8]}: {', '.join(summary_parts) or 'no details'}"

            self._agent_context_ops.record_outcome(
                session_id=session_id,
                status="success",
                summary=summary,
                metrics=commit_data.metrics or {},
            )

            logger.info(
                f"Synced commit {commit_data.commit_hash[:8]} to SurrealDB "
                f"(session={session_id})"
            )

        except Exception as e:
            logger.warning(
                f"SurrealDB sync failed for {commit_data.commit_hash[:8]}, "
                f"continuing without it: {e}"
            )

    async def _create_vault_note(self, commit_data: CommitData) -> None:
        """Create a vault note for a commit.

        Args:
            commit_data: Parsed commit data
        """
        # Create checkpoint directory if needed
        checkpoint_dir = self.vault_path / "daily" / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Build filename
        date_str = commit_data.timestamp.date().isoformat()
        filename = f"{date_str}-{commit_data.commit_hash[:8]}.md"
        filepath = checkpoint_dir / filename

        # Build note content
        content = self._build_checkpoint_note(commit_data)

        # Write to vault
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Created checkpoint note: {filepath}")

    def _build_checkpoint_note(self, commit_data: CommitData) -> str:
        """Build markdown checkpoint note.

        Args:
            commit_data: Parsed commit data

        Returns:
            Markdown content
        """
        date_str = commit_data.timestamp.date().isoformat()
        time_str = commit_data.timestamp.time().isoformat()

        outcomes_text = (
            "\n".join(f"- {outcome}" for outcome in commit_data.outcomes)
            if commit_data.outcomes
            else "No outcomes recorded"
        )

        metrics_text = ""
        if commit_data.metrics:
            for key, value in sorted(commit_data.metrics.items()):
                if key.endswith("_coverage"):
                    metrics_text += f"- {key.replace('_coverage', '').title()}: {value * 100:.1f}%\n"

        next_actions_text = (
            "\n".join(f"- {action}" for action in commit_data.next_actions)
            if commit_data.next_actions
            else "No next actions recorded"
        )

        return f"""---
title: "Checkpoint - {date_str}"
date: {date_str}
time: {time_str}
status: completed
agent_id: {commit_data.agent_id}
commit_hash: {commit_data.commit_hash}
tags: [checkpoint, entire-io, {commit_data.agent_id}]
---

# {date_str} Checkpoint

**Agent**: {commit_data.agent_id}
**Time**: {time_str}

## Outcomes Achieved

{outcomes_text}

## Metrics

{metrics_text if metrics_text else "No metrics recorded"}

## Team Status

{commit_data.team_status}

## Next Actions

{next_actions_text}

---

*Synced from entire.io checkpoint: {commit_data.commit_hash}*
"""

    async def get_status(self) -> dict[str, Any]:
        """Get current daemon status."""
        return {
            "status": "running",
            "last_sync": self.last_sync_time.isoformat()
            if self.last_sync_time
            else None,
            "processed_count": self.work_queue.get_pending_count(),
            "dlq_count": self.dlq.get_count(),
            "poll_interval": self.poll_interval,
            "surrealdb_enabled": self._agent_context_ops is not None,
            "surrealdb_url": self.surrealdb_url,
        }

    async def retry_failed(self, commit_hash: str) -> bool:
        """Retry a failed commit.

        Args:
            commit_hash: Commit hash to retry

        Returns:
            True if retry was initiated, False if commit not found
        """
        dlq_entries = self.dlq.get_all()
        if any(e["commit_hash"] == commit_hash for e in dlq_entries):
            self.dlq.retry(commit_hash)
            logger.info(f"Scheduled retry for commit {commit_hash}")
            return True
        return False
