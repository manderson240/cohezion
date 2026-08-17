"""Unit tests for Transformative Pillars A, B, C, D."""

import asyncio
import tempfile
from pathlib import Path

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.agi.zkfv_compiler import ZKFVCompiler
from cohezion.physics.poincare_manifold import PoincareManifoldTracker
from scripts.lanes.nightly_swarm_daemon import NightlySwarmDaemon
from scripts.ops.visual_cockpit import generate_html_cockpit, render_terminal_cockpit


def test_pillar_a_autoharness_policy() -> None:
    policy = AutoHarnessPolicy()
    valid_code = "def foo(a: int) -> int:\n    return a + 1\n"
    res = policy.verify_code(valid_code)
    assert res.valid is True
    assert res.latency_ms < 10.0
    assert res.ast_nodes_scanned > 0

    invalid_code = "def bar():\n    eval('1+1')\n"
    res_bad = policy.verify_code(invalid_code)
    assert res_bad.valid is False
    assert len(res_bad.violations) > 0


def test_pillar_a_zkfv_compiler() -> None:
    zkfv = ZKFVCompiler()
    code = "def test_func() -> None:\n    pass\n"
    proof = zkfv.compile_proof(code)
    assert proof.verified is True
    assert len(proof.code_hash) == 64
    assert len(proof.polynomial_signature) == 64


def test_pillar_b_poincare_manifold() -> None:
    tracker = PoincareManifoldTracker(dimension=64)
    v1 = tracker.project_and_track("s1", [0.1] * 64, timestamp=1.0)
    v2 = tracker.project_and_track("s2", [0.2] * 64, timestamp=2.0)

    assert v1.dim == 64
    assert v2.dim == 64
    drift = tracker.get_trajectory_drift()
    assert drift > 0


def test_pillar_c_nightly_swarm_daemon() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        daemon = NightlySwarmDaemon(repo_root=Path(tmpdir))
        # Create dummy python file
        src_dir = Path(tmpdir) / "src" / "cohezion"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "dummy.py").write_text(
            "def hello() -> str:\n    return 'hi'\n", encoding="utf-8"
        )

        summary = asyncio.run(daemon.run_nightly_cycle(max_files=1))
        assert summary["files_inspected"] == 1
        assert summary["verified_count"] == 1


def test_pillar_d_visual_cockpit() -> None:
    # Test terminal cockpit render
    render_terminal_cockpit()

    # Test HTML dashboard generation
    with tempfile.TemporaryDirectory() as tmpdir:
        out_html = Path(tmpdir) / "test_cockpit.html"
        generate_html_cockpit(out_html)
        assert out_html.exists()
        assert "Cohezion Swarm Visual Cockpit" in out_html.read_text(encoding="utf-8")
