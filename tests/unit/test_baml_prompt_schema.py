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
import subprocess
from pathlib import Path

import pytest


os.environ.setdefault("BAML_TELEMETRY_DISABLED", "1")

from baml_client import b


REPO = Path(__file__).resolve().parents[2]

# (function name, two args, TYPED schema lines the rendered prompt must contain).
# Typed lines ("field: type") only come from ctx.output_format — prompt prose that merely names
# a field ("- harness_name: camelCase identifier", SynthesizeCodeHarness pre-fix) cannot
# satisfy them, and they do not depend on the wording of output_format's prefix.
FUNCTIONS = [
    (
        "RecommendNextStep",
        ("ctx", "cands"),
        ["action: string", 'risk_level: "low" or "medium" or "high"'],
    ),
    (
        "DeriveTaskInvariants",
        ("task", "in: [[1]] -> out: [[1]]"),
        [
            "conserved_colors: int[]",
            "forbidden_colors: int[]",
            "description: string",
            'symmetry_detected: "none" or "horizontal"',
        ],
    ),
    (
        "SynthesizeCodeHarness",
        ("spec", "trace"),
        [
            "harness_name: string",
            "precondition_assertions: string[]",
            "estimated_latency_ms: float",
        ],
    ),
    (
        "AuditLeaderboardNextAction",
        ("comp", "snapshot"),
        ["competition_id: string", "confidence_score: float", '"hold_for_audit"'],
    ),
]


def _rendered_prompt(name: str, args: tuple[str, str]) -> str:
    body = getattr(b.request, name)(*args).body.json()
    return "\n".join(m["content"] for m in body["messages"] if isinstance(m["content"], str))


@pytest.mark.parametrize(("name", "args", "typed_lines"), FUNCTIONS)
def test_rendered_prompt_states_the_output_schema(
    name: str, args: tuple[str, str], typed_lines: list[str]
) -> None:
    prompt = _rendered_prompt(name, args)
    for line in typed_lines:
        assert line in prompt, f"{name}: model is not given the typed schema line {line!r}"


@pytest.mark.parametrize(("name", "args"), [(row[0], row[1]) for row in FUNCTIONS])
def test_rendered_prompt_has_a_user_turn(name: str, args: tuple[str, str]) -> None:
    """A prompt with no role marker renders as a lone `system` message. Qwen-family chat
    templates raise "No user query found in messages." on that, so every call to the pinned
    qwen3-4b-FLM lane failed and HybridCohezion fell through to the metered cloud leg.
    Measured 2026-09-21 on FLM/NPU qwen3.5:4b: system-only 0/12 (HTTP error in 0.1 s);
    with `{{ _.role("user") }}` 8/12 parsed inside the 60 s client timeout."""
    roles = [m["role"] for m in getattr(b.request, name)(*args).body.json()["messages"]]
    assert "user" in roles, f"{name}: rendered roles {roles} contain no user turn"


def _baml_sources() -> dict[str, str]:
    return {p.name: p.read_text() for p in sorted((REPO / "baml_src").glob("*.baml"))}


def test_every_baml_function_is_covered() -> None:
    """A new function (in ANY baml_src file) without a row here would escape the check above."""
    declared = {
        stripped.split()[1].split("(")[0]
        for source in _baml_sources().values()
        for stripped in (line.strip() for line in source.splitlines())
        if stripped.startswith("function ")
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
    # Tracked files only: an rglob would descend into .claude/worktrees/* on the main
    # checkout and report other worktrees' copies of these same files.
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.baml"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    stray = {p for p in tracked.split("\0") if p and not p.startswith("baml_src/")}
    assert stray == known_stray


def test_generated_client_embeds_current_baml_src() -> None:
    """baml_client/ must be regenerated whenever baml_src/ changes (`baml-cli generate`)."""
    from baml_client.inlinedbaml import get_baml_files

    assert get_baml_files() == _baml_sources()
