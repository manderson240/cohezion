"""Tests for Neural Audio Streaming (Story 2.6)."""

from __future__ import annotations

import pytest

from cohezion.audio.neural_audio import AudioStreamStatus, NeuralAudioStream


class TestNeuralAudioStream:
    def test_connect_sets_connected_status(self):
        stream = NeuralAudioStream()
        state = stream.connect()
        assert state.status == AudioStreamStatus.CONNECTED

    def test_encode_trajectory_produces_chunk(self):
        stream = NeuralAudioStream()
        stream.connect()
        chunk = stream.encode_trajectory(coherence=0.5, ca_density=0.7)
        assert isinstance(chunk.encoded, str)
        assert len(chunk.encoded) > 0
        assert chunk.sequence == 1

    def test_chunk_is_decodable(self):
        stream = NeuralAudioStream()
        stream.connect()
        chunk = stream.encode_trajectory(coherence=0.5, ca_density=0.3)
        decoded = chunk.decode()
        assert len(decoded) > 0

    def test_stream_drop_activates_degraded_mode(self):
        stream = NeuralAudioStream()
        stream.connect()
        state = stream.simulate_stream_drop()
        assert state.status == AudioStreamStatus.DEGRADED
        assert stream.is_degraded() is True

    def test_reconnect_restores_connected_state(self):
        stream = NeuralAudioStream()
        stream.connect()
        stream.simulate_stream_drop()
        state = stream.reconnect()
        assert state.status == AudioStreamStatus.CONNECTED
        assert not stream.is_degraded()

    def test_encode_fails_when_not_connected(self):
        stream = NeuralAudioStream()
        with pytest.raises(RuntimeError, match="not connected"):
            stream.encode_trajectory(0.5, 0.5)

    def test_chunks_sent_counter(self):
        stream = NeuralAudioStream()
        stream.connect()
        stream.encode_trajectory(0.5, 0.5)
        stream.encode_trajectory(0.6, 0.4)
        assert stream.chunks_sent == 2
