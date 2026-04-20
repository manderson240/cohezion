"""Tests for Distributed Manifold Sharding (Story 1.9)."""

from __future__ import annotations

import pytest

from cohezion.core.manifold_sharding import DistributedManifold, PulseMode


class TestDistributedManifold:
    def test_local_mode_by_default(self):
        manifold = DistributedManifold()
        assert manifold.mode == PulseMode.LOCAL

    def test_enable_distributed_pulse_creates_shards(self):
        manifold = DistributedManifold(shard_count=8)
        shards = manifold.enable_distributed_pulse()
        assert len(shards) == 8
        assert manifold.mode == PulseMode.DISTRIBUTED

    def test_shards_cover_full_soul_dim(self):
        manifold = DistributedManifold(shard_count=8)
        shards = manifold.enable_distributed_pulse()
        total = sum(s.size for s in shards)
        assert total == 2048

    def test_atomic_flip_updates_shard(self):
        manifold = DistributedManifold(shard_count=4)
        shards = manifold.enable_distributed_pulse()
        shard_id = shards[0].shard_id
        dim = shards[0].size
        new_data = [0.5] * dim
        manifold.atomic_flip(shard_id, new_data)
        updated = [s for s in manifold.shards if s.shard_id == shard_id][0]
        assert updated.data == new_data

    def test_atomic_flip_unknown_shard_raises(self):
        manifold = DistributedManifold()
        manifold.enable_distributed_pulse()
        with pytest.raises(KeyError):
            manifold.atomic_flip("nonexistent", [0.0])

    def test_coherence_report_has_correct_shard_count(self):
        manifold = DistributedManifold(shard_count=4)
        manifold.enable_distributed_pulse()
        report = manifold.compute_coherence()
        assert report.shard_count == 4
        assert report.total_dims == 2048

    def test_pointer_flip_counted(self):
        manifold = DistributedManifold(shard_count=2)
        shards = manifold.enable_distributed_pulse()
        manifold.atomic_flip(shards[0].shard_id, [0.0] * shards[0].size)
        manifold.atomic_flip(shards[0].shard_id, [0.1] * shards[0].size)
        report = manifold.compute_coherence()
        assert report.pointer_flips == 2
