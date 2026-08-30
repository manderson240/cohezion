#!/usr/bin/env python3
"""Tests the Robust Dynamic Model Hot-Swapper."""

import asyncio
from cohezion.inference.robust_hotswapper import RobustModelHotSwapper

async def run_test():
    print("\n" + "=" * 110)
    print("🔄 TESTING ROBUST DYNAMIC MODEL HOT-SWAPPER")
    print("=" * 110)

    # Test safe unload & hot-swap check
    success, msg = await RobustModelHotSwapper.hotswap("Qwen3-Coder-30B-A3B-Instruct-GGUF", estimated_size_gb=17.4)
    print(f"• Hot-Swap Result: Success = {success} | Notice: {msg}")

    print("=" * 110 + "\n")

if __name__ == "__main__":
    asyncio.run(run_test())
