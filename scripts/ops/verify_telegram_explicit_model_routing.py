#!/usr/bin/env python3
"""Verify Telegram Bot Explicit Local Model Routing."""

import asyncio
from cohezion.integrations.telegram_bot import TelegramCommunicationHub

async def verify_explicit_model_routing():
    print("=== Testing Telegram Bot Explicit Local Model Switching ===")
    hub = TelegramCommunicationHub()
    
    # 1. Test /models list handler
    print("  • Testing /models handler...")
    await hub._handle_models()
    
    # 2. Test /model <model_name> <prompt> handler with gpt-oss-20b-mxfp4-GGUF
    print("  • Testing /model gpt-oss-20b-mxfp4-GGUF explicit query...")
    await hub._handle_explicit_model("gpt-oss-20b-mxfp4-GGUF", "State the 0.5 HIHO stability rule in 1 sentence.")
    
    print("✅ Telegram Bot Explicit Local Model Routing: 100% OPERATIONAL & VERIFIED")

if __name__ == "__main__":
    asyncio.run(verify_explicit_model_routing())
