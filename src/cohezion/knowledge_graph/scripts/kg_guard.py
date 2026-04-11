#!/usr/bin/env python3
"""
KG Guard v2.0 - Knowledge Precipitation & Latent Linker.

Automates learning extraction from agent journeys and uses semantic
vector similarity to densify the knowledge graph.
"""

import asyncio
import glob
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import aiofiles
import numpy as np

# Resolve project root
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.flume.embedding_provider import AsyncOllamaEmbeddingProvider

# Paths
JOURNEY_PATTERN = str(PROJECT_ROOT / 'data/universe/journey_*.json')
PROCESSED_FILE = PROJECT_ROOT / '.kg_processed_journeys.json'
LEARNINGS_FILE = PROJECT_ROOT / 'src/cohezion/knowledge_graph/KEY_LEARNINGS.md'

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("kg-guard")

async def find_related_learnings(text: str, provider: AsyncOllamaEmbeddingProvider):
    """Placeholder for latent linking logic. 
    In production, this queries SurrealDB for nearest neighbors.
    For this implementation, we log the intent to link.
    """
    try:
        vec = await provider.embed(text)
        logger.info(f"  Generated {len(vec)}D latent vector for linking.")
        return [] # Returns list of related IDs
    except Exception as e:
        logger.warning(f"  Latent linking failed: {e}")
        return []

async def run_kg_guard():
    # Load processed IDs
    processed_ids = set()
    if PROCESSED_FILE.exists():
        async with aiofiles.open(PROCESSED_FILE, 'r') as f:
            try:
                processed_ids = set(json.loads(await f.read()))
            except (json.JSONDecodeError, ValueError):
                pass

    new_learnings = []
    provider = AsyncOllamaEmbeddingProvider()
    
    # Scan journeys
    journey_files = glob.glob(JOURNEY_PATTERN)
    for journey_file in journey_files:
        try:
            async with aiofiles.open(journey_file, 'r') as f:
                data = json.loads(await f.read())
            
            journey_id = data.get('id')
            if not journey_id or journey_id in processed_ids:
                continue
                
            status = data.get('status')
            coherence = data.get('final_coherence', 0)
            
            if status == 'complete' and coherence >= 0.8:
                intent = data.get('intent', 'Unknown Intent')
                summary = data.get('summary') or data.get('final_report') or intent
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                logger.info(f"🚀 Precipitating learning from journey {journey_id}")
                
                # Perform Latent Linking
                related = await find_related_learnings(summary, provider)
                
                learning_entry = f"\n## Auto-Learning: {intent} (Coherence: {coherence})\n"
                learning_entry += f"- **Summary**: {summary}\n"
                learning_entry += f"- **Source**: Journey {journey_id}\n"
                learning_entry += f"- **Date**: {current_date}\n"
                if related:
                    learning_entry += f"- **Related**: {', '.join(related)}\n"
                
                new_learnings.append(learning_entry)
                processed_ids.add(journey_id)
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error processing {journey_file}: {e}")

    # Append new learnings to KEY_LEARNINGS.md
    if new_learnings:
        async with aiofiles.open(LEARNINGS_FILE, 'a') as f:
            for entry in new_learnings:
                await f.write(entry)
        
        # Save processed IDs
        async with aiofiles.open(PROCESSED_FILE, 'w') as f:
            await f.write(json.dumps(list(processed_ids), indent=2))
            
        logger.info(f"✅ Added {len(new_learnings)} new learning(s) to {LEARNINGS_FILE}")
    else:
        logger.info("No new high-coherence completed journeys found.")

if __name__ == "__main__":
    asyncio.run(run_kg_guard())
