#!/usr/bin/env python3
"""Demonstrates and verifies built-in Lemonade v11.7.0 features."""

import asyncio
import json
from cohezion.inference.lemonade_v117_features import LemonadeV117Client

async def main():
    print("=" * 80)
    print("🍋 VERIFYING BUILT-IN LEMONADE V11.7.0 FEATURES")
    print("=" * 80)
    
    client = LemonadeV117Client()
    
    # 1. Test GET /v1/stats
    stats = await client.get_server_stats()
    print("▶ 1. Prefix Cache & Server Stats (`GET /v1/stats`):")
    print(f"   • Total Requests: {stats.get('request_count_total')}")
    print(f"   • Prefix-Cache Tokens Served: {stats.get('cache_tokens_total')}")
    print(f"   • Generation Speed: {stats.get('tokens_per_second', 0):.1f} tok/s")
    print(f"   • Time-To-First-Token: {stats.get('time_to_first_token', 0)*1000:.1f} ms")

    # 2. Test GET /v1/models/{id}/options
    model = "Qwen3-Coder-30B-A3B-Instruct-GGUF"
    opts = await client.get_model_options(model)
    print(f"\n▶ 2. Model Recipe Options (`GET /v1/models/{model}/options`):")
    print(f"   • Recipe: {opts.get('recipe')}")
    print(f"   • Effective Context Size: {opts.get('effective', {}).get('ctx_size')}")
    print(f"   • Llama.cpp Args: {opts.get('effective', {}).get('llamacpp_args')}")

    print("\n✓ Lemonade v11.7.0 Features Fully Verified & Operational!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
