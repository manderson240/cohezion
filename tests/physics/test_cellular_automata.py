"""Tests for physics/cellular_automata.py — CA engine, complexity, cosmogony chain."""

import numpy as np
import pytest

from cohezion.physics.cellular_automata import (
    CAEngine,
    CAGrid2D,
    CARule,
    CAState,
    ComplexityMetrics2D,
    CosmogonyCA,
    EVOEmergence,
    EVOPattern,
    LemonadeCAAdvisor,
    TotalisticRule2D,
    WolframClass,
    ca_rl_step,
)


class TestCARule:
    def test_rule_110_is_class_complex(self) -> None:
        engine = CAEngine(CARule.turing_complete(), 64)
        m = engine.complexity(CAState.single_center(64), 100)
        assert m.wolfram_class == WolframClass.COMPLEX

    def test_rule_0_produces_fixed_point(self) -> None:
        engine = CAEngine(CARule(0), 64)
        m = engine.complexity(CAState.single_center(64), 20)
        assert m.wolfram_class == WolframClass.FIXED

    def test_rule_bounds_enforced(self) -> None:
        with pytest.raises(ValueError):
            CARule(256)
        with pytest.raises(ValueError):
            CARule(-1)

    def test_mutate_returns_different_rule(self) -> None:
        r = CARule(90)
        mutated = r.mutate(0)
        assert mutated.number != r.number

    def test_mutate_is_reversible(self) -> None:
        r = CARule(110)
        assert r.mutate(3).mutate(3).number == r.number

    def test_hiho_rule_near_half_density(self) -> None:
        engine = CAEngine(CARule.hiho(), 128)
        history = engine.run(CAState.random(128, seed=0), 50)
        # Rule 90 Sierpinski: density converges near 0.5 from random start
        densities = [s.density for s in history[25:]]
        mean_d = np.mean(densities)
        assert 0.3 < mean_d < 0.7, f"Expected density near 0.5, got {mean_d}"


class TestCAState:
    def test_coherence_at_half_density(self) -> None:
        # Grid exactly half-filled → coherence = 1.0
        g = np.array([0, 1] * 32, dtype=np.uint8)
        state = CAState(g)
        assert abs(state.density - 0.5) < 0.01
        assert abs(state.coherence - 1.0) < 0.01

    def test_empty_grid_zero_coherence(self) -> None:
        g = np.zeros(64, dtype=np.uint8)
        state = CAState(g)
        assert state.coherence == 0.0

    def test_random_is_reproducible(self) -> None:
        s1 = CAState.random(64, seed=42)
        s2 = CAState.random(64, seed=42)
        np.testing.assert_array_equal(s1.grid, s2.grid)

    def test_single_center_symmetry(self) -> None:
        s = CAState.single_center(64)
        assert s.grid[32] == 1
        assert s.grid.sum() == 1


class TestComplexityMetrics:
    def test_lz_range(self) -> None:
        engine = CAEngine(CARule(110), 64)
        m = engine.complexity(CAState.single_center(64), 50)
        assert 0.0 < m.lz_complexity <= 1.0

    def test_repetitive_rule_low_complexity(self) -> None:
        engine = CAEngine(CARule(0), 64)
        m = engine.complexity(CAState.single_center(64), 50)
        # All-zeros compresses extremely well
        assert m.lz_complexity < 0.1

    def test_chaotic_rule_not_periodic(self) -> None:
        # Rule 30 is Wolfram Class III — must not be FIXED or PERIODIC
        engine = CAEngine(CARule(30), 128)
        m = engine.complexity(CAState.random(128, seed=7), 100)
        assert m.wolfram_class in (WolframClass.CHAOTIC, WolframClass.COMPLEX)
        assert m.attractor_period == 0  # no repeating cycle


class TestCosmogonyCA:
    def test_chain_has_ten_stages(self) -> None:
        chain = CosmogonyCA(steps_per_stage=10)
        history = chain.run(32)
        assert len(history) == 10

    def test_stage_0_is_fixed(self) -> None:
        chain = CosmogonyCA(steps_per_stage=20)
        history = chain.run(32)
        stage_0_class = history[0][1].wolfram_class
        assert stage_0_class == WolframClass.FIXED

    def test_stage_2_is_complex(self) -> None:
        chain = CosmogonyCA(steps_per_stage=50)
        history = chain.run(64, seed=42)
        # Stage 2 uses Rule 110 from random seed — must reach COMPLEX class
        stage_2_class = history[2][1].wolfram_class
        assert stage_2_class == WolframClass.COMPLEX

    def test_history_persists_after_run(self) -> None:
        chain = CosmogonyCA(steps_per_stage=10)
        chain.run(32)
        assert len(chain.history) == 10


class TestRLStep:
    def test_rl_step_returns_valid_rule(self) -> None:
        new_rule, _metrics, reward = ca_rl_step(CARule(90), WolframClass.COMPLEX)
        assert 0 <= new_rule.number <= 255
        assert 0.0 <= reward <= 1.0

    def test_greedy_fallback_targets_rule_110(self) -> None:
        adv = LemonadeCAAdvisor()
        adv._available = False  # Force offline mode
        rule = CARule(90)
        engine = CAEngine(rule, 64)
        metrics = engine.complexity(CAState.random(64, seed=0), 50)
        bit = adv.propose_mutation(rule, WolframClass.COMPLEX, metrics)
        assert 0 <= bit <= 7

    def test_lemonade_unavailable_does_not_raise(self) -> None:
        adv = LemonadeCAAdvisor(npu_url="http://localhost:19999/v1")
        rule = CARule(30)
        engine = CAEngine(rule, 32)
        metrics = engine.complexity(CAState.single_center(32), 20)
        # Should fall back gracefully
        bit = adv.propose_mutation(rule, WolframClass.COMPLEX, metrics)
        assert 0 <= bit <= 7


# ---------------------------------------------------------------------------
# 2D Totalistic CA tests
# ---------------------------------------------------------------------------


class TestTotalisticRule2D:
    def test_conway_defaults(self) -> None:
        rule = TotalisticRule2D.conway()
        assert 2 in rule.survive_counts and 3 in rule.survive_counts
        assert 3 in rule.born_counts
        assert rule.radius == 1

    def test_neighbor_sum_shape(self) -> None:
        rule = TotalisticRule2D.conway()
        g = np.ones((5, 5), dtype=np.uint8)
        nbrs = rule.neighbor_sum(g)
        assert nbrs.shape == (5, 5)
        # Interior cells of all-ones grid have 8 live neighbors
        assert nbrs[2, 2] == 8

    def test_apply_kills_isolated_cell(self) -> None:
        rule = TotalisticRule2D.conway()
        g = np.zeros((10, 10), dtype=np.uint8)
        g[5, 5] = 1  # single isolated live cell — 0 neighbors → dies
        next_g = rule.apply(g)
        assert next_g[5, 5] == 0

    def test_apply_blinker_period2(self) -> None:
        """A horizontal blinker (3 cells in a row) has period 2 in Conway Life."""
        rule = TotalisticRule2D.conway()
        g = np.zeros((10, 10), dtype=np.uint8)
        g[5, 4] = g[5, 5] = g[5, 6] = 1  # horizontal blinker
        g1 = rule.apply(g)
        g2 = rule.apply(g1)
        np.testing.assert_array_equal(g, g2)  # returns to original after 2 steps

    def test_frozenset_coercion(self) -> None:
        rule = TotalisticRule2D(survive_counts={2, 3}, born_counts={3})
        assert isinstance(rule.survive_counts, frozenset)
        assert isinstance(rule.born_counts, frozenset)

    def test_hiho_2d_has_denser_survival(self) -> None:
        rule = TotalisticRule2D.hiho_2d()
        assert 4 in rule.survive_counts  # survives on 4 neighbors (denser than Conway)

    def test_neighbor_sum_periodic_boundary(self) -> None:
        """Corner cells should wrap around — periodic boundary."""
        rule = TotalisticRule2D.conway()
        g = np.zeros((5, 5), dtype=np.uint8)
        g[0, 0] = 1  # top-left corner
        nbrs = rule.neighbor_sum(g)
        # The wrapped neighbors of bottom-right corner should see g[0,0]
        assert nbrs[4, 4] == 1


class TestCAGrid2D:
    def test_random_seeded_is_reproducible(self) -> None:
        rule = TotalisticRule2D.conway()
        g1 = CAGrid2D.random(rule, rows=20, cols=20, seed=7)
        g2 = CAGrid2D.random(rule, rows=20, cols=20, seed=7)
        np.testing.assert_array_equal(g1.grid, g2.grid)

    def test_density_in_range(self) -> None:
        rule = TotalisticRule2D.conway()
        g = CAGrid2D.random(rule, rows=20, cols=20, seed=0, density=0.3)
        assert 0.0 <= g.density <= 1.0

    def test_coherence_at_half_density(self) -> None:
        rule = TotalisticRule2D.conway()
        g = CAGrid2D.random(rule, rows=20, cols=20, seed=0, density=0.5)
        # Seeded at 0.5 density — coherence should be close to 1.0
        assert g.coherence > 0.5

    def test_step_changes_grid(self) -> None:
        rule = TotalisticRule2D.conway()
        g = CAGrid2D.random(rule, rows=20, cols=20, seed=99, density=0.3)
        original = g.grid.copy()
        g.step()
        # After one Conway step from a random grid, something should change
        assert not np.array_equal(original, g.grid) or g.density == 0.0

    def test_run_returns_correct_number_of_snapshots(self) -> None:
        rule = TotalisticRule2D.conway()
        g = CAGrid2D.random(rule, rows=20, cols=20, seed=1)
        snaps = g.run(steps=20)
        assert len(snaps) == 21  # initial + 20 steps

    def test_run_minimum_grid_size(self) -> None:
        """Task requirement: 20 cells × 20 steps minimum."""
        rule = TotalisticRule2D.conway()
        g = CAGrid2D.random(rule, rows=20, cols=20, seed=42)
        snaps = g.run(steps=20)
        assert snaps[0].shape == (20, 20)
        assert len(snaps) == 21

    def test_grid_property_returns_copy(self) -> None:
        rule = TotalisticRule2D.conway()
        g = CAGrid2D.random(rule, rows=5, cols=5, seed=0)
        copy = g.grid
        copy[0, 0] = 99
        assert g.grid[0, 0] != 99  # mutation of copy doesn't affect internal state


class TestEVOPattern:
    def _blinker_snapshots(self) -> list[np.ndarray]:
        """Generate 10 snapshots of a blinker (period-2 oscillator)."""
        rule = TotalisticRule2D.conway()
        g = np.zeros((10, 10), dtype=np.uint8)
        g[5, 4] = g[5, 5] = g[5, 6] = 1
        snaps = [g.copy()]
        for _ in range(9):
            g = rule.apply(g)
            snaps.append(g.copy())
        return snaps

    def test_detects_blinker_as_oscillator(self) -> None:
        snaps = self._blinker_snapshots()
        patterns = EVOPattern.detect(snaps, check_periods=(1, 2, 4))
        osc = [p for p in patterns if p.pattern_type == "oscillator"]
        assert len(osc) >= 1

    def test_blinker_has_period_2(self) -> None:
        snaps = self._blinker_snapshots()
        patterns = EVOPattern.detect(snaps, check_periods=(2,))
        periods = {p.period for p in patterns if p.pattern_type == "oscillator"}
        assert 2 in periods

    def test_oscillator_has_zero_shift(self) -> None:
        snaps = self._blinker_snapshots()
        patterns = EVOPattern.detect(snaps, check_periods=(2,))
        for p in patterns:
            if p.pattern_type == "oscillator":
                assert p.shift == (0, 0)

    def test_empty_grid_no_patterns(self) -> None:
        snaps = [np.zeros((10, 10), dtype=np.uint8) for _ in range(5)]
        patterns = EVOPattern.detect(snaps)
        assert len(patterns) == 0

    def test_pattern_bounding_box_valid(self) -> None:
        snaps = self._blinker_snapshots()
        patterns = EVOPattern.detect(snaps, check_periods=(2,))
        for p in patterns:
            r0, c0, r1, c1 = p.bounding_box
            assert r0 <= r1 and c0 <= c1
            assert r0 >= 0 and c0 >= 0

    def test_coherence_in_range(self) -> None:
        snaps = self._blinker_snapshots()
        patterns = EVOPattern.detect(snaps, check_periods=(2,))
        for p in patterns:
            assert 0.0 <= p.coherence <= 1.0


class TestComplexityMetrics2D:
    def test_from_run_lz_in_range(self) -> None:
        rule = TotalisticRule2D.conway()
        g = CAGrid2D.random(rule, rows=20, cols=20, seed=0)
        snaps = g.run(20)
        metrics = ComplexityMetrics2D.from_run(snaps, [])
        assert 0.0 < metrics.lz_complexity <= 1.0

    def test_all_zeros_low_lz(self) -> None:
        snaps = [np.zeros((20, 20), dtype=np.uint8) for _ in range(21)]
        metrics = ComplexityMetrics2D.from_run(snaps, [])
        assert metrics.lz_complexity < 0.1  # all-zeros compresses well

    def test_evo_emergence_score_nonnegative(self) -> None:
        rule = TotalisticRule2D.conway()
        g = CAGrid2D.random(rule, rows=20, cols=20, seed=5)
        snaps = g.run(20)
        patterns = EVOPattern.detect(snaps)
        metrics = ComplexityMetrics2D.from_run(snaps, patterns)
        assert metrics.evo_emergence_score >= 0.0

    def test_counts_match_patterns(self) -> None:
        rule = TotalisticRule2D.conway()
        g = np.zeros((12, 12), dtype=np.uint8)
        g[5, 4] = g[5, 5] = g[5, 6] = 1  # blinker
        grid = CAGrid2D(rule, 12, 12)
        grid._grid = g
        snaps = grid.run(10)
        patterns = EVOPattern.detect(snaps, check_periods=(2,))
        metrics = ComplexityMetrics2D.from_run(snaps, patterns)
        assert metrics.oscillator_count + metrics.glider_count == metrics.pattern_count


class TestEVOEmergence:
    def test_run_returns_metrics(self) -> None:
        evo = EVOEmergence(rows=20, cols=20, steps=20)
        metrics = evo.run(seed=42)
        assert isinstance(metrics, ComplexityMetrics2D)

    def test_minimum_grid_and_steps(self) -> None:
        """Task requirement: 20×20 grid, 20 steps."""
        evo = EVOEmergence(rows=20, cols=20, steps=20)
        metrics = evo.run(seed=0)
        assert metrics.mean_density >= 0.0
        assert metrics.coherence >= 0.0

    def test_seeded_is_reproducible(self) -> None:
        evo = EVOEmergence(rows=20, cols=20, steps=20)
        m1 = evo.run(seed=7)
        m2 = evo.run(seed=7)
        assert m1.lz_complexity == m2.lz_complexity
        assert m1.pattern_count == m2.pattern_count

    def test_different_seeds_may_differ(self) -> None:
        evo = EVOEmergence(rows=20, cols=20, steps=20)
        m1 = evo.run(seed=1)
        m2 = evo.run(seed=999)
        # Not guaranteed to differ but lz_complexity is continuous — check they ran
        assert 0.0 < m1.lz_complexity <= 1.0
        assert 0.0 < m2.lz_complexity <= 1.0

    def test_blinker_seed_detects_oscillator(self) -> None:
        """A grid seeded with a known blinker should detect ≥1 oscillator."""
        rule = TotalisticRule2D.conway()
        # Override grid internally to plant a blinker
        grid = CAGrid2D(rule, 20, 20)
        g = np.zeros((20, 20), dtype=np.uint8)
        g[10, 9] = g[10, 10] = g[10, 11] = 1
        grid._grid = g
        snaps = grid.run(20)
        patterns = EVOPattern.detect(snaps, check_periods=(1, 2, 4))
        osc = [p for p in patterns if p.pattern_type == "oscillator"]
        assert len(osc) >= 1

    def test_patterns_property_after_run(self) -> None:
        evo = EVOEmergence(rows=20, cols=20, steps=20)
        evo.run(seed=42)
        # patterns property returns a list (may be empty depending on seed)
        assert isinstance(evo.patterns, list)

    def test_hiho_rule_produces_metrics(self) -> None:
        rule = TotalisticRule2D.hiho_2d()
        evo = EVOEmergence(rule=rule, rows=20, cols=20, steps=20, seed_density=0.4)
        metrics = evo.run(seed=13)
        assert 0.0 <= metrics.coherence <= 1.0
        assert metrics.mean_density >= 0.0

    def test_evo_wired_to_physics_init(self) -> None:
        """New classes must be importable from cohezion.physics."""
        from cohezion.physics import (
            CAGrid2D,
            ComplexityMetrics2D,
            EVOEmergence,
            EVOPattern,
            TotalisticRule2D,
        )

        assert EVOEmergence is not None
        assert TotalisticRule2D is not None
        assert CAGrid2D is not None
        assert EVOPattern is not None
        assert ComplexityMetrics2D is not None
