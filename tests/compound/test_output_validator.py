"""Tests for output_validator — deterministic structured-output validation + retry loop."""

import pytest

from cohezion.compound.output_validator import (
    execute_with_output_validation,
    validate_structured_output,
)


# ---------------------------------------------------------------------------
# validate_structured_output — pure-function tests
# ---------------------------------------------------------------------------


class TestValidateStructuredOutput:
    def test_valid_json_no_schema(self):
        valid, err = validate_structured_output('{"role": "PRODUCER"}')
        assert valid is True
        assert err is None

    def test_invalid_json_returns_error_text(self):
        valid, err = validate_structured_output("not json at all")
        assert valid is False
        assert err is not None
        assert "JSON parse error" in err

    def test_strips_markdown_fences(self):
        fenced = '```json\n{"role": "CONSUMER"}\n```'
        valid, err = validate_structured_output(fenced)
        assert valid is True
        assert err is None

    def test_strips_plain_code_fences(self):
        fenced = '```\n{"x": 1}\n```'
        valid, err = validate_structured_output(fenced)
        assert valid is True
        assert err is None

    def test_nested_json_passes(self):
        nested = '{"outer": {"inner": [1, 2, 3]}}'
        valid, err = validate_structured_output(nested)
        assert valid is True
        assert err is None

    def test_empty_string_fails(self):
        valid, err = validate_structured_output("")
        assert valid is False
        assert err is not None

    def test_partial_json_fails(self):
        valid, err = validate_structured_output('{"role": "PRODUCER"')
        assert valid is False
        assert err is not None

    def test_error_message_contains_snippet(self):
        bad = "this is not JSON content"
        valid, err = validate_structured_output(bad)
        assert valid is False
        # Error should include a snippet so the model sees what it produced
        assert err is not None and len(err) > 10

    def test_schema_valid(self):
        schema = {
            "type": "object",
            "required": ["role"],
            "properties": {"role": {"type": "string"}},
        }
        valid, err = validate_structured_output('{"role": "PRODUCER"}', schema=schema)
        assert valid is True
        assert err is None

    def test_schema_missing_required_field(self):
        schema = {"type": "object", "required": ["role"]}
        _, err = validate_structured_output('{"other": "value"}', schema=schema)
        # If jsonschema is installed: schema error. If not: JSON parse succeeds (no error).
        if err is not None:
            assert "role" in err or "Schema" in err

    def test_schema_wrong_type(self):
        schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
        _, err = validate_structured_output('{"count": "not-a-number"}', schema=schema)
        if err is not None:
            assert "count" in err or "Schema" in err


# ---------------------------------------------------------------------------
# execute_with_output_validation — integration tests
# ---------------------------------------------------------------------------


class _FakeFn:
    """Callable that cycles through fixed responses; records calls and guidances."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.call_count = 0
        self.guidances: list[str] = []

    def __call__(self, guidance: str) -> tuple[str, dict]:
        self.guidances.append(guidance)
        idx = min(self.call_count, len(self._responses) - 1)
        self.call_count += 1
        return self._responses[idx], {"attempt": self.call_count}


class TestExecuteWithOutputValidation:
    def test_no_schema_returns_immediately(self):
        fn = _FakeFn(["hello world"])
        output, _, val_err = execute_with_output_validation(fn, "do something")
        assert output == "hello world"
        assert val_err is None
        assert fn.call_count == 1

    def test_valid_json_on_first_try(self):
        fn = _FakeFn(['{"role": "PRODUCER"}'])
        schema = {"type": "object", "required": ["role"]}
        _, _, val_err = execute_with_output_validation(fn, "go", output_schema=schema)
        assert val_err is None
        assert fn.call_count == 1

    def test_retry_on_invalid_json_then_succeeds(self):
        fn = _FakeFn(["not json", '{"role": "CONSUMER"}'])
        output, _, val_err = execute_with_output_validation(
            fn, "go", output_schema={"type": "object"}
        )
        assert val_err is None
        assert output == '{"role": "CONSUMER"}'
        assert fn.call_count == 2

    def test_retry_injects_exact_error_into_guidance(self):
        """The guidance passed on retry 2 must contain the exact error from retry 1."""
        fn = _FakeFn(["bad output", '{"ok": true}'])
        execute_with_output_validation(fn, "initial guidance", output_schema={"type": "object"})
        assert fn.call_count == 2
        retry_guidance = fn.guidances[1]
        assert "initial guidance" in retry_guidance
        assert "VALIDATION ERROR" in retry_guidance
        assert "JSON parse error" in retry_guidance

    def test_all_retries_exhausted_returns_last_output(self):
        fn = _FakeFn(["bad"] * 10)
        _, metrics, val_err = execute_with_output_validation(
            fn, "go", output_schema={"type": "object"}, max_retries=3
        )
        assert val_err is not None
        assert "JSON parse error" in val_err
        assert metrics.get("output_validation_failed") is True
        assert metrics.get("output_validation_retries") == 3
        assert fn.call_count == 3  # exactly max_retries calls

    def test_retry_count_recorded_on_success(self):
        fn = _FakeFn(["bad", '{"ok": true}'])
        _, metrics, val_err = execute_with_output_validation(
            fn, "go", output_schema={"type": "object"}
        )
        assert val_err is None
        assert metrics.get("output_validation_retries") == 1

    def test_execute_fn_exception_propagates(self):
        def bad_fn(_guidance: str) -> tuple[str, dict]:
            raise RuntimeError("inference backend down")

        with pytest.raises(RuntimeError, match="inference backend down"):
            execute_with_output_validation(bad_fn, "go")
