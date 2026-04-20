"""Tests for TurboQuant Phase 3 streaming integration."""
import pytest

torch = pytest.importorskip("torch")

from cohezion.inference.turboquant_streaming import StreamingKVCompressor
from cohezion.inference.registry import KVQuant


class TestStreamingKVCompressor:
    """Test KV-cache compression for streaming inference."""
    
    def test_compressor_creation(self):
        kv = KVQuant(scheme="turboquant", bits=3.5)
        compressor = StreamingKVCompressor(kv)
        assert compressor.kv_quant.scheme == "turboquant"
    
    def test_should_compress_long_context(self):
        kv = KVQuant(scheme="turboquant", bits=3.5)
        compressor = StreamingKVCompressor(kv)
        assert compressor.should_compress(128_000) is True
        assert compressor.should_compress(16_000) is False  # Below threshold
    
    def test_should_not_compress_when_scheme_none(self):
        kv = KVQuant(scheme="none")
        compressor = StreamingKVCompressor(kv)
        assert compressor.should_compress(128_000) is False
    
    def test_target_footprint_128k(self):
        kv = KVQuant(scheme="turboquant", bits=3.5)
        compressor = StreamingKVCompressor(kv)
        # Should be roughly 55GB target per ROADMAP
        target = compressor.get_target_footprint(128_000)
        assert target <= 80.0  # Baseline is ~80GB
    
    def test_validate_target_128k(self):
        kv = KVQuant(scheme="turboquant", bits=3.5)
        compressor = StreamingKVCompressor(kv)
        # Theoretical check (no actual stats)
        assert compressor.validate_target(128_000) is True
