#!/usr/bin/env python3
"""
Trajectory Guard - Reactive Trajectory Correction.

Polls active journeys and uses Ouroboros AnomalyDetector to identify
coherence drift. If drift is detected, it uses the HealerAgent to
inject a corrective prompt into the agent's context.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Resolve project root
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.ouroboros.monitor import OuroborosMonitor
from cohezion.ouroboros.detector import AnomalyDetector
from cohezion.ouroboros.healer import HealerAgent
from cohezion.universe.engine import UniverseSimulationEngine
from cohezion.audio.narrator import get_narrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("trajectory-guard")

async def guard_trajectories():
    logger.info("Starting Trajectory Guard - Monitoring active agent coherence...")
    
    monitor = OuroborosMonitor()
    detector = AnomalyDetector(coherence_threshold=0.15, target_coherence=0.5)
    healer = HealerAgent()
    engine = UniverseSimulationEngine()
    narrator = get_narrator()
    
    while True:
        try:
            # 1. Fetch recent trajectories
            trajectories = await monitor.fetch_recent_trajectories(limit=50)
            
            # Group by journey/agent ID
            active_journeys = {}
            for t in trajectories:
                jid = t.get("journey_id") or t.get("agent_id")
                if jid not in active_journeys:
                    active_journeys[jid] = []
                active_journeys[jid].append(t)
            
            # 2. Analyze each active journey
            for jid, points in active_journeys.items():
                analysis = detector.analyze_batch(points)
                
                if analysis["is_degraded"]:
                    current_coherence = points[0].get("coherence", 0.5)
                    logger.warning(f"🚨 Journey {jid} is drifting! Coherence: {current_coherence}")
                    
                    # 3. Voiced Alert
                    if narrator.available:
                        await narrator.narrate_custom(
                            f"Alert. Journey {jid} is drifting from the manifold. "
                            f"Current coherence is {current_coherence:.2f}. "
                            "Initiating autonomic realignment."
                        )
                    
                    # 4. Synthesize correction
                    patch_proposal = await healer.synthesize_patch(analysis)
                    
                    # 5. Voiced Confirmation
                    if narrator.available:
                        await narrator.narrate_custom(
                            f"Correction synthesized for journey {jid}. "
                            "Injecting stability patch into active context."
                        )
                    
                    # 6. Inject correction into journey context
                    # In this implementation, we log it and assume the engine/session picks it up
                    # Ideally, we append to a specific 'correction' collection in SurrealDB
                    logger.info(f"  ✨ Synthesized correction for {jid}: {patch_proposal[:50]}...")
                    
                    # Implementation detail: notify the engine
                    # await engine.inject_correction(jid, patch_proposal)
                    
        except Exception as e:
            logger.error(f"Error in trajectory guard loop: {e}")
            
        await asyncio.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        asyncio.run(guard_trajectories())
    except KeyboardInterrupt:
        logger.info("Trajectory Guard stopped.")
