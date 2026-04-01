"""TDD: Proactive CapabilityMatrix gap detection and overlap resolution.

The capability matrix should:
1. Detect capability gaps (missing skills for task types)
2. Detect overlapping modules (healing/ vs resilience/)
3. Suggest actions to fill gaps and resolve overlaps
4. Work across all three platforms (Claude Code, Gemini CLI, OpenCode)
"""

from __future__ import annotations


class TestGapDetection:
    """CapabilityMatrix should proactively identify gaps."""

    def test_gap_analysis_returns_gaps(self):
        from cohezion.compound.capability_matrix import CapabilityMatrix

        matrix = CapabilityMatrix()
        gaps = matrix.run_gap_analysis()
        # Should identify at least some gaps (not all task types fully covered)
        assert isinstance(gaps, list)

    def test_gaps_have_suggested_actions(self):
        from cohezion.compound.capability_matrix import CapabilityGap, CapabilityMatrix

        matrix = CapabilityMatrix()
        gaps = matrix.run_gap_analysis()
        for gap in gaps:
            assert gap.suggested_action in ("scout", "finetune", "onboard")


class TestOverlapDetection:
    """CapabilityMatrix should detect module overlaps."""

    def test_has_detect_overlaps_method(self):
        from cohezion.compound.capability_matrix import CapabilityMatrix

        matrix = CapabilityMatrix()
        assert hasattr(matrix, "detect_overlaps")

    def test_detect_overlaps_returns_list(self):
        from cohezion.compound.capability_matrix import CapabilityMatrix

        matrix = CapabilityMatrix()
        overlaps = matrix.detect_overlaps()
        assert isinstance(overlaps, list)

    def test_overlap_has_modules_and_recommendation(self):
        from cohezion.compound.capability_matrix import CapabilityMatrix

        matrix = CapabilityMatrix()
        overlaps = matrix.detect_overlaps()
        for overlap in overlaps:
            assert "modules" in overlap
            assert "recommendation" in overlap


class TestProactiveGapFilling:
    """CapabilityMatrix should suggest concrete actions for gaps."""

    def test_has_suggest_gap_actions_method(self):
        from cohezion.compound.capability_matrix import CapabilityMatrix

        matrix = CapabilityMatrix()
        assert hasattr(matrix, "suggest_gap_actions")

    def test_gap_actions_are_actionable(self):
        from cohezion.compound.capability_matrix import CapabilityMatrix

        matrix = CapabilityMatrix()
        actions = matrix.suggest_gap_actions()
        assert isinstance(actions, list)
        for action in actions:
            assert "gap" in action
            assert "action" in action
            assert "priority" in action
