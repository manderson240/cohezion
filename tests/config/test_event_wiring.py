"""Tests for event wiring and commit batching."""

import pytest

from cohezion.config.event_wiring import (
    CommitBatcher,
    EventSubscriber,
    SyncEventSubscriber,
)


class TestCommitBatcher:
    """Test commit batching to prevent git churn."""

    @pytest.mark.asyncio
    async def test_queue_file(self) -> None:
        """Test queuing files."""
        batcher = CommitBatcher(batch_window_seconds=5)

        await batcher.queue_file("CLAUDE.md")
        assert await batcher.pending_count() == 1

        await batcher.queue_file("GEMINI.md")
        assert await batcher.pending_count() == 2

    @pytest.mark.asyncio
    async def test_should_commit_empty(self) -> None:
        """Test no commit when no pending files."""
        batcher = CommitBatcher()

        assert not await batcher.should_commit()

    @pytest.mark.asyncio
    async def test_should_commit_first_batch(self) -> None:
        """Test first batch commits immediately."""
        batcher = CommitBatcher()

        await batcher.queue_file("CLAUDE.md")
        assert await batcher.should_commit()

    @pytest.mark.asyncio
    async def test_should_commit_respects_window(self) -> None:
        """Test batch window is respected."""
        batcher = CommitBatcher(batch_window_seconds=100)

        await batcher.queue_file("CLAUDE.md")
        assert await batcher.should_commit()

        # Get and reset
        await batcher.get_pending_and_reset()

        # Queue again within window
        await batcher.queue_file("GEMINI.md")
        assert not await batcher.should_commit()

    @pytest.mark.asyncio
    async def test_get_pending_and_reset(self) -> None:
        """Test retrieving and clearing pending files."""
        batcher = CommitBatcher()

        await batcher.queue_file("CLAUDE.md")
        await batcher.queue_file("GEMINI.md")

        pending = await batcher.get_pending_and_reset()
        assert pending == {"CLAUDE.md", "GEMINI.md"}
        assert await batcher.pending_count() == 0

    @pytest.mark.asyncio
    async def test_reset_clears_state(self) -> None:
        """Test reset clears all state."""
        batcher = CommitBatcher()

        await batcher.queue_file("CLAUDE.md")
        assert await batcher.pending_count() == 1

        await batcher.reset()
        assert await batcher.pending_count() == 0
        assert not await batcher.should_commit()


class TestEventSubscriber:
    """Test event subscriber base class."""

    @pytest.mark.asyncio
    async def test_base_subscriber_no_op(self) -> None:
        """Test base subscriber methods are no-ops."""
        subscriber = EventSubscriber()

        await subscriber.on_vault_decision_added("test")
        await subscriber.on_vault_pattern_updated("test")
        await subscriber.on_config_file_modified("CLAUDE.md")
        await subscriber.on_sync_completed("CLAUDE.md")


class TestSyncEventSubscriber:
    """Test sync event subscriber."""

    @pytest.mark.asyncio
    async def test_on_vault_decision_added(self) -> None:
        """Test decision added queues CLAUDE.md."""
        batcher = CommitBatcher()

        def callback(x):
            return None

        subscriber = SyncEventSubscriber(callback, batcher)
        await subscriber.on_vault_decision_added("cost-optimization")

        assert await batcher.pending_count() == 1
        pending = await batcher.get_pending_and_reset()
        assert "CLAUDE.md" in pending

    @pytest.mark.asyncio
    async def test_on_vault_pattern_updated(self) -> None:
        """Test pattern update queues CLAUDE.md."""
        batcher = CommitBatcher()

        def callback(x):
            return None

        subscriber = SyncEventSubscriber(callback, batcher)
        await subscriber.on_vault_pattern_updated("consensus-voting")

        assert await batcher.pending_count() == 1
        pending = await batcher.get_pending_and_reset()
        assert "CLAUDE.md" in pending

    @pytest.mark.asyncio
    async def test_multiple_events_batched(self) -> None:
        """Test multiple events are batched together."""
        batcher = CommitBatcher()

        def callback(x):
            return None

        subscriber = SyncEventSubscriber(callback, batcher)

        await subscriber.on_vault_decision_added("decision1")
        await subscriber.on_vault_decision_added("decision2")
        await subscriber.on_vault_pattern_updated("pattern1")

        # All should be batched for single CLAUDE.md commit
        assert await batcher.pending_count() == 1
        assert "CLAUDE.md" in (await batcher.get_pending_and_reset())

    @pytest.mark.asyncio
    async def test_config_file_modified_logged(self) -> None:
        """Test manual config edit is logged (not auto-synced)."""
        batcher = CommitBatcher()

        def callback(x):
            return None

        subscriber = SyncEventSubscriber(callback, batcher)
        await subscriber.on_config_file_modified("CLAUDE.md")

        # Should NOT queue for sync
        assert await batcher.pending_count() == 0
