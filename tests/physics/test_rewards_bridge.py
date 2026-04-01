"""Tests for the rewards bridge — HIHO Gaussian reward + coherence ratchet."""



from cohezion.physics.rewards_bridge import CoherenceRatchet, RewardsBridge


class TestRewardsBridge:
    """Verify RewardsBridge wraps RewardCalculator correctly."""

    def test_peak_reward_at_hiho(self) -> None:
        """HIHO reward peaks at coherence=0.5 (Brahmagupta's zero)."""
        bridge = RewardsBridge()
        reward_at_hiho = bridge.compute(0.5)
        reward_at_0 = bridge.compute(0.0)
        reward_at_1 = bridge.compute(1.0)

        assert reward_at_hiho > reward_at_0
        assert reward_at_hiho > reward_at_1

    def test_reward_is_gaussian_shaped(self) -> None:
        """Reward decreases symmetrically from the 0.5 peak."""
        bridge = RewardsBridge()
        r_05 = bridge.compute(0.5)
        r_04 = bridge.compute(0.4)
        r_06 = bridge.compute(0.6)

        # Symmetric around 0.5
        assert abs(r_04 - r_06) < 0.01
        # Both lower than peak
        assert r_05 > r_04
        assert r_05 > r_06

    def test_reward_near_zero_at_extremes(self) -> None:
        """At coherence far from 0.5, the Gaussian drops near zero."""
        bridge = RewardsBridge()
        r_0 = bridge.compute(0.0)
        r_1 = bridge.compute(1.0)

        # Gaussian with sigma=0.1 at distance 0.5 from center
        # exp(-0.5^2 / (2*0.1^2)) = exp(-12.5) ≈ 3.7e-6
        assert r_0 < 0.01
        assert r_1 < 0.01

    def test_reset_clears_ratchet(self) -> None:
        """After reset, ratchet best_deviation goes back to worst."""
        bridge = RewardsBridge()
        # Drive toward HIHO to set a good best_deviation
        bridge.compute(0.5)
        bridge.reset()
        # After reset, no penalty for any coherence
        penalty = bridge.ratchet.check(0.9)
        assert penalty == 0.0

    def test_token_penalty_reduces_reward(self) -> None:
        """Token penalty weight reduces the score."""
        bridge_no_penalty = RewardsBridge(token_penalty_weight=0.0)
        bridge_with_penalty = RewardsBridge(token_penalty_weight=0.1)

        r_no = bridge_no_penalty.compute(0.5, tokens_used=1000)
        r_with = bridge_with_penalty.compute(0.5, tokens_used=1000)

        assert r_no > r_with


class TestCoherenceRatchet:
    """Verify the ratchet prevents HIHO regression."""

    def test_no_penalty_on_improvement(self) -> None:
        """Moving closer to HIHO should never be penalised."""
        ratchet = CoherenceRatchet()
        # Start far from HIHO
        p1 = ratchet.check(0.2)
        # Move closer
        p2 = ratchet.check(0.4)
        p3 = ratchet.check(0.5)

        assert p1 == 0.0
        assert p2 == 0.0
        assert p3 == 0.0

    def test_penalty_on_backslide(self) -> None:
        """Moving away from HIHO after reaching it incurs a penalty."""
        ratchet = CoherenceRatchet(margin=0.05, penalty=0.2)
        # Reach near-HIHO
        ratchet.check(0.5)
        # Now backslide significantly
        penalty = ratchet.check(0.2)

        # Deviation went from 0.0 to 0.3, regression = 0.3 > margin=0.05
        assert penalty < 0.0

    def test_small_backslide_within_margin(self) -> None:
        """Tiny backslides within margin incur no penalty."""
        ratchet = CoherenceRatchet(margin=0.05, penalty=0.2)
        ratchet.check(0.5)
        # Tiny backslide: deviation goes from 0.0 to 0.02 (< margin 0.05)
        penalty = ratchet.check(0.48)

        assert penalty == 0.0

    def test_ratchet_tracks_best_deviation(self) -> None:
        """Best deviation ratchets only inward, never outward."""
        ratchet = CoherenceRatchet()
        ratchet.check(0.3)  # deviation = 0.2
        ratchet.check(0.5)  # deviation = 0.0 (new best)
        ratchet.check(0.45)  # deviation = 0.05 (worse than best)

        # Internal best should still be 0.0
        assert ratchet._best_deviation == 0.0

    def test_reset_allows_fresh_start(self) -> None:
        """After reset, ratchet forgets previous best."""
        ratchet = CoherenceRatchet()
        ratchet.check(0.5)  # best = 0.0
        ratchet.reset()

        # After reset, deviation 0.3 is the new best — no penalty
        penalty = ratchet.check(0.2)
        assert penalty == 0.0
