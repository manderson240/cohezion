"""`@pytest.mark.integration` is an escape hatch out of every blocking test gate; audit it.

Both gates (scripts/ci/automerge_guard.sh, .github/workflows/ci.yml) run the gated dirs with
`-m "not integration"` and run the marked tests only as an ADVISORY step, whose failure is
recorded as a pass (`step_advisory` appends "(advisory)" to GATES_PASSED). So marking a test
`integration` silently removes it from the merge gate. That is legitimate only for tests whose
verdict depends on LIVE services (fleet residency, :13305, kokoro/whisper/sd) -- never as a way
to park a test that is red for a code reason. Adversarial review 2026-09-21.

Rules enforced here:
1. Every integration-marked test in a gated dir must be listed, by node id, in
   INTEGRATION_MARKER_ALLOWLIST (adding one is a reviewed diff to this file).
2. tests/security and tests/reliability may never mark a test integration: those gates hold
   safety contracts, and a live dependency there must be mocked or skipped, not deselected.
3. Module/class-level `pytestmark = ...integration` is refused: it would deselect tests that
   are added later without anyone listing them.
"""

from __future__ import annotations

import ast
from pathlib import Path


TESTS = Path(__file__).resolve().parents[1]
GATED_DIRS = ("unit", "inference", "reliability", "security")
FORBIDDEN_DIRS = ("reliability", "security")

# node id -> why it cannot be deterministic (a live service it asserts on)
INTEGRATION_MARKER_ALLOWLIST: dict[str, str] = {
    "tests/inference/test_extend_availability_local.py::test_live_local_completion_via_registered_endpoint": (
        "live :13305 router must answer locally"
    ),
    "tests/inference/test_fleet_recipe_gate.py::test_get_lemonade_health_live_returns_real_snapshot": (
        "live :13305 health snapshot"
    ),
    "tests/inference/test_fleet_recipe_gate.py::test_route_against_live_omni_with_real_probe": (
        "routes against the live omni router"
    ),
    "tests/inference/test_image_tier.py::test_image_render_256_live": "live sd image model",
    "tests/inference/test_image_tier.py::test_image_render_512_compound_prompt_live": (
        "live sd image model"
    ),
    "tests/inference/test_image_tier.py::test_image_render_batch_n3_live": "live sd image model",
    "tests/inference/test_image_tier.py::test_image_is_alive_live": "live sd image model",
    "tests/inference/test_lemonade_health.py::test_probe_lemonade_live": "live :13305 health",
    "tests/inference/test_lemonade_health.py::test_is_lemonade_alive_live": "live :13305 health",
    "tests/inference/test_p0_resilience.py::TestHealthChecker::test_live_npu_server_healthy": (
        "live NPU server"
    ),
    "tests/inference/test_recipe_constraint_support.py::test_rc1_lanes_are_actually_running": (
        "RC1 canary: fails on an evicted model by design"
    ),
    "tests/inference/test_recipe_constraint_support.py::test_recipe_grammar_enforcement": (
        "live llamacpp/flm lanes enforce a grammar"
    ),
    "tests/inference/test_stt_tier.py::test_stt_transcribe_silence_live": "live whisper model",
    "tests/inference/test_stt_tier.py::test_stt_transcribe_tts_roundtrip_live": (
        "live whisper + kokoro models"
    ),
    "tests/inference/test_stt_tier.py::test_stt_transcribe_verbose_live": "live whisper model",
    "tests/inference/test_stt_tier.py::test_stt_is_alive_live": "live whisper model",
    "tests/inference/test_tts_tier.py::test_tts_default_voice_mp3": "live kokoro model",
    "tests/inference/test_tts_tier.py::test_tts_af_sky_voice": "live kokoro model",
    "tests/inference/test_tts_tier.py::test_tts_wav_format": "live kokoro model",
    "tests/inference/test_tts_tier.py::test_tts_is_alive": "live kokoro model",
}


def _is_integration_mark(node: ast.AST) -> bool:
    """True for `pytest.mark.integration` / `mark.integration` (called or not)."""
    if isinstance(node, ast.Call):
        node = node.func
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "integration"
        and (isinstance(node.value, ast.Attribute) and node.value.attr == "mark")
    )


def _mentions_integration_mark(node: ast.AST) -> bool:
    return any(_is_integration_mark(n) for n in ast.walk(node))


def _scan_body(
    body: list[ast.stmt], node_prefix: str, marked: set[str], blanket: list[str]
) -> None:
    for node in body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
        ):
            if _mentions_integration_mark(node.value):
                blanket.append(f"{node_prefix.split('::')[0]}:{node.lineno}")
        elif isinstance(node, ast.ClassDef):
            if any(_is_integration_mark(d) for d in node.decorator_list):
                blanket.append(f"{node_prefix}::{node.name} (class decorator)")
            _scan_body(node.body, f"{node_prefix}::{node.name}", marked, blanket)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            _is_integration_mark(d) for d in node.decorator_list
        ):
            marked.add(f"{node_prefix}::{node.name}")


def scan(root: Path = TESTS) -> tuple[set[str], list[str]]:
    """Return (marked node ids, blanket-mark locations) under the gated dirs."""
    marked: set[str] = set()
    blanket: list[str] = []
    for sub in GATED_DIRS:
        for path in sorted((root / sub).rglob("*.py")):
            rel = path.relative_to(root.parent).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            _scan_body(tree.body, rel, marked, blanket)
    return marked, blanket


def test_no_blanket_integration_marks_in_gated_dirs():
    _, blanket = scan()
    assert blanket == [], f"blanket integration marks deselect future tests unseen: {blanket}"


def test_security_and_reliability_never_mark_integration():
    marked, _ = scan()
    bad = sorted(m for m in marked if m.split("/")[1] in FORBIDDEN_DIRS)
    assert bad == [], f"safety-contract gates must not deselect tests: {bad}"


def test_every_integration_marked_test_is_allow_listed():
    marked, _ = scan()
    unlisted = sorted(marked - INTEGRATION_MARKER_ALLOWLIST.keys())
    assert unlisted == [], (
        f"integration-marked tests leave the blocking gate; list each with its live-service "
        f"reason in INTEGRATION_MARKER_ALLOWLIST: {unlisted}"
    )


def test_allow_list_has_no_stale_entries():
    """A stale entry would silently pre-approve a future test of the same name."""
    marked, _ = scan()
    assert sorted(INTEGRATION_MARKER_ALLOWLIST.keys() - marked) == []


def test_scanner_detects_a_planted_mark(tmp_path):
    """The audit can fail: a planted security mark, an unlisted unit mark and a pytestmark."""
    for sub in GATED_DIRS:
        (tmp_path / "tests" / sub).mkdir(parents=True)
    (tmp_path / "tests" / "security" / "test_x.py").write_text(
        "import pytest\n\n@pytest.mark.integration\ndef test_a():\n    pass\n"
    )
    (tmp_path / "tests" / "unit" / "test_y.py").write_text(
        "import pytest\npytestmark = [pytest.mark.integration]\n\n"
        "class TestK:\n    @pytest.mark.integration()\n    async def test_b(self):\n        pass\n"
    )
    marked, blanket = scan(tmp_path / "tests")
    assert marked == {
        "tests/security/test_x.py::test_a",
        "tests/unit/test_y.py::TestK::test_b",
    }
    assert blanket == ["tests/unit/test_y.py:2"]
