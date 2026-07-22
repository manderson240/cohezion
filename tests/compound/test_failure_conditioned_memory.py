"""Failure-conditioned retrieval — discriminating tests.

The claim under test: SkillRefiner's L1 failure-refinement recommendation is
driven by RETRIEVAL of an analogous past failure+fix, not just a generic
per-category template. A no-op / retrieval-absent implementation must FAIL
these tests.

Local-first: uses an injected deterministic embed_fn (no live :13305 call
required for CI); a separate live-smoke test at the bottom exercises the real
LemonadeEmbedBridge when reachable and skips otherwise.
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.compound.failure_memory import FailureConditionedMemory
from cohezion.compound.skill_refiner import SkillRefiner


class _FakeEmbed:
    """Deterministic stand-in for LemonadeEmbedBridge.encode — controllable cosine geometry."""

    _VECTORS = {
        "malformed json": np.array([1.0, 0.0, 0.0], dtype=np.float32),
        "unparseable output": np.array([0.95, 0.05, 0.0], dtype=np.float32),
        "unrelated": np.array([0.0, 0.0, 1.0], dtype=np.float32),
    }

    def __call__(self, text: str) -> np.ndarray:
        key = text.lower()
        for phrase, vec in self._VECTORS.items():
            if phrase in key:
                return vec / np.linalg.norm(vec)
        return np.array([0.0, 1.0, 0.0], dtype=np.float32)


class TestFailureConditionedMemoryUnit:
    """Direct tests of the storage/retrieval primitive."""

    def test_retrieve_on_empty_store_returns_empty_list(self):
        mem = FailureConditionedMemory(embed_fn=_FakeEmbed())
        assert mem.retrieve("anything") == []

    def test_similar_failure_ranks_above_unrelated_failure(self):
        mem = FailureConditionedMemory(embed_fn=_FakeEmbed(), similarity_threshold=0.5)
        mem.record("tool X returned malformed JSON", "add schema validation before parse")
        mem.record("completely unrelated timeout error", "increase request timeout")

        results = mem.retrieve("tool Y emitted unparseable output", k=3)

        assert len(results) == 1
        top_record, score = results[0]
        assert top_record.fix_text == "add schema validation before parse"
        assert score > 0.9

    def test_embed_failure_falls_back_to_keyword_overlap_not_crash(self):
        def _raising_embed(_text: str) -> np.ndarray:
            raise RuntimeError("lemonade offline")

        mem = FailureConditionedMemory(embed_fn=_raising_embed, similarity_threshold=0.1)
        mem.record("parser threw invalid JSON schema error", "add schema validation before parse")
        # Shares keywords ("schema", "json"/"parser") with the seeded failure text.
        results = mem.retrieve("parser threw invalid schema error again", k=3)
        assert results, "keyword-overlap fallback should still surface a match"
        assert results[0][0].fix_text == "add schema validation before parse"


class TestSkillRefinerFailureConditionedRecommendation:
    """The compound-loop-facing claim: L1 failure recommendations cite retrieved fixes."""

    def _refiner(self) -> SkillRefiner:
        memory = FailureConditionedMemory(embed_fn=_FakeEmbed(), similarity_threshold=0.5)
        return SkillRefiner(failure_memory=memory)

    def test_similar_new_failure_retrieves_and_cites_past_fix(self):
        refiner = self._refiner()
        refiner._failure_memory.record(
            failure_text="tool X returned malformed JSON",
            fix_text="add schema validation before parse",
            skill_name="skill-a",
            category="format",
        )

        signal = refiner._generate_failure_signal(
            skill_name="skill-b",
            operation_type="analyze",
            category="format",
            evidence="tool Y emitted unparseable output",
        )

        # Discriminating: a no-op/ignore-retrieval implementation returns the
        # generic per-category template and would FAIL this assertion.
        assert "add schema validation before parse" in signal.recommendation
        assert "Add structured-output format examples" not in signal.recommendation

    def test_no_analogous_failure_falls_back_to_generic_recommendation(self):
        refiner = self._refiner()
        # No seeded memory — retrieval must yield nothing above threshold.
        signal = refiner._generate_failure_signal(
            skill_name="skill-c",
            operation_type="analyze",
            category="format",
            evidence="totally unrelated failure text about timeouts",
        )
        assert "Add structured-output format examples" in signal.recommendation

    def test_successful_l1_fix_is_recorded_into_failure_memory(self, tmp_path, monkeypatch):
        """After an L1 refinement is applied, the (failure, fix) pair becomes retrievable."""
        refiner = self._refiner()

        prime_file = tmp_path / "TEST_SKILL_PRIME.md"
        prime_file.write_text("# Test Skill\n\n## Version: 1.0.0\n")
        monkeypatch.setattr(refiner, "_find_prime_file", lambda _skill: prime_file)

        refiner._apply_l1_failure_refinement(
            skill_name="skill-d",
            operation_type="analyze",
            category="format",
            evidence="tool Z returned malformed JSON output",
        )

        results = refiner._failure_memory.retrieve("tool W emitted unparseable output", k=1)
        assert results, "the applied fix should now be retrievable for an analogous failure"


class TestLiveEmbedSmoke:
    """Live :13305 smoke — skipped when lemonade/nomic-embed is unreachable."""

    def test_paraphrased_failures_are_near_in_embedding_space(self):
        from cohezion.inference.lemonade_embed_bridge import LemonadeEmbedBridge

        bridge = LemonadeEmbedBridge()
        if not bridge.is_available():
            pytest.skip("lemonade :13305 unreachable — local-first smoke skipped")

        mem = FailureConditionedMemory(embed_fn=bridge.encode, similarity_threshold=0.0)
        mem.record(
            "tool X returned malformed JSON",
            "add schema validation before parse",
        )
        mem.record(
            "the database connection pool was exhausted",
            "increase pool size and add backoff retry",
        )

        results = mem.retrieve("tool Y emitted unparseable JSON output", k=2)
        assert results
        top_record, _top_score = results[0]
        assert top_record.fix_text == "add schema validation before parse"
