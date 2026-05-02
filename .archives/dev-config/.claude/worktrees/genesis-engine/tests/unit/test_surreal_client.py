"""Tests for the SurrealDB client module (cohezion.core.persistence.surreal_client)."""

from __future__ import annotations

import base64
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cohezion.core.persistence.surreal_client import (
    InMemoryStore,
    PhysicsState,
    SurrealClient,
    UniverseNode,
)


# ---------------------------------------------------------------------------
# PhysicsState tests
# ---------------------------------------------------------------------------


class TestPhysicsState:
    def test_default_values(self):
        ps = PhysicsState()
        assert ps.x == 0.0
        assert ps.precipitation == 0.0

    def test_to_array_returns_12_elements(self):
        ps = PhysicsState(x=1.0, y=2.0, z=3.0)
        arr = ps.to_array()
        assert len(arr) == 12
        assert float(arr[0]) == 1.0
        assert float(arr[1]) == 2.0
        assert float(arr[2]) == 3.0

    def test_from_array_roundtrip(self):
        original = PhysicsState(
            x=1.0,
            y=2.0,
            z=3.0,
            time=4.0,
            physics=5.0,
            biology=6.0,
            logic=7.0,
            quantum=8.0,
            field=9.0,
            control=10.0,
            novelty=11.0,
            precipitation=12.0,
        )
        arr = original.to_array()
        restored = PhysicsState.from_array(arr)
        assert abs(restored.x - 1.0) < 0.01
        assert abs(restored.precipitation - 12.0) < 0.01

    def test_from_array_wrong_length_raises(self):
        with pytest.raises(ValueError, match="Expected 12"):
            PhysicsState.from_array(np.array([1.0, 2.0]))

    def test_to_dict_keys(self):
        ps = PhysicsState()
        d = ps.to_dict()
        assert "dim_1_x" in d
        assert "dim_12_precipitation" in d
        assert len(d) == 12

    def test_pack_unpack_roundtrip(self):
        ps = PhysicsState(x=0.5, y=1.5, z=2.5)
        packed = ps.pack()
        assert isinstance(packed, str)
        unpacked = PhysicsState.unpack(packed)
        assert abs(unpacked.x - 0.5) < 0.01
        assert abs(unpacked.y - 1.5) < 0.01
        assert abs(unpacked.z - 2.5) < 0.01


# ---------------------------------------------------------------------------
# UniverseNode tests
# ---------------------------------------------------------------------------


class TestUniverseNode:
    def test_to_dict_basic(self):
        node = UniverseNode(id="n1", content="hello")
        d = node.to_dict()
        assert d["id"] == "n1"
        assert d["content"] == "hello"
        assert d["compressed"] is False
        assert "packed_physics" in d

    def test_to_dict_with_compression(self):
        # Content must be > 100 chars for compression
        long_content = "A" * 200
        node = UniverseNode(id="n2", content=long_content)
        d = node.to_dict(compress=True)
        assert d["compressed"] is True
        # Content should be base64-encoded compressed data, not the original
        assert d["content"] != long_content

    def test_to_dict_no_compression_short_content(self):
        node = UniverseNode(id="n3", content="short")
        d = node.to_dict(compress=True)
        # Short content is not compressed even with compress=True
        assert d["content"] == "short"
        assert d["compressed"] is False

    def test_to_dict_metadata(self):
        node = UniverseNode(id="n4", content="hi", metadata={"key": "val"})
        d = node.to_dict()
        assert d["metadata"] == {"key": "val"}


# ---------------------------------------------------------------------------
# InMemoryStore tests
# ---------------------------------------------------------------------------


class TestInMemoryStore:
    def test_store_and_get(self):
        store = InMemoryStore()
        store.store("key1", {"value": "data"})
        assert store.get("key1") == {"value": "data"}

    def test_get_missing_returns_none(self):
        store = InMemoryStore()
        assert store.get("nonexistent") is None

    def test_get_all(self):
        store = InMemoryStore()
        store.store("a", {"v": 1})
        store.store("b", {"v": 2})
        store.store("c", {"v": 3})
        all_items = store.get_all(limit=2)
        assert len(all_items) == 2

    def test_get_all_empty(self):
        store = InMemoryStore()
        assert store.get_all() == []

    def test_search_similar_empty(self):
        store = InMemoryStore()
        results = store.search_similar([1.0, 0.0, 0.0], limit=5)
        assert results == []

    def test_search_similar_with_embeddings(self):
        store = InMemoryStore()
        store.store("a", {"embedding": [1.0, 0.0, 0.0]})
        store.store("b", {"embedding": [0.0, 1.0, 0.0]})
        store.store("c", {"embedding": [0.9, 0.1, 0.0]})
        results = store.search_similar([1.0, 0.0, 0.0], limit=2)
        assert len(results) == 2
        # First result should be most similar (the [1.0, 0.0, 0.0] vector)
        assert results[0]["embedding"] == [1.0, 0.0, 0.0]

    def test_search_similar_skips_no_embedding(self):
        store = InMemoryStore()
        store.store("a", {"data": "no embedding"})
        store.store("b", {"embedding": [1.0, 0.0]})
        results = store.search_similar([1.0, 0.0], limit=5)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# SurrealClient tests
# ---------------------------------------------------------------------------


class TestSurrealClientInit:
    def test_default_params(self):
        client = SurrealClient()
        assert client.url == "ws://localhost:8000/rpc"
        assert client.namespace == "cohezion"
        assert client.database == "universe"
        assert client._connected is False

    def test_custom_params(self):
        client = SurrealClient(
            url="ws://custom:9000/rpc",
            namespace="test_ns",
            database="test_db",
        )
        assert client.url == "ws://custom:9000/rpc"
        assert client.namespace == "test_ns"
        assert client.database == "test_db"


class TestSurrealClientConnect:
    @pytest.mark.asyncio
    async def test_fallback_to_inmemory_when_import_fails(self):
        """When surrealdb package is not importable, should use InMemoryStore."""
        import cohezion.core.persistence.surreal_client as mod

        old_shared = mod._SHARED_STORE
        mod._SHARED_STORE = None

        client = SurrealClient()
        with patch("cohezion.core.persistence.surreal_client.get_circuit") as mock_circuit:
            mock_breaker = MagicMock()
            mock_breaker.allow_request.return_value = True
            mock_circuit.return_value = mock_breaker

            # Patch the import inside connect to fail
            import builtins

            real_import = builtins.__import__

            def fake_import(name, *args, **kwargs):
                if name == "surrealdb":
                    raise ImportError("no surrealdb")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                result = await client.connect()

        assert result is True
        assert client._connected is True
        assert isinstance(client._client, InMemoryStore)

        # Restore
        mod._SHARED_STORE = old_shared


class TestSurrealClientStoreNode:
    @pytest.mark.asyncio
    async def test_store_with_inmemory(self):
        client = SurrealClient()
        client._connected = True
        client._client = InMemoryStore()

        node = UniverseNode(id="test_node", content="test content")
        result = await client.store_node(node)
        assert result == "test_node"

        # Verify it's stored
        stored = client._client.get("test_node")
        assert stored is not None
        assert stored["id"] == "test_node"


class TestSurrealClientGetNode:
    @pytest.mark.asyncio
    async def test_get_node_with_inmemory(self):
        client = SurrealClient()
        client._connected = True
        client._client = InMemoryStore()

        # Store a node-like dict
        node = UniverseNode(id="gn1", content="get me", physics_state=PhysicsState(x=1.0))
        await client.store_node(node)

        retrieved = await client.get_node("gn1")
        assert retrieved is not None
        assert retrieved.id == "gn1"
        assert retrieved.content == "get me"

    @pytest.mark.asyncio
    async def test_get_missing_node(self):
        client = SurrealClient()
        client._connected = True
        client._client = InMemoryStore()
        result = await client.get_node("missing")
        assert result is None


class TestSurrealClientQuerySimilar:
    @pytest.mark.asyncio
    async def test_query_similar_inmemory(self):
        client = SurrealClient()
        client._connected = True
        client._client = InMemoryStore()

        # Store nodes with embeddings
        for i in range(3):
            vec = [0.0] * 768
            vec[i] = 1.0
            node_data = UniverseNode(id=f"sim_{i}", content=f"node {i}", embedding=vec).to_dict()
            client._client.store(f"sim_{i}", node_data)

        query_vec = [0.0] * 768
        query_vec[0] = 1.0
        results = await client.query_similar(query_vec, limit=2)
        assert len(results) == 2


class TestSurrealClientCreateRelationship:
    @pytest.mark.asyncio
    async def test_create_relationship_inmemory(self):
        client = SurrealClient()
        client._connected = True
        client._client = InMemoryStore()

        rel_id = await client.create_relationship(
            from_id="node_a",
            to_id="node_b",
            relation_type="bridges",
            weight=0.8,
            metadata={"reason": "test"},
        )
        assert rel_id is not None
        assert "node_a" in rel_id
        assert "node_b" in rel_id


class TestDictToNode:
    def test_basic_conversion(self):
        client = SurrealClient()
        data = {
            "id": "t1",
            "content": "hello",
            "embedding": [0.1] * 10,
            "physics_state": PhysicsState(x=1.0).to_dict(),
            "node_type": "document",
            "created_at": datetime.now().isoformat(),
            "metadata": {"k": "v"},
            "packed_physics": PhysicsState(x=1.0).pack(),
        }
        node = client._dict_to_node(data)
        assert node.id == "t1"
        assert node.content == "hello"
        assert abs(node.physics_state.x - 1.0) < 0.01

    def test_compressed_content_decompression(self):
        client = SurrealClient()
        import zlib

        original = "A" * 200
        compressed = base64.b64encode(zlib.compress(original.encode("utf-8"))).decode("ascii")
        data = {
            "id": "t2",
            "content": compressed,
            "compressed": True,
            "physics_state": {},
            "node_type": "document",
        }
        node = client._dict_to_node(data)
        assert node.content == original
