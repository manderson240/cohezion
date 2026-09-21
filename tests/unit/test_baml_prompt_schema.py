"""Every BAML function's RENDERED prompt must tell the model the output schema.

Without `{{ ctx.output_format }}` in the prompt, the model is never told the field names or
the enum values, so it answers in prose. Measured 2026-09-21 on DeriveTaskInvariants
(Bonsai-8B-gguf via :13305, 12 synthetic ARC tasks): without the placeholder 0/12 outputs
parsed, with BAML's own parser AND the hand-rolled one; with it 12/12. The existing
test_baml_client.py mocks `_b` wholesale, so no prompt is ever rendered there and it could
not see this. `b.request` renders the real HTTP body offline — no model call is made.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


os.environ.setdefault("BAML_TELEMETRY_DISABLED", "1")

from baml_client import b


REPO = Path(__file__).resolve().parents[2]

# (function name, two args, fields the model must be told about, one enum value if any)
FUNCTIONS = [
    ("RecommendNextStep", ("ctx", "cands"), ["action", "rationale", "risk_level"], "medium"),
    (
        "DeriveTaskInvariants",
        ("task", "in: [[1]] -> out: [[1]]"),
        [
            "grid_dimension_rule",
            "conserved_colors",
            "forbidden_colors",
            "symmetry_detected",
            "description",
        ],
        "rotational_180",
    ),
    (
        "SynthesizeCodeHarness",
        ("spec", "trace"),
        ["harness_name", "precondition_assertions", "python_verifier_code"],
        None,
    ),
    (
        "AuditLeaderboardNextAction",
        ("comp", "snapshot"),
        ["competition_id", "recommended_action", "confidence_score", "reasoning"],
        "hold_for_audit",
    ),
]


def _rendered_prompt(name: str, args: tuple[str, str]) -> str:
    body = getattr(b.request, name)(*args).body.json()
    return "\n".join(m["content"] for m in body["messages"] if isinstance(m["content"], str))


@pytest.mark.parametrize(("name", "args", "fields", "enum_value"), FUNCTIONS)
def test_rendered_prompt_states_the_output_schema(
    name: str, args: tuple[str, str], fields: list[str], enum_value: str | None
) -> None:
    prompt = _rendered_prompt(name, args)
    assert "schema" in prompt.lower(), f"{name}: prompt carries no output schema"
    for field in fields:
        assert f"{field}:" in prompt, f"{name}: model is never told about field {field!r}"
    if enum_value:
        # Enum values appear only via the schema block; the prose never lists them verbatim.
        assert f'"{enum_value}"' in prompt, f"{name}: enum values not given to the model"


def test_every_baml_function_is_covered() -> None:
    """A new function added without a row here would silently escape the check above."""
    source = (REPO / "baml_src" / "cohezion.baml").read_text()
    declared = {
        line.split()[1].split("(")[0]
        for line in source.splitlines()
        if line.startswith("function ")
    }
    assert declared == {row[0] for row in FUNCTIONS}


def test_no_baml_schema_lives_outside_the_generator_root() -> None:
    """`baml-cli generate` reads only baml_src/; a .baml file elsewhere generates nothing.

    Known debt, grandfathered by exact path so a NEW stray file fails immediately: the two
    files under src/cohezion/baml/schemas/ declare 8+ classes that no client ever received.
    Move one into baml_src/ (and regenerate) or delete it, then drop it from this set.
    """
    known_stray = {
        "src/cohezion/baml/schemas/cohezion_core.baml",
        "src/cohezion/baml/schemas/vault_graph.baml",
    }
    stray = {
        p.relative_to(REPO).as_posix()
        for top in ("src", "scripts", "tests", "notebooks")
        for p in (REPO / top).rglob("*.baml")
    }
    assert stray == known_stray


def test_generated_client_embeds_current_baml_src() -> None:
    """baml_client/ must be regenerated whenever baml_src/ changes (`baml-cli generate`)."""
    from baml_client.inlinedbaml import get_baml_files

    embedded = get_baml_files()["cohezion.baml"]
    assert embedded == (REPO / "baml_src" / "cohezion.baml").read_text()
