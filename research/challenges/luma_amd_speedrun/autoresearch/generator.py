"""Submission.py generator with LLM synthesis + template fallback.

Two-tier code generation:
1. LLM synthesis (K-Search pi_code) — novel code from strategy description
2. Template substitution — deterministic parameter-based generation

Falls back to templates if LLM is unavailable or generates invalid code.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from string import Template
from typing import Any

from templates import (
    gemm_cached_template,
    gemm_fused_template,
    gemm_template,
    mla_flash_template,
    mla_template,
    moe_template,
    moe_triton_template,
)


log = logging.getLogger("generator")

# Tracks the source of the last generation (read by driver.py for trajectory)
last_source: str = "template"

TEMPLATES = {
    "moe": moe_template.TEMPLATE,
    "moe_triton": moe_triton_template.TEMPLATE,
    "gemm": gemm_template.TEMPLATE,
    "gemm_cached": gemm_cached_template.TEMPLATE,
    "gemm_fused": gemm_fused_template.TEMPLATE,
    "mla": mla_template.TEMPLATE,
    "mla_flash": mla_flash_template.TEMPLATE,
}

DEFAULTS = {
    "moe": moe_template.DEFAULT_PARAMS,
    "moe_triton": moe_triton_template.DEFAULT_PARAMS,
    "gemm": gemm_template.DEFAULT_PARAMS,
    "gemm_cached": gemm_cached_template.DEFAULT_PARAMS,
    "gemm_fused": gemm_fused_template.DEFAULT_PARAMS,
    "mla": mla_template.DEFAULT_PARAMS,
    "mla_flash": mla_flash_template.DEFAULT_PARAMS,
}


def generate_submission(
    kernel: str,
    parameters: dict[str, Any],
    output_path: Path | None = None,
    strategy: str = "",
    trajectory: list[dict[str, Any]] | None = None,
    use_llm: bool = True,
) -> str:
    """Generate a submission.py, trying LLM synthesis first then templates.

    Args:
        kernel: "moe", "gemm", or "mla"
        parameters: Overrides for template defaults
        output_path: If provided, write the generated code to this file
        strategy: Strategy description for LLM synthesis
        trajectory: Past attempts for LLM context
        use_llm: Whether to attempt LLM synthesis before templates

    Returns:
        Generated Python source code
    """
    global last_source

    # Tier 1: Try LLM synthesis if strategy is provided
    if use_llm and strategy:
        try:
            from code_synthesizer import synthesize_kernel

            code = synthesize_kernel(
                strategy=strategy,
                kernel=kernel,
                trajectory=trajectory,
            )
            if code:
                last_source = "llm"
                log.info(f"Using LLM-synthesized code for {kernel}")
                if output_path:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(code)
                return code
            log.info("LLM synthesis returned None, falling back to template")
        except Exception as e:
            log.warning(f"LLM synthesis failed, falling back to template: {e}")

    last_source = "template"

    # Tier 2: Template-based generation
    if kernel not in TEMPLATES:
        raise ValueError(f"Unknown kernel: {kernel}. Expected: {list(TEMPLATES)}")

    # Merge defaults with overrides
    params = {**DEFAULTS[kernel], **parameters}

    # Convert Python objects to repr strings for template substitution
    subs = {}
    for key, value in params.items():
        if isinstance(value, (dict, list)):
            subs[key] = json.dumps(value)
        elif isinstance(value, bool) or isinstance(value, (int, float)):
            subs[key] = str(value)
        else:
            subs[key] = str(value)

    template = Template(TEMPLATES[kernel])
    code = template.substitute(subs)

    # Check for unresolved template variables (catches typos)
    unresolved = re.findall(r"\$[A-Z_]+", code)
    if unresolved:
        raise ValueError(f"Unresolved template variables: {unresolved}")

    # Validate syntax
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Generated code has syntax error: {e}\n---\n{code}") from e

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code)

    return code


def generate_from_node(
    kernel: str,
    node_parameters: dict[str, Any],
    output_dir: Path,
) -> Path:
    """Generate submission.py from a K-Search node's parameters.

    Returns path to generated file.
    """
    output_path = output_dir / "submission.py"
    generate_submission(kernel, node_parameters, output_path)
    return output_path
