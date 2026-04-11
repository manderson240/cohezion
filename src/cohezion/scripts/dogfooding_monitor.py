#!/usr/bin/env python3
"""
Dogfooding Monitor - Proactive Journey Monitoring & Metric Capture.

Tracks active dogfooding journeys, captures system metrics, and triggers 
the final precipitation and distillation loop.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime

import aiofiles

# Resolve project root
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.universe.engine import UniverseSimulationEngine
from cohezion.observability.unified_metrics import get_metrics_collector
from cohezion.mcp.servers.surreal_server import get_server as get_surreal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("dogfooding-monitor")

async def capture_metrics(journey_id: str, status: str):
    """Capture and store metrics for a journey in SurrealDB."""
    collector = get_metrics_collector()
    metrics = collector.get_aggregate_metrics()
    
    # Store in SurrealDB
    surreal = get_surreal()
    try:
        await surreal.store_node(
            content=f"Dogfooding Journey {journey_id} metrics: {status}",
            node_type="metric_capture",
            physics={
                "time": time.time(),
                "novelty": metrics.get("aggregate_cache_hit_rate", 0) / 100.0,
                "logic": metrics.get("avg_tokens_per_operation", 0) / 10000.0,
                "quantum": metrics.get("total_operations", 0) / 10.0,
                "physics": metrics.get("uptime_seconds", 0) / 3600.0
            }
        )
        logger.info(f"✅ Metrics captured for {journey_id}")
    except Exception as e:
        logger.error(f"❌ Failed to store metrics: {e}")

async def monitor_loop(journey_ids: list[str]):
    """Poll journeys until all are complete."""
    engine = UniverseSimulationEngine()
    pending = set(journey_ids)
    
    logger.info(f"Monitoring {len(pending)} dogfooding journeys...")
    
    while pending:
        completed = []
        for jid in list(pending):
            # In our implementation, journeys save status to data/universe/journey_{jid}.json
            status_file = PROJECT_ROOT / f"data/universe/journey_{jid}.json"
            
            if status_file.exists():
                async with aiofiles.open(status_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                status = data.get("status")
                if status in ["completed", "failed"]:
                    logger.info(f"🏁 Journey {jid} finished with status: {status}")
                    await capture_metrics(jid, status)
                    completed.append(jid)
            else:
                # Journey hasn't written its file yet or is still early
                pass
                
        for jid in completed:
            pending.remove(jid)
            
        if pending:
            await asyncio.sleep(10)
            
    logger.info("All dogfooding journeys complete.")
    
    # Trigger final steps
    logger.info("🎬 Triggering Knowledge Precipitation (kg-guard)...")
    import subprocess
    subprocess.run(["make", "kg-guard"], cwd=str(PROJECT_ROOT))
    
    logger.info("🎬 Triggering Skill Distillation (omega-distiller)...")
    subprocess.run(["make", "omega-distiller"], cwd=str(PROJECT_ROOT))
    
    logger.info("✅ Dogfooding mission complete.")

if __name__ == "__main__":
    # In a real run, we'd pass IDs via args
    # For now, we scan for the ones we just started
    JOURNEY_IDS = [
        # These are from our previous 'start_journey' logs
        # Since I can't easily pass them, I'll scan for 'journey_1775926878_*'
    ]
    
    import glob
    pattern = str(PROJECT_ROOT / "data/universe/journey_1775926878_*.json")
    for f in glob.glob(pattern):
        with open(f) as jf:
            data = json.load(jf)
            JOURNEY_IDS.append(data["id"])
            
    if not JOURNEY_IDS:
        logger.warning("No active dogfooding journeys found to monitor.")
        sys.exit(0)
        
    asyncio.run(monitor_loop(JOURNEY_IDS))
