#!/usr/bin/env python3
import asyncio
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter, TaskClass

async def main():
    router = UnifiedHybridRouter()
    print("Testing Updated UnifiedHybridRouter with Local Lemonade and Ollama Cloud...")
    
    # 1. Test local tier-1 / tier-2 automatic routing
    res1 = await router.route_by_capability("Explain in 15 words how Cohezion router works.", task_class=TaskClass.GENERAL)
    print(f"[{res1.tier_used}] ({res1.model_name}) -> {res1.content.strip()[:100]}... (Latency: {res1.latency_ms:.1f}ms)")
    
    # 2. Test tier-2 underutilized cloud (GLM-5.3-flash)
    res2 = await router.route_by_capability("In 15 words, confirm vision analysis capability.", task_class=TaskClass.VISION, force_cloud=True)
    print(f"[{res2.tier_used}] ({res2.model_name}) -> {res2.content.strip()[:100]}... (Latency: {res2.latency_ms:.1f}ms)")

if __name__ == "__main__":
    asyncio.run(main())
