"""Tests for FLUME training data pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np


class TestSyntheticTaskGenerator:
    """Test synthetic task template generation."""

    def test_generates_correct_count(self):
        """Should generate requested number of task descriptions."""
        from cohezion.flume.data_pipeline import SyntheticTaskGenerator

        gen = SyntheticTaskGenerator()
        tasks = gen.generate(n=100)

        assert len(tasks) == 100

    def test_covers_all_operation_types(self):
        """Generated tasks should span all 5 operation types."""
        from cohezion.flume.data_pipeline import SyntheticTaskGenerator

        gen = SyntheticTaskGenerator()
        tasks = gen.generate(n=500)

        op_types = {t["op_type"] for t in tasks}
        assert op_types == {"generate", "analyze", "search", "transform", "persist"}

    def test_each_task_has_required_fields(self):
        """Each task should have text, op_type, and group_id."""
        from cohezion.flume.data_pipeline import SyntheticTaskGenerator

        gen = SyntheticTaskGenerator()
        tasks = gen.generate(n=10)

        for t in tasks:
            assert "text" in t
            assert "op_type" in t
            assert "group_id" in t
            assert isinstance(t["text"], str)
            assert len(t["text"]) > 0


class TestContrastivePairMiner:
    """Test contrastive pair mining from task groups."""

    def test_same_group_pairs(self):
        """Should find pairs from same group (positive pairs)."""
        from cohezion.flume.data_pipeline import ContrastivePairMiner

        tasks = [
            {"text": "deploy API", "group_id": "g1"},
            {"text": "API deployment", "group_id": "g1"},
            {"text": "run tests", "group_id": "g2"},
            {"text": "execute tests", "group_id": "g2"},
        ]
        miner = ContrastivePairMiner()
        pairs = miner.mine_pairs(tasks)

        # Should have at least 2 positive pairs
        assert len(pairs) >= 2
        for anchor_idx, positive_idx in pairs:
            assert tasks[anchor_idx]["group_id"] == tasks[positive_idx]["group_id"]

    def test_returns_index_pairs(self):
        """Pairs should be tuples of (anchor_index, positive_index)."""
        from cohezion.flume.data_pipeline import ContrastivePairMiner

        tasks = [
            {"text": "a", "group_id": "g1"},
            {"text": "b", "group_id": "g1"},
        ]
        miner = ContrastivePairMiner()
        pairs = miner.mine_pairs(tasks)

        for pair in pairs:
            assert len(pair) == 2
            assert isinstance(pair[0], int)
            assert isinstance(pair[1], int)


class TestTrainingDataPipeline:
    """Test the full data preparation pipeline."""

    def test_prepare_returns_embeddings_and_pairs(self):
        """Pipeline should produce embedded vectors and contrastive pairs."""
        from cohezion.flume.data_pipeline import TrainingDataPipeline

        mock_provider = MagicMock()
        mock_provider.embed_batch.side_effect = lambda batch: np.random.randn(
            len(batch), 768
        ).astype(np.float32)
        mock_provider.embedding_dim = 768

        pipeline = TrainingDataPipeline(embedding_provider=mock_provider)
        result = pipeline.prepare(n_synthetic=10, augment_factor=0, cache_dir=None)

        assert "embeddings" in result
        assert "texts" in result
        assert "pairs" in result
        assert result["embeddings"].shape[0] == 10
        assert result["embeddings"].shape[1] == 768

    def test_calls_provider_for_embedding(self):
        """Pipeline should call embedding provider to produce vectors."""
        from cohezion.flume.data_pipeline import TrainingDataPipeline

        mock_provider = MagicMock()
        mock_provider.embed_batch.return_value = np.random.randn(20, 768).astype(np.float32)
        mock_provider.embedding_dim = 768

        pipeline = TrainingDataPipeline(embedding_provider=mock_provider)
        pipeline.prepare(n_synthetic=20, cache_dir=None)

        assert mock_provider.embed_batch.called
