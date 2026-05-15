"""Adversarial batch Z62: provenance mutability + guardrail stats gap.

Two real bugs found via adversarial probing:
1. ProvenanceRecord is documented as 'immutable' but is a plain mutable dataclass —
   content can be tampered after registration and verify() still passes.
2. GuardrailPipeline.get_stats() silently drops LOG_AND_ALLOW actions —
   avg_latency_ms returns 0 and the action is never counted.
"""

from __future__ import annotations

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Module 1: security/provenance_hash.py — mutable "immutable" record
# ---------------------------------------------------------------------------


class TestProvenanceMutabilityGap:
    def _make_registry(self):
        from cohezion.security.provenance_hash import ProvenanceRegistry

        return ProvenanceRegistry()

    def test_tampering_record_after_registration_is_detected(self):
        """Mutating a ProvenanceRecord after registration must raise AttributeError.

        BUG: @dataclass (mutable) lets callers overwrite content_hash/source after
        registration. The registry still verifies the original key, but get_chain()
        returns the tampered payload — 'immutable provenance' is a lie.
        Fix: use @dataclass(frozen=True).
        """
        reg = self._make_registry()
        rec = reg.register("skill-1", "skill", "def foo(): pass", "vault:decision-1")
        original_hash = rec.provenance_hash

        # Attempting to mutate MUST raise AttributeError on a frozen dataclass
        with pytest.raises(AttributeError):
            rec.content_hash = "TAMPERED_CONTENT"

        # And the registry must still return the original, untampered record
        chain = reg.get_chain(original_hash)
        assert len(chain) == 1
        assert chain[0].content_hash != "TAMPERED_CONTENT"

    def test_source_field_immutable_after_registration(self):
        """Source attribution must be immutable — prevents audit-trail manipulation."""
        reg = self._make_registry()
        rec = reg.register("pattern-x", "pattern", "some content", "arxiv:2401.99999")

        with pytest.raises(AttributeError):
            rec.source = "evil:attacker"

    def test_verify_chain_returns_original_content(self):
        """get_chain must return the exact content registered, not a mutated copy."""
        reg = self._make_registry()
        content = "canonical skill content"
        rec = reg.register("skill-2", "skill", content, "vault:decision-99")

        import hashlib

        expected_content_hash = hashlib.sha256(content.encode()).hexdigest()
        chain = reg.get_chain(rec.provenance_hash)
        assert chain[0].content_hash == expected_content_hash

    def test_chained_records_verify_correctly(self):
        """Parent-child provenance chain must verify to original content."""
        reg = self._make_registry()
        parent = reg.register("skill-v1", "skill", "v1 content", "vault:d1")
        child = reg.register("skill-v2", "skill", "v2 content", "vault:d2", parent_hash=parent.provenance_hash)

        chain = reg.get_chain(child.provenance_hash)
        assert len(chain) == 2
        assert chain[0].artifact_id == "skill-v2"
        assert chain[1].artifact_id == "skill-v1"


# ---------------------------------------------------------------------------
# Module 2: security/guardrail_pipeline.py — LOG_AND_ALLOW not counted
# ---------------------------------------------------------------------------


class TestGuardrailStatsGap:
    def _make_pipeline(self, guardrail, name="g1"):
        from cohezion.security.guardrail_pipeline import GuardrailPipeline

        return GuardrailPipeline(guardrails=[(name, guardrail)])

    def test_log_and_allow_counted_in_stats(self):
        """LOG_AND_ALLOW actions must be counted in stats — currently silently dropped.

        BUG: the stats update block only handles ALLOW/BLOCK/SANITIZE.
        LOG_AND_ALLOW falls through without incrementing any counter.
        avg_latency_ms then divides by zero and returns 0.
        Fix: add elif result.action == GuardrailAction.LOG_AND_ALLOW: stats.allowed += 1
        """
        from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailResult

        class LogAndAllowGuard:
            async def check(self, text, context):
                return GuardrailResult(action=GuardrailAction.LOG_AND_ALLOW, reason="audit")

        pipeline = self._make_pipeline(LogAndAllowGuard())
        asyncio.run(pipeline.check_input("probe text"))

        stats = pipeline.get_stats()["g1"]
        total = stats["allowed"] + stats["blocked"] + stats["sanitized"]
        assert total == 1, f"LOG_AND_ALLOW action not counted in stats (total={total})"

    def test_log_and_allow_avg_latency_nonzero(self):
        """avg_latency_ms must be > 0 after a LOG_AND_ALLOW check — not division-by-zero 0."""
        from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailResult

        class LogAndAllowGuard:
            async def check(self, text, context):
                return GuardrailResult(action=GuardrailAction.LOG_AND_ALLOW, reason="audit")

        pipeline = self._make_pipeline(LogAndAllowGuard())
        asyncio.run(pipeline.check_input("probe text"))

        avg = pipeline.get_stats()["g1"]["avg_latency_ms"]
        assert avg > 0, f"avg_latency_ms is {avg} after LOG_AND_ALLOW — stats denominator is 0"

    def test_log_and_allow_pipeline_still_returns_allow(self):
        """Pipeline must return ALLOW when all guards return LOG_AND_ALLOW."""
        from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailResult

        class LogAndAllowGuard:
            async def check(self, text, context):
                return GuardrailResult(action=GuardrailAction.LOG_AND_ALLOW)

        pipeline = self._make_pipeline(LogAndAllowGuard())
        result = asyncio.run(pipeline.check_input("safe text"))
        assert result.action == GuardrailAction.ALLOW

    def test_mixed_allow_and_log_and_allow_counts(self):
        """After two checks (one ALLOW, one LOG_AND_ALLOW), total must be 2."""
        from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailResult

        call_count = [0]

        class AlternatingGuard:
            async def check(self, text, context):
                call_count[0] += 1
                if call_count[0] % 2 == 0:
                    return GuardrailResult(action=GuardrailAction.LOG_AND_ALLOW)
                return GuardrailResult(action=GuardrailAction.ALLOW)

        pipeline = self._make_pipeline(AlternatingGuard())
        asyncio.run(pipeline.check_input("first"))
        asyncio.run(pipeline.check_input("second"))

        stats = pipeline.get_stats()["g1"]
        total = stats["allowed"] + stats["blocked"] + stats["sanitized"]
        assert total == 2, f"Expected total=2 after 2 checks, got {total}"
