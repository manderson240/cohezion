"""hardcoded_model_scan: catches frozen model defaults, ignores tables, and is gated."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_PATH = Path(__file__).resolve().parents[2] / "scripts/ci/hardcoded_model_scan.py"
_spec = importlib.util.spec_from_file_location("hardcoded_model_scan", _PATH)
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)  # type: ignore[union-attr]


def test_flags_module_constant_and_parameter_default() -> None:
    src = 'DEV_MODEL = "Gemma-4-26B-A4B-it-GGUF"\ndef f(model_id="llama3.2-1b-FLM"):\n    pass\n'
    assert scan.findings_in(src, "m.py") == ["m.py:DEV_MODEL", "m.py:f(model_id)"]


def test_ignores_tables_roles_and_none_defaults() -> None:
    src = (
        'MODEL_FOOTPRINT_GB = {"Gemma-4-26B-A4B-it-GGUF": 18.1}\n'
        'ROLE = "interactive"\nLABEL = "Gemma-4-26B-A4B-it-GGUF"\n'
        "def f(model=None):\n    pass\n"
    )
    assert scan.findings_in(src, "m.py") == []


def test_live_tree_has_no_new_findings() -> None:
    assert set(scan.scan()) <= scan.baseline()


def test_scan_is_wired_into_both_gates() -> None:
    root = Path(__file__).resolve().parents[2]
    for gate in ("scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"):
        text = (root / gate).read_text()
        assert "hardcoded_model_scan.py --self-test" in text, gate
        assert "hardcoded_model_scan.py\n" in text, gate
