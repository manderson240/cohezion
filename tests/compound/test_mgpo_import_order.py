"""MGPO import-order regression guard (consumption, not declaration).

e9869f425 made ``cohezion.learning`` eagerly import ``vault_neuron_reader``, which imported
``cohezion.core.persistence`` at module scope. That path reaches
``compound.skill_refiner`` while ``vault_neuron_reader`` is still partially initialised, so
skill_refiner's guarded ``from ... import VaultNeuronWriter`` hit ImportError and bound the
name to None. ``SkillRefiner.mgpo_weight`` then returned 1.0 for every skill: RL4 boundary
weighting was silently dead in any process that imported ``cohezion.learning`` first
(pytest does, via tests/conftest.py).

Run in a fresh interpreter because import order is process-global state.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


_SRC = Path(__file__).resolve().parents[2] / "src"


def _probe(first_import: str) -> subprocess.CompletedProcess[str]:
    code = (
        f"import {first_import}\n"
        "import cohezion.compound.skill_refiner as s\n"
        "print('VNW_BOUND' if s.VaultNeuronWriter is not None else 'VNW_NONE')\n"
    )
    env = {**os.environ, "PYTHONPATH": f"{_SRC}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"}
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=300
    )


def test_vault_neuron_writer_bound_when_learning_imported_first() -> None:
    """DISCRIMINATING: with the import cycle restored this prints VNW_NONE."""
    proc = _probe("cohezion.learning")
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "VNW_BOUND" in proc.stdout, "import cycle re-bound VaultNeuronWriter to None"
