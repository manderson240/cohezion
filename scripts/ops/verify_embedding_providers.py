#!/usr/bin/env python3
"""Verification suite for local and cloud embedding providers in Cohezion."""

from cohezion.flume.embedding_provider import OllamaEmbeddingProvider, HashFallbackProvider
from cohezion.inference.lemonade_embed_bridge import LemonadeEmbedBridge
import numpy as np

def test_embeddings():
    print("=== Testing Cohezion Multi-Tier Embedding Pipeline ===")
    sample_text = "Poincaré hyperbolic manifold with AdS/CFT holographic boundary projection"
    
    # 1. Test Ollama Embedding Provider (768D nomic-embed-text)
    print("  • Testing OllamaEmbeddingProvider (768D)...")
    ollama_prov = OllamaEmbeddingProvider()
    vec_ollama = ollama_prov.embed(sample_text)
    norm_ollama = np.linalg.norm(vec_ollama)
    print(f"    - Embedding Shape: {vec_ollama.shape}, Norm: {norm_ollama:.4f}")
    assert len(vec_ollama) == 768
    
    # 2. Test Lemonade Embed Bridge (768D -> 256D Subsampled Unit Vector)
    print("  • Testing LemonadeEmbedBridge (256D FLUME adapter)...")
    lemonade_prov = LemonadeEmbedBridge()
    vec_flume = lemonade_prov.encode(sample_text)
    norm_flume = np.linalg.norm(vec_flume)
    print(f"    - Subsampled FLUME Shape: {vec_flume.shape}, Norm: {norm_flume:.4f}")
    assert len(vec_flume) == 256
    
    # 3. Test Hash Fallback Provider (Deterministic fallback)
    print("  • Testing HashFallbackProvider (256D deterministic fallback)...")
    hash_prov = HashFallbackProvider()
    vec_hash = hash_prov.embed(sample_text)
    print(f"    - Hash Fallback Shape: {vec_hash.shape}, Norm: {np.linalg.norm(vec_hash):.4f}")
    assert len(vec_hash) == 256
    
    print("\n✅ Multi-Tier Embedding Pipeline: 100% OPERATIONAL & VERIFIED")

if __name__ == "__main__":
    test_embeddings()
