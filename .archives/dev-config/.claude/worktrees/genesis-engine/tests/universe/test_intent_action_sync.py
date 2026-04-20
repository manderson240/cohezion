"""Tests for Intent-Action Synchronization (Story 3.7, FR6).

Cryptographically signs the relationship between intent and action
to detect Middle-Man Drift or substrate tampering.
"""

from __future__ import annotations

from cohezion.universe.intent_action_sync import (
    IntentActionPair,
    IntentActionSync,
)


class TestIntentActionPair:
    def test_pair_creation(self):
        """A pair links intent payload to resulting 12D state."""
        pair = IntentActionPair(
            agent_id="engineer-1",
            intent_vector=[0.5] * 12,
            action_vector=[0.5] * 12,
            intent_text="Adjusting coherence",
        )
        assert pair.agent_id == "engineer-1"
        assert len(pair.intent_vector) == 12
        assert len(pair.action_vector) == 12

    def test_pair_signature(self):
        """Each pair gets a cryptographic signature (HMAC-SHA256)."""
        pair = IntentActionPair(
            agent_id="agent-1",
            intent_vector=[0.1] * 12,
            action_vector=[0.2] * 12,
            intent_text="Testing",
        )
        sig = pair.compute_signature()
        assert len(sig) == 64  # SHA-256 hex

    def test_signature_changes_with_drift(self):
        """Different intent/action vectors produce different signatures."""
        pair1 = IntentActionPair(
            agent_id="a1",
            intent_vector=[0.1] * 12,
            action_vector=[0.1] * 12,
            intent_text="Same",
        )
        pair2 = IntentActionPair(
            agent_id="a1",
            intent_vector=[0.1] * 12,
            action_vector=[0.9] * 12,  # Drifted action
            intent_text="Same",
        )
        assert pair1.compute_signature() != pair2.compute_signature()


class TestIntentActionSync:
    def test_aligned_intent_action_passes(self):
        """When intent and action are aligned, verification passes."""
        sync = IntentActionSync(drift_threshold=0.3)
        pair = IntentActionPair(
            agent_id="agent-1",
            intent_vector=[0.5] * 12,
            action_vector=[0.52] * 12,  # Very close
            intent_text="Minor adjustment",
        )
        verdict = sync.verify(pair)
        assert verdict.aligned is True
        assert verdict.drift < 0.3

    def test_drifted_intent_action_fails(self):
        """When action diverges from intent beyond threshold, flag drift."""
        sync = IntentActionSync(drift_threshold=0.3)
        pair = IntentActionPair(
            agent_id="agent-1",
            intent_vector=[0.1] * 12,
            action_vector=[0.9] * 12,  # Major drift
            intent_text="Should be small change",
        )
        verdict = sync.verify(pair)
        assert verdict.aligned is False
        assert verdict.drift > 0.3

    def test_drift_history_accumulates(self):
        """Sync tracks verification history for Ouroboros training."""
        sync = IntentActionSync(drift_threshold=0.3)
        for i in range(3):
            pair = IntentActionPair(
                agent_id="agent-1",
                intent_vector=[0.5] * 12,
                action_vector=[0.5 + i * 0.01] * 12,
                intent_text=f"Step {i}",
            )
            sync.verify(pair)
        assert len(sync.history) == 3

    def test_export_drift_events(self):
        """Export drift events for Ouroboros training."""
        sync = IntentActionSync(drift_threshold=0.1)
        # One aligned, one drifted
        sync.verify(IntentActionPair("a1", [0.5] * 12, [0.51] * 12, "close"))
        sync.verify(IntentActionPair("a1", [0.1] * 12, [0.9] * 12, "far"))
        events = sync.get_drift_events()
        assert len(events) == 1  # Only the drifted one
        assert events[0]["aligned"] is False

    def test_custom_threshold(self):
        """Drift threshold is configurable."""
        strict = IntentActionSync(drift_threshold=0.01)
        pair = IntentActionPair("a1", [0.5] * 12, [0.52] * 12, "small")
        assert strict.verify(pair).aligned is False  # 0.02 > 0.01
