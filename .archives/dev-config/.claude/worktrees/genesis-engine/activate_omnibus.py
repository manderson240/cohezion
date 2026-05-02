"""Activate Omnibus - Unlock All 9 Gateways.

The master activation script invoked by Party Mode Consensus.
"""

from __future__ import annotations

import asyncio
import sys


sys.path.insert(0, "/home/mike-anderson/dev/cohezion")

from cohezion.gateways.omnibus import Omnibus


async def activate_omnibus():
    """Activate Omnibus and unlock all 9 gateways."""
    print("=" * 70)
    print("🌟 OMNIBUS MASTER ACTIVATION")
    print("=" * 70)
    print()

    # Initialize Omnibus
    omnibus = Omnibus()

    # Print initial state
    print("📊 Initial Gateway Status:")
    print(omnibus.get_gateway_dashboard())
    print()

    # Activate all gateways
    gateways = ["cache", "security", "vault", "swarm", "universe", "flume", "skills", "api"]

    print("🔓 Unlocking remaining 8 gateways...")
    print("-" * 70)

    for gateway in gateways:
        print(f"\n🚀 Activating {gateway.upper()} Gateway...")
        success = await omnibus.unlock_gateway(gateway)

        if success:
            print(f"✅ {gateway.upper()} Gateway UNLOCKED")
        else:
            print(f"❌ {gateway.upper()} Gateway failed to unlock")

    print()
    print("=" * 70)
    print("🌟 OMNIBUS FULLY ACTIVATED")
    print("=" * 70)
    print()

    # Final dashboard
    print("📊 Final Gateway Status:")
    print(omnibus.get_gateway_dashboard())
    print()

    # Get master status
    status = omnibus.get_master_status()
    print(f"Total Gateways: {status['gateways_unlocked']}/9")
    print(f"Total Health: {status['total_health']:.1%}")
    print(f"Cycles Completed: {status['omnibus_cycles']}")
    print()

    print("🐍 Running continuous optimization...")
    print("   (Press Ctrl+C to stop)")
    print()

    # Run forever
    await omnibus.run_forever()


if __name__ == "__main__":
    asyncio.run(activate_omnibus())
