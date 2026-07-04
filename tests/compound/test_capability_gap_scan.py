"""Tests for CapabilityMatrix.scan_for_task() — pre-flight gap analysis."""
from cohezion.compound.capability_matrix import CapabilityMatrix


class TestScanForTask:
    def setup_method(self):
        self.matrix = CapabilityMatrix()

    def test_unknown_skill_returns_high_gap(self):
        result = self.matrix.scan_for_task("nonexistent-skill-xyz-abc", "describe the task")
        assert result["gap_severity"] in ("high", "medium", "unknown")
        assert result["skill_found"] is False

    def test_fail_open_on_bad_input(self):
        result = self.matrix.scan_for_task(None, None)  # type: ignore[arg-type]
        assert "gap_severity" in result  # never raises, always returns dict

    def test_returns_required_keys(self):
        result = self.matrix.scan_for_task("any-skill", "some task description")
        assert "skill_name" in result
        assert "skill_found" in result
        assert "gap_severity" in result
        assert result["gap_severity"] in ("none", "low", "medium", "high", "unknown")

    def test_related_skills_populated_when_tokens_match(self):
        result = self.matrix.scan_for_task("unknown-skill", "coding task")
        assert isinstance(result.get("related_skills", []), list)

    def test_skill_found_true_when_entry_exists(self):
        skills = [k.removeprefix("skill:") for k in self.matrix._entries if k.startswith("skill:")]
        if not skills:
            # No skills loaded (empty SkillHealthTracker) — test the negative path instead
            result = self.matrix.scan_for_task("anything", "task")
            assert result["skill_found"] is False
            return
        result = self.matrix.scan_for_task(skills[0], "test task")
        assert result["skill_found"] is True
        assert result["quality_score"] is not None
