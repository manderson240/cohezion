"""Unit tests for ARIA Kaggle Dispatch Guard (arXiv:2610.20780)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cohezion.aria.kaggle_guard import (
    KaggleDispatchGuard,
    KaggleJob,
    VerifierHistory,
)


@pytest.fixture
def clean_script_path(tmp_path: Path) -> Path:
    p = tmp_path / "solution.py"
    code = (
        "import pandas as pd\n"
        "df = pd.DataFrame({'id': [1, 2], 'pred': [0.8, 0.2]})\n"
        "df.to_csv('submission.csv', index=False)\n"
    )
    p.write_text(code, encoding="utf-8")
    return p


@pytest.fixture
def clean_notebook_path(tmp_path: Path) -> Path:
    p = tmp_path / "notebook.ipynb"
    nb = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "sub = pd.DataFrame({'id': [1, 2], 'target': [1, 0]})\n",
                    "sub.to_csv('submission.csv', index=False)\n",
                ],
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 2,
    }
    p.write_text(json.dumps(nb), encoding="utf-8")
    return p


@pytest.fixture
def defect_notebook_path(tmp_path: Path) -> Path:
    """Notebook without export and with unhandled NaN."""
    p = tmp_path / "defect.ipynb"
    nb = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import numpy as np\n",
                    "import pandas as pd\n",
                    "sub = pd.DataFrame({'id': [1, 2], 'score': [0.5, np.nan]})\n",
                ],
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 2,
    }
    p.write_text(json.dumps(nb), encoding="utf-8")
    return p


@pytest.fixture
def syntax_error_path(tmp_path: Path) -> Path:
    p = tmp_path / "broken.py"
    p.write_text("def broken_syntax(:\n    pass\n", encoding="utf-8")
    return p


def test_guard_pass_on_clean_script(clean_script_path: Path) -> None:
    guard = KaggleDispatchGuard(enforce=True)
    job = KaggleJob(
        comp_slug="rsna-knee-abnormality-detection",
        slot_num=1,
        code_path=clean_script_path,
        target_filename="submission.csv",
    )
    decision = guard.evaluate(job)
    assert decision.action == "PASS"
    assert decision.confidence == 1.0
    assert decision.severity == 0.0
    assert len(decision.reasons) > 0


def test_guard_pass_on_clean_notebook(clean_notebook_path: Path) -> None:
    guard = KaggleDispatchGuard(enforce=True)
    job = KaggleJob(
        comp_slug="arc-prize-2026-arc-agi-3",
        slot_num=1,
        code_path=clean_notebook_path,
        target_filename="submission.csv",
    )
    decision = guard.evaluate(job)
    assert decision.action == "PASS"
    assert decision.confidence == 1.0


def test_guard_amends_defect_notebook(defect_notebook_path: Path) -> None:
    guard = KaggleDispatchGuard(enforce=True)
    job = KaggleJob(
        comp_slug="enveda-CASMI26-molecule-id-mass-spectra",
        slot_num=2,
        code_path=defect_notebook_path,
        target_filename="submission.csv",
    )
    decision = guard.evaluate(job)
    assert decision.action == "AMEND"
    assert decision.amended_artifact is not None
    assert decision.amended_artifact.ast_valid is True
    # Verify amendment added export and NaN sanitation
    amended_code = "\n".join(decision.amended_artifact.code_cells)
    assert "submission.csv" in amended_code
    assert "fillna" in amended_code


def test_guard_rollback_on_syntax_error_with_champion(
    syntax_error_path: Path, clean_script_path: Path
) -> None:
    guard = KaggleDispatchGuard(enforce=True)
    job = KaggleJob(
        comp_slug="name-that-llm",
        slot_num=3,
        code_path=syntax_error_path,
        target_filename="submission.csv",
    )
    decision = guard.evaluate(job, last_known_good_path=clean_script_path)
    assert decision.action == "ROLLBACK"
    assert decision.rollback_target == clean_script_path
    assert decision.severity == 0.85


def test_guard_blocks_when_no_rollback_available(syntax_error_path: Path) -> None:
    guard = KaggleDispatchGuard(enforce=True)
    job = KaggleJob(
        comp_slug="name-that-llm",
        slot_num=3,
        code_path=syntax_error_path,
        target_filename="submission.csv",
    )
    decision = guard.evaluate(job, last_known_good_path=None)
    assert decision.action == "BLOCK"
    assert decision.confidence == 1.0
    assert decision.severity == 1.0


def test_guard_verifier_regression_detection(clean_script_path: Path, tmp_path: Path) -> None:
    champion_path = tmp_path / "champ.py"
    champion_path.write_text("print('champion')\n", encoding="utf-8")

    guard = KaggleDispatchGuard(enforce=True, score_drop_tolerance=0.10)
    job = KaggleJob(
        comp_slug="rsna-knee-abnormality-detection",
        slot_num=2,
        code_path=clean_script_path,
        target_filename="submission.csv",
    )
    # Median is ~0.95, current drops to 0.70 (drop of 0.25 > 0.10)
    history = VerifierHistory(
        scores=[0.95, 0.96, 0.94],
        champion_score=0.96,
        min_score_floor=0.50,
        max_acceptable_drop=0.10,
    )
    decision = guard.evaluate(
        job,
        current_verifier_score=0.70,
        history=history,
        last_known_good_path=champion_path,
    )
    assert decision.action == "ROLLBACK"
    assert "Severe verifier score degradation" in decision.reasons[0] or any(
        "Severe verifier score degradation" in r for r in decision.reasons
    )


def test_guard_shadow_mode_overrides_block(syntax_error_path: Path) -> None:
    guard = KaggleDispatchGuard(enforce=False)  # Shadow mode
    job = KaggleJob(
        comp_slug="gemma-4-developer-agent",
        slot_num=1,
        code_path=syntax_error_path,
        target_filename="submission.csv",
    )
    decision = guard.evaluate(job)
    assert decision.action == "PASS"
    assert any("[SHADOW OVERRIDE]" in r for r in decision.reasons)
