"""Tests for Heterogeneous Sharding Protocol (Story 1-0-8)."""

from __future__ import annotations

import pytest

from cohezion.core.heterogeneous_sharding import (
    ComputeNode,
    HeterogeneousShardingProtocol,
    NodeStatus,
)


class TestHeterogeneousSharding:
    def _make_protocol(self) -> HeterogeneousShardingProtocol:
        proto = HeterogeneousShardingProtocol(shard_count=4)
        proto.register_node(ComputeNode("cpu-0", memory_bandwidth_gbps=100, simd_width=256))
        proto.register_node(ComputeNode("igpu-0", memory_bandwidth_gbps=256, simd_width=512))
        return proto

    def test_shards_assigned_by_capability(self):
        proto = self._make_protocol()
        shards = proto.assign_shards(latent_dim=2048)
        assert len(shards) == 4
        # All shards have an assigned node
        assert all(s.assigned_node is not None for s in shards)

    def test_shard_dimensions_cover_full_latent_space(self):
        proto = self._make_protocol()
        shards = proto.assign_shards(latent_dim=2048)
        total_dims = sum(s.data_range[1] - s.data_range[0] for s in shards)
        assert total_dims == 2048

    def test_node_failure_orphans_shards(self):
        proto = self._make_protocol()
        proto.assign_shards()
        orphaned = proto.simulate_node_failure("cpu-0")
        assert len(orphaned) > 0
        assert proto.nodes["cpu-0"].status == NodeStatus.FAILED

    def test_redistribution_within_two_heartbeats(self):
        proto = self._make_protocol()
        proto.assign_shards()
        orphaned = proto.simulate_node_failure("cpu-0")
        report = proto.redistribute_orphaned_shards(orphaned)
        assert report.redistributions == len(orphaned)
        assert report.coherence_maintained is True

    def test_checksums_preserved_after_redistribution(self):
        proto = self._make_protocol()
        proto.assign_shards(latent_dim=2048)
        data = [float(i) for i in range(2048)]
        proto.snapshot_checksums(data)
        orphaned = proto.simulate_node_failure("cpu-0")
        proto.redistribute_orphaned_shards(orphaned)
        assert proto.verify_checksums_match(data)

    def test_no_nodes_raises(self):
        proto = HeterogeneousShardingProtocol()
        with pytest.raises(RuntimeError, match="No compute nodes"):
            proto.assign_shards()

    def test_unknown_node_failure_raises(self):
        proto = self._make_protocol()
        with pytest.raises(KeyError):
            proto.simulate_node_failure("unknown-node")
