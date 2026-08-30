#!/usr/bin/env python3
"""Direct End-to-End Test of Telegram Bot Local Inference Pipeline."""

import asyncio
from cohezion.integrations.telegram_bot import TelegramCommunicationHub, QueryComplexity

async def test_telegram_inference():
    print("=== Testing Telegram Bot Local Inference Routing ===")
    hub = TelegramCommunicationHub()
    
    # 1. Health check probe
    is_healthy = await hub._verify_inference_health()
    print(f"  • Inference Health Verified: {is_healthy}")
    assert is_healthy, "Local Lemonade :13305 router not reachable!"
    
    # 2. Test chat inference on local silicon
    messages = [
        {"role": "system", "content": "You are Cohezion AI on AMD Strix Halo."},
        {"role": "user", "content": "Explain what 2048D Poincaré Ball hyperbolic manifolds are in one concise sentence."},
    ]
    
    print("  • Dispatching test query to Lemonade OmniRouter (:13305)...")
    content, telem = await hub._chat_omnirouter(
        complexity=QueryComplexity.MEDIUM,
        messages=messages,
        max_tokens=256,
    )
    
    print(f"\n=== LOCAL INFERENCE RESPONSE RECEIVED ===")
    print(f"  • Model Used : {telem.actual_model}")
    print(f"  • Backend    : {telem.backend} (Port {telem.port})")
    print(f"  • Route Note : {telem.route_reason}")
    print(f"  • Response   :\n\n{content}\n")
    
    assert content and len(content) > 10
    print("✅ Telegram Bot Local Inference Pipeline: 100% OPERATIONAL & VERIFIED")

if __name__ == "__main__":
    asyncio.run(test_telegram_inference())
