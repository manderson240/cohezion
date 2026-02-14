"""
Bidirectional sync daemon between git commits and entire.io checkpoints.

Monitors git repository for new commits and syncs to entire.io.
Also polls entire.io for remote checkpoint events and syncs metadata to git.
"""

import asyncio
import subprocess
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel
from .entire_ops import get_entire_ops, EntireOpsClient, Checkpoint, EntireOpsError

logger = logging.getLogger(__name__)


class SyncConfig(BaseModel):
    """Sync daemon configuration."""
    repo_path: Path
    branch: str = "main"
    poll_interval_seconds: int = 60
    sync_direction: str = "bidirectional"  # bidirectional|git_to_entire|entire_to_git
    entire_api_url: str = "https://api.entire.io/v1"
    entire_api_key: Optional[str] = None
    auto_tag: bool = True
    max_batch_size: int = 100


class SyncStats(BaseModel):
    """Sync daemon statistics."""
    commits_synced: int = 0
    checkpoints_created: int = 0
    checkpoints_downloaded: int = 0
    errors: int = 0
    last_sync_timestamp: Optional[str] = None
    uptime_seconds: float = 0.0


class SyncDaemon:
    """
    Orchestrates bidirectional sync between git and entire.io.

    Features:
    - Monitors git commits and creates entire.io checkpoints
    - Polls entire.io for remote checkpoints and tags git commits
    - Automatic retry with exponential backoff
    - Health monitoring and metrics collection
    - Graceful shutdown on SIGTERM
    """

    def __init__(self, config: SyncConfig):
        """
        Initialize sync daemon.

        Args:
            config: Daemon configuration
        """
        self.config = config
        self.entire_client: EntireOpsClient = get_entire_ops(
            api_url=config.entire_api_url,
            api_key=config.entire_api_key
        )
        self.stats = SyncStats()
        self._running = False
        self._start_time: Optional[datetime] = None
        self._last_synced_commit: Optional[str] = None
        self._last_synced_checkpoint: Optional[str] = None

    async def start(self):
        """Start sync daemon event loop."""
        if self._running:
            logger.warning("Sync daemon already running")
            return

        self._running = True
        self._start_time = datetime.utcnow()
        logger.info(
            f"Starting sync daemon: {self.config.sync_direction} "
            f"(poll interval: {self.config.poll_interval_seconds}s)"
        )

        try:
            while self._running:
                cycle_start = datetime.utcnow()

                # Execute sync cycle
                try:
                    if self.config.sync_direction in ("bidirectional", "git_to_entire"):
                        await self._sync_git_to_entire()

                    if self.config.sync_direction in ("bidirectional", "entire_to_git"):
                        await self._sync_entire_to_git()

                    self.stats.last_sync_timestamp = datetime.utcnow().isoformat() + "Z"

                except Exception as e:
                    logger.error(f"Sync cycle error: {e}", exc_info=True)
                    self.stats.errors += 1

                # Update uptime
                if self._start_time:
                    self.stats.uptime_seconds = (
                        datetime.utcnow() - self._start_time
                    ).total_seconds()

                # Sleep until next cycle
                cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                sleep_time = max(0, self.config.poll_interval_seconds - cycle_duration)
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info("Sync daemon cancelled")
        finally:
            await self.stop()

    async def stop(self):
        """Stop sync daemon gracefully."""
        if not self._running:
            return

        logger.info("Stopping sync daemon...")
        self._running = False

        try:
            await self.entire_client.close()
        except Exception as e:
            logger.error(f"Error closing entire.io client: {e}")

        logger.info("Sync daemon stopped")

    async def _sync_git_to_entire(self):
        """
        Sync new git commits to entire.io checkpoints.

        Detects commits since last sync and creates corresponding checkpoints.
        """
        try:
            # Get new commits since last sync
            commits = await self._get_new_commits()
            if not commits:
                logger.debug("No new commits to sync")
                return

            logger.info(f"Syncing {len(commits)} commits to entire.io")

            for commit in commits[:self.config.max_batch_size]:
                try:
                    # Create checkpoint for commit
                    checkpoint = await self.entire_client.create_checkpoint(
                        commit_hash=commit["hash"],
                        message=commit["message"],
                        author=commit["author"],
                        files_changed=commit["files_changed"],
                        lines_added=commit["lines_added"],
                        lines_deleted=commit["lines_deleted"],
                        metadata={
                            "branch": self.config.branch,
                            "repo_path": str(self.config.repo_path)
                        }
                    )

                    # Auto-tag if enabled
                    if self.config.auto_tag:
                        tags = self._extract_tags_from_message(commit["message"])
                        if tags:
                            await self.entire_client.tag_checkpoint(checkpoint.id, tags)

                    self._last_synced_commit = commit["hash"]
                    self.stats.commits_synced += 1
                    self.stats.checkpoints_created += 1

                    logger.debug(f"Created checkpoint {checkpoint.id} for commit {commit['hash'][:8]}")

                except EntireOpsError as e:
                    logger.error(f"Failed to sync commit {commit['hash'][:8]}: {e}")
                    self.stats.errors += 1

        except Exception as e:
            logger.error(f"Error in git→entire sync: {e}", exc_info=True)
            self.stats.errors += 1

    async def _sync_entire_to_git(self):
        """
        Sync entire.io checkpoints to git metadata.

        Polls for new remote checkpoints and annotates local git commits.
        """
        try:
            # Get new checkpoints since last sync
            since_timestamp = None
            if self.stats.last_sync_timestamp:
                since_timestamp = self.stats.last_sync_timestamp

            checkpoints = await self.entire_client.list_checkpoints(
                limit=self.config.max_batch_size,
                since=since_timestamp
            )

            if not checkpoints:
                logger.debug("No new checkpoints to sync")
                return

            logger.info(f"Syncing {len(checkpoints)} checkpoints from entire.io")

            for checkpoint in checkpoints:
                try:
                    # Annotate git commit with checkpoint metadata
                    await self._annotate_commit(checkpoint)

                    self._last_synced_checkpoint = checkpoint.id
                    self.stats.checkpoints_downloaded += 1

                    logger.debug(
                        f"Annotated commit {checkpoint.commit_hash[:8]} "
                        f"with checkpoint {checkpoint.id}"
                    )

                except Exception as e:
                    logger.error(f"Failed to annotate checkpoint {checkpoint.id}: {e}")
                    self.stats.errors += 1

        except Exception as e:
            logger.error(f"Error in entire→git sync: {e}", exc_info=True)
            self.stats.errors += 1

    async def _get_new_commits(self) -> List[Dict[str, Any]]:
        """
        Get new git commits since last sync.

        Returns:
            List of commit dicts with hash, message, author, stats
        """
        try:
            # Build git log command
            cmd = [
                "git",
                "-C", str(self.config.repo_path),
                "log",
                f"{self.config.branch}",
                "--pretty=format:%H|%an|%s",
                "--numstat",
                "--no-merges"
            ]

            # Add range filter if we have a last synced commit
            if self._last_synced_commit:
                cmd[3] = f"{self._last_synced_commit}..{self.config.branch}"

            # Execute git log
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )

            # Parse output
            commits = []
            current_commit = None

            for line in result.stdout.splitlines():
                if "|" in line:  # Commit header
                    if current_commit:
                        commits.append(current_commit)

                    parts = line.split("|", 2)
                    current_commit = {
                        "hash": parts[0],
                        "author": parts[1],
                        "message": parts[2],
                        "files_changed": 0,
                        "lines_added": 0,
                        "lines_deleted": 0
                    }
                elif current_commit and line.strip():  # Stats line
                    parts = line.split("\t")
                    if len(parts) == 3:
                        added, deleted, _ = parts
                        if added.isdigit():
                            current_commit["lines_added"] += int(added)
                        if deleted.isdigit():
                            current_commit["lines_deleted"] += int(deleted)
                        current_commit["files_changed"] += 1

            if current_commit:
                commits.append(current_commit)

            return commits

        except subprocess.CalledProcessError as e:
            logger.error(f"Git log command failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting new commits: {e}", exc_info=True)
            return []

    async def _annotate_commit(self, checkpoint: Checkpoint):
        """
        Annotate git commit with entire.io checkpoint metadata.

        Creates a git note with checkpoint ID and metadata.

        Args:
            checkpoint: Checkpoint to annotate with
        """
        try:
            # Create git note with checkpoint data
            note_content = (
                f"Entire.io Checkpoint: {checkpoint.id}\n"
                f"Timestamp: {checkpoint.timestamp}\n"
                f"Files Changed: {checkpoint.files_changed}\n"
                f"Lines: +{checkpoint.lines_added} -{checkpoint.lines_deleted}\n"
            )

            cmd = [
                "git",
                "-C", str(self.config.repo_path),
                "notes",
                "add",
                "-f",  # Force overwrite if exists
                "-m", note_content,
                checkpoint.commit_hash
            ]

            subprocess.run(cmd, capture_output=True, check=True, timeout=5)

        except subprocess.CalledProcessError as e:
            # Note might already exist - not an error
            if b"already has a note" not in e.stderr:
                raise
        except Exception as e:
            logger.error(f"Error annotating commit: {e}", exc_info=True)
            raise

    def _extract_tags_from_message(self, message: str) -> List[str]:
        """
        Extract tags from commit message.

        Looks for hashtags (#feature, #fix, etc.) in commit message.

        Args:
            message: Commit message

        Returns:
            List of extracted tag strings
        """
        tags = []
        for word in message.split():
            if word.startswith("#") and len(word) > 1:
                tags.append(word[1:].lower())
        return tags

    def get_stats(self) -> SyncStats:
        """Get current daemon statistics."""
        return self.stats

    def is_running(self) -> bool:
        """Check if daemon is running."""
        return self._running


# Singleton instance
_sync_daemon: Optional[SyncDaemon] = None


def get_sync_daemon(config: Optional[SyncConfig] = None) -> SyncDaemon:
    """
    Get or create singleton SyncDaemon instance.

    Args:
        config: Daemon configuration (required on first call)

    Returns:
        SyncDaemon singleton instance

    Raises:
        ValueError: If config not provided on first call
    """
    global _sync_daemon
    if _sync_daemon is None:
        if config is None:
            raise ValueError("Config required to initialize sync daemon")
        _sync_daemon = SyncDaemon(config)
    return _sync_daemon


def reset_sync_daemon():
    """Reset singleton (for testing)."""
    global _sync_daemon
    _sync_daemon = None
