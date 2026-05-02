"""Custom MCP Architecture for secure Obsidian Vault read/writes."""

from __future__ import annotations

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class ObsidianVaultMCP:
    """Model Context Protocol server for interacting with the Obsidian External Brain."""

    vault_path: Path

    def __init__(self, vault_path: str = "/home/mike-anderson/dev/cohezion/obsidian_vault") -> None:
        self.vault_path = Path(vault_path)

    async def write_markdown_artifact(self, filename: str, content: str, tags: list[str] | None = None) -> bool:
        """Write a documented artifact with bidirectional links and tags into Obsidian."""
        self.vault_path.mkdir(parents=True, exist_ok=True)

        file_path = self.vault_path / filename

        # Enforce Red Wall: Only allow writes within the vault path
        if not file_path.resolve().is_relative_to(self.vault_path.resolve()):
            logger.error(f"Red Wall Violation: Attempted to write outside Obsidian Vault: {file_path}")
            return False

        header = "---\ntags:\n"
        if tags:
            for tag in tags:
                header += f"  - {tag}\n"
        header += "---\n\n"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                _ = f.write(header + content)
            logger.info(f"Successfully wrote MCP artifact to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write MCP artifact: {e}")
            return False

    async def read_markdown_artifact(self, filename: str) -> str | None:
        """Read a documented artifact from Obsidian."""
        file_path = self.vault_path / filename

        # Enforce Red Wall
        if not file_path.resolve().is_relative_to(self.vault_path.resolve()):
            logger.error(f"Red Wall Violation: Attempted to read outside Obsidian Vault: {file_path}")
            return None

        if not file_path.exists():
            logger.warning(f"MCP artifact not found: {file_path}")
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read MCP artifact: {e}")
            return None
