"""Tests for conflict resolution policies."""

from cohezion.config.conflict_policy import (
    ConflictPolicy,
    ConflictResolutionPolicy,
    ConflictResolutionStrategy,
)


class TestConflictResolutionStrategy:
    """Test conflict resolution strategy enum."""

    def test_strategy_values(self) -> None:
        """Test strategy enum values."""
        assert ConflictResolutionStrategy.VAULT_WINS.value == "vault_wins"
        assert ConflictResolutionStrategy.CONFIG_WINS.value == "config_wins"
        assert ConflictResolutionStrategy.MANUAL_REVIEW.value == "manual_review"


class TestConflictPolicy:
    """Test conflict policy behavior."""

    def test_vault_wins_policy(self) -> None:
        """Test vault-wins strategy."""
        policy = ConflictPolicy(
            strategy=ConflictResolutionStrategy.VAULT_WINS,
            auto_resolve=True,
        )

        assert policy.should_auto_resolve()
        assert policy.get_winner() == "vault"

    def test_config_wins_policy(self) -> None:
        """Test config-wins strategy."""
        policy = ConflictPolicy(
            strategy=ConflictResolutionStrategy.CONFIG_WINS,
            auto_resolve=True,
        )

        assert policy.should_auto_resolve()
        assert policy.get_winner() == "config"

    def test_manual_review_never_auto_resolves(self) -> None:
        """Test manual review policy never auto-resolves."""
        policy = ConflictPolicy(
            strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
            auto_resolve=True,  # Set to True but should be overridden
        )

        assert not policy.should_auto_resolve()
        assert policy.get_winner() == "manual"

    def test_newer_wins_logic(self) -> None:
        """Test newer-wins logic with timestamps."""
        # Vault is newer
        policy = ConflictPolicy(
            strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
            vault_last_modified=1000.0,
            config_last_modified=500.0,
        )

        assert policy.use_newer()

        # Config is newer
        policy2 = ConflictPolicy(
            strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
            vault_last_modified=500.0,
            config_last_modified=1000.0,
        )

        assert not policy2.use_newer()

    def test_missing_timestamps_no_newer_wins(self) -> None:
        """Test that newer-wins returns False with missing timestamps."""
        policy = ConflictPolicy(
            strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
            vault_last_modified=None,
            config_last_modified=1000.0,
        )

        assert not policy.use_newer()


class TestConflictResolutionPolicies:
    """Test pre-built policy templates."""

    def test_vault_canonical_policy(self) -> None:
        """Test vault-canonical template."""
        policy = ConflictResolutionPolicy.vault_canonical()

        assert policy.strategy == ConflictResolutionStrategy.VAULT_WINS
        assert policy.should_auto_resolve()

    def test_config_manual_policy(self) -> None:
        """Test config-manual (requires review) template."""
        policy = ConflictResolutionPolicy.config_manual()

        assert policy.strategy == ConflictResolutionStrategy.MANUAL_REVIEW
        assert not policy.should_auto_resolve()

    def test_newer_wins_policy(self) -> None:
        """Test newer-wins template."""
        policy = ConflictResolutionPolicy.newer_wins(
            vault_ts=1000.0,
            config_ts=500.0,
        )

        assert policy.strategy == ConflictResolutionStrategy.MANUAL_REVIEW
        assert policy.use_newer()
