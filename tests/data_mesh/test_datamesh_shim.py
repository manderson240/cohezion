"""The datamesh/ -> data_mesh/ fold (coherence tranche 4, 2026-10-22).

The old package must be a shim and nothing more: same objects, a deprecation warning,
no modules of its own, and no production importer left on the old path.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import warnings
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SHIM_DIR = REPO / "src" / "cohezion" / "datamesh"


def _fresh_import_shim():
    sys.modules.pop("cohezion.datamesh", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        mod = importlib.import_module("cohezion.datamesh")
    return mod, caught


def test_shim_warns_with_deprecation_warning():
    _, caught = _fresh_import_shim()
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_shim_re_exports_the_canonical_objects_not_copies():
    shim, _ = _fresh_import_shim()
    from cohezion.data_mesh import federation, knowledge_graph_layer, schema

    assert shim.UnifiedRecord is schema.UnifiedRecord
    assert shim.FederationLayer is federation.FederationLayer
    assert shim.KnowledgeGraphLayer is knowledge_graph_layer.KnowledgeGraphLayer
    assert set(shim.__all__) <= set(dir(shim))


def test_old_package_holds_only_the_shim():
    assert sorted(p.name for p in SHIM_DIR.glob("*.py")) == ["__init__.py"]


def test_no_production_importer_uses_the_old_path():
    out = subprocess.run(
        [
            "git",
            "grep",
            "-lE",
            r"^\s*(from|import) cohezion\.datamesh\b",
            "--",
            "src",
            ":!src/cohezion/datamesh/",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).stdout.split()
    assert out == [], f"still importing the deprecated path: {out}"
