"""Tests for Memory-R1 split — MemoryManager + DecisionAgent in RetrospectionEngine.

Discriminating tests: a wrong implementation that always returns True would fail
test_decision_agent_update_skill_false_on_empty (empty findings → no update).
"""

from __future__ import annotations

from cohezion.core.compound.retrospection import (
    DecisionAgent,
    MemoryManager,
    RetrospectionEngine,
)


class TestMemoryManager:
    def test_store_retrieve(self):
        """Stored value is retrievable by the same key."""
        mm = MemoryManager()
        mm.store("coherence", 0.75)
        assert mm.retrieve("coherence") == 0.75

    def test_retrieve_missing_returns_default(self):
        """Missing key returns the provided default."""
        mm = MemoryManager()
        assert mm.retrieve("missing_key", "fallback") == "fallback"
        assert mm.retrieve("also_missing") is None

    def test_clear_wipes_all_state(self):
        """clear() removes all stored keys."""
        mm = MemoryManager()
        mm.store("a", 1)
        mm.store("b", 2)
        mm.clear()
        assert mm.retrieve("a") is None
        assert mm.retrieve("b") is None

    def test_summarize_returns_stored_dict(self):
        """summarize() returns a snapshot with all stored keys."""
        mm = MemoryManager()
        mm.store("x", 42)
        mm.store("y", "hello")
        summary = mm.summarize()
        assert "x" in summary
        assert summary["x"] == 42
        assert "y" in summary

    def test_summarize_is_snapshot_not_reference(self):
        """Mutating the summarize() result does not affect stored state."""
        mm = MemoryManager()
        mm.store("key", "value")
        snap = mm.summarize()
        snap["key"] = "mutated"
        assert mm.retrieve("key") == "value"

    def test_overwrite_existing_key(self):
        """Storing to the same key overwrites the old value."""
        mm = MemoryManager()
        mm.store("coherence", 0.5)
        mm.store("coherence", 0.9)
        assert mm.retrieve("coherence") == 0.9


class TestDecisionAgent:
    def test_update_skill_true_on_improvement_key(self):
        """Findings with an 'improvement' key triggers skill update."""
        da = DecisionAgent()
        findings = {"improvement_opportunity": "cache hit rate can improve"}
        assert da.should_update_skill(None, findings) is True

    def test_update_skill_true_on_issue_key(self):
        """Findings with an 'issue' key triggers skill update."""
        da = DecisionAgent()
        findings = {"issue_detected": "latency spike"}
        assert da.should_update_skill(None, findings) is True

    def test_update_skill_false_on_empty(self):
        """Empty findings dict never warrants an update (discriminating test)."""
        da = DecisionAgent()
        assert da.should_update_skill(None, {}) is False

    def test_update_skill_false_on_unrelated_keys(self):
        """Findings with unrelated keys do not trigger update."""
        da = DecisionAgent()
        findings = {"status": "ok", "coherence": 0.8}
        assert da.should_update_skill(None, findings) is False

    def test_escalate_on_low_coherence(self):
        """coherence < 0.4 triggers escalation."""
        da = DecisionAgent()
        assert da.should_escalate(None, {"coherence": 0.3}) is True

    def test_escalate_on_high_error_rate(self):
        """error_rate > 0.3 triggers escalation."""
        da = DecisionAgent()
        assert da.should_escalate(None, {"error_rate": 0.5, "coherence": 0.9}) is True

    def test_no_escalate_healthy(self):
        """Healthy metrics (low error_rate, high coherence) → no escalation."""
        da = DecisionAgent()
        assert da.should_escalate(None, {"error_rate": 0.1, "coherence": 0.8}) is False

    def test_no_escalate_default_findings(self):
        """Missing keys use safe defaults (error_rate=0, coherence=1.0) → no escalation."""
        da = DecisionAgent()
        assert da.should_escalate(None, {}) is False


class TestRetrospectionEngineMemoryR1Integration:
    def test_engine_exposes_memory_manager(self):
        """RetrospectionEngine.memory_manager property returns a MemoryManager."""
        engine = RetrospectionEngine()
        assert isinstance(engine.memory_manager, MemoryManager)

    def test_engine_exposes_decision_agent(self):
        """RetrospectionEngine.decision_agent property returns a DecisionAgent."""
        engine = RetrospectionEngine()
        assert isinstance(engine.decision_agent, DecisionAgent)

    def test_analyze_execution_result_stores_coherence(self):
        """analyze_execution_result stores coherence in memory_manager."""

        class FakeResult:
            success = True
            metrics = {"coherence": 0.85}
            duration_seconds = 1.0
            output = "done"

        engine = RetrospectionEngine()
        engine.analyze_execution_result(FakeResult(), skill_name="test_skill")
        assert engine.memory_manager.retrieve("last_coherence") == 0.85

    def test_memory_manager_isolated_per_instance(self):
        """Each RetrospectionEngine instance has its own MemoryManager."""
        e1 = RetrospectionEngine()
        e2 = RetrospectionEngine()
        e1.memory_manager.store("key", "e1_value")
        assert e2.memory_manager.retrieve("key") is None
