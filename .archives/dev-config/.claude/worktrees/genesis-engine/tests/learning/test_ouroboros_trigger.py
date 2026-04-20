"""Tests for Ouroboros Trigger VAE Fine-Tuning Loop (Story 5.1, NFR-4, NFR-8)."""

from __future__ import annotations

from cohezion.learning.ouroboros_trigger import (
    OuroborosTrigger,
    TriggerState,
)


class TestOuroborosTrigger:
    def test_trigger_starts_training(self):
        """TDD failure with consensus triggers VAE training."""
        trigger = OuroborosTrigger()
        event = trigger.trigger("fail_hash_001", consensus_reached=True)
        assert event.state == TriggerState.TRAINING
        assert trigger.active_event is not None

    def test_no_consensus_defers(self):
        """Without consensus, training is deferred."""
        trigger = OuroborosTrigger()
        event = trigger.trigger("fail_hash_002", consensus_reached=False)
        assert event.state == TriggerState.DEFERRED
        assert trigger.active_event is None

    def test_epoch_recording(self):
        """Epoch losses are tracked during training."""
        trigger = OuroborosTrigger()
        trigger.trigger("fail_hash_003")
        state = trigger.record_epoch(0.5)
        assert state == TriggerState.TRAINING

    def test_divergence_detection(self):
        """Loss increasing for 3+ epochs triggers rollback."""
        trigger = OuroborosTrigger(patience=3)
        trigger.trigger("fail_hash_004")
        trigger.record_epoch(0.5)
        trigger.record_epoch(0.6)
        state = trigger.record_epoch(0.7)  # 3 consecutive increases
        assert state == TriggerState.DIVERGED
        assert trigger.active_event is None

    def test_non_monotonic_loss_continues(self):
        """Non-monotonic loss doesn't trigger divergence."""
        trigger = OuroborosTrigger(patience=3)
        trigger.trigger("fail_hash_005")
        trigger.record_epoch(0.5)
        trigger.record_epoch(0.6)
        state = trigger.record_epoch(0.4)  # Drops — not diverging
        assert state == TriggerState.TRAINING

    def test_completion(self):
        """Completed training returns the event."""
        trigger = OuroborosTrigger()
        trigger.trigger("fail_hash_006")
        trigger.record_epoch(0.5)
        trigger.record_epoch(0.3)
        completed = trigger.complete()
        assert completed is not None
        assert completed.state == TriggerState.COMPLETED

    def test_complete_without_active_returns_none(self):
        """Completing with no active event returns None."""
        trigger = OuroborosTrigger()
        assert trigger.complete() is None

    def test_training_history(self):
        """All events are tracked in history."""
        trigger = OuroborosTrigger()
        trigger.trigger("h1", consensus_reached=True)
        trigger.complete()
        trigger.trigger("h2", consensus_reached=False)
        history = trigger.get_training_history()
        assert len(history) == 2

    def test_rollback_checkpoint_preserved(self):
        """Diverged event preserves rollback checkpoint."""
        trigger = OuroborosTrigger(patience=3)
        event = trigger.trigger("h3", checkpoint="checkpoint_v5")
        trigger.record_epoch(0.5)
        trigger.record_epoch(0.6)
        trigger.record_epoch(0.7)
        assert event.state == TriggerState.DIVERGED
        assert event.rollback_checkpoint == "checkpoint_v5"

    def test_record_epoch_when_idle(self):
        """Recording epoch with no active training returns idle."""
        trigger = OuroborosTrigger()
        assert trigger.record_epoch(0.5) == TriggerState.IDLE
