"""Tests for BranchIntegrationMarkov — Markov chain integration sequencer (Phase 4).

Covers: phi score formula, transition probability estimation, optimal sequencing,
steady-state distribution, and runtime state tracking.
"""

from __future__ import annotations

import pytest

from cohezion.compound.branch_integration_markov import BranchIntegrationMarkov


class TestPhiScore:
    def test_phi_peak_near_ten_commits(self):
        markov = BranchIntegrationMarkov()
        # phi = 4*c*(1-c) where c = exp(-n/20); peak is at c=0.5 → n ≈ 13.9
        b10 = markov.add_branch("b10", commit_count=10)
        b20 = markov.add_branch("b20", commit_count=20)
        b1 = markov.add_branch("b1", commit_count=1)
        b100 = markov.add_branch("b100", commit_count=100)
        # Near-peak branches should beat extremes
        assert b10.phi_score > b1.phi_score
        assert b20.phi_score > b100.phi_score

    def test_phi_formula_values(self):
        markov = BranchIntegrationMarkov()
        # At commit_count=0: c=1.0 → phi = 4*1*(1-1) = 0.0
        b0 = markov.add_branch("b0", commit_count=0)
        assert b0.phi_score == pytest.approx(0.0, abs=1e-9)

    def test_phi_bounded_zero_one(self):
        markov = BranchIntegrationMarkov()
        for n in [1, 5, 10, 20, 50, 100, 500]:
            b = markov.add_branch(f"b{n}", commit_count=n)
            assert 0.0 <= b.phi_score <= 1.0


class TestTransitionProbabilities:
    def test_small_branch_full_pipeline(self):
        markov = BranchIntegrationMarkov()
        b = markov.add_branch("small", commit_count=5, overlap_ratio=0.0)
        # commit_count < 10 → p_conflict_check = 1.0; overlap=0 → p_tests_green = 1.0
        assert b.transition_probs["unreviewed"] == pytest.approx(1.0)
        assert b.transition_probs["assessed"] == pytest.approx(1.0)
        assert b.transition_probs["conflict_checked"] == pytest.approx(1.0)
        assert b.transition_probs["tests_green"] == pytest.approx(1.0)

    def test_large_branch_reduced_conflict_prob(self):
        markov = BranchIntegrationMarkov()
        b = markov.add_branch("large", commit_count=50, overlap_ratio=0.0)
        # commit_count=50 → p_conflict_check = max(0.6, 1 - 50/100) = 0.6
        assert b.transition_probs["assessed"] == pytest.approx(0.6)

    def test_overlap_reduces_test_probability(self):
        markov = BranchIntegrationMarkov()
        b = markov.add_branch("overlapping", commit_count=5, overlap_ratio=0.5)
        # p_tests_green = max(0.4, 1.0 - 0.5) = 0.5
        assert b.transition_probs["conflict_checked"] == pytest.approx(0.5)

    def test_full_overlap_floor(self):
        markov = BranchIntegrationMarkov()
        b = markov.add_branch("heavy-overlap", commit_count=5, overlap_ratio=1.0)
        # p_tests_green = max(0.4, 1.0 - 1.0) = 0.4
        assert b.transition_probs["conflict_checked"] == pytest.approx(0.4)


class TestExpectedValue:
    def test_expected_value_small_branch_no_overlap(self):
        markov = BranchIntegrationMarkov()
        b = markov.add_branch("easy", commit_count=5, overlap_ratio=0.0)
        # All transition probs = 1.0, so expected_value = phi_score * 1.0
        assert b.expected_value == pytest.approx(b.phi_score)

    def test_expected_value_decreases_with_overlap(self):
        markov = BranchIntegrationMarkov()
        b_clean = markov.add_branch("clean", commit_count=10, overlap_ratio=0.0)
        b_dirty = markov.add_branch("dirty", commit_count=10, overlap_ratio=0.9)
        assert b_clean.expected_value > b_dirty.expected_value

    def test_expected_value_nonnegative(self):
        markov = BranchIntegrationMarkov()
        for n, r in [(1, 0.0), (5, 0.5), (100, 1.0)]:
            b = markov.add_branch(f"b{n}r{int(r * 10)}", commit_count=n, overlap_ratio=r)
            assert b.expected_value >= 0.0


class TestOptimalSequence:
    def test_higher_value_first(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("large-risky", commit_count=100, overlap_ratio=0.8)
        markov.add_branch("easy", commit_count=10, overlap_ratio=0.0)
        seq = markov.optimal_sequence()
        assert seq[0][0].name == "easy"

    def test_tie_broken_by_commit_count(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("small", commit_count=9, overlap_ratio=0.0)
        markov.add_branch("large", commit_count=100, overlap_ratio=0.0)
        seq = markov.optimal_sequence()
        assert len(seq) == 2

    def test_empty_returns_empty(self):
        markov = BranchIntegrationMarkov()
        assert markov.optimal_sequence() == []


class TestSteadyState:
    def test_steady_state_keys(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("b", commit_count=5, overlap_ratio=0.0)
        ss = markov.steady_state()
        assert set(ss.keys()) == {
            "unreviewed",
            "assessed",
            "conflict_checked",
            "tests_green",
            "merged",
        }

    def test_steady_state_sums_to_one(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("a", commit_count=5, overlap_ratio=0.0)
        markov.add_branch("b", commit_count=20, overlap_ratio=0.3)
        ss = markov.steady_state()
        assert sum(ss.values()) == pytest.approx(1.0, abs=1e-6)

    def test_steady_state_nonnegative(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("a", commit_count=10)
        for v in markov.steady_state().values():
            assert v >= 0.0

    def test_empty_steady_state(self):
        markov = BranchIntegrationMarkov()
        ss = markov.steady_state()
        assert all(v == 0.0 for v in ss.values())


class TestAdvance:
    def test_advance_sequential(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("feat/x", commit_count=5)
        result = markov.advance("feat/x", "assessed")
        assert result is not None
        assert result.state == "assessed"

    def test_advance_full_pipeline(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("feat/x", commit_count=5)
        states = ["assessed", "conflict_checked", "tests_green", "merged"]
        for state in states:
            result = markov.advance("feat/x", state)
            assert result is not None
            assert result.state == state

    def test_advance_skip_not_allowed(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("feat/x", commit_count=5)
        # Cannot skip from unreviewed to conflict_checked
        result = markov.advance("feat/x", "conflict_checked")
        assert result is not None
        assert result.state == "unreviewed"  # state unchanged

    def test_advance_unknown_branch(self):
        markov = BranchIntegrationMarkov()
        assert markov.advance("nonexistent", "assessed") is None


class TestCounts:
    def test_merged_count(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("a", commit_count=5, current_state="merged")
        markov.add_branch("b", commit_count=5)
        assert markov.merged_count() == 1
        assert markov.pending_count() == 1

    def test_branches_property_is_copy(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("a", commit_count=5)
        branches = markov.branches
        branches.clear()
        assert len(markov.branches) == 1


class TestSummary:
    def test_summary_contains_headers(self):
        markov = BranchIntegrationMarkov()
        markov.add_branch("feat/feature", commit_count=10, overlap_ratio=0.2)
        s = markov.summary()
        assert "Branch Integration Plan" in s
        assert "feat/feature" in s
        assert "Steady-state" in s
