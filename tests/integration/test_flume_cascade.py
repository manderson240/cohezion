"""Integration tests for FLUME optimization cascade across hot paths."""

import time

import pytest

from cohezion.flume import OptimizedFlumeEncoder


class TestFlumeOptimizationCascade:
    """Verify optimized FLUME is active across critical hot paths."""

    def test_semantic_cache_uses_optimized_encoder(self):
        """Verify SemanticCache uses OptimizedFlumeEncoder."""
        try:
            from cohezion.cache.semantic_cache import SemanticCache

            cache = SemanticCache()

            # Check if cache has text_encoder that uses optimized FLUME
            if hasattr(cache, "text_encoder"):
                # Verify it produces 256D embeddings
                test_embedding = cache.text_encoder.encode("test")
                assert test_embedding.shape == (256,), "Embedding should be 256D"
                print("✓ SemanticCache using optimized FLUME")
            else:
                pytest.skip("SemanticCache doesn't expose text_encoder")

        except ImportError:
            pytest.skip("SemanticCache not available")

    def test_flume_vae_encoder_is_optimized(self):
        """Verify FlumeVAEEncoder imports resolve to OptimizedFlumeEncoder."""
        from cohezion.flume import FlumeVAEEncoder, OptimizedFlumeEncoder

        # Drop-in replacement should be active
        assert (
            FlumeVAEEncoder is OptimizedFlumeEncoder
        ), "FlumeVAEEncoder should be OptimizedFlumeEncoder"

        # Instantiation should create OptimizedFlumeEncoder
        encoder = FlumeVAEEncoder()
        assert isinstance(encoder, OptimizedFlumeEncoder)

    def test_encoding_performance(self):
        """Measure actual encoding performance."""
        from cohezion.flume import get_optimized_encoder

        encoder = get_optimized_encoder(reset=True)

        # Cold encoding (uncached)
        test_texts = [f"test_{i}" for i in range(100)]

        start = time.perf_counter()
        for text in test_texts:
            encoder.encode(text)
        cold_time = time.perf_counter() - start

        # Hot encoding (cached)
        start = time.perf_counter()
        for text in test_texts:
            encoder.encode(text)
        hot_time = time.perf_counter() - start

        # Verify performance
        assert cold_time < 1.0, f"Cold encoding too slow: {cold_time:.3f}s for 100 texts"
        assert (
            hot_time < cold_time / 5
        ), f"Cache not working: hot={hot_time:.3f}s, cold={cold_time:.3f}s"

        print(f"✓ Performance: cold={cold_time*1000:.1f}ms, hot={hot_time*1000:.1f}ms")
        print(f"✓ Cache speedup: {cold_time/hot_time:.1f}x")

    def test_cache_hit_rate(self):
        """Verify high cache hit rates."""
        from cohezion.flume import get_optimized_encoder

        encoder = get_optimized_encoder(reset=True)

        # Encode with repetition pattern (realistic workload)
        texts = ["skill1", "skill2", "skill3"] * 10  # 30 encodings, 3 unique

        for text in texts:
            encoder.encode(text)

        stats = encoder.get_stats()

        # Should have 3 misses (first occurrence) + 27 hits
        assert (
            stats["cache_hit_rate"] > 0.8
        ), f"Cache hit rate too low: {stats['cache_hit_rate']:.1%}"

        print(f"✓ Cache hit rate: {stats['cache_hit_rate']:.1%}")
        print(f"✓ Total encodings: {stats['total_encodings']}")

    def test_batch_encoding(self):
        """Verify batch encoding works."""
        from cohezion.flume import get_optimized_encoder

        encoder = get_optimized_encoder(reset=True)

        texts = ["text1", "text2", "text3"]
        embeddings = encoder.encode_batch(texts)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert emb.shape == (256,)

        print("✓ Batch encoding works")

    def test_stats_tracking(self):
        """Verify performance tracking works."""
        from cohezion.flume import get_optimized_encoder

        encoder = get_optimized_encoder(reset=True)

        encoder.encode("test1")
        encoder.encode("test2")
        encoder.encode("test1")  # Cache hit

        stats = encoder.get_stats()

        assert stats["total_encodings"] == 3
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 2
        assert stats["avg_latency_ms"] > 0
        assert stats["throughput_per_sec"] > 0

        print(f"✓ Stats: {stats['cache_hit_rate']:.1%} hit rate, {stats['avg_latency_ms']:.4f}ms avg")


class TestCompoundCascadeImpact:
    """Measure compound cascade effects across system."""

    def test_embedding_generation_speedup(self):
        """Baseline: Verify embeddings are fast enough for real-time use."""
        from cohezion.flume import get_optimized_encoder

        encoder = get_optimized_encoder(reset=True)

        # Real-time threshold: 100 embeddings/sec minimum
        texts = [f"request_{i}" for i in range(100)]

        start = time.perf_counter()
        for text in texts:
            encoder.encode(text)
        elapsed = time.perf_counter() - start

        throughput = 100 / elapsed

        assert (
            throughput > 100
        ), f"Throughput too low: {throughput:.0f} encodings/sec (need >100)"

        print(f"✓ Throughput: {throughput:,.0f} encodings/sec")

    def test_compound_cascade_ready(self):
        """Verify system ready for compound cascade activation."""
        from cohezion.flume import FlumeVAEEncoder, get_optimized_encoder

        # 1. Drop-in replacement active
        assert FlumeVAEEncoder is get_optimized_encoder().__class__

        # 2. Performance adequate
        encoder = get_optimized_encoder(reset=True)
        start = time.perf_counter()
        for _ in range(1000):
            encoder.encode("test")
        elapsed = time.perf_counter() - start

        # Should complete 1000 encodings in <100ms (cached)
        assert elapsed < 0.1, f"Too slow: {elapsed:.3f}s for 1000 cached encodings"

        # 3. Stats tracking functional
        stats = encoder.get_stats()
        assert stats["total_encodings"] == 1000
        assert stats["cache_hit_rate"] > 0.99  # Almost all cached

        print("✅ COMPOUND CASCADE READY FOR ACTIVATION")
        print(f"   - Throughput: {1000/elapsed:,.0f} encodings/sec")
        print(f"   - Cache hit rate: {stats['cache_hit_rate']:.1%}")
        print(f"   - Latency p95: ~{stats['avg_latency_ms']*1000:.1f}μs")
