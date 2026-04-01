import pytest

from cohezion.integrations.kaggle_eval import KaggleEvaluator


def test_extract_boxed_answer_success():
    """Test extracting answer from LaTeX \boxed{}."""
    evaluator = KaggleEvaluator()
    text = "The final result is \\boxed{42}."
    assert evaluator.extract_answer(text) == "42"
    
    text_multiple = "Step 1: \\boxed{10}. Final answer: \\boxed{100}."
    assert evaluator.extract_answer(text_multiple) == "100"

def test_extract_boxed_answer_none():
    """Test when no \boxed{} is present."""
    evaluator = KaggleEvaluator()
    text = "The answer is 42."
    assert evaluator.extract_answer(text) is None

def test_score_answers():
    """Test accuracy scoring logic."""
    evaluator = KaggleEvaluator()
    predictions = ["42", "100", "None"]
    references = ["42", "101", "None"]
    
    metrics = evaluator.score(predictions, references)
    assert metrics["accuracy"] == pytest.approx(0.666, 0.01)
    assert metrics["correct"] == 2
    assert metrics["total"] == 3

def test_extract_complex_boxed():
    """Test extracting complex content from \boxed{}."""
    evaluator = KaggleEvaluator()
    text = "Result: \\boxed{\\frac{1}{2}}"
    assert evaluator.extract_answer(text) == "\\frac{1}{2}"
