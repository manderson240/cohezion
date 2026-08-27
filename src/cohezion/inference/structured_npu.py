"""Structured output for NPU tier via GBNF grammar mode — CLAIM FALSIFIED, DO NOT USE AS-IS.

DORMANT: zero production consumers. That is WHY the claim below survived unchallenged for a
year — a capability with no consumer never has its claims tested.

    2026-06-23 (original, WRONG): "Direct GBNF grammar mode via :13305 works natively."
    2026-07-28 (measured, Lemonade 11.5.0): the NPU/flm lane IGNORES `grammar` entirely.

Probed live with a discriminating grammar (`root ::= "BANANA" | "PENGUIN"`) against a prompt
whose natural answer is neither: `llama3.2-1b-FLM` returned 'No' — HTTP 200, non-empty, wholly
unconstrained. The split is STRUCTURAL, not a config gap: GBNF is a llama.cpp SAMPLER feature,
and the `flm` recipe is FastFlowLM, a separate from-scratch NPU runtime whose documented request
params (model/messages/stream/temperature/top_p/presence_penalty) include no constraint field.

THE HAZARD — failure is SILENT, not loud. FastFlowLM does not reject unknown request fields; it
accepts and discards them (a bogus `totally_bogus_param_xyz` also returns 200 OK with a normal
completion). So `npu_structured_json()` below does not raise, does not warn, and does not
constrain: it returns whatever the model felt like emitting. json.loads() then fails on prose, or
worse, succeeds on plausible-but-unconstrained JSON.

WIRING TARGET if a consumer ever appears (per .claude/rules/non-destructive-wiring.md — this
module is a wiring TODO, not a deletion candidate): retarget at a `llamacpp` recipe model
(iGPU `Gemma-4-E4B-it-GGUF`, CPU `Gemma-4-E2B-it-GGUF`), where GBNF IS enforced. A single
unrepeated probe also suggested bare GBNF alternation is cheaper there than the
`response_format` enum path used by `transition_controller.enum_schema` — n=1, NOT established;
re-measure before letting it drive a choice (see the vault report's latency caveat).

Running the `__main__` fixture below on a live box PRINTS `✗ Test failed` — that outcome is now
EXPECTED and is the falsification, not a regression to repair. The live evidence is pinned in
tests/inference/test_recipe_constraint_support.py (invariant RC1); read that before "fixing"
anything here.
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

    rules = ['root ::= "{" ws fields ws "}"']
    rules.append('fields ::= field ("," ws field)*')
    rules.append('field ::= key ws ":" ws value')
    rules.append('key ::= """ [a-zA-Z_][a-zA-Z0-9_]* """')
    rules.append("value ::= (string | number | boolean)")
    rules.append('string ::= """ [^"]* """')
    rules.append('number ::= ("-"? [0-9]+ ("." [0-9]+)?)')
    rules.append('boolean ::= ("true" | "false")')
    rules.append("ws ::= ([ \t\n])*")

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
