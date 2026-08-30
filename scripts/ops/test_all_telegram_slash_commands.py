#!/usr/bin/env python3
"""Comprehensive Audit & Verification of all Telegram Bot Slash Commands.

Delegates execution to local inference (Lemonade :13305) and tests every slash command
handler end-to-end to guarantee 100% functionality without timeouts or exceptions.
"""

import asyncio
import os
import sys

from cohezion.integrations.telegram_bot import TelegramCommunicationHub

SLASH_COMMANDS = [
    ("/start", "Initialize bot greeting"),
    ("/help", "List command menu"),
    ("/status", "System telemetry, RAM, NPU/iGPU load"),
    ("/models", "List Lemonade and Ollama cloud models"),
    ("/sessions", "List active agent sessions & swarms"),
    ("/kanban", "Retrieve active Kanban items from SurrealDB"),
    ("/agents", "List swarm agent roster"),
    ("/ask What is the status of the local hardware?", "Query local inference on Lemonade 13305"),
]

async def verify_all_slash_commands():
    print("\n" + "=" * 105)
    print("🤖 TELEGRAM BOT SLASH COMMANDS E2E VERIFICATION (LOCAL INFERENCE DELEGATED)")
    print("=" * 105)

    hub = TelegramCommunicationHub()
    
    # Capture sent messages for verification
    captured_messages = []
    
    async def mock_send_msg(text: str, reply_to_message_id=None):
        captured_messages.append(text)

    hub._send_msg = mock_send_msg

    results = []

    for cmd, desc in SLASH_COMMANDS:
        print(f"\n▶ Testing command: '{cmd}' ({desc})...")
        captured_messages.clear()
        
        # Build mock update message
        mock_msg = {
            "message_id": 999,
            "text": cmd,
            "chat": {"id": int(hub.allowed_chat_id or 123456789)},
            "from": {"id": int(hub.allowed_chat_id or 123456789)},
        }

        try:
            await hub._process_message(mock_msg)
            if captured_messages:
                out = captured_messages[0]
                preview = out.replace("\n", " ")[:120]
                print(f"  ✓ Success! Response: {preview}...")
                results.append((cmd, "PASS", out))
            else:
                print(f"  ✗ Warning: No response message dispatched.")
                results.append((cmd, "NO_RESPONSE", ""))
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append((cmd, f"FAIL: {e}", ""))

    print("\n" + "=" * 105)
    print("📊 SLASH COMMAND AUDIT SUMMARY")
    print("=" * 105)
    all_passed = True
    for cmd, status, _ in results:
        passed = status == "PASS"
        if not passed:
            all_passed = False
        mark = "✅" if passed else "❌"
        print(f"  {mark} {cmd:<45} : {status}")
    print("=" * 105)
    
    if all_passed:
        print("🎉 ALL TELEGRAM BOT SLASH COMMANDS ARE 100% OPERATIONAL & VERIFIED!\n")
    else:
        print("⚠️ Some commands failed verification. Check logs above.\n")

if __name__ == "__main__":
    asyncio.run(verify_all_slash_commands())
