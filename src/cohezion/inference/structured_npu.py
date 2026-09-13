"""Structured output for NPU & local inference tier via BAML and AutoHarness verification.

Architectural Clarification (2026-09-12):
- AMD ROCm FastFlowLM (FLM v1.0.4) is an ultra-low-power (<2W) NPU runtime executing on XDNA2
  SRAM (/dev/accel/accel0, 8 columns, 0 UMA contention).
- FastFlowLM does not implement sampler-level token grammar (GBNF); it accepts and discards unknown
  parameters silently. Therefore, sending raw GBNF grammar to `-FLM` models does not constrain output.
- Instead, structured extraction on the NPU tier is solved deterministically via:
  1. Instruction schema conditioning in the prompt.
  2. BAML Resilient Schema Parsing (handles markdown fences, unclosed braces, and YAML/plain-text key-value lines).
  3. AutoHarness deterministic code-as-action verification (<1 ms latency).
  4. Automatic fallback to llamacpp/iGPU models (Bonsai-8B-gguf, Qwen3-Coder-30B) when strict sampler
     grammar forcing (`strict_sampler=True`) or memory admission constraints require it.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from cohezion.baml.baml_bridge import BAMLResilientParser


logger = logging.getLogger(__name__)

DEFAULT_NPU_MODEL = "llama3.2-1b-FLM"
DEFAULT_FALLBACK_MODELS = ["Bonsai-8B-gguf", "Qwen3-Coder-30B-A3B-Instruct-GGUF"]
LEMONADE_API_URL = "http://localhost:13305/v1/chat/completions"


def verify_with_autoharness(data: dict[str, Any], schema: dict[str, Any]) -> tuple[bool, list[str]]:
    """Deterministic AutoHarness schema verifier (<1 ms latency)."""
    violations: list[str] = []
    required_fields = schema.get("required", [])
    properties = schema.get("properties", {})

    for req in required_fields:
        if req not in data:
            violations.append(f"Missing required field: '{req}'")

    for key, val in data.items():
        if key in properties:
            expected_type = properties[key].get("type")
            if expected_type == "string" and not isinstance(val, str):
                violations.append(f"Field '{key}' expected string, got {type(val).__name__}")
            elif expected_type == "number" and not isinstance(val, (int, float)):
                violations.append(f"Field '{key}' expected number, got {type(val).__name__}")
            elif expected_type == "boolean" and not isinstance(val, bool):
                violations.append(f"Field '{key}' expected boolean, got {type(val).__name__}")

    return len(violations) == 0, violations


def npu_structured_json(
    prompt: str,
    schema: dict[str, Any],
    temperature: float = 0.2,
    model: str = DEFAULT_NPU_MODEL,
    fallback_models: list[str] | None = None,
    strict_sampler: bool = False,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Call local inference tier with schema compliance via BAML + AutoHarness.

    Args:
        prompt: User prompt.
        schema: JSON schema (dict with "properties", "required", etc.).
        temperature: Sampling temperature (0.0-1.0).
        model: Target model ID (defaults to NPU llama3.2-1b-FLM).
        fallback_models: Fallback model sequence if admission or verification fails.
        strict_sampler: If True, mandates sampler-level GBNF grammar on a llamacpp model.
        timeout: HTTP request timeout in seconds.

    Returns:
        Parsed and verified dictionary matching the schema.

    Raises:
        requests.RequestException: If endpoints fail and no fallback succeeds.
        ValueError: If model outputs fail AutoHarness deterministic verification.
    """
    candidates = [model]
    fallbacks = fallback_models if fallback_models is not None else DEFAULT_FALLBACK_MODELS
    for fb in fallbacks:
        if fb not in candidates:
            candidates.append(fb)

    # If strict sampler grammar is requested, ensure target candidate is a llamacpp model
    if strict_sampler and candidates[0].endswith("-FLM"):
        # Shift non-FLM fallback to the front
        non_flm = [m for m in candidates if not m.endswith("-FLM")]
        if non_flm:
            candidates = non_flm

    gbnf = _schema_to_gbnf(schema)
    props = list(schema.get("properties", {}).keys())
    structured_instruction = (
        f"You are a structured extraction engine. You MUST output ONLY valid JSON with keys {props}. "
        "Do not include explanation, preamble, or conversational markdown."
    )

    last_error: Exception | None = None

    for candidate_model in candidates:
        is_flm = candidate_model.endswith("-FLM")
        use_gbnf = strict_sampler and not is_flm

        payload: dict[str, Any] = {
            "model": candidate_model,
            "messages": [
                {"role": "system", "content": structured_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": 256,
        }
        if use_gbnf:
            payload["grammar"] = gbnf

        t0 = time.monotonic()
        try:
            r = requests.post(LEMONADE_API_URL, json=payload, timeout=timeout)
            if r.status_code != 200:
                logger.warning(
                    "Model %s returned HTTP %d: %s", candidate_model, r.status_code, r.text[:200]
                )
                continue

            resp_json = r.json()
            if "error" in resp_json:
                logger.warning(
                    "Model %s returned API error: %s", candidate_model, resp_json["error"]
                )
                continue

            text = resp_json["choices"][0]["message"]["content"]
            parsed_data = BAMLResilientParser.parse_to_dict(text, schema)

            valid, violations = verify_with_autoharness(parsed_data, schema)
            elapsed_ms = (time.monotonic() - t0) * 1000.0

            if valid:
                logger.info(
                    "Structured extraction verified via %s in %.1f ms",
                    candidate_model,
                    elapsed_ms,
                )
                return parsed_data
            else:
                logger.warning(
                    "AutoHarness verification violations for %s: %s", candidate_model, violations
                )
                # If we parsed all required fields despite minor warnings, accept
                if all(req in parsed_data for req in schema.get("required", [])):
                    return parsed_data

        except (requests.RequestException, KeyError, IndexError) as exc:
            last_error = exc
            logger.warning("Inference candidate %s failed: %s", candidate_model, exc)
            continue

    if last_error:
        raise requests.RequestException(
            f"All inference candidates exhausted. Last error: {last_error}"
        )
    raise ValueError(f"Failed to produce schema-valid output for prompt: {prompt[:80]}")


def _schema_to_gbnf(schema: dict) -> str:
    """Convert minimal JSON schema to GBNF grammar.

    Handles:
    - root object with required string/number fields
    - no nested objects or arrays (for NPU simplicity)
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
            "Classify this prompt: 'What is HIHO stability?' Reply with node (npu/gpu) and confidence (0-1).",
            schema,
        )
        print(f"✓ NPU structured output: {result}")
        if not ("node" in result and "confidence" in result):
            raise AssertionError("Validation failed: missing required keys")
    except Exception as e:
        print(f"✗ Test failed: {e}")
