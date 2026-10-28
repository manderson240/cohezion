"""Unit tests for structured_npu inference module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from cohezion.inference.structured_npu import (
    _schema_to_gbnf,
    npu_structured_json,
    verify_with_autoharness,
)


@pytest.fixture
def sample_schema() -> dict:
    return {
        "properties": {
            "node": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["node", "confidence"],
    }


def test_verify_with_autoharness(sample_schema):
    valid_data = {"node": "npu", "confidence": 0.95}
    valid, violations = verify_with_autoharness(valid_data, sample_schema)
    assert valid is True
    assert len(violations) == 0

    missing_field_data = {"node": "npu"}
    valid, violations = verify_with_autoharness(missing_field_data, sample_schema)
    assert valid is False
    assert any("Missing required field: 'confidence'" in v for v in violations)

    wrong_type_data = {"node": "npu", "confidence": "high"}
    valid, violations = verify_with_autoharness(wrong_type_data, sample_schema)
    assert valid is False
    assert any("expected number" in v for v in violations)


def test_schema_to_gbnf(sample_schema):
    gbnf = _schema_to_gbnf(sample_schema)
    assert 'root ::= "{" ws fields ws "}"' in gbnf
    assert 'field ::= key ws ":" ws value' in gbnf
    assert "key ::=" in gbnf


@patch("cohezion.inference.structured_npu.requests.post")
def test_npu_structured_json_direct_json(mock_post, sample_schema):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"node": "npu", "confidence": 0.88}',
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    result = npu_structured_json("Analyze compute", sample_schema)
    assert result["node"] == "npu"
    assert result["confidence"] == 0.88

    # Verify that grammar was NOT sent for FLM model
    called_payload = mock_post.call_args[1]["json"]
    assert "grammar" not in called_payload


@patch("cohezion.inference.structured_npu.requests.post")
def test_npu_structured_json_plain_key_value(mock_post, sample_schema):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Node: GPU\nConfidence: 0.75",
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    result = npu_structured_json("Analyze compute", sample_schema)
    assert result["node"] == "GPU"
    assert result["confidence"] == 0.75


@patch("cohezion.inference.structured_npu.requests.post")
def test_npu_structured_json_fallback_cascade(mock_post, sample_schema):
    # First response fails (e.g. 503 admission refused)
    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 503
    mock_resp_fail.text = "admission refused"

    # Second response succeeds (fallback model)
    mock_resp_ok = MagicMock()
    mock_resp_ok.status_code = 200
    mock_resp_ok.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"node": "gpu", "confidence": 0.99}',
                }
            }
        ]
    }

    mock_post.side_effect = [mock_resp_fail, mock_resp_ok]

    result = npu_structured_json("Analyze compute", sample_schema)
    assert result["node"] == "gpu"
    assert result["confidence"] == 0.99
    assert mock_post.call_count == 2


@patch("cohezion.inference.structured_npu.requests.post")
def test_npu_structured_json_strict_sampler(mock_post, sample_schema):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"node": "npu", "confidence": 0.92}',
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    result = npu_structured_json("Analyze compute", sample_schema, strict_sampler=True)
    assert result["node"] == "npu"
    assert result["confidence"] == 0.92

    # Verify that grammar WAS sent for strict sampler (using non-FLM fallback)
    called_payload = mock_post.call_args[1]["json"]
    assert "grammar" in called_payload
    assert not called_payload["model"].endswith("-FLM")


@patch("cohezion.inference.structured_npu.requests.post")
def test_npu_structured_json_all_exhausted(mock_post, sample_schema):
    mock_post.side_effect = requests.RequestException("Connection error")

    with pytest.raises(requests.RequestException, match="All inference candidates exhausted"):
        npu_structured_json("Analyze compute", sample_schema)
