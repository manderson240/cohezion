"""Tests for Compound Engineering Flywheel: AutoHarness Invariant Factory and Retrospective Skill Extractor.
"""

import ast
from pathlib import Path
import pytest

from cohezion.compound.invariant_factory import (
    AutoHarnessInvariantFactory,
    InvariantSeverity,
    MonotonicAttemptInvariant,
    SoftKolmogorovMonotonicityInvariant,
    TautomerCanonicalInChIKeyInvariant,
    ZobristCycleInvariant,
    BudgetLimitInvariant,
)
from cohezion.compound.retrospective_skill_extractor import (
    RetrospectiveSkillExtractor,
    ExtractedSkillSpec,
)
from cohezion.compound.universal_competition_harness import (
    UniversalCompetitionHarness,
    CompetitionManifest,
    SubmissionMode,
)


def test_autoharness_monotonic_attempt_invariant():
    # Bad code: overwriting attempt_1 with heuristics without checking attempt_2 or dummy
    bad_code = """
attempt_1 = dsl_solve(task)
"""
    res = AutoHarnessInvariantFactory.compile_and_verify(
        bad_code, "arc-prize-2026-arc-agi-2"
    )
    assert not res.passed
    assert any("attempt_1" in v.message for v in res.violations)

    # Good code: non-destructive attempt_2 injection
    good_code = """
if attempt_1 == [[0]]:
    attempt_1 = dsl_solve(task)
else:
    attempt_2 = dsl_solve(task)
"""
    res = AutoHarnessInvariantFactory.compile_and_verify(
        good_code, "arc-prize-2026-arc-agi-2"
    )
    assert res.passed
    assert not res.has_critical_violations


def test_autoharness_kolmogorov_monotonicity_invariant():
    inv = SoftKolmogorovMonotonicityInvariant()
    
    # Runtime violation check
    bad_runtime = {"Abnormal": 0.40, "ACL": 0.95, "Meniscus": 0.80}
    violations = inv.verify_runtime(bad_runtime, {})
    assert len(violations) > 0
    assert violations[0].severity == InvariantSeverity.P0_CRITICAL

    # Runtime compliant check
    good_runtime = {"Abnormal": 0.95, "ACL": 0.95, "Meniscus": 0.80}
    violations = inv.verify_runtime(good_runtime, {})
    assert len(violations) == 0


def test_autoharness_casmi26_tautomer_inchikey_invariant():
    bad_code = """
w_ppm = 0.15
sigma_ppm = 2.5
"""
    res = AutoHarnessInvariantFactory.compile_and_verify(
        bad_code, "enveda-CASMI26-molecule-id-mass-spectra"
    )
    assert not res.passed
    assert any("Gaussian mass penalty" in v.message for v in res.violations)


def test_retrospective_skill_extractor_lifecycle(tmp_path):
    extractor = RetrospectiveSkillExtractor(workspace_root=tmp_path)
    (tmp_path / "src" / "cohezion" / "skills").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "cohezion" / "knowledge_graph").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "cohezion" / "knowledge_graph" / "KEY_LEARNINGS.md").write_text(
        "# KEY LEARNINGS\n\n## Learning 521: Prior Learning\nPrior notes.\n", encoding="utf-8"
    )

    sample_code = """
def copula_rank_align(probs, condition_weights):
    '''Aligns heterogeneous probabilities using quantile rank normalization.'''
    import numpy as np
    return np.clip(probs, 1e-6, 1.0 - 1e-6)
"""
    spec = extractor.extract_from_python_code(
        code_content=sample_code,
        name="TEST_COPULA_ALIGN",
        domain_expertise="Quantile rank calibration and gradient bounding under ROC-AUC.",
        source_artifact="test_copula.py",
    )
    result = extractor.extract_and_register(spec)
    assert result["status"] == "SUCCESS"
    assert result["learning_id"] == 522
    assert Path(result["skill_path"]).exists()

    # Verify skill markdown structure
    skill_text = Path(result["skill_path"]).read_text()
    assert "# SKILL: TEST_COPULA_ALIGN_PRIME" in skill_text
    assert "## DOMAIN EXPERTISE" in skill_text
    assert "## KEY TEXTS & CONCEPTS" in skill_text
    assert "## INSTRUCTION" in skill_text
    assert "## VERSION" in skill_text

    # Verify KEY_LEARNINGS update
    learnings_text = (tmp_path / "src" / "cohezion" / "knowledge_graph" / "KEY_LEARNINGS.md").read_text()
    assert "## Learning 522: Test Copula Align" in learnings_text
    assert "12D State Vector" in learnings_text
