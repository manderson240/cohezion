"""Deterministic structured-output validator for execute_task().

Implements the "validate → inject exact error → retry" pattern from:
  "What to do when reflection won't fix your AI agent's output"
  (freecodecamp.org, 2026-06)

A model that can't generate a valid constraint also can't detect that it's
missing — LLM-on-LLM critique fails for hard constraints (JSON schema, types).
Use deterministic validators and inject the exact error text instead.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_FENCE_PREFIX = re.compile(r"^```(?:json)?\n?", re.MULTILINE)
_FENCE_SUFFIX = re.compile(r"\n?```$", re.MULTILINE)


def validate_structured_output(
    output: str,
    schema: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    """Check that output is valid JSON and optionally matches a JSON Schema.

    Returns:
        (True, None) on success.
        (False, error_message) on failure — error_message is injected verbatim
        into the next prompt so the model sees the exact constraint it violated.
    """
    text = _FENCE_PREFIX.sub("", output.strip())
    text = _FENCE_SUFFIX.sub("", text.strip()).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = text[:200].replace("\n", "\\n")
        return False, f"JSON parse error at position {exc.pos}: {exc.msg}. Got: {snippet!r}"

    if schema is not None:
        try:
            import jsonschema  # optional dep — nested so ValidationError is always bound

            try:
                jsonschema.validate(parsed, schema)
            except jsonschema.ValidationError as exc:
                path = " → ".join(str(p) for p in exc.absolute_path) or "(root)"
                return False, f"Schema validation failed at {path!r}: {exc.message}"
        except ImportError:
            pass  # jsonschema not installed — JSON parse check was sufficient

    return True, None


def execute_with_output_validation(
    execute_fn: Callable[[str], tuple[str, dict]],
    guidance: str,
    output_schema: dict[str, Any] | None = None,
    max_retries: int = _MAX_RETRIES,
) -> tuple[str, dict, str | None]:
    """Run execute_fn with deterministic output validation and retry on failure.

    On each failed validation attempt the exact error message is appended to
    ``guidance`` so the model receives the precise constraint it violated,
    not a vague "please try again" instruction.

    Args:
        execute_fn: Callable ``(guidance) → (output, metrics)``.
        guidance: Initial guidance string passed to execute_fn.
        output_schema: Optional JSON Schema dict. When supplied, output must
            parse as JSON and validate against this schema. When None, no
            validation is performed.
        max_retries: Maximum number of execute_fn calls (including first).

    Returns:
        ``(output, metrics, validation_error)`` where ``validation_error`` is
        None when output passed validation (or no schema was given), or the
        last error message string when all retries were exhausted.

    Raises:
        Any exception raised by execute_fn propagates unchanged so the
        caller's existing error handling applies.
    """
    retry_guidance = guidance
    output = ""
    metrics: dict[str, Any] = {}
    last_error: str | None = None

    for attempt in range(max_retries):
        output, metrics = execute_fn(retry_guidance)

        if output_schema is None:
            return output, metrics, None

        valid, error = validate_structured_output(output, output_schema)
        if valid:
            if attempt > 0:
                logger.info(
                    "output_validator: structured output validated after %d retries", attempt
                )
                metrics["output_validation_retries"] = attempt
            return output, metrics, None

        last_error = error
        logger.warning(
            "output_validator: attempt %d/%d failed: %s",
            attempt + 1,
            max_retries,
            error,
        )

        if attempt < max_retries - 1:
            retry_guidance = (
                guidance
                + f"\n\n[VALIDATION ERROR — attempt {attempt + 1}/{max_retries}]: {error}\n"
                "Correct the error above. Return only valid JSON that satisfies the schema."
            )

    logger.error(
        "output_validator: all %d attempts exhausted. Last error: %s", max_retries, last_error
    )
    metrics["output_validation_failed"] = True
    metrics["output_validation_error"] = last_error
    metrics["output_validation_retries"] = max_retries
    return output, metrics, last_error
