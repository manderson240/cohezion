"""Tests for scripts/ci/producer_consumer_audit.py (Verification Depth Seam Audit).

Validates:
1. Self-test capability (falsifiability: reliably goes RED on dormant/hollow seams and GREEN on live repo).
2. Live repo execution (all 10 architectural and hardware seams pass with zero hollow seams).
3. Falsifiability: synthetic missing producer drops count below floor -> goes RED.
4. Falsifiability: synthetic missing consumer drops count below floor -> goes RED.
5. Markdown report formatting and coverage.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# Load by FILE PATH, not by bare module name. Two files share the basename
# `producer_consumer_audit.py` (scripts/ and scripts/ci/); other tests in this
# directory insert `scripts/` at sys.path[0], so a bare import here resolved to
# the WRONG file whenever they were collected first (ImportError: AUDIT_PAIRS),
# aborting collection of the whole suite.
_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "producer_consumer_audit.py"
_MODULE_NAME = "ci_producer_consumer_audit"
_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_pca = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = _pca  # dataclasses resolve cls.__module__ via sys.modules
_spec.loader.exec_module(_pca)

AUDIT_PAIRS = _pca.AUDIT_PAIRS
AuditPair = _pca.AuditPair
execute_audit = _pca.execute_audit
format_markdown_report = _pca.format_markdown_report
run_self_test = _pca.run_self_test


def test_producer_consumer_audit_self_test() -> None:
    """Proves the audit gate's self-test passes cleanly."""
    assert run_self_test() == 0


def test_producer_consumer_audit_live_repo() -> None:
    """Proves all 10 architectural and hardware seams have live producers and consumers."""
    results = execute_audit(pairs=AUDIT_PAIRS)
    assert len(results) == len(AUDIT_PAIRS)
    assert len(results) >= 10

    failed = [r for r in results if not r.passed]
    assert not failed, f"Detected hollow seams on live repo: {[f.name for f in failed]}"

    # Verify each result has non-zero producer and consumer matches
    for r in results:
        assert r.producers_found >= r.expected_min_producers
        assert r.consumers_found >= r.expected_min_consumers
        assert r.amd_skill != ""
        assert r.hardware_lane in {"npu", "igpu", "cpu", "cloud", "substrate", "architecture"}


def test_producer_consumer_audit_falsifiable_on_missing_consumer() -> None:
    """Proves that a producer without a consumer fails closed."""
    broken_pair = AuditPair(
        name="Counterfactual Hollow Seam",
        producer="Real Producer",
        producer_pattern=r"def npu_structured_json\(",
        consumer="Non-Existent Consumer",
        consumer_pattern=r"MISSING_GHOST_CONSUMER_TOKEN_99999",
        amd_skill="FASTFLOWLM_PRIME",
        hardware_lane="npu",
        expected_min_producers=1,
        expected_min_consumers=1,
    )

    results = execute_audit(pairs=[broken_pair])
    assert len(results) == 1
    assert not results[0].passed
    assert any(
        "Consumer count (0) < minimum required floor" in reason
        for reason in results[0].failure_reasons
    )


def test_producer_consumer_audit_falsifiable_on_missing_producer() -> None:
    """Proves that an absent producer fails closed."""
    broken_pair = AuditPair(
        name="Counterfactual Dormant Producer Seam",
        producer="Ghost Producer",
        producer_pattern=r"MISSING_GHOST_PRODUCER_TOKEN_88888",
        consumer="Real Consumer",
        consumer_pattern=r"BAMLResilientParser",
        amd_skill="FASTFLOWLM_PRIME",
        hardware_lane="npu",
        expected_min_producers=1,
        expected_min_consumers=1,
    )

    results = execute_audit(pairs=[broken_pair])
    assert len(results) == 1
    assert not results[0].passed
    assert any(
        "Producer count (0) < minimum required floor" in reason
        for reason in results[0].failure_reasons
    )


def test_producer_consumer_audit_markdown_report() -> None:
    """Proves markdown report generation formats all seams and verification badges."""
    results = execute_audit(pairs=AUDIT_PAIRS)
    report = format_markdown_report(results)

    assert "# Cohezion Producer-Consumer Architectural & Hardware Seam Audit" in report
    assert "✅ 100% VERIFIED — ZERO HOLLOW SEAMS" in report
    assert "FASTFLOWLM_PRIME" in report
    assert "AMD_GEMM_MXFP4_PRIME" in report
    assert "VENTRAL_HIPPOCAMPUS_CIRCUITS_PRIME" in report
    for pair in AUDIT_PAIRS:
        assert pair.name in report
