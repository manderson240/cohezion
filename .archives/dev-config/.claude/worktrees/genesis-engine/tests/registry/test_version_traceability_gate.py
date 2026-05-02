"""Tests for Version Traceability Gate (Story 7.6)."""

from __future__ import annotations

from cohezion.registry.version_traceability_gate import (
    VersionContract,
    VersionTraceabilityGate,
)


class TestVersionTraceabilityGate:
    def _gate_with_contracts(self) -> VersionTraceabilityGate:
        gate = VersionTraceabilityGate()
        gate.register_contract(VersionContract("requests", ">=2.32.0", "1-3", "epic-1"))
        gate.register_contract(VersionContract("numpy", ">=2.0.0", "1-9", "epic-1"))
        return gate

    def test_register_contract_stores_entry(self):
        gate = VersionTraceabilityGate()
        gate.register_contract(VersionContract("flask", ">=2.3.0", "4-1", "epic-4"))
        assert len(gate.all_contracts()) == 1

    def test_epic_gate_passes_when_all_stories_covered(self):
        gate = self._gate_with_contracts()
        result = gate.check_epic_gate("epic-1", expected_stories=["1-3", "1-9"])
        assert result.blocked is False
        assert result.missing_contracts == []

    def test_epic_gate_blocked_on_missing_contracts(self):
        gate = self._gate_with_contracts()
        result = gate.check_epic_gate("epic-1", expected_stories=["1-3", "1-9", "1-4"])
        assert result.blocked is True
        assert "1-4" in result.missing_contracts
        assert len(result.remediation_steps) > 0

    def test_release_report_generated(self):
        gate = self._gate_with_contracts()
        report = gate.generate_release_report("1.1.0", story_ids=["1-3", "1-9"])
        assert report.release_version == "1.1.0"
        assert len(report.version_changes) == 2

    def test_incident_response_query_fast(self):
        gate = self._gate_with_contracts()
        result = gate.incident_response_query("requests", ">=2.32.0")
        assert result["query_duration_s"] < 1.0
        assert "1-3" in result["affected_stories"]

    def test_incident_response_includes_affected_epics(self):
        gate = self._gate_with_contracts()
        result = gate.incident_response_query("requests", ">=2.32.0")
        assert "epic-1" in result["affected_epics"]

    def test_no_match_returns_empty_lists(self):
        gate = VersionTraceabilityGate()
        result = gate.incident_response_query("unknown-pkg", ">=99.0")
        assert result["affected_stories"] == []
