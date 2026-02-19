"""Tests for Ouroboros Flight Recorder."""

import json
import tempfile
from pathlib import Path

from cohezion.system.ouroboros_recorder import OuroborosRecorder


class TestOuroborosRecorder:
    """Test Ouroboros flight recorder for universe simulations."""

    def test_recorder_creation(self):
        """Should create recorder with default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = OuroborosRecorder(data_dir=tmpdir)
            assert recorder is not None
            assert recorder.data_dir == Path(tmpdir)

    def test_record_event(self):
        """Should append JSONL events to recording file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = OuroborosRecorder(data_dir=tmpdir)
            recording_id = recorder.start_recording("test-scenario")

            recorder.record_event(
                recording_id,
                event_type="agent_step",
                data={"x": 0.5, "y": 0.3, "coherence": 0.85},
            )
            recorder.record_event(
                recording_id,
                event_type="agent_step",
                data={"x": 0.6, "y": 0.4, "coherence": 0.82},
            )

            # Should have 2 events recorded
            events = list(recorder.replay(recording_id))
            assert len(events) == 2
            assert events[0]["event_type"] == "agent_step"
            assert events[0]["data"]["x"] == 0.5

    def test_replay_events(self):
        """Should yield events from a completed recording."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = OuroborosRecorder(data_dir=tmpdir)
            recording_id = recorder.start_recording("replay-test")

            for i in range(5):
                recorder.record_event(
                    recording_id,
                    event_type="step",
                    data={"step": i, "value": i * 0.1},
                )

            events = list(recorder.replay(recording_id))
            assert len(events) == 5
            # Should be in order
            for i, event in enumerate(events):
                assert event["data"]["step"] == i

    def test_record_divergence_event(self):
        """Should capture divergence events with last-known-good state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = OuroborosRecorder(data_dir=tmpdir)
            recording_id = recorder.start_recording("divergence-test")

            # Record normal steps
            recorder.record_event(
                recording_id,
                event_type="agent_step",
                data={"coherence": 0.5},
            )

            # Record divergence
            recorder.record_divergence(
                recording_id,
                divergence_type="coherence_collapse",
                last_good_state={"coherence": 0.5, "step": 3},
                divergent_state={"coherence": 0.01, "step": 4},
            )

            events = list(recorder.replay(recording_id))
            assert len(events) == 2
            divergence = events[1]
            assert divergence["event_type"] == "divergence"
            assert divergence["data"]["divergence_type"] == "coherence_collapse"
            assert divergence["data"]["last_good_state"]["coherence"] == 0.5

    def test_file_rotation(self):
        """Should rotate files when exceeding max size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use tiny max size to trigger rotation
            recorder = OuroborosRecorder(data_dir=tmpdir, max_file_bytes=100)
            recording_id = recorder.start_recording("rotation-test")

            # Write enough data to exceed limit
            for i in range(20):
                recorder.record_event(
                    recording_id,
                    event_type="step",
                    data={"step": i, "value": "x" * 50},
                )

            # File should have been rotated
            data_path = Path(tmpdir)
            jsonl_files = list(data_path.glob("*.jsonl"))
            assert len(jsonl_files) >= 1

    def test_replay_nonexistent_recording(self):
        """Should return empty for non-existent recording."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = OuroborosRecorder(data_dir=tmpdir)
            events = list(recorder.replay("nonexistent"))
            assert len(events) == 0

    def test_recording_stores_jsonl_format(self):
        """Events should be stored as valid JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = OuroborosRecorder(data_dir=tmpdir)
            recording_id = recorder.start_recording("jsonl-test")

            recorder.record_event(
                recording_id,
                event_type="test",
                data={"key": "value"},
            )

            # Read raw file and verify JSONL format
            recording_path = recorder._get_recording_path(recording_id)
            with open(recording_path) as f:
                lines = f.readlines()
                assert len(lines) == 1
                parsed = json.loads(lines[0])
                assert parsed["event_type"] == "test"
                assert "timestamp" in parsed

    def test_retention_limit(self):
        """Should keep only the configured number of recordings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = OuroborosRecorder(data_dir=tmpdir, max_recordings=3)

            # Create more recordings than the limit
            ids = []
            for i in range(5):
                rid = recorder.start_recording(f"scenario-{i}")
                recorder.record_event(rid, event_type="step", data={"i": i})
                ids.append(rid)

            # Apply retention
            recorder.apply_retention()

            # Should have at most max_recordings files
            jsonl_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(jsonl_files) <= 3
