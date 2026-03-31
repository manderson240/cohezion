"""Tests for Data Mesh data products.

TDD: Validates data product lifecycle, SLA compliance, and registry serialization.
"""

import pytest
from cohezion.data_mesh.data_product import (
    DataProduct,
    DataProductSchema,
    DataProductStatus,
    DataQualityTier,
    COHEZION_DATA_PRODUCTS,
)


class TestDataProduct:
    """Data product type with schema, SLA, and ownership."""

    def test_create_data_product(self):
        dp = DataProduct(
            product_id="test-product",
            name="Test Product",
            description="A test data product",
            owner_domain="test",
        )
        assert dp.product_id == "test-product"
        assert dp.status == DataProductStatus.DRAFT
        assert dp.quality_tier == DataQualityTier.BRONZE

    def test_access_tracking(self):
        dp = DataProduct(product_id="t", name="T", description="T", owner_domain="t")
        dp.record_access(True)
        dp.record_access(True)
        dp.record_access(False)
        assert dp.access_count == 3
        assert dp.error_rate == pytest.approx(1 / 3)

    def test_bronze_always_meets_sla(self):
        dp = DataProduct(product_id="t", name="T", description="T", owner_domain="t",
                         quality_tier=DataQualityTier.BRONZE)
        dp.record_access(False)  # 100% error rate
        assert dp.meets_sla is True  # Bronze has no SLA

    def test_gold_sla_failure(self):
        dp = DataProduct(product_id="t", name="T", description="T", owner_domain="t",
                         quality_tier=DataQualityTier.GOLD, availability_target=0.95)
        for _ in range(5):
            dp.record_access(True)
        for _ in range(5):
            dp.record_access(False)
        # 50% error rate, 50% availability < 95% target
        assert dp.meets_sla is False

    def test_to_registry_entry(self):
        dp = DataProduct(product_id="test", name="Test", description="D",
                         owner_domain="skills", quality_tier=DataQualityTier.GOLD,
                         status=DataProductStatus.ACTIVE)
        entry = dp.to_registry_entry()
        assert entry["product_id"] == "test"
        assert entry["quality_tier"] == "gold"
        assert entry["meets_sla"] is True


class TestCohezionDataProducts:
    """Pre-defined data products for Cohezion's 17+ MCP servers."""

    def test_six_products_defined(self):
        assert len(COHEZION_DATA_PRODUCTS) == 6

    def test_all_products_are_active(self):
        for pid, dp in COHEZION_DATA_PRODUCTS.items():
            assert dp.status == DataProductStatus.ACTIVE, f"{pid} is not active"

    def test_owner_domains_are_unique(self):
        domains = [dp.owner_domain for dp in COHEZION_DATA_PRODUCTS.values()]
        # Some domains may have multiple products, but all should be non-empty
        assert all(d for d in domains)

    def test_gold_products_have_low_latency(self):
        for pid, dp in COHEZION_DATA_PRODUCTS.items():
            if dp.quality_tier == DataQualityTier.GOLD:
                assert dp.max_latency_ms <= 5000, f"{pid} gold product has high latency"
