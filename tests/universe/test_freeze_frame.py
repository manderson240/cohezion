"""Tests for Freeze-Frame Reality Capture (Story 3.4, NFR-8).

Captures full 12D state snapshots during TDD failures for Ouroboros training.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from cohezion.universe.freeze_frame import (
    FreezeFrame,
    FreezeFrameCapture,
    FreezeFrameStore,
)


class TestFreezeFrame:
    def test_freeze_frame_captures_state(self):
        """A freeze-frame must contain 12D latent state and metadata."""
        frame = FreezeFrame(
            trigger="tdd_red",
            latent_state=np.zeros(12).tolist(),
            failure_hash="abc123",
            agent_id="researcher-1",
            context={"test_name": "test_something", "error": "AssertionError"},
        )
        assert frame.trigger == "tdd_red"
        assert len(frame.latent_state) == 12
        assert frame.failure_hash == "abc123"
        assert frame.timestamp > 0

    def test_freeze_frame_serializes_to_json(self):
        """FreezeFrame must be JSON-serializable for vault persistence."""
        frame = FreezeFrame(
            trigger="tdd_red",
            latent_state=[0.1] * 12,
            failure_hash="def456",
            agent_id="engineer-1",
        )
        data = frame.to_dict()
        roundtrip = json.loads(json.dumps(data))
        assert roundtrip["trigger"] == "tdd_red"
        assert len(roundtrip["latent_state"]) == 12
        assert roundtrip["failure_hash"] == "def456"

    def test_freeze_frame_computes_content_hash(self):
        """Each frame gets a deterministic content hash for deduplication."""
        frame = FreezeFrame(
            trigger="tdd_red",
            latent_state=[0.5] * 12,
            failure_hash="ghi789",
            agent_id="agent-1",
        )
        h = frame.content_hash()
        assert len(h) == 64  # SHA-256 hex digest
        # Same data = same hash
        frame2 = FreezeFrame(
            trigger="tdd_red",
            latent_state=[0.5] * 12,
            failure_hash="ghi789",
            agent_id="agent-1",
        )
        assert frame.content_hash() == frame2.content_hash()


class TestFreezeFrameCapture:
    def test_capture_from_failure(self):
        """Capture creates a freeze-frame from a TDD failure event."""
        capture = FreezeFrameCapture()
        frame = capture.capture(
            trigger="tdd_red",
            latent_state=np.random.default_rng(0).standard_normal(12).tolist(),
            failure_hash="test_hash_001",
            agent_id="researcher-1",
            context={"test": "test_foo", "error": "AssertionError: expected 1 got 2"},
        )
        assert frame.trigger == "tdd_red"
        assert frame.agent_id == "researcher-1"
        assert "test" in frame.context

    def test_capture_validates_latent_dimension(self):
        """Latent state must be 12D (axiomatic manifold dimension)."""
        capture = FreezeFrameCapture()
        with pytest.raises(ValueError, match="12D"):
            capture.capture(
                trigger="tdd_red",
                latent_state=[0.0] * 5,  # Wrong dimension
                failure_hash="bad_dim",
                agent_id="agent-1",
            )

    def test_capture_requires_failure_hash(self):
        """Failure hash is mandatory for deduplication."""
        capture = FreezeFrameCapture()
        with pytest.raises(ValueError, match="failure_hash"):
            capture.capture(
                trigger="tdd_red",
                latent_state=[0.0] * 12,
                failure_hash="",
                agent_id="agent-1",
            )


class TestFreezeFrameStore:
    def test_store_and_retrieve(self):
        """Frames can be stored and retrieved."""
        store = FreezeFrameStore()
        frame = FreezeFrame(
            trigger="tdd_red",
            latent_state=[0.1] * 12,
            failure_hash="store_test",
            agent_id="agent-1",
        )
        store.add(frame)
        assert len(store.frames) == 1
        assert store.frames[0].failure_hash == "store_test"

    def test_store_deduplicates_by_hash(self):
        """Duplicate frames (same content hash) are not stored twice."""
        store = FreezeFrameStore()
        frame1 = FreezeFrame(
            trigger="tdd_red",
            latent_state=[0.2] * 12,
            failure_hash="dup_test",
            agent_id="agent-1",
        )
        frame2 = FreezeFrame(
            trigger="tdd_red",
            latent_state=[0.2] * 12,
            failure_hash="dup_test",
            agent_id="agent-1",
        )
        store.add(frame1)
        store.add(frame2)
        assert len(store.frames) == 1

    def test_export_training_data(self):
        """Export all frames as Ouroboros training data."""
        store = FreezeFrameStore()
        for i in range(3):
            store.add(
                FreezeFrame(
                    trigger="tdd_red",
                    latent_state=[float(i)] * 12,
                    failure_hash=f"hash_{i}",
                    agent_id="agent-1",
                )
            )
        data = store.export_training_data()
        assert len(data) == 3
        assert all("latent_state" in d for d in data)

    def test_clear_after_consumption(self):
        """Frames can be cleared after Ouroboros consumes them."""
        store = FreezeFrameStore()
        store.add(
            FreezeFrame(
                trigger="tdd_red",
                latent_state=[0.0] * 12,
                failure_hash="clear_test",
                agent_id="agent-1",
            )
        )
        assert len(store.frames) == 1
        store.clear()
        assert len(store.frames) == 0
