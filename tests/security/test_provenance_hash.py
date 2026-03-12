"""Tests for Immutable Provenance Hashing (Story 4.7, FR5)."""

from __future__ import annotations

from cohezion.security.provenance_hash import ProvenanceRecord, ProvenanceRegistry


class TestProvenanceRecord:
    def test_provenance_hash_is_deterministic(self):
        """Same inputs produce same provenance hash."""
        r1 = ProvenanceRecord("art-1", "pattern", "hash1", "arxiv:123")
        r2 = ProvenanceRecord("art-1", "pattern", "hash1", "arxiv:123")
        assert r1.provenance_hash == r2.provenance_hash

    def test_different_content_different_hash(self):
        """Different content produces different provenance hash."""
        r1 = ProvenanceRecord("art-1", "pattern", "hash1", "arxiv:123")
        r2 = ProvenanceRecord("art-1", "pattern", "hash2", "arxiv:123")
        assert r1.provenance_hash != r2.provenance_hash

    def test_serialization(self):
        """Record serializes to dict with provenance hash."""
        r = ProvenanceRecord("art-1", "skill", "h1", "vault:dec-1")
        d = r.to_dict()
        assert d["artifact_id"] == "art-1"
        assert "provenance_hash" in d
        assert len(d["provenance_hash"]) == 64


class TestProvenanceRegistry:
    def test_register_and_verify(self):
        """Registered artifacts can be verified by hash."""
        registry = ProvenanceRegistry()
        record = registry.register("skill-1", "skill", "def foo(): pass", "vault:exp-1")
        assert registry.verify(record.provenance_hash)

    def test_unregistered_hash_fails_verification(self):
        """Unknown hashes fail verification."""
        registry = ProvenanceRegistry()
        assert not registry.verify("nonexistent_hash")

    def test_chain_tracks_lineage(self):
        """Provenance chain links artifact versions."""
        registry = ProvenanceRegistry()
        v1 = registry.register("skill-1", "skill", "version 1", "vault:exp-1")
        v2 = registry.register(
            "skill-1",
            "skill",
            "version 2",
            "vault:exp-2",
            parent_hash=v1.provenance_hash,
        )
        chain = registry.get_chain(v2.provenance_hash)
        assert len(chain) == 2
        assert chain[0].content_hash != chain[1].content_hash

    def test_export_all_records(self):
        """All records can be exported for audit."""
        registry = ProvenanceRegistry()
        registry.register("a1", "pattern", "content1", "source1")
        registry.register("a2", "skill", "content2", "source2")
        records = registry.get_all()
        assert len(records) == 2
