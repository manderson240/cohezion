"""Conflict resolution policies for bidirectional sync.

Handles simultaneous edits in CLAUDE.md and vault.
"""

from __future__ import annotations

from enum import Enum


class ConflictResolutionStrategy(Enum):
    """Explicit conflict resolution strategies."""

    VAULT_WINS = "vault_wins"
    """Vault canonical content wins; CLAUDE.md changes archived."""

    CONFIG_WINS = "config_wins"
    """CLAUDE.md manual edits win; vault is updated from config."""

    MANUAL_REVIEW = "manual_review"
    """Alert human; require explicit approval before resolving."""


class ConflictPolicy:
    """Policy for handling detected conflicts during bidirectional sync."""

    def __init__(
        self,
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MANUAL_REVIEW,
        auto_resolve: bool = False,
        vault_last_modified: float | None = None,
        config_last_modified: float | None = None,
    ):
        """Initialize conflict policy.

        Args:
            strategy: How to resolve conflicts
            auto_resolve: Automatically apply strategy (True) or require manual approval (False)
            vault_last_modified: Timestamp of last vault change
            config_last_modified: Timestamp of last config change
        """
        self.strategy = strategy
        self.auto_resolve = auto_resolve
        self.vault_last_modified = vault_last_modified
        self.config_last_modified = config_last_modified

    def should_auto_resolve(self) -> bool:
        """Check if conflict should be auto-resolved."""
        if self.strategy == ConflictResolutionStrategy.MANUAL_REVIEW:
            return False  # Always requires manual review
        return self.auto_resolve

    def get_winner(self) -> str:
        """Get which source wins based on strategy."""
        if self.strategy == ConflictResolutionStrategy.VAULT_WINS:
            return "vault"
        elif self.strategy == ConflictResolutionStrategy.CONFIG_WINS:
            return "config"
        else:
            return "manual"

    def use_newer(self) -> bool:
        """If using 'newer wins' strategy, prefer most recent edit."""
        if self.vault_last_modified is None or self.config_last_modified is None:
            return False
        return self.vault_last_modified > self.config_last_modified


class ConflictResolutionPolicy:
    """Default policies for common scenarios."""

    @staticmethod
    def vault_canonical() -> ConflictPolicy:
        """Vault is canonical; config is secondary."""
        return ConflictPolicy(
            strategy=ConflictResolutionStrategy.VAULT_WINS,
            auto_resolve=True,
        )

    @staticmethod
    def config_manual() -> ConflictPolicy:
        """Manual edits in config take precedence; always review."""
        return ConflictPolicy(
            strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
            auto_resolve=False,
        )

    @staticmethod
    def newer_wins(
        vault_ts: float | None = None,
        config_ts: float | None = None,
    ) -> ConflictPolicy:
        """Most recent edit wins (if timestamps available)."""
        policy = ConflictPolicy(
            strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
            auto_resolve=False,
        )
        policy.vault_last_modified = vault_ts
        policy.config_last_modified = config_ts
        return policy
