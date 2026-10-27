"""Self-test for scripts/ci/check_agent_surfaces.py (repo convention: self-tested).

Covers: real-map parsing, longest-match specificity, ambiguity ties, unowned
fail-closed behavior, a probe sweep asserting every owner is reachable and the
delegation-time exception rows hold, and CLI exit codes. Pure string matching
-- no filesystem traversal, no network.
"""

import importlib.util
import sys
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "check_agent_surfaces.py"
_spec = importlib.util.spec_from_file_location("check_agent_surfaces", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["check_agent_surfaces"] = _mod
_spec.loader.exec_module(_mod)

resolve_owner = _mod.resolve_owner
parse_map = _mod.parse_map
main = _mod.main

_REAL = parse_map()


def _resolve(path: str, surfaces=None):
    return resolve_owner(path, _REAL if surfaces is None else surfaces)


def test_real_map_has_ownership_rows():
    assert len(_REAL) >= 30
    assert all(s.owner.startswith("@") for s in _REAL)
    assert all(s.pattern for s in _REAL)


def test_real_map_probe_paths_resolve_to_expected_owners():
    expected = {
        "AGENTS.md": "@docs-keeper",
        "docs/retrospectives/x.md": "@docs-keeper",
        "src/cohezion/skills/skill_registry.json": "@docs-keeper",
        ".github/workflows/testing-paradigms.yml": "@ci-governance",
        "scripts/ci/check_paradigms.py": "@ci-governance",
        "scripts/hooks/pre-commit.py": "@ci-governance",
        "pyproject.toml": "@ci-governance",
        "tests/property/test_x.py": "@ci-governance",
        "scripts/maintenance/check_status_8001.py": "@ops-fleet",
        "scripts/ops/submit_arc3_when_ready.py": "@ops-fleet",
        "config/crontab.example": "@ops-fleet",
        "src/cohezion/__main__.py": "@ops-fleet",
        "scripts/kaggle/rsna/monitor.py": "@research-daemon",
        "scripts/lanes/lane_a.py": "@research-daemon",
        "src/cohezion/researcher/daily_researcher.py": "@research-daemon",
        "src/cohezion/flume/vae_encoder.py": "@research-daemon",
        "src/cohezion/platform/admission_proxy.py": "@platform-gate",
        "tests/platform/test_admission_proxy.py": "@platform-gate",
        "src/cohezion/inference/fabric.py": "@inference-fabric",
        "src/cohezion/inference/delegation_logger.py": "@inference-fabric",
        "tests/inference/test_fabric.py": "@inference-fabric",
        "src/cohezion/cache/semantic_cache.py": "@inference-fabric",
        "src/cohezion/reliability/semantic_cache.py": "@inference-fabric",
        "tests/unit/test_delegation_logger.py": "@inference-fabric",
        "src/cohezion/swarm/model_pool_manager.py": "@swarm-pool",
        "tests/swarm/test_pool_manager.py": "@swarm-pool",
        "src/cohezion/agi/dream_rsi.py": "@agi-research",
        "src/cohezion/agi/kst_eval.py": "@agi-research",
        "tests/unit/test_dream_rsi.py": "@agi-research",
        "src/cohezion/learning/ouroboros.py": "@agi-research",
        "src/cohezion/compound/compound_health_oracle.py": "@compound-loop",
        "src/cohezion/core/event_bus.py": "@compound-loop",
        "src/cohezion/agents/generated/skill_0_agent.py": "@compound-loop",
        "src/cohezion/universe/triune_engine.py": "@compound-loop",
        "tests/mycelium/generated_test_dummy.py": "@compound-loop",
        "src/cohezion/data_mesh/kanban_bridge.py": "@data-mesh",
        "src/cohezion/persistence/obsidian_mcp.py": "@data-mesh",
        "src/cohezion/knowledge_graph/graphrag_engine.py": "@data-mesh",
        "tests/knowledge_graph/test_graphrag_engine.py": "@data-mesh",
    }
    for path, owner in expected.items():
        got, ties = _resolve(path)
        assert got == owner, f"{path}: expected {owner}, got {got} (ties={ties})"
        assert ties == []


def test_exception_row_beats_baseline_by_specificity():
    surfaces = _mod.Surface
    rows = [
        surfaces("tests/unit/**", "@agi-research", 1),
        surfaces("tests/unit/test_delegation_logger.py", "@inference-fabric", 2),
    ]
    owner, ties = resolve_owner("tests/unit/test_delegation_logger.py", rows)
    assert owner == "@inference-fabric" and ties == []
    owner, ties = resolve_owner("tests/unit/test_other.py", rows)
    assert owner == "@agi-research" and ties == []


def test_specificity_tie_between_owners_is_ambiguous():
    rows = [
        _mod.Surface("src/**/gen_*.py", "@a", 1),
        _mod.Surface("src/xy/gen_*.py", "@b", 2),
    ]
    owner, ties = resolve_owner("src/xy/gen_1.py", rows)
    assert owner is None
    assert {s.owner for s in ties} == {"@a", "@b"}


def test_unowned_path_returns_none_with_no_ties():
    owner, ties = _resolve("definitely/not/mapped/x.py")
    assert owner is None and ties == []


def test_same_owner_tie_is_not_ambiguous():
    rows = [
        _mod.Surface("src/a/**", "@a", 1),
        _mod.Surface("src/a/**", "@a", 2),
    ]
    owner, ties = resolve_owner("src/a/f.py", rows)
    assert owner == "@a" and ties == []


def test_cli_exit_codes_on_real_map():
    assert main(["pyproject.toml", "src/cohezion/agi/dream_rsi.py"]) == 0
    assert main(["no/such/surface.py"]) == 1
    assert main([]) == 2


def test_fnmatch_crosses_slashes_so_globstar_is_transitive():
    # fnmatch '*' matches across '/' -- document the semantics the map relies on.
    owner, _ = _resolve("src/cohezion/inference/deep/nested/module.py")
    assert owner == "@inference-fabric"


def test_self_test_flag_plants_each_defect_and_passes():
    """The meta-gate (scripts/ci/self_test_coverage.py) RUNS every CI gate's --self-test.

    Without the flag this script was the one gate that could not prove it still detects
    anything, which kept the blocking meta-gate red (found 2026-10-27).
    """
    assert main(["--self-test"]) == 0


def test_self_test_is_wired_before_the_gate_in_ci():
    workflow = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "agent-surfaces.yml"
    text = workflow.read_text(encoding="utf-8")
    self_test = text.find("check_agent_surfaces.py --self-test")
    gate = text.find("check_agent_surfaces.py $paths")
    assert self_test != -1, "agent-surfaces.yml never self-tests the checker"
    assert gate != -1, "agent-surfaces.yml never runs the checker"
    assert self_test < gate, "self-test must run before the gate so a broken checker cannot pass"
