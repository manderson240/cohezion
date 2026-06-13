"""Coverage batch Z43: shadow_scripter, vanguard_attribution, lru_persistent_token_cache."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module 1: learning/shadow_scripter.py
# ---------------------------------------------------------------------------


class TestShadowScripter:
    def test_generated_test_dataclass(self):
        from cohezion.learning.shadow_scripter import GeneratedTest, TestGenStatus

        gt = GeneratedTest(
            test_name="test_foo", test_code="def test_foo(): pass", source_skill="CODE_REVIEW"
        )
        assert gt.test_name == "test_foo"
        assert gt.status == TestGenStatus.GENERATED

    def test_generated_test_to_dict(self):
        from cohezion.learning.shadow_scripter import GeneratedTest

        gt = GeneratedTest(test_name="t", test_code="pass", source_skill="sk")
        d = gt.to_dict()
        assert d["test_name"] == "t"
        assert d["status"] == "generated"

    def test_shadow_scripter_generate_valid_code(self):
        from cohezion.learning.shadow_scripter import ShadowScripter, TestGenStatus

        ss = ShadowScripter()
        result = ss.generate("test_add", "def test_add():\n    assert 1 + 1 == 2", "MATH_SKILL")
        assert result.status == TestGenStatus.VALIDATED
        assert len(ss.generated_tests) == 1

    def test_shadow_scripter_generate_invalid_code(self):
        from cohezion.learning.shadow_scripter import ShadowScripter, TestGenStatus

        ss = ShadowScripter()
        result = ss.generate("test_bad", "def test_bad(: invalid python !!!", "BAD_SKILL")
        assert result.status == TestGenStatus.QUARANTINED
        assert result.error is not None
        assert len(ss.quarantined_tests) == 1

    def test_shadow_scripter_get_committable_tests(self):
        from cohezion.learning.shadow_scripter import ShadowScripter

        ss = ShadowScripter()
        ss.generate("valid_test", "def t(): pass", "s1")
        ss.generate("invalid_test", "def t(: broken", "s2")
        committable = ss.get_committable_tests()
        assert len(committable) == 1
        assert committable[0].test_name == "valid_test"

    def test_shadow_scripter_get_quarantine_report(self):
        from cohezion.learning.shadow_scripter import ShadowScripter

        ss = ShadowScripter()
        ss.generate("bad", "def t(: broken", "skill")
        report = ss.get_quarantine_report()
        assert len(report) == 1
        assert report[0]["test_name"] == "bad"
        assert "error" in report[0]

    def test_shadow_scripter_generated_tests_property(self):
        from cohezion.learning.shadow_scripter import ShadowScripter

        ss = ShadowScripter()
        ss.generate("t1", "def t1(): pass", "s1")
        ss.generate("t2", "def t2(): pass", "s2")
        assert len(ss.generated_tests) == 2

    def test_shadow_scripter_quarantined_tests_property(self):
        from cohezion.learning.shadow_scripter import ShadowScripter

        ss = ShadowScripter()
        ss.generate("bad1", "INVALID (((", "s1")
        ss.generate("bad2", "def t(: broken", "s2")
        assert len(ss.quarantined_tests) == 2

    def test_validate_syntax_valid(self):
        from cohezion.learning.shadow_scripter import ShadowScripter

        ss = ShadowScripter()
        assert ss._validate_syntax("x = 1 + 2") is True

    def test_validate_syntax_invalid(self):
        from cohezion.learning.shadow_scripter import ShadowScripter

        ss = ShadowScripter()
        assert ss._validate_syntax("def f(: broken") is False


# ---------------------------------------------------------------------------
# Module 2: vanguard/attribution.py
# ---------------------------------------------------------------------------


def _make_discovery_record(source_url="https://example.com/paper"):
    from cohezion.vanguard.source_connector import DiscoveryRecord

    return DiscoveryRecord(
        title="Test Paper",
        abstract="Some content.",
        source_url=source_url,
        category="cs.AI",
        source_name="arxiv",
    )


class TestVanguardAttribution:
    def test_license_status_enum(self):
        from cohezion.vanguard.attribution import LicenseStatus

        assert LicenseStatus.COMPATIBLE.value == "compatible"
        assert LicenseStatus.INCOMPATIBLE.value == "incompatible"

    def test_attribution_metadata_to_dict(self):
        from cohezion.vanguard.attribution import AttributionMetadata, LicenseStatus

        meta = AttributionMetadata(
            origin_url="https://example.com",
            authors=["Alice"],
            license_type="mit",
            content_hash="abc123",
            status=LicenseStatus.COMPATIBLE,
        )
        d = meta.to_dict()
        assert d["origin_url"] == "https://example.com"
        assert d["status"] == "compatible"

    def test_process_compatible_license(self):
        from cohezion.vanguard.attribution import AttributionEngine, LicenseStatus

        engine = AttributionEngine()
        record = _make_discovery_record()
        attributed = engine.process(record, authors=["Alice"], license_type="mit")
        assert attributed.attribution.status == LicenseStatus.COMPATIBLE
        assert not attributed.quarantined

    def test_process_incompatible_license(self):
        from cohezion.vanguard.attribution import AttributionEngine, LicenseStatus

        engine = AttributionEngine()
        record = _make_discovery_record()
        attributed = engine.process(record, authors=["Bob"], license_type="gpl-3.0")
        assert attributed.attribution.status == LicenseStatus.INCOMPATIBLE
        assert attributed.quarantined

    def test_process_unknown_license(self):
        from cohezion.vanguard.attribution import AttributionEngine, LicenseStatus

        engine = AttributionEngine()
        record = _make_discovery_record()
        attributed = engine.process(record, authors=["Carol"], license_type="some-weird-license")
        assert attributed.attribution.status == LicenseStatus.UNKNOWN
        assert attributed.attribution.flagged_for_review is True

    def test_quarantined_records(self):
        from cohezion.vanguard.attribution import AttributionEngine

        engine = AttributionEngine()
        engine.process(_make_discovery_record(), authors=["x"], license_type="gpl-3.0")
        engine.process(_make_discovery_record(), authors=["y"], license_type="mit")
        assert engine.quarantine_count() == 1
        report = engine.quarantined_records()
        assert len(report) == 1
        assert "attribution" in report[0]

    def test_content_hash_is_from_source_url(self):
        from cohezion.vanguard.attribution import AttributionEngine

        engine = AttributionEngine()
        source_url = "https://example.com/stable"
        record = _make_discovery_record(source_url=source_url)
        attributed = engine.process(record, authors=[], license_type="mit")
        expected = hashlib.sha256(source_url.encode()).hexdigest()[:16]
        assert attributed.attribution.content_hash == expected

    def test_apache_is_compatible(self):
        from cohezion.vanguard.attribution import AttributionEngine, LicenseStatus

        engine = AttributionEngine()
        record = _make_discovery_record()
        attributed = engine.process(record, authors=[], license_type="apache-2.0")
        assert attributed.attribution.status == LicenseStatus.COMPATIBLE


# ---------------------------------------------------------------------------
# Module 3: swarm/lru_persistent_token_cache.py
# ---------------------------------------------------------------------------


class TestLRUPersistentTokenCache:
    def _make_cache(self, tmp_path, max_entries=10):
        from cohezion.swarm.lru_persistent_token_cache import LRUPersistentTokenCache

        return LRUPersistentTokenCache(
            cache_dir=str(tmp_path),
            max_entries=max_entries,
            persistence_enabled=False,
            auto_restore=False,
        )

    def test_cache_basic_set_get(self, tmp_path):
        from cohezion.swarm.batch_processor import CacheEntry

        cache = self._make_cache(tmp_path)
        entry = MagicMock(spec=CacheEntry)
        cache["key1"] = entry
        assert cache["key1"] is entry

    def test_cache_stores_entries_in_lru(self, tmp_path):
        cache = self._make_cache(tmp_path)
        cache["key1"] = MagicMock()
        assert "key1" in cache

    def test_cache_delete(self, tmp_path):
        cache = self._make_cache(tmp_path)
        cache["key1"] = MagicMock()
        del cache["key1"]
        assert "key1" not in cache

    def test_get_stats_returns_dict(self, tmp_path):
        cache = self._make_cache(tmp_path)
        stats = cache.get_stats()
        assert "memory_entries" in stats
        assert "max_entries" in stats
        assert stats["max_entries"] == 10

    def test_get_stats_utilization(self, tmp_path):
        cache = self._make_cache(tmp_path, max_entries=10)
        for i in range(5):
            cache[f"k{i}"] = MagicMock()
        stats = cache.get_stats()
        assert stats["memory_entries"] == 5
        assert stats["utilization"] == pytest.approx(0.5)

    def test_get_hit_rate(self, tmp_path):
        cache = self._make_cache(tmp_path)
        rate = cache.get_hit_rate()
        assert 0.0 <= rate <= 1.0

    def test_get_eviction_stats(self, tmp_path):
        cache = self._make_cache(tmp_path)
        stats = cache.get_eviction_stats()
        assert isinstance(stats, dict)

    def test_clear(self, tmp_path):
        cache = self._make_cache(tmp_path)
        cache["k1"] = MagicMock()
        cache["k2"] = MagicMock()
        cache.clear()
        assert len(cache) == 0
