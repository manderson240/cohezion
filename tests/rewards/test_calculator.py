from cohezion.rewards.calculator import RewardCalculator


def test_reward_calculator_perfect_coherence():
    """Test that 0.5 coherence (HIHO) yields a high score."""
    calc = RewardCalculator()
    # At exactly 0.5, coherence reward should be maximal
    score = calc.calculate_score(coherence=0.5, tokens_used=100)
    assert score >= 0.9

def test_reward_calculator_low_coherence():
    """Test that distance from 0.5 reduces the score."""
    calc = RewardCalculator()
    high_score = calc.calculate_score(coherence=0.5, tokens_used=100)
    low_score = calc.calculate_score(coherence=0.1, tokens_used=100)
    assert low_score < high_score

def test_reward_calculator_token_efficiency():
    """Test that lower token usage yields a higher score for same coherence."""
    calc = RewardCalculator()
    efficient_score = calc.calculate_score(coherence=0.5, tokens_used=10)
    expensive_score = calc.calculate_score(coherence=0.5, tokens_used=1000)
    assert efficient_score > expensive_score

def test_reward_calculator_bounds():
    """Test that scores are within [0, 1]."""
    calc = RewardCalculator()
    assert 0 <= calc.calculate_score(0.5, 1) <= 1.0
    assert 0 <= calc.calculate_score(0.0, 10000) <= 1.0
    assert 0 <= calc.calculate_score(1.0, 10000) <= 1.0
