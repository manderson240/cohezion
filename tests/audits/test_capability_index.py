"""Verify gate for the capability index (pathway Move 1, V-model structural).

Spot-checks that KNOWN-EXISTING components appear in a fresh index — the
discriminating failure this guards: an index that generates cleanly but
misses whole surfaces would silently re-enable "built-then-forgotten".
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "scripts" / "audits" / "capability_index.py"


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("capability_index", GEN)
    mod = importlib.util.module_from_spec(spec)
    out = tmp_path_factory.mktemp("capindex")
    argv, sys.argv = sys.argv, ["capability_index.py", "--out", str(out)]
    try:
        spec.loader.exec_module(mod)
        mod.main()
    finally:
        sys.argv = argv
    import json

    return {
        "json": json.loads((out / "capabilities.json").read_text()),
        "md": (out / "CAPABILITIES.md").read_text(),
    }


class TestKnownComponentsPresent:
    def test_gauntlet_surfaces_indexed(self, index):
        pub = index["json"]["packages"]["inference"]["public"]
        assert any("npu_gauntlet" in f for f in pub)
        assert "BenchTask" in index["md"]

    def test_hooks_visible_including_warmup(self, index):
        # The 418-autoload incident hook must be discoverable.
        assert any("lemonade-warmup" in h["command"] for h in index["json"]["hooks"])

    def test_idle_eviction_module_indexed(self, index):
        pub = index["json"]["packages"]["inference"]["public"]
        assert any("idle_eviction" in f for f in pub)

    def test_fleet_roles_roster_indexed(self, index):
        assert "FleetRoster" in index["md"]

    def test_skill_stores_enumerated(self, index):
        stores = index["json"]["skill_stores"]
        assert "global" in stores and "repo_prime" in stores

    def test_labs_orphan_zone_listed(self, index):
        assert index["json"]["entry_points"].get("labs_orphan_zone")

    def test_generated_invariant_stamped(self, index):
        assert "never hand-edit" in index["json"]["invariant"]
        assert "do not hand-edit" in index["md"].splitlines()[0]

    def test_tables_have_wire_gap_flags(self, index):
        tables = index["json"]["surreal_tables"]
        if "_error" in tables:
            pytest.skip("SurrealDB unreachable in this environment")
        # model_performance gained its writer today — must NOT be a wire gap.
        assert tables["model_performance"]["wire_gap"] is False
        assert len(tables["model_performance"]["referenced_by"]) >= 1
        # The wire-gap flag must actually fire for known-unreferenced tables.
        assert any(info.get("wire_gap") for info in tables.values())
