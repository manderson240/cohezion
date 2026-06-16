"""Tests: non-destructive wiring of datamesh/ orphan types into data_mesh/ canonical surface.

Verifies:
  - FederationLayer and DomainEndpoint are importable from data_mesh
  - UnifiedRecord (and schema types) are importable from data_mesh
  - Physics12D.coherence returns 0.5 at all-zero HIHO equilibrium
  - DataMeshEventBridge.watch_federation signature is correct
  - DataProduct.from_unified_record constructs a valid DataProduct
"""

from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# Import guard: the entire orphan wiring relies on torch being present via
# schema.py → import torch.  Skip the suite when torch is absent so CI on
# torch-free environments doesn't red-flag structural wiring tests.
# ---------------------------------------------------------------------------
torch = pytest.importorskip("torch", reason="datamesh schema.py requires torch")


def test_federation_layer_importable_from_data_mesh():
    """FederationLayer must be available on the canonical data_mesh surface."""
    from cohezion.data_mesh import FederationLayer

    assert FederationLayer is not None
    # It should be the real class, not a stub.
    assert inspect.isclass(FederationLayer)


def test_domain_endpoint_importable_from_data_mesh():
    """DomainEndpoint must also be promoted to the canonical surface."""
    from cohezion.data_mesh import DomainEndpoint

    assert inspect.isclass(DomainEndpoint)
    # DomainEndpoint has a 'name' field.
    ep = DomainEndpoint(name="test-domain")
    assert ep.name == "test-domain"


def test_unified_record_importable_from_data_mesh():
    """UnifiedRecord must be available on the canonical data_mesh surface."""
    from cohezion.data_mesh import UnifiedRecord

    assert inspect.isclass(UnifiedRecord)
    record = UnifiedRecord()
    assert hasattr(record, "id")
    assert hasattr(record, "lineage")


def test_physics_12d_coherence():
    """Physics12D HIHO equilibrium: all-zero inputs → coherence == 0.5 exactly.

    Formula: 0.5 + (r * 0.25) + (t * 0.25) - (b * 0.25)
    With all fields at 0: r=0, t=0, b=0 → coherence = 0.5
    """
    from cohezion.data_mesh import Physics12D

    p = Physics12D()  # All defaults are 0.0
    assert p.coherence == pytest.approx(0.5, abs=1e-9)


def test_watch_federation_signature():
    """DataMeshEventBridge.watch_federation must accept `federation` and `poll_interval_s`."""
    from cohezion.data_mesh.event_bridge import DataMeshEventBridge

    sig = inspect.signature(DataMeshEventBridge.watch_federation)
    params = set(sig.parameters)
    assert "federation" in params, f"Missing 'federation' param; got {params}"
    assert "poll_interval_s" in params, f"Missing 'poll_interval_s' param; got {params}"

    # poll_interval_s must have a default of 30.0
    assert sig.parameters["poll_interval_s"].default == 30.0


def test_from_unified_record_returns_data_product():
    """DataProduct.from_unified_record must construct a valid DataProduct."""
    from cohezion.data_mesh import UnifiedRecord
    from cohezion.data_mesh.data_product import DataProduct

    # Build a minimal UnifiedRecord with known fields.
    record = UnifiedRecord(content="test content")
    record.metadata["title"] = "Test Record"
    record.lineage.origin = "test-domain"

    dp = DataProduct.from_unified_record(record)

    assert isinstance(dp, DataProduct)
    assert dp.product_id == str(record.id)
    assert dp.name == "Test Record"
    assert "test content" in dp.description
    assert dp.owner_domain == "test-domain"


def test_from_unified_record_fallback_name():
    """When metadata has no title, from_unified_record falls back to record type name."""
    from cohezion.data_mesh import UnifiedRecord
    from cohezion.data_mesh.data_product import DataProduct
    from cohezion.datamesh.schema import RecordType

    record = UnifiedRecord(type=RecordType.EMBEDDING, content="")
    # No 'title' in metadata.

    dp = DataProduct.from_unified_record(record)

    assert isinstance(dp, DataProduct)
    assert dp.name == "EMBEDDING"
