#!/usr/bin/env python3
"""
Autoresearch Daemon - Autonomous Overnight Literature Review.

Polls arXiv and HuggingFace for terms related to "Latent Space Geometry",
"Manifold Topology", and "Representation Learning".
Outputs high-confidence hypotheses and theoretical models to data/universe/.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

import aiofiles

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("autoresearch-daemon")

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.universe.engine import UniverseSimulationEngine
from cohezion.mcp.research_server import get_server
from cohezion.reliability.heartbeat import update_heartbeat

UNIVERSE_DATA_DIR = PROJECT_ROOT / "data/universe"

async def run_autoresearch():
    logger.info("Starting Autonomous Overnight Literature Review")
    
    queries = [
        "Latent Space Geometry",
        "Manifold Topology",
        "Representation Learning",
        "Persistent Homology Autoencoders"
    ]
    
    server = get_server()
    engine = UniverseSimulationEngine()
    
    while True:
        update_heartbeat("autoresearch-daemon")
        for query in queries:
            logger.info(f"Querying arXiv for: {query}")
            try:
                results = server.search_arxiv(query, limit=3)
                
                for paper in results:
                    paper_id = paper.get("id", "unknown").replace("/", "_")
                    title = paper.get("title", "Untitled")
                    summary = paper.get("summary", "")
                    
                    logger.info(f"Found Paper: {title}")
                    
                    # Create hypothesis artifact
                    hypothesis = {
                        "source": "autoresearch_daemon",
                        "paper_id": paper_id,
                        "title": title,
                        "abstract": summary,
                        "status": "pending_validation",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    artifact_path = UNIVERSE_DATA_DIR / f"research_hypothesis_{paper_id}.json"
                    if not UNIVERSE_DATA_DIR.exists():
                        UNIVERSE_DATA_DIR.mkdir(parents=True)
                    
                    if not artifact_path.exists():
                        async with aiofiles.open(artifact_path, "w") as f:
                            await f.write(json.dumps(hypothesis, indent=2))
                        logger.info(f"  ✅ Saved hypothesis artifact to {artifact_path.name}")
                        
                        # Trigger a journey to process the hypothesis
                        await engine.start_journey(
                            agent_name="ResearchOrchestrator",
                            intent=f"Analyze and validate hypothesis from {title}",
                            context={
                                "hypothesis_file": str(artifact_path)
                            }
                        )
                    else:
                        logger.info(f"  - Hypothesis already exists for {paper_id}")
                        
            except Exception as e:
                logger.error(f"Failed to query {query}: {e}")
        
        # Add a sleep interval for the loop to avoid spinning
        await asyncio.sleep(3600)  # Check every hour

if __name__ == "__main__":
    asyncio.run(run_autoresearch())
