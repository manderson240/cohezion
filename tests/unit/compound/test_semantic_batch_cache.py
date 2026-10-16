"""Unit tests for Token-Efficient Semantic Cache & Micro-Batching System."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cohezion.compound.semantic_batch_cache import MicroBatcher, SemanticBatchCache


def test_semantic_cache_put_get() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = SemanticBatchCache(cache_dir=Path(tmpdir), max_memory_entries=10)
        domain = "test_domain"
        payload = {"x": 10, "prompt": "extract invariants"}
        value = {"result": "invariants_found"}

        assert cache.get(domain, payload) is None
        assert cache.telemetry.cache_misses == 1

        cache.put(domain, payload, value, estimated_tokens=128)
        retrieved = cache.get(domain, payload)
        assert retrieved == value
        assert cache.telemetry.cache_hits == 1
        assert cache.telemetry.tokens_saved == 128


def test_deterministic_bypass_avoids_llm() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = SemanticBatchCache(cache_dir=Path(tmpdir))

        def mock_verifier(payload: dict) -> tuple[bool, str]:
            if payload.get("type") == "ast_rule":
                return True, "valid_ast"
            return False, ""

        def mock_fallback(payload: dict) -> tuple[str, int]:
            return "llm_generated_output", 2048

        # Case 1: Deterministic bypass applies (0 tokens spent, 2048 saved)
        res, bypassed = cache.evaluate_or_bypass(
            "rules", {"type": "ast_rule"}, mock_verifier, mock_fallback
        )
        assert res == "valid_ast"
        assert bypassed is True
        assert cache.telemetry.deterministic_bypasses == 1
        assert cache.telemetry.tokens_spent == 0

        # Case 2: Deterministic bypass doesn't apply; invokes fallback
        res2, bypassed2 = cache.evaluate_or_bypass(
            "rules", {"type": "creative_reasoning"}, mock_verifier, mock_fallback
        )
        assert res2 == "llm_generated_output"
        assert bypassed2 is False
        assert cache.telemetry.tokens_spent == 2048

        # Case 3: Subsequent call hits semantic cache
        res3, bypassed3 = cache.evaluate_or_bypass(
            "rules", {"type": "creative_reasoning"}, mock_verifier, mock_fallback
        )
        assert res3 == "llm_generated_output"
        assert bypassed3 is True
        assert cache.telemetry.cache_hits == 1


def test_micro_batcher() -> None:
    batcher = MicroBatcher(batch_size=3)
    assert not batcher.is_ready()

    batcher.add("1", "req1")
    batcher.add("2", "req2")
    assert not batcher.is_ready()

    batcher.add("3", "req3")
    assert batcher.is_ready()

    def dummy_processor(batch: list[dict]) -> list[dict]:
        return [{"id": item["id"], "out": f"processed_{item['payload']}"} for item in batch]

    results = batcher.execute_batch(dummy_processor)
    assert len(results) == 3
    assert results[0]["out"] == "processed_req1"
    assert results[2]["out"] == "processed_req3"
    assert not batcher.is_ready()
