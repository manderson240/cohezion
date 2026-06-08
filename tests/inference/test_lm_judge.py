"""Tests for the LLM-judge preference function (item 99 — lm_judge.py).

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: Blind descriptions DO NOT include model_id.
     Kills impl that exposes model identity in the judge prompt.

  2. _parse_verdict returns 'a' on 'A' response, 'b' on 'B', None on gibberish.
     Kills impl that returns a constant or crashes on unexpected text.

  3. granite_prefer falls back to deterministic proxy when judge returns None.
     Kills impl that raises or returns None when the LLM is unreachable.

  4. granite_prefer accepts a task with no affinity match in either model.
     Kills impl that assumes one model always has task affinity.

  5. is_judge_available() returns bool (not raises) when :13305 is reachable or not.
     Kills impl that propagates exceptions.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from cohezion.inference.lm_judge import (
    _build_judge_prompt,
    _describe_model,
    _parse_verdict,
    granite_prefer,
    is_judge_available,
)
from cohezion.inference.model_tournament import _default_preference
from cohezion.inference.registry import Lane, ModelEntry, Task, WeightQuant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _entry(model_id: str, task_affinity: frozenset, verified: bool = False, priority: int = 100) -> ModelEntry:
    """Minimal ModelEntry for testing."""
    return ModelEntry(
        model_id=model_id,
        lane=Lane.NPU,
        endpoint="http://localhost:13306/v1",
        runtime_backend="flm",
        task_affinity=task_affinity,
        weight_quant=WeightQuant.Q4_K_M,
        context_window=8192,
        verified_working=verified,
        priority=priority,
    )


MODEL_A = _entry("llama3.2-1b-FLM", frozenset({Task.GENERAL, Task.ROUTING}), verified=True)
MODEL_B = _entry("Granite-4.1-8B-GGUF", frozenset({Task.GENERAL, Task.REASONING}), verified=True)
MODEL_C = _entry("mystery-model-xyz", frozenset(), verified=False)


# ---------------------------------------------------------------------------
# Test 1: Blind descriptions don't include model_id (PRIMARY DISCRIMINATOR)
# ---------------------------------------------------------------------------


def test_describe_model_excludes_model_id() -> None:
    """Blind descriptions must NOT include model_id.

    PRIMARY DISCRIMINATOR: kills impl that exposes model identity in the prompt.
    The judge should evaluate capabilities, not brand names.
    """
    desc_a = _describe_model(MODEL_A, Task.GENERAL)
    assert "llama3.2-1b-FLM" not in desc_a, (
        "model_id must be redacted from judge descriptions; found 'llama3.2-1b-FLM' in: "
        + repr(desc_a)
    )
    # Also verify the description contains meaningful information
    assert "Task coverage" in desc_a, "description should mention task coverage"
    assert "YES" in desc_a, "GENERAL task affinity should be YES for MODEL_A"


def test_build_judge_prompt_blind_to_model_ids() -> None:
    """Judge prompt must not contain either model_id.

    Kills impl that embeds model names/IDs in the comparison prompt.
    """
    prompt = _build_judge_prompt(MODEL_A, MODEL_B, Task.GENERAL)
    assert "llama3.2-1b-FLM" not in prompt, "model_id A must be absent from judge prompt"
    assert "Granite-4.1-8B-GGUF" not in prompt, "model_id B must be absent from judge prompt"
    assert "Model A" in prompt and "Model B" in prompt, "prompt must use anonymous labels"


# ---------------------------------------------------------------------------
# Test 2: _parse_verdict handles A/B/ambiguous correctly
# ---------------------------------------------------------------------------


def test_parse_verdict_returns_a_on_a_response() -> None:
    """_parse_verdict returns MODEL_A when judge says 'A'.

    Kills impl returning a constant or always returning MODEL_B.
    """
    result = _parse_verdict("A", MODEL_A, MODEL_B)
    assert result is MODEL_A, f"expected MODEL_A; got {result}"


def test_parse_verdict_returns_b_on_b_response() -> None:
    """_parse_verdict returns MODEL_B when judge says 'B'."""
    result = _parse_verdict("B.", MODEL_A, MODEL_B)
    assert result is MODEL_B, f"expected MODEL_B; got {result}"


def test_parse_verdict_returns_none_on_gibberish() -> None:
    """_parse_verdict returns None on ambiguous/empty/unexpected text.

    Kills impl that crashes or returns a default on ambiguous verdict.
    """
    assert _parse_verdict("C. Neither is suitable.", MODEL_A, MODEL_B) is None
    assert _parse_verdict("", MODEL_A, MODEL_B) is None
    assert _parse_verdict(None, MODEL_A, MODEL_B) is None


# ---------------------------------------------------------------------------
# Test 3: granite_prefer falls back on network failure (NOT raises)
# ---------------------------------------------------------------------------


def test_granite_prefer_falls_back_on_network_failure() -> None:
    """granite_prefer returns deterministic fallback when :13305 is unreachable.

    Kills impl that raises or returns None when the LLM is offline.
    """
    with patch("cohezion.inference.lm_judge._call_judge", return_value=None):
        result = granite_prefer(MODEL_A, MODEL_B, Task.GENERAL)
    # Must return one of the two models, not raise, not return None
    assert result in (MODEL_A, MODEL_B), (
        f"expected MODEL_A or MODEL_B on fallback; got {result}"
    )
    # Should agree with deterministic proxy
    expected = _default_preference(MODEL_A, MODEL_B, Task.GENERAL)
    assert result is expected, (
        f"fallback should match deterministic proxy; expected {expected.model_id}, got {result.model_id}"
    )


def test_granite_prefer_uses_judge_verdict_when_available() -> None:
    """granite_prefer returns judge's choice when judge responds clearly.

    Kills impl that always uses the deterministic fallback (ignores judge).
    Uses a task where MODEL_B has affinity and MODEL_A does not, so the
    deterministic proxy would pick MODEL_B; if the mock judge says 'A',
    granite_prefer must return MODEL_A (overriding the proxy).
    """
    # For Task.REASONING: MODEL_B has affinity, MODEL_A does not.
    # Deterministic proxy would pick MODEL_B.
    # If judge says 'A', granite_prefer must return MODEL_A.
    with patch("cohezion.inference.lm_judge._call_judge", return_value="A — model A is better"):
        result = granite_prefer(MODEL_A, MODEL_B, Task.REASONING)
    assert result is MODEL_A, (
        "granite_prefer must return the judge's choice 'A' even when deterministic proxy disagrees"
    )


# ---------------------------------------------------------------------------
# Test 4: Works with no task affinity in either model
# ---------------------------------------------------------------------------


def test_granite_prefer_handles_no_task_affinity() -> None:
    """granite_prefer works when neither model has affinity for the task.

    Kills impl that assumes one model always has task affinity set.
    """
    with patch("cohezion.inference.lm_judge._call_judge", return_value=None):
        result = granite_prefer(MODEL_C, MODEL_A, Task.MATH)
    # Must return one of the two models, not crash
    assert result in (MODEL_C, MODEL_A), (
        f"expected MODEL_C or MODEL_A; got {result}"
    )


# ---------------------------------------------------------------------------
# Test 5: is_judge_available returns bool, never raises
# ---------------------------------------------------------------------------


def test_is_judge_available_returns_bool_on_connection_error() -> None:
    """is_judge_available() returns False (not raises) when :13305 is unreachable.

    Kills impl that propagates URLError or ConnectionRefusedError.
    """
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        result = is_judge_available()
    assert isinstance(result, bool), f"expected bool; got {type(result)}"
    assert result is False, "unreachable endpoint → False"


def test_is_judge_available_returns_true_when_live() -> None:
    """is_judge_available() returns True when endpoint responds 200."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = is_judge_available()
    assert result is True, "reachable endpoint → True"
