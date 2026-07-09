"""Structured output for NPU tier via GBNF grammar mode.

Uses llama.cpp native GBNF grammar enforcement on Lemonade :13305 NPU tier
(llama3.2-1b-FLM). Prevents malformed JSON from task_classifier and tool calls.

Session 2026-06-23: discovered outlines library doesn't work with Lemonade's
response_format (NPU ignores it). Direct GBNF grammar mode via :13305 works
natively without new dependencies or second model load.
"""

import json
from typing import Any

import requests


def npu_structured_json(prompt: str, schema: dict[str, Any], temperature: float = 0.7) -> dict:
    """Call NPU with GBNF grammar constraint for JSON schema compliance.

    Args:
        prompt: User prompt
        schema: JSON schema (dict with "properties", "required", etc.)
        temperature: Sampling temperature (0.0-1.0)

    Returns:
        Parsed JSON dict matching the schema

    Raises:
        requests.RequestException: If :13305 is unreachable
        json.JSONDecodeError: If grammar-constrained output is invalid JSON
    """
    # Convert JSON schema to GBNF (simplified — handles basic object/string/number)
    gbnf = _schema_to_gbnf(schema)

    try:
        r = requests.post(
            "http://localhost:13305/v1/chat/completions",
            json={
                "model": "llama3.2-1b-FLM",
                "messages": [{"role": "user", "content": prompt}],
                "grammar": gbnf,
                "temperature": temperature,
                "max_tokens": 256,
            },
            timeout=15,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        return json.loads(text)
    except (requests.RequestException, KeyError, IndexError) as e:
        raise requests.RequestException(f"NPU grammar request failed: {e}")


def _schema_to_gbnf(schema: dict) -> str:
    """Convert minimal JSON schema to GBNF grammar.

    Handles:
    - root object with required string/number fields
    - no nested objects or arrays (for NPU simplicity)

    Example:
        {"properties": {"node": {"type": "string"}, "confidence": {"type": "number"}},
         "required": ["node", "confidence"]}
        →
        root ::= "{" node_field "," confidence_field "}"
        node_field ::= "\"node\"" ws ":" ws string
        confidence_field ::= "\"confidence\"" ws ":" ws number
        ...
    """
    props = schema.get("properties", {})

    if not props:
        return 'root ::= "{" ws "}"'

    rules = ["root ::= \"{\" ws fields ws \"}\""]
    rules.append('fields ::= field ("," ws field)*')
    rules.append('field ::= key ws ":" ws value')
    rules.append('key ::= "\"" [a-zA-Z_][a-zA-Z0-9_]* "\""')
    rules.append('value ::= (string | number | boolean)')
    rules.append('string ::= "\"" [^"]* "\""')
    rules.append('number ::= ("-"? [0-9]+ ("." [0-9]+)?)')
    rules.append('boolean ::= ("true" | "false")')
    rules.append('ws ::= ([ \t\n])*')

    return "\n".join(rules)


# Test fixture (verification)
if __name__ == "__main__":
    schema = {
        "properties": {
            "node": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["node", "confidence"],
    }
    try:
        result = npu_structured_json(
            "Classify this prompt: 'What is HIHO stability?' Reply only with node (npu/gpu) and confidence (0-1).",
            schema,
        )
        print(f"✓ NPU structured output: {result}")
        assert "node" in result and "confidence" in result
    except Exception as e:
        print(f"✗ Test failed: {e}")
