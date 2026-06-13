"""Adversarial batch Z66: config to_dict partial serialization + cache key collision.

Real bugs found:
1. CohezionConfig.to_dict() cherry-picks fields — any non-default value for
   context_prune_ratio, retry_on_timeout, ttl_seconds, hash_method, etc. is
   silently dropped from the serialized output.
2. _cache_key() uses sorted(set(texts)) — two inputs that differ only by
   duplicate entries produce the same key, causing cache shape mismatch and
   permanent cache misses.
3. ModelConfig.for_operation() uses unconstrained getattr — passing an internal
   attribute name (e.g. 'for_operation') returns a non-string value.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Module 1: core/config.py — partial to_dict and reflection safety
# ---------------------------------------------------------------------------


class TestCohezionConfigToDict:
    def test_to_dict_preserves_modified_inference_fields(self):
        """Modified InferenceConfig fields must appear in to_dict() output.

        BUG: to_dict() only serialises context_max_tokens and timeout_default.
        Any other InferenceConfig change is silently dropped — callers that
        serialise a customised config and pass it on lose their settings.
        """
        from cohezion.core.config import CohezionConfig

        cfg = CohezionConfig()
        cfg.inference.context_prune_ratio = 0.5  # default 0.8
        cfg.inference.retry_on_timeout = 5  # default 2
        cfg.inference.stream_responses = False  # default True

        d = cfg.to_dict()
        inf = d.get("inference", {})

        assert "context_prune_ratio" in inf, "context_prune_ratio missing from to_dict()"
        assert inf["context_prune_ratio"] == pytest.approx(0.5)

        assert "retry_on_timeout" in inf, "retry_on_timeout missing from to_dict()"
        assert inf["retry_on_timeout"] == 5

        assert "stream_responses" in inf, "stream_responses missing from to_dict()"
        assert inf["stream_responses"] is False

    def test_to_dict_preserves_modified_cache_fields(self):
        """Modified CacheConfig fields must appear in to_dict() output."""
        from cohezion.core.config import CohezionConfig

        cfg = CohezionConfig()
        cfg.cache.ttl_seconds = 3600  # default None
        cfg.cache.hash_method = "blake2b"  # default sha256

        d = cfg.to_dict()
        cache = d.get("cache", {})

        assert "ttl_seconds" in cache, "ttl_seconds missing from to_dict()"
        assert cache["ttl_seconds"] == 3600

        assert "hash_method" in cache, "hash_method missing from to_dict()"
        assert cache["hash_method"] == "blake2b"

    def test_to_dict_preserves_modified_token_budget_fields(self):
        """Per-operation token limits must appear in to_dict() output."""
        from cohezion.core.config import CohezionConfig

        cfg = CohezionConfig()
        cfg.token_budget.generate_max = 2048  # default 1024
        cfg.token_budget.analyze_max = 1024  # default 512

        d = cfg.to_dict()
        tb = d.get("token_budget", {})

        assert "generate_max" in tb, "generate_max missing from to_dict()"
        assert tb["generate_max"] == 2048

        assert "analyze_max" in tb, "analyze_max missing from to_dict()"
        assert tb["analyze_max"] == 1024

    def test_to_dict_preserves_modified_batch_fields(self):
        """Modified BatchConfig fields must appear in to_dict() output."""
        from cohezion.core.config import CohezionConfig

        cfg = CohezionConfig()
        cfg.batch.timeout_seconds = 600  # default 300

        d = cfg.to_dict()
        batch = d.get("batch", {})

        assert "timeout_seconds" in batch, "timeout_seconds missing from to_dict()"
        assert batch["timeout_seconds"] == 600

    def test_default_config_to_dict_round_trips_cleanly(self):
        """Default config to_dict must include all operational fields at minimum."""
        from cohezion.core.config import CohezionConfig

        d = CohezionConfig().to_dict()
        # Core fields that must be present at minimum
        assert "models" in d
        assert "token_budget" in d
        assert "cache" in d
        assert "batch" in d
        assert "inference" in d


class TestModelConfigForOperation:
    def test_for_operation_always_returns_string(self):
        """for_operation() must always return a str, never a method or class.

        BUG: uses getattr(self, operation, default) without validating the
        result type — passing 'for_operation' returns the bound method itself.
        """
        from cohezion.core.config import ModelConfig

        mc = ModelConfig()
        result = mc.for_operation("for_operation")
        assert isinstance(result, str), (
            f"for_operation('for_operation') returned {type(result).__name__}, expected str"
        )

    def test_for_operation_unknown_key_returns_default(self):
        """Unknown operation returns the default model string, not an error."""
        from cohezion.core.config import ModelConfig

        mc = ModelConfig()
        result = mc.for_operation("nonexistent_op")
        assert isinstance(result, str)
        assert result == "phi3:mini"

    def test_for_operation_known_operations_return_correct_model(self):
        """Known operations return the configured model."""
        from cohezion.core.config import ModelConfig

        mc = ModelConfig()
        assert mc.for_operation("generate") == "qwen3-coder:30b"
        assert mc.for_operation("analyze") == "phi3:mini"


# ---------------------------------------------------------------------------
# Module 2: flume/data_pipeline.py — cache key collision on duplicate texts
# ---------------------------------------------------------------------------


class TestCacheKeyCollision:
    def test_cache_key_distinguishes_duplicate_inputs(self):
        """_cache_key must produce different keys for inputs with different lengths.

        BUG: uses sorted(set(texts)) — deduplication means ['a','a','b'] and
        ['a','b'] produce the same key. When the cache is loaded, shape[0]==2
        but len(texts)==3, causing a mismatch and permanent cache invalidation.
        """
        from cohezion.flume.data_pipeline import _cache_key

        key_with_dup = _cache_key(["a", "a", "b"], seed=None)
        key_no_dup = _cache_key(["a", "b"], seed=None)
        assert key_with_dup != key_no_dup, (
            "Cache key collision: ['a','a','b'] and ['a','b'] produced the same key"
        )

    def test_cache_key_is_order_independent(self):
        """Same texts in different order must produce the same key (valid dedup)."""
        from cohezion.flume.data_pipeline import _cache_key

        assert _cache_key(["b", "a"], seed=42) == _cache_key(["a", "b"], seed=42)

    def test_cache_key_differs_by_seed(self):
        """Different seeds must produce different keys for the same texts."""
        from cohezion.flume.data_pipeline import _cache_key

        assert _cache_key(["a", "b"], seed=0) != _cache_key(["a", "b"], seed=1)

    def test_cache_key_none_seed_differs_from_int_seed(self):
        """seed=None and seed=0 must produce different keys."""
        from cohezion.flume.data_pipeline import _cache_key

        assert _cache_key(["a", "b"], seed=None) != _cache_key(["a", "b"], seed=0)


class TestContrastivePairMiner:
    def test_mine_pairs_single_element_group_produces_no_pairs(self):
        """Groups with only one sample contribute no pairs."""
        from cohezion.flume.data_pipeline import ContrastivePairMiner

        tasks = [{"group_id": "g1"}, {"group_id": "g2"}, {"group_id": "g2"}]
        pairs = ContrastivePairMiner().mine_pairs(tasks)
        # g1 has 1 sample (no pairs), g2 has 2 samples (1 pair)
        assert len(pairs) == 1
        assert all(tasks[a]["group_id"] == tasks[b]["group_id"] for a, b in pairs)

    def test_mine_pairs_respects_max_pairs_per_group(self):
        """Pairs per group must not exceed max_pairs_per_group."""
        from cohezion.flume.data_pipeline import ContrastivePairMiner

        # 6 items in same group → 15 combinations
        tasks = [{"group_id": "g1"}] * 6
        pairs = ContrastivePairMiner().mine_pairs(tasks, max_pairs_per_group=5, seed=0)
        assert len(pairs) <= 5
