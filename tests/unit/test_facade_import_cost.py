"""Import-cost and import-side-effect budgets for lazily-loaded package facades.

The eager package ``__init__`` files (``contextlib.suppress(Exception)`` re-export blocks) made
importing almost any leaf module load ~500 cohezion modules plus torch. The facades for ``core``,
``compound`` and ``reliability`` are now PEP 562 lazy. These budgets fail if an eager facade creeps
back. See docs/audits/DYNAMIC_MODULARITY_AUDIT_2026-09-24.md (R1, R2).

Each probe runs in a FRESH interpreter: the test process itself has long since imported everything.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SRC = Path(__file__).resolve().parents[2] / "src"

_PROBE = r"""
import importlib, json, logging, os, sys
before = set(os.listdir("."))
importlib.import_module(sys.argv[1])
print(json.dumps({
    "n_cohezion": sum(1 for m in sys.modules if m.startswith("cohezion")),
    "torch": "torch" in sys.modules,
    "root_handlers": len(logging.getLogger().handlers),
    "files_created": sorted(set(os.listdir(".")) - before),
}))
"""

# (module, max cohezion modules). Measured 2026-09-27: event_bus 4, oom_guard 5, config 25,
# compound.executor 66 -- versus 498 / 337 / 498 / 536 with eager facades.
BUDGETS = [
    ("cohezion.core.event_bus", 10),
    ("cohezion.reliability.oom_guard", 15),
    ("cohezion.config", 50),
    ("cohezion.compound", 10),
    ("cohezion.reliability", 10),
    ("cohezion.compound.executor", 120),
]


def _probe(module: str, cwd: Path) -> dict:
    out = subprocess.run(
        [sys.executable, "-c", _PROBE, module],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(SRC), "PYTHONWARNINGS": "ignore"},
    )
    assert out.returncode == 0, out.stderr[-800:]
    return dict(json.loads(out.stdout.strip().splitlines()[-1]))


@pytest.mark.parametrize(("module", "max_modules"), BUDGETS)
def test_facade_import_stays_within_budget(module: str, max_modules: int, tmp_path: Path) -> None:
    r = _probe(module, tmp_path)
    assert not r["torch"], f"{module} loads torch"
    assert r["n_cohezion"] <= max_modules, (
        f"{module} loads {r['n_cohezion']} cohezion modules (budget {max_modules}); "
        "an eager package facade has probably crept back"
    )


def test_persistence_import_creates_no_file_and_leaves_root_logger_alone(tmp_path: Path) -> None:
    # core/persistence/admin.py used to call logging.basicConfig(FileHandler('dba_operations.log'))
    # at import, so any process touching cohezion.core.persistence got a log file in its cwd and,
    # depending on import order, all of its INFO logs routed into it.
    r = _probe("cohezion.core.persistence.admin", tmp_path)
    assert r["files_created"] == []
    assert r["root_handlers"] == 0
