"""Unit tests for Stanford Memorilla: Latent Semantic Memory (arXiv:2610.21375)."""

import numpy as np
import pytest
import torch

from cohezion.memory.memorilla_engine import (
    AgenticLoopDetector,
    HybridMemorillaRAG,
    MemorillaDocumentStore,
    MemorillaEngine,
    MemorillaMemoryModule,
)


class TestMemorillaDocumentStore:
    def test_store_lifecycle_and_matrix_stacking(self):
        store = MemorillaDocumentStore(embedding_dim=64)
        assert store.size() == 0

        # Add documents
        emb1 = np.random.randn(64).astype(np.float32)
        emb2 = np.random.randn(64).astype(np.float32)

        idx1 = store.add_document("doc_1", "User prefers concise answers", emb1)
        idx2 = store.add_document("doc_2", "User works in computational biology", emb2)

        assert idx1 == 0
        assert idx2 == 1
        assert store.size() == 2

        matrix = store.get_matrix()
        assert matrix.shape == (2, 64)
        np.testing.assert_allclose(matrix[0], emb1)
        np.testing.assert_allclose(matrix[1], emb2)

    def test_invalid_dimension_raises_value_error(self):
        store = MemorillaDocumentStore(embedding_dim=64)
        bad_emb = np.random.randn(32).astype(np.float32)
        with pytest.raises(ValueError, match="Expected embedding shape"):
            store.add_document("doc_bad", "Invalid embedding", bad_emb)

    def test_add_turn_metadata_and_idempotence(self):
        store = MemorillaDocumentStore(embedding_dim=32)
        emb = np.random.randn(32).astype(np.float32)

        idx = store.add_turn(
            turn_idx=1,
            observation="Arrived at Room A",
            action="take key",
            embedding=emb,
            reward=1.0,
        )
        assert idx == 0
        docs = store.get_documents()
        assert docs[0].doc_id == "turn_0001"
        assert docs[0].metadata["type"] == "agent_turn"
        assert docs[0].metadata["reward"] == 1.0

        # Overwrite same turn
        idx_updated = store.add_turn(
            turn_idx=1,
            observation="Arrived at Room A (updated)",
            action="take key",
            embedding=emb,
            reward=1.0,
        )
        assert idx_updated == 0
        assert store.size() == 1
        assert "updated" in store.get_documents()[0].text


class TestMemorillaMemoryModule:
    def test_module_forward_pass_output_shape(self):
        encoder_dim = 64
        llm_dim = 128
        k_slots = 8
        module = MemorillaMemoryModule(
            encoder_dim=encoder_dim,
            llm_dim=llm_dim,
            num_memory_tokens=k_slots,
            num_refinement_blocks=2,
            num_heads=2,
        )

        batch_size = 2
        num_docs = 5

        z_query = torch.randn(batch_size, 1, encoder_dim)
        z_docs = torch.randn(batch_size, num_docs, encoder_dim)

        memory_tokens = module(z_query, z_docs)
        assert memory_tokens.shape == (batch_size, k_slots, llm_dim)

    def test_module_2d_query_and_empty_collection_fallback(self):
        encoder_dim = 32
        llm_dim = 64
        k_slots = 4
        module = MemorillaMemoryModule(
            encoder_dim=encoder_dim,
            llm_dim=llm_dim,
            num_memory_tokens=k_slots,
            num_refinement_blocks=1,
            num_heads=2,
        )

        z_query_2d = torch.randn(1, encoder_dim)
        z_docs_empty = torch.empty(1, 0, encoder_dim)

        memory_tokens = module(z_query_2d, z_docs_empty)
        assert memory_tokens.shape == (1, k_slots, llm_dim)


class TestAgenticLoopDetector:
    def test_loop_detection_on_cyclic_states(self):
        detector = AgenticLoopDetector(loop_threshold=3, similarity_threshold=0.90)

        room_a = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        room_b = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

        # Move A -> B -> A -> B -> A
        assert not detector.record_step(room_a, "go east")
        assert not detector.record_step(room_b, "go west")
        assert not detector.record_step(room_a, "go east")
        assert not detector.record_step(room_b, "go west")
        # 3rd revisit to room A: should trigger loop
        is_loop = detector.record_step(room_a, "go east")
        assert is_loop is True

        penalty = detector.get_loop_penalty_bias()
        assert penalty > 0.0

    def test_reset_clears_history(self):
        detector = AgenticLoopDetector()
        room = np.ones(4, dtype=np.float32)
        detector.record_step(room, "act")
        assert len(detector.state_history) == 1
        detector.reset()
        assert len(detector.state_history) == 0


class TestHybridMemorillaRAG:
    def test_hybrid_context_generation(self):
        store = MemorillaDocumentStore(embedding_dim=32)
        module = MemorillaMemoryModule(
            encoder_dim=32,
            llm_dim=64,
            num_memory_tokens=4,
            num_refinement_blocks=1,
            num_heads=2,
        )

        # Add 4 documents
        for i in range(4):
            emb = np.zeros(32, dtype=np.float32)
            emb[i] = 1.0  # Orthogonal features
            store.add_document(f"doc_{i}", f"Document text content {i} with key data", emb)

        hybrid = HybridMemorillaRAG(
            document_store=store,
            memory_module=module,
            top_k_text_chunks=2,
        )

        query_emb = np.zeros(32, dtype=np.float32)
        query_emb[2] = 1.0  # Closest to doc_2

        payload = hybrid.build_hybrid_context(
            query_text="What is key data 2?",
            query_embedding=query_emb,
        )

        assert payload["memory_tokens"].shape == (1, 4, 64)
        assert len(payload["retrieved_passages"]) == 2
        assert "Document text content 2" in payload["retrieved_passages"][0]
        assert payload["compression_ratio"] > 0.0


class TestMemorillaEngine:
    def test_end_to_end_engine_process_turn(self):
        engine = MemorillaEngine(
            encoder_dim=32,
            llm_dim=64,
            num_memory_tokens=4,
            num_refinement_blocks=1,
        )

        obs_emb = np.random.randn(32).astype(np.float32)

        turn_result = engine.process_agent_turn(
            turn_idx=1,
            observation="Found iron chest in armory",
            action="open chest",
            obs_embedding=obs_emb,
            reward=0.5,
        )

        assert turn_result["turn_idx"] == 1
        assert turn_result["is_loop"] is False
        assert turn_result["memory_tokens"].shape == (4, 64)

        # Extract tokens directly
        tokens = engine.extract_memory_tokens(obs_emb)
        assert tokens.shape == (4, 64)
