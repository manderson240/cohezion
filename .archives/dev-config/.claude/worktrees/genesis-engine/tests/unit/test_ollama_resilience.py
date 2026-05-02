"""Tests for the ResilientOllamaClient."""

import pytest

from cohezion.swarm.ollama_resilience import ResilientOllamaClient


class TestResilientOllamaClient:
    def test_init_defaults(self):
        client = ResilientOllamaClient()
        assert client.model == "phi3:mini"
        assert client.base_url == "http://localhost:11434"
        assert client.max_retries == 2
        assert client.circuit is not None

    def test_init_custom(self):
        client = ResilientOllamaClient(
            model="deepseek-r1:70b",
            failure_threshold=5,
            recovery_timeout=60.0,
            max_retries=3,
        )
        assert client.model == "deepseek-r1:70b"
        assert client.max_retries == 3

    def test_fallback_message(self):
        msg = ResilientOllamaClient._fallback("test prompt")
        assert "circuit breaker open" in msg.lower()
        assert "test prompt" in msg

    def test_circuit_breaker_integration(self):
        client = ResilientOllamaClient(failure_threshold=2)
        # Circuit should start closed
        assert client.circuit.allow_request()

    @pytest.mark.asyncio
    async def test_close(self):
        client = ResilientOllamaClient()
        await client.close()
        assert client._client is None


class TestPatternDetector:
    """Test the upgraded PatternDetector."""

    def test_record_new_pattern(self):
        from cohezion.learning import PatternDetector

        detector = PatternDetector()
        p = detector.record("test", "desc", "example")
        assert p.name == "test"
        assert p.occurrences == 1

    def test_record_increments(self):
        from cohezion.learning import PatternDetector

        detector = PatternDetector()
        detector.record("test", "desc", "example")
        p = detector.record("test", "desc", "example")
        assert p.occurrences == 2

    def test_get_patterns_sorted(self):
        from cohezion.learning import PatternDetector

        detector = PatternDetector()
        detector.record("a", "d", "e")
        detector.record("b", "d", "e")
        detector.record("b", "d", "e")
        patterns = detector.get_patterns()
        assert patterns[0].name == "b"
        assert patterns[0].occurrences == 2

    def test_get_frequent(self):
        from cohezion.learning import PatternDetector

        detector = PatternDetector()
        for _ in range(5):
            detector.record("hot", "d", "e")
        detector.record("cold", "d", "e")
        frequent = detector.get_frequent(min_occurrences=3)
        assert len(frequent) == 1
        assert frequent[0].name == "hot"

    def test_clear(self):
        from cohezion.learning import PatternDetector

        detector = PatternDetector()
        detector.record("test", "d", "e")
        detector.clear()
        assert detector.get_patterns() == []
