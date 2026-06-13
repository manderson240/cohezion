"""Coverage batch Z55: routing_feedback_loop, neural_audio, flume_dataset."""

from __future__ import annotations

import json

import numpy as np
import pytest
import torch


# ---------------------------------------------------------------------------
# Module 1: compound/routing_feedback_loop.py
# ---------------------------------------------------------------------------


class TestRoutingFeedbackLoop:
    def _make_feedback(self, window_size=10):
        from cohezion.compound.routing_feedback_loop import RoutingOptimizationFeedback

        return RoutingOptimizationFeedback(window_size=window_size)

    def _make_decision(self, model="phi3:mini", success=True, task_type="inference"):
        from cohezion.compound.routing_feedback_loop import RoutingDecision, RoutingDecisionType

        return RoutingDecision(
            decision_type=RoutingDecisionType.MODEL_SELECTION,
            selected_model=model,
            task_type=task_type,
            context_length=100,
            success=success,
        )

    def test_routing_decision_dataclass(self):
        d = self._make_decision()
        assert d.selected_model == "phi3:mini"
        assert d.success is True

    def test_routing_metrics_success_rate_zero_total(self):
        from cohezion.compound.routing_feedback_loop import RoutingMetrics

        m = RoutingMetrics()
        assert m.success_rate == pytest.approx(0.0)

    def test_record_decision_increments_counter(self):
        fb = self._make_feedback()
        fb.record_decision(self._make_decision())
        fb.record_decision(self._make_decision())
        assert fb.get_metrics().total_decisions == 2

    def test_record_decision_tracks_failures(self):
        fb = self._make_feedback()
        fb.record_decision(self._make_decision(success=True))
        fb.record_decision(self._make_decision(success=False))
        metrics = fb.get_metrics()
        assert metrics.successful_decisions == 1
        assert metrics.total_decisions == 2

    def test_record_decision_circular_buffer(self):
        fb = self._make_feedback(window_size=3)
        for _ in range(5):
            fb.record_decision(self._make_decision())
        assert len(fb._decisions) == 3

    def test_detect_anomalies_model_thrashing(self):
        fb = self._make_feedback(window_size=4)
        # Alternating models → >50% switches
        fb.record_decision(self._make_decision("model_a"))
        fb.record_decision(self._make_decision("model_b"))
        fb.record_decision(self._make_decision("model_a"))
        fb.record_decision(self._make_decision("model_b"))
        anomalies = fb.detect_anomalies()
        assert any(a["type"] == "model_thrashing" for a in anomalies)

    def test_detect_anomalies_no_thrashing_same_model(self):
        fb = self._make_feedback()
        for _ in range(5):
            fb.record_decision(self._make_decision("phi3:mini"))
        anomalies = fb.detect_anomalies()
        assert len([a for a in anomalies if a["type"] == "model_thrashing"]) == 0

    def test_detect_anomalies_insufficient_decisions(self):
        fb = self._make_feedback()
        fb.record_decision(self._make_decision())
        anomalies = fb.detect_anomalies()
        assert anomalies == []

    def test_get_routing_recommendations(self):
        fb = self._make_feedback()
        recs = fb.get_routing_recommendations()
        assert "warnings" in recs

    def test_reset_clears_state(self):
        fb = self._make_feedback()
        fb.record_decision(self._make_decision())
        fb.reset()
        assert fb.get_metrics().total_decisions == 0
        assert len(fb._decisions) == 0

    def test_singleton_getter(self):
        from cohezion.compound.routing_feedback_loop import get_routing_feedback

        import cohezion.compound.routing_feedback_loop as mod

        mod._routing_feedback = None  # reset
        fb1 = get_routing_feedback()
        fb2 = get_routing_feedback()
        assert fb1 is fb2
        mod._routing_feedback = None  # cleanup


# ---------------------------------------------------------------------------
# Module 2: audio/neural_audio.py
# ---------------------------------------------------------------------------


class TestNeuralAudioStream:
    def _make_streamer(self):
        from cohezion.audio.neural_audio import NeuralAudioStream

        return NeuralAudioStream()

    def test_audio_chunk_dataclass(self):
        import base64

        from cohezion.audio.neural_audio import AudioChunk

        raw = b"hello audio"
        chunk = AudioChunk(encoded=base64.b64encode(raw).decode(), latency_ms=5.0, sequence=1)
        assert chunk.decode() == raw

    def test_audio_stream_state_to_dict(self):
        from cohezion.audio.neural_audio import AudioStreamState, AudioStreamStatus

        state = AudioStreamState(status=AudioStreamStatus.CONNECTED, latency_ms=10.0)
        d = state.to_dict()
        assert d["status"] == "connected"

    def test_initial_state_disconnected(self):
        from cohezion.audio.neural_audio import AudioStreamStatus

        streamer = self._make_streamer()
        state = streamer._state()
        assert state.status == AudioStreamStatus.DISCONNECTED

    def test_connect_returns_connected(self):
        from cohezion.audio.neural_audio import AudioStreamStatus

        streamer = self._make_streamer()
        state = streamer.connect()
        assert state.status == AudioStreamStatus.CONNECTED

    def test_encode_trajectory_returns_audio_chunk(self):
        from cohezion.audio.neural_audio import AudioChunk

        streamer = self._make_streamer()
        streamer.connect()
        chunk = streamer.encode_trajectory(coherence=0.5, ca_density=0.3)
        assert isinstance(chunk, AudioChunk)
        assert chunk.sequence == 1

    def test_encode_trajectory_increments_sequence(self):
        streamer = self._make_streamer()
        streamer.connect()
        streamer.encode_trajectory(coherence=0.5, ca_density=0.3)
        streamer.encode_trajectory(coherence=0.5, ca_density=0.3)
        assert streamer.chunks_sent == 2

    def test_simulate_stream_drop_sets_degraded(self):
        from cohezion.audio.neural_audio import AudioStreamStatus

        streamer = self._make_streamer()
        state = streamer.simulate_stream_drop("network error")
        assert state.status == AudioStreamStatus.DEGRADED
        assert streamer.is_degraded() is True

    def test_reconnect_restores_connected(self):
        from cohezion.audio.neural_audio import AudioStreamStatus

        streamer = self._make_streamer()
        streamer.simulate_stream_drop()
        state = streamer.reconnect()
        assert state.status == AudioStreamStatus.CONNECTED
        assert streamer.is_degraded() is False


# ---------------------------------------------------------------------------
# Module 3: flume/dataset.py
# ---------------------------------------------------------------------------


class TestFlumeTrajectoryDataset:
    def test_empty_dir_generates_synthetic(self, tmp_path):
        from cohezion.flume.dataset import FlumeTrajectoryDataset

        # Empty dir → synthetic data generated
        ds = FlumeTrajectoryDataset(data_dir=str(tmp_path))
        assert len(ds) > 0

    def test_dataset_loads_jsonl(self, tmp_path):
        from cohezion.flume.dataset import FlumeTrajectoryDataset

        z_dim = 16
        artifacts_dir = tmp_path
        # Write a JSONL file with vectors
        jsonl_file = artifacts_dir / "trajectories.jsonl"
        vectors = [[float(i) / z_dim] * z_dim for i in range(5)]
        with jsonl_file.open("w") as f:
            for v in vectors:
                f.write(json.dumps({"latent": v}) + "\n")

        ds = FlumeTrajectoryDataset(data_dir=str(artifacts_dir), z_dim=z_dim)
        assert len(ds) == 5

    def test_dataset_getitem_returns_tensor(self, tmp_path):
        from cohezion.flume.dataset import FlumeTrajectoryDataset

        z_dim = 8
        jsonl_file = tmp_path / "traj.jsonl"
        v = [0.5] * z_dim
        jsonl_file.write_text(json.dumps({"latent": v}) + "\n")

        ds = FlumeTrajectoryDataset(data_dir=str(tmp_path), z_dim=z_dim)
        item = ds[0]
        assert isinstance(item, torch.Tensor)
        assert item.shape == (z_dim,)

    def test_dataset_loads_npy(self, tmp_path):
        from cohezion.flume.dataset import FlumeTrajectoryDataset

        z_dim = 8
        arr = np.random.randn(3, z_dim).astype(np.float32)
        np.save(str(tmp_path / "vectors.npy"), arr)

        ds = FlumeTrajectoryDataset(data_dir=str(tmp_path), z_dim=z_dim)
        assert len(ds) == 3
