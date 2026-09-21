"""Importing a data_mesh submodule must not drag in the ML stack (2026-09-21).

``import cohezion.data_mesh.event_consumer`` took 13.6 s and ~590 MB on every 5-min
timer run, although event_consumer itself imports only the stdlib: the package
``__init__`` eagerly re-exported ~34 names, and one of them (data_product) pulls
governance -> core -> physics -> reliability -> compound -> flume -> transformers/JAX.
The re-exports are now resolved on first attribute access (PEP 562).

The discriminating check is ``sys.modules`` in a fresh interpreter, not wall clock.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
HEAVY = ("transformers", "torch", "jax", "cohezion.physics", "cohezion.compound")

# Public names cohezion.data_mesh exposed BEFORE the change, recorded at runtime from the
# eager __init__ (commit 22b6a1e46). Do NOT regenerate this from _LAZY_EXPORTS: the list
# is the oracle that map is checked against. Every name must still resolve.
PUBLIC_NAMES = [
    "AgentSpec", "AudioSegmentMetadata", "AudioTelemetryEvent", "BirdSpeciesNode",
    "CorpusQualityConsumer", "DEFAULT_AGENT_SPECS", "DataLineage", "DataMeshEventBridge",
    "DataProduct", "DataProductSchema", "DataProductStatus", "DataQualityTier",
    "DomainEndpoint", "FederationLayer", "FlumeJourneyEvent", "GaiaAgentRoster",
    "GaiaDataAgent", "GapMiner", "HardwareTier", "LemonadeMultimodalClient", "Physics12D",
    "QuadratureFabrics", "RecordType", "SpectrogramConfig", "TaxonomyLevel",
    "UnifiedRecord", "UniverseStateEvent", "backfill_items", "deploy_gaia_agent_roster",
    "get_cohezion_data_products", "make_corpus_quality_consumer", "make_event_bridge",
    "make_gap_miner", "persist_item",
]  # fmt: skip


def _fresh(code: str) -> str:
    env = {"PYTHONPATH": f"{REPO}:{REPO / 'src'}", "PATH": "/usr/bin:/bin"}
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=300
    )
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout.strip().splitlines()[-1]


def test_event_consumer_import_does_not_load_the_ml_stack() -> None:
    loaded = json.loads(
        _fresh(
            "import sys, json\n"
            "import cohezion.data_mesh.event_consumer\n"
            f"print(json.dumps([m for m in {list(HEAVY)!r} if m in sys.modules]))"
        )
    )
    assert loaded == []


@pytest.mark.parametrize("name", PUBLIC_NAMES)
def test_public_name_still_importable_from_package(name: str) -> None:
    import cohezion.data_mesh as pkg

    assert getattr(pkg, name) is not None


def test_reexport_is_the_same_object_as_its_source() -> None:
    from cohezion.data_mesh import DataProduct, persist_item
    from cohezion.data_mesh.data_product import DataProduct as src_dp
    from cohezion.data_mesh.kanban_bridge import persist_item as src_pi

    assert DataProduct is src_dp
    assert persist_item is src_pi


def test_submodule_attribute_access_still_works() -> None:
    import cohezion.data_mesh as pkg

    assert pkg.kanban_bridge.persist_item is pkg.persist_item


def test_unknown_name_raises_attribute_error() -> None:
    import cohezion.data_mesh as pkg

    with pytest.raises(AttributeError):
        _ = pkg.definitely_not_a_real_name
