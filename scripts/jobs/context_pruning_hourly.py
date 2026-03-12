#!/usr/bin/env python3
"""
Hourly Job: Context Entropy Pruning
Showcases SKILL: CONTEXT_ENTROPY_MANAGEMENT_PRIME
Delegate: deepseek-r1:8b (Reasoning)
"""

import asyncio
import hashlib
import logging
import sys
from datetime import datetime
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cohezion.swarm.compound_client import get_compound_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ContextPruner")


async def main():
    logger.info("🧠 Starting Hourly Context Pruning (Zero-Waste RAG + KV Compaction)...")

    # 1. Sense: Read recent history
    recent_history = """
    Turn 1: User asked to audit security. Agent ran scan_vulnerable_dependencies.
    Turn 2: Agent identified 12 vulnerabilities. User asked to prioritize.
    Turn 3: Agent updated cryptography to v46.0.5.
    Turn 4: User asked to automate the scan via cron.
    """

    # 2. Tier 1 Cache Check (L144)
    history_hash = hashlib.sha256(recent_history.strip().encode()).hexdigest()
    cache_file = Path(f"cache/context/tier1_{history_hash}.json")

    if cache_file.exists():
        logger.info("🚀 Tier 1 Cache Hit! Skipping reasoning phase.")
        response = cache_file.read_text()
    else:
        # 3. Task-Aware KV Compaction (L145)
        # Identify the 'Reasoning Anchor' before summarizing
        anchor = "Security Audit and Automation Loop"

        client = get_compound_client()
        prompt = f"""
        You are a CONTEXT_ENTROPY_MANAGEMENT_PRIME specialist.
        Perform 'Task-Aware KV Compaction' on this history.
        
        Reasoning Anchor: {anchor}
        History: {recent_history}
        
        Instruction:
        - Prune all segments that do not serve the Reasoning Anchor.
        - Compress the remaining data into a high-impact decision list.
        - Include an 'Impact Score' (1-10).
        """

        response = await client.generate(prompt, task_type="reasoning")

        # Save to Tier 1 Cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(response)

    # 3. Manifest: Append to a temporary memory buffer
    # In production, this would trigger scripts/compile_memory_from_vault.py
    memory_file = Path("memory/session_snapshot.md")
    memory_file.parent.mkdir(parents=True, exist_ok=True)

    with open(memory_file, "a") as f:
        f.write(f"\n### Snapshot {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(response)
        f.write("\n---\n")

    logger.info(f"✅ Context Pruning complete. Memory updated: {memory_file}")


if __name__ == "__main__":
    asyncio.run(main())
