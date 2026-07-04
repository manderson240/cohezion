"""TDD tests for RubricMiddleware (Task #22) — V-model MD/AD level.

RubricMiddleware evaluates task outputs against a rubric via Lemonade :13305,
returning a structured verdict before outputs are persisted to cache/learning stores.

V-Model contracts tested here:
  MD1: RubricVerdict dataclass with passed/reason/raw_response fields
  MD2: RubricMiddleware has evaluate() method returning RubricVerdict
  MD3: evaluate() returns passed=True on network/parse failure (fail-open)
  MD4: evaluate() passes when perceived_error=false in JSON response
  MD5: evaluate() fails when perceived_error=true in JSON response
  MD6: reason field captured from JSON response
  MD7: raw_response stored on verdict
  AD1: evaluate() calls :13305 /v1/chat/completions with response_format json_object
  AD2: system prompt embeds the rubric; user message carries the task output
  AD3: model parameter forwarded to inference call (or router picks when None)
"""

from __future__ import annotations

import json
from dataclasses import fields
from unittest.mock import MagicMock, patch



def _import_middleware():
    from cohezion.compound.rubric_middleware import RubricMiddleware, RubricVerdict
    return RubricMiddleware, RubricVerdict


# ── MD1: RubricVerdict structure ──────────────────────────────────────────────


def test_rubric_verdict_importable():
    _, RubricVerdict = _import_middleware()
    assert RubricVerdict is not None


def test_rubric_verdict_has_required_fields():
    _, RubricVerdict = _import_middleware()
    field_names = {f.name for f in fields(RubricVerdict)}
    assert "passed" in field_names, "RubricVerdict must have 'passed' field"
    assert "reason" in field_names, "RubricVerdict must have 'reason' field"
    assert "raw_response" in field_names, "RubricVerdict must have 'raw_response' field"


def test_rubric_verdict_passed_is_bool():
    _, RubricVerdict = _import_middleware()
    v = RubricVerdict(passed=True, reason="ok", raw_response="{}")
    assert isinstance(v.passed, bool)


# ── MD2: RubricMiddleware structure ───────────────────────────────────────────


def test_rubric_middleware_importable():
    RubricMiddleware, _ = _import_middleware()
    assert RubricMiddleware is not None


def test_rubric_middleware_has_evaluate():
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Output must be factually correct.")
    assert hasattr(rm, "evaluate"), "RubricMiddleware must expose evaluate()"
    assert callable(rm.evaluate)


def test_rubric_middleware_stores_rubric():
    RubricMiddleware, _ = _import_middleware()
    rubric = "The output must not contradict itself."
    rm = RubricMiddleware(rubric=rubric)
    assert rm.rubric == rubric


# ── MD3: fail-open on network error ──────────────────────────────────────────


def test_evaluate_fail_open_on_network_error():
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Any rubric.")

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        import httpx as _real_httpx
        mock_httpx.post.side_effect = _real_httpx.ConnectError("refused")
        mock_httpx.ConnectError = _real_httpx.ConnectError
        mock_httpx.TimeoutException = _real_httpx.TimeoutException
        verdict = rm.evaluate("some output")

    assert verdict.passed is True, "Network error must yield fail-open passed=True"


def test_evaluate_fail_open_on_invalid_json():
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Any rubric.")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "not json at all"}}]
    }

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = mock_resp
        verdict = rm.evaluate("some output")

    assert verdict.passed is True, "Unparseable JSON must yield fail-open passed=True"


def test_evaluate_fail_open_on_missing_perceived_error_key():
    """JSON without 'perceived_error' key must be treated as passed (fail-open)."""
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Any rubric.")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"some_other_key": "value"})}}]
    }

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = mock_resp
        verdict = rm.evaluate("some output")

    assert verdict.passed is True


# ── MD4/MD5: verdict from perceived_error field ───────────────────────────────


def _make_mock_response(perceived_error: bool, reason: str) -> MagicMock:
    raw = json.dumps({"perceived_error": perceived_error, "reason": reason})
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"choices": [{"message": {"content": raw}}]}
    return mock_resp


def test_evaluate_passes_when_no_perceived_error():
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Output must be coherent.")

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = _make_mock_response(False, "Output is coherent.")
        verdict = rm.evaluate("A well-formed output string.")

    assert verdict.passed is True


def test_evaluate_fails_when_perceived_error():
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Output must be coherent.")

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = _make_mock_response(True, "Output contradicts itself.")
        verdict = rm.evaluate("Contradictory content here.")

    assert verdict.passed is False


# ── MD6/MD7: reason and raw_response captured ─────────────────────────────────


def test_reason_captured_from_response():
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Output must be factual.")

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = _make_mock_response(True, "Contains hallucinated date.")
        verdict = rm.evaluate("The event happened in 1823.")

    assert verdict.reason == "Contains hallucinated date."


def test_raw_response_stored():
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Output must be factual.")

    raw = json.dumps({"perceived_error": False, "reason": "All good."})
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"choices": [{"message": {"content": raw}}]}

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = mock_resp
        verdict = rm.evaluate("Good output.")

    assert verdict.raw_response == raw


# ── AD1: inference call shape ─────────────────────────────────────────────────


def test_evaluate_calls_13305_chat_completions():
    """evaluate() must POST to :13305/v1/chat/completions."""
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Must be concise.")

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = _make_mock_response(False, "ok")
        rm.evaluate("Short output.")

    mock_httpx.post.assert_called_once()
    url_arg = mock_httpx.post.call_args[0][0]
    assert "13305" in url_arg, f"Must call :13305; got {url_arg}"
    assert "chat/completions" in url_arg


def test_evaluate_sends_response_format_json_object():
    """evaluate() must request response_format: json_object for structured output."""
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Must be structured.")

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = _make_mock_response(False, "ok")
        rm.evaluate("Some task output.")

    call_kwargs = mock_httpx.post.call_args[1]
    body = call_kwargs.get("json", {})
    assert body.get("response_format") == {"type": "json_object"}, (
        "response_format must be json_object for structured verdict"
    )


# ── AD2: prompt construction ──────────────────────────────────────────────────


def test_rubric_embedded_in_system_prompt():
    """The rubric text must appear in the system message."""
    RubricMiddleware, _ = _import_middleware()
    rubric = "UNIQUE_RUBRIC_SENTINEL_XYZ"
    rm = RubricMiddleware(rubric=rubric)

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = _make_mock_response(False, "ok")
        rm.evaluate("output")

    body = mock_httpx.post.call_args[1]["json"]
    messages = body["messages"]
    system_msgs = [m for m in messages if m.get("role") == "system"]
    assert system_msgs, "Must have a system message"
    assert rubric in system_msgs[0]["content"], (
        "Rubric must be embedded in the system prompt"
    )


def test_task_output_in_user_message():
    """The task output must appear in the user message."""
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Any rubric.")
    sentinel = "UNIQUE_OUTPUT_SENTINEL_ABC"

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = _make_mock_response(False, "ok")
        rm.evaluate(sentinel)

    body = mock_httpx.post.call_args[1]["json"]
    messages = body["messages"]
    user_msgs = [m for m in messages if m.get("role") == "user"]
    assert user_msgs, "Must have a user message"
    assert sentinel in user_msgs[0]["content"]


# ── AD3: model forwarding ─────────────────────────────────────────────────────


def test_model_parameter_forwarded_when_set():
    """When model is provided, it must appear in the inference call body."""
    RubricMiddleware, _ = _import_middleware()
    rm = RubricMiddleware(rubric="Any rubric.", model="my-custom-model")

    with patch("cohezion.compound.rubric_middleware.httpx") as mock_httpx:
        mock_httpx.post.return_value = _make_mock_response(False, "ok")
        rm.evaluate("output")

    body = mock_httpx.post.call_args[1]["json"]
    assert body.get("model") == "my-custom-model"
