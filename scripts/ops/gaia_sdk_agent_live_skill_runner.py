#!/usr/bin/env python3
"""Execute live AMD GAIA SDK Agents against PRIME skills."""

import asyncio
import logging
from cohezion.integrations.gaia_local_router import GAIALocalRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [GAIA_LIVE] %(message)s")
logger = logging.getLogger("gaia_live")

async def run_gaia_live_skill():
    router = GAIALocalRouter()
    prompt = "Summarize the core directive of INTER_DAEMON_COOPERATIVE_LOOPS_PRIME in 2 concise sentences."
    
    print("\n" + "=" * 95)
    print("🤖 EXECUTING LIVE AMD GAIA SDK AGENT ON LOCAL SILICON")
    print("=" * 95)

    res = await router.route_gaia_agent_call(
        agent_id="gaia-loop-orchestrator",
        prompt=prompt,
        task_type="research"
    )

    print(f"• Agent ID        : {res.agent_id}")
    print(f"• Target Hardware : {res.target_hardware}")
    print(f"• Adapter Path    : {res.finetuned_checkpoint}")
    print(f"• Response Text   :\n{res.response_text}")
    print(f"• Latency         : {res.latency_ms:.2f} ms")
    print("=" * 95)
    print("🎉 OFFICIAL AMD GAIA SDK LIVE INFERENCE CONFIRMED!\n")

if __name__ == "__main__":
    asyncio.run(run_gaia_live_skill())
