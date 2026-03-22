"""Configuration sync engine - Phase 4.

Real-time sync operations: regenerate config files, create commits,
handle conflicts, and manage atomic operations.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.config.config_state import FileMetadata
from cohezion.config.config_sync_logger import ConfigSyncLogger
from cohezion.config.config_templates import (
    ConfigTemplateEngine,
    TemplateContext,
    TemplateType,
)
from cohezion.config.git_utils import GitUtils


logger = logging.getLogger(__name__)


class ConfigSyncEngine:
    """Handles real-time synchronization of configuration files."""

    def __init__(
        self,
        repo_root: Path | None = None,
        vault_root: Path | None = None,
        sync_logger: ConfigSyncLogger | None = None,
    ):
        """Initialize sync engine."""
        if repo_root is None:
            repo_root = Path.cwd()
        if vault_root is None:
            vault_root = Path.home() / "vaults" / "cohezion-vault"
        self.repo_root = Path(repo_root)
        self.vault_root = Path(vault_root)
        self.git_utils = GitUtils(repo_root)
        self.template_engine = ConfigTemplateEngine()
        self.sync_logger = sync_logger or ConfigSyncLogger()

        # Config file paths
        self.claude_md = repo_root / "CLAUDE.md"
        self.gemini_md = repo_root / "GEMINI.md"

    async def sync_config_file(
        self,
        filename: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Sync a config file with vault content.

        Args:
            filename: "CLAUDE.md" or "GEMINI.md"
            force: Force regeneration even if no changes

        Returns:
            Sync result with status and details
        """
        start_time = asyncio.get_event_loop().time()
        result = {
            "file": filename,
            "synced": False,
            "commit_hash": None,
            "details": {},
        }

        try:
            if filename == "CLAUDE.md":
                file_path = self.claude_md
                template_type = TemplateType.CLAUDE_MD
            elif filename == "GEMINI.md":
                file_path = self.gemini_md
                template_type = TemplateType.GEMINI_MD
            else:
                logger.error(f"Unknown config file: {filename}")
                return result

            # Check for conflicts
            conflicts = await self._check_conflicts(file_path)
            if conflicts and not force:
                logger.warning(f"Conflicts detected in {filename}, skipping sync")
                result["details"]["conflicts"] = conflicts
                return result

            # Extract vault content
            vault_content = await self._extract_vault_content()

            # Create template context
            context = TemplateContext(
                latest_decisions=vault_content.get("decisions", []),
                operational_protocols=vault_content.get("protocols", []),
                operational_guardrails=vault_content.get("guardrails", []),
                recent_patterns=vault_content.get("patterns", []),
                sync_timestamp=datetime.now().isoformat(),
            )

            # Render new content
            new_content = self._render_config_file(template_type, context)

            # Check if content changed
            if file_path.exists():
                old_content = file_path.read_text()
                if old_content == new_content and not force:
                    logger.debug(f"No changes in {filename}, skipping sync")
                    return result

            # Write new content
            file_path.write_text(new_content)

            # Create backup commit before sync
            backup_success = await self.git_utils.create_backup_commit(file_path)
            if not backup_success:
                logger.warning("Backup commit failed, continuing with sync")

            # Generate commit message
            commit_msg = await self._generate_commit_message(
                filename,
                vault_content,
            )

            # Commit the changes
            commit_success = await self.git_utils.auto_commit(
                file_path,
                commit_msg,
                author_name="Cohezion ConfigOrchestrator",
                author_email="config@cohezion.local",
            )

            if commit_success:
                # Get commit hash
                history = self.git_utils.get_commit_history(file_path, max_count=1)
                if history:
                    result["commit_hash"] = history[0]["hash"]

                result["synced"] = True
                result["details"] = {
                    "message": commit_msg,
                    "content_size": len(new_content),
                    "lines": len(new_content.splitlines()),
                }

                # Log sync operation
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                await self.sync_logger.log_sync(
                    file=filename,
                    status="success",
                    details=result["details"],
                    duration_ms=duration_ms,
                )

            else:
                logger.warning(f"Commit failed for {filename}")
                result["details"]["error"] = "Commit failed"

        except Exception as e:
            logger.error(f"Sync error for {filename}: {e}", exc_info=True)
            result["details"]["error"] = str(e)
            await self.sync_logger.log_sync(
                file=filename,
                status="failed",
                error_message=str(e),
                details={"error": str(e)},
            )

        return result

    async def _check_conflicts(self, file_path: Path) -> list[str]:
        """Check for conflicts in file.

        Returns:
            List of conflicts, empty if none
        """
        if not file_path.exists():
            return []

        # Check for manual edits
        is_manual = self.git_utils.is_manual_edit(file_path)
        if not is_manual:
            return []

        # Check for uncommitted changes
        has_changes = self.git_utils.get_uncommitted_changes(file_path)
        if has_changes:
            return [f"Uncommitted changes in {file_path.name}"]

        return []

    async def _extract_vault_content(self) -> dict[str, Any]:
        """Extract canonical content from vault.

        Returns:
            Dict with decisions, patterns, protocols, etc.
        """
        content = {
            "decisions": [],
            "patterns": [],
            "protocols": [],
            "guardrails": [],
        }

        try:
            # Extract latest decisions
            decisions_dir = self.vault_root / "decisions"
            if decisions_dir.exists():
                decision_files = sorted(
                    decisions_dir.glob("*.md"),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True,
                )[:5]

                for decision_file in decision_files:
                    title = decision_file.stem
                    content["decisions"].append(title)

            # Extract patterns
            patterns_dir = self.vault_root / "patterns"
            if patterns_dir.exists():
                pattern_files = sorted(
                    patterns_dir.glob("*.md"),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True,
                )[:5]

                for pattern_file in pattern_files:
                    title = pattern_file.stem
                    content["patterns"].append(title)

        except Exception as e:
            logger.warning(f"Error extracting vault content: {e}")

        # Add default operational content
        content["protocols"] = [
            "Hallucination Resolution: Ground specs in truth anchors",
            "Verification First: Run validation before completion",
            "Delegate Specialized Tasks: Use sub-agents for focused work",
            "Retrospection: Explicit review at phase completion",
        ]

        content["guardrails"] = [
            "No WMD uplift, critical infrastructure attacks, malicious code",
            "All agentic actions idempotent (0.5 coherence baseline)",
            "Honesty non-negotiable: Assert only believed truth",
            "Resource limit: 4 concurrent large model calls",
        ]

        return content

    def _render_config_file(
        self,
        template_type: TemplateType,
        context: TemplateContext,
    ) -> str:
        """Render config file from template."""
        if template_type == TemplateType.CLAUDE_MD:
            return self.template_engine.render_claude_md(context)
        else:
            return self.template_engine.render_gemini_md(context)

    async def _generate_commit_message(
        self,
        filename: str,
        vault_content: dict[str, Any],
    ) -> str:
        """Generate AI-style commit message.

        Phase 4: Simple heuristic-based generation.
        Could be enhanced with actual LLM in production.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Determine what changed
        changes = []

        if vault_content.get("decisions"):
            changes.append(
                f"sync {filename} with {len(vault_content['decisions'])} new decisions"
            )
        elif vault_content.get("patterns"):
            changes.append(
                f"sync {filename} with {len(vault_content['patterns'])} patterns"
            )
        else:
            changes.append(f"sync {filename} with latest vault content")

        # Format message
        commit_msg = f"config: {changes[0]}\n\nTimestamp: {timestamp}"

        return commit_msg

    async def sync_all(self, force: bool = False) -> dict[str, Any]:
        """Sync both CLAUDE.md and GEMINI.md."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "files": {},
            "total_synced": 0,
        }

        for filename in ["CLAUDE.md", "GEMINI.md"]:
            result = await self.sync_config_file(filename, force=force)
            results["files"][filename] = result

            if result["synced"]:
                results["total_synced"] += 1

        return results

    def get_sync_status(self) -> dict[str, Any]:
        """Get current sync status for both files."""
        status = {}

        for filename, file_path in [
            ("CLAUDE.md", self.claude_md),
            ("GEMINI.md", self.gemini_md),
        ]:
            if file_path.exists():
                metadata = FileMetadata.from_file(file_path)
                status[filename] = {
                    "exists": True,
                    "size_bytes": metadata.size_bytes,
                    "lines": metadata.line_count,
                    "last_modified": metadata.last_modified.isoformat(),
                    "hash": metadata.content_hash,
                }
            else:
                status[filename] = {"exists": False}

        return status
