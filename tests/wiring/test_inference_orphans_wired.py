"""Discriminating identity tests: inference orphan modules wired round-5."""

from cohezion.inference import AntiSycophancyGuard as pkg_asg
from cohezion.inference import CompoundEngineeringAutoHarness as pkg_ceah
from cohezion.inference import ContextEngineer as pkg_ce
from cohezion.inference import EvaluationHarness as pkg_eh
from cohezion.inference import HardwareTelemetry as pkg_ht
from cohezion.inference import StrixHaloOrchestrator as pkg_sho
from cohezion.inference import TransitionController as pkg_tc
from cohezion.inference import build_triune_orchestrator as pkg_bto
from cohezion.inference import check_ram as pkg_check_ram
from cohezion.inference import higuchi_fd as pkg_hfd
from cohezion.inference.anti_sycophancy import AntiSycophancyGuard as src_asg
from cohezion.inference.autoharness_ce import (
    CompoundEngineeringAutoHarness as src_ceah,
)
from cohezion.inference.context_engineering import ContextEngineer as src_ce
from cohezion.inference.evaluation_harness import EvaluationHarness as src_eh
from cohezion.inference.fractal_metrics import higuchi_fd as src_hfd
from cohezion.inference.hardware_telemetry import HardwareTelemetry as src_ht
from cohezion.inference.oom_guard import check_ram as src_check_ram
from cohezion.inference.orchestrator_autoharness import (
    StrixHaloOrchestrator as src_sho,
)
from cohezion.inference.transition_controller import (
    TransitionController as src_tc,
)
from cohezion.inference.triune_orchestrator import (
    build_triune_orchestrator as src_bto,
)


def test_anti_sycophancy_guard_is_same():
    assert pkg_asg is src_asg


def test_compound_autoharness_is_same():
    assert pkg_ceah is src_ceah


def test_context_engineer_is_same():
    assert pkg_ce is src_ce


def test_evaluation_harness_is_same():
    assert pkg_eh is src_eh


def test_higuchi_fd_is_same():
    assert pkg_hfd is src_hfd


def test_hardware_telemetry_is_same():
    assert pkg_ht is src_ht


def test_check_ram_is_same():
    assert pkg_check_ram is src_check_ram


def test_strix_halo_orchestrator_is_same():
    assert pkg_sho is src_sho


def test_transition_controller_is_same():
    assert pkg_tc is src_tc


def test_build_triune_orchestrator_is_same():
    assert pkg_bto is src_bto


def test_higuchi_fd_discriminating():
    """higuchi_fd on a monotone sequence must give FD < 1.3 (CC1 invariant)."""
    trend = [float(i) for i in range(50)]
    fd = src_hfd(trend)
    assert fd < 1.3, f"Monotone trend should have low FD, got {fd}"


def test_transition_controller_markov():
    """TransitionController.is_valid and detect_stuck_loops use the matrix correctly.

    Discriminating: a controller built with A→B,B→A must accept A→B but reject A→C.
    If is_valid were always True, the second assertion would fail.
    """
    from cohezion.inference.transition_controller import detect_stuck_loops

    tc = src_tc(matrix={"A": ["B"], "B": ["A", "C"], "C": []})
    assert tc.is_valid("A", "B"), "A→B is in the matrix"
    assert not tc.is_valid("A", "C"), "A→C is NOT in the matrix"

    stuck = detect_stuck_loops(["X", "X", "X", "X"], threshold=3)
    assert "X" in stuck


def test_oom_guard_returns_tuple():
    """check_ram must return (bool, float) — discriminating against a no-op stub."""
    ok, free_gb = src_check_ram(min_free_gb=0.0)
    assert isinstance(ok, bool)
    assert isinstance(free_gb, float)
    assert free_gb >= 0.0
