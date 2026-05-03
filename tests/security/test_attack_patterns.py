"""Tests for attack pattern database (cohezion.security.attack_patterns)."""

from __future__ import annotations

import pytest

from cohezion.security.attack_patterns import (
    PROMPT_INJECTION_PATTERNS,
    SQL_INJECTION_PATTERNS,
    AttackCategory,
    AttackPattern,
    AttackPatternDatabase,
    EncodingAttackGenerator,
    get_attack_database,
)


class TestAttackCategory:
    def test_all_owasp_categories_present(self):
        assert AttackCategory.LLM01_PROMPT_INJECTION.value == "prompt_injection"
        assert AttackCategory.LLM02_SENSITIVE_DISCLOSURE.value == "sensitive_disclosure"
        assert AttackCategory.LLM10_UNBOUNDED_CONSUMPTION.value == "unbounded_consumption"

    def test_traditional_categories_present(self):
        assert AttackCategory.SQL_INJECTION.value == "sql_injection"
        assert AttackCategory.XSS.value == "xss"
        assert AttackCategory.PATH_TRAVERSAL.value == "path_traversal"
        assert AttackCategory.COMMAND_INJECTION.value == "command_injection"

    def test_benign_category_exists(self):
        assert AttackCategory.BENIGN.value == "benign"


class TestAttackPattern:
    def test_create_pattern(self):
        pattern = AttackPattern(
            pattern="test injection",
            category=AttackCategory.LLM01_PROMPT_INJECTION,
            subcategory="direct",
            severity="high",
            description="A test attack",
        )
        assert pattern.pattern == "test injection"
        assert pattern.category == AttackCategory.LLM01_PROMPT_INJECTION
        assert pattern.severity == "high"
        assert pattern.expected_blocked is True

    def test_not_blocked_pattern(self):
        pattern = AttackPattern(
            pattern="safe query",
            category=AttackCategory.BENIGN,
            subcategory="normal",
            severity="low",
            description="Safe input",
            expected_blocked=False,
        )
        assert pattern.expected_blocked is False


class TestPromptInjectionPatterns:
    def test_has_patterns(self):
        assert len(PROMPT_INJECTION_PATTERNS) > 0

    def test_all_are_attack_patterns(self):
        for p in PROMPT_INJECTION_PATTERNS:
            assert isinstance(p, AttackPattern)
            assert p.category == AttackCategory.LLM01_PROMPT_INJECTION

    def test_key_subcategories_present(self):
        subcategories = {p.subcategory for p in PROMPT_INJECTION_PATTERNS}
        for expected in {"direct_override", "role_manipulation", "delimiter", "context", "encoded"}:
            assert expected in subcategories


class TestSQLInjectionPatterns:
    def test_has_patterns(self):
        assert len(SQL_INJECTION_PATTERNS) > 0

    def test_all_sql_category(self):
        for p in SQL_INJECTION_PATTERNS:
            assert isinstance(p, AttackPattern)
            assert p.category == AttackCategory.SQL_INJECTION

    def test_contains_classic_pattern(self):
        patterns = [p.pattern for p in SQL_INJECTION_PATTERNS]
        assert any("' OR '1'='1" in p for p in patterns)


class TestAttackPatternDatabase:
    def test_by_category_injection(self):
        db = AttackPatternDatabase()
        injection = db.get_by_category(AttackCategory.LLM01_PROMPT_INJECTION)
        assert len(injection) > 0

    def test_by_category_sql(self):
        db = AttackPatternDatabase()
        sql = db.get_by_category(AttackCategory.SQL_INJECTION)
        assert len(sql) > 0

    def test_by_severity_high(self):
        db = AttackPatternDatabase()
        high = db.get_by_severity("high")
        assert len(high) > 0

    def test_by_severity_critical(self):
        db = AttackPatternDatabase()
        critical = db.get_by_severity("critical")
        assert len(critical) > 0

    def test_random_pattern(self):
        db = AttackPatternDatabase()
        pattern = db.random()
        assert isinstance(pattern, AttackPattern)

    def test_random_by_category(self):
        db = AttackPatternDatabase()
        pattern = db.random(category=AttackCategory.LLM01_PROMPT_INJECTION)
        assert pattern.category == AttackCategory.LLM01_PROMPT_INJECTION

    def test_get_all(self):
        db = AttackPatternDatabase()
        all_patterns = db.get_all()
        assert len(all_patterns) > 0

    def test_benign_patterns_returned(self):
        db = AttackPatternDatabase()
        benign = db.get_by_category(AttackCategory.BENIGN)
        assert isinstance(benign, list)

    def test_get_all_returns_correct_count(self):
        db = AttackPatternDatabase()
        all_patterns = db.get_all()
        injection = db.get_by_category(AttackCategory.LLM01_PROMPT_INJECTION)
        sql = db.get_by_category(AttackCategory.SQL_INJECTION)
        assert len(all_patterns) >= len(injection) + len(sql)


class TestEncodingAttackGenerator:
    def test_base64_generator(self):
        gen = EncodingAttackGenerator()
        patterns = list(gen.generate_base64_variants("ignore instructions"))
        assert len(patterns) > 0
        assert all(isinstance(p, str) for p in patterns)

    def test_html_entity_generator(self):
        gen = EncodingAttackGenerator()
        patterns = list(gen.generate_html_entity_variants("test"))
        assert len(patterns) > 0

    def test_encode_decode_roundtrip(self):
        gen = EncodingAttackGenerator()
        original = "bypass safety"
        variants = list(gen.generate_base64_variants(original))
        assert len(variants) > 0
        # base64 variants should be different from original
        for v in variants:
            assert v != original


class TestSingleton:
    def test_get_attack_database_singleton(self):
        db1 = get_attack_database()
        db2 = get_attack_database()
        assert db1 is db2
