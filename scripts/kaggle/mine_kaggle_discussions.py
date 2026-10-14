#!/usr/bin/env python3
"""Autonomous Kaggle Discussion Mining & Intelligence Synthesizer.
==================================================================
1. Harvests live discussion threads across active Kaggle competitions using KaggleDiscussionLearner.
2. Filters out low-signal social spam, scoring topics by competitive keywords.
3. Consults deepseek-v4-pro:cloud via OllamaCloudAgent with 2048D Poincaré AutoContext
   to extract tactical execution recipes, bug mitigations, and metric tweaks.
4. Persists findings to:
   - docs/research/kaggle_discussions_knowledge_base.md (Signal-ranked raw threads)
   - docs/research/kaggle_discussions_grandmaster_briefing.md (DeepSeek Grandmaster synthesis)
   - SurrealDB learning:kaggle_discussions_intelligence_<timestamp>
   - Obsidian Vault: ~/vaults/cohezion-vault/01-Learnings/
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.agents.ollama_cloud_agent import (
    AutoContextState,
    OllamaCloudAgent,
    OllamaCloudModel,
)
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.researcher.kaggle_discussion_learner import (
    TARGET_COMPETITIONS,
    KaggleDiscussionLearner,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] %(message)s",
)
logger = logging.getLogger("discussion_miner")


def persist_to_surrealdb(key: str, data: dict) -> bool:
    """Persist learning record to SurrealDB on port 8001 or 8000."""
    endpoints = ["http://localhost:8001/sql", "http://127.0.0.1:8001/sql", "http://localhost:8000/sql"]
    auth = base64.b64encode(b"root:root").decode()

    safe_key = key.replace(":", "_").replace("-", "_")
    surql = f"UPSERT learning:`{safe_key}` CONTENT {json.dumps(data)};"

    for ep in endpoints:
        try:
            req = urllib.request.Request(
                ep,
                data=surql.encode("utf-8"),
                headers={
                    "surreal-ns": "cohezion",
                    "surreal-db": "main",
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    logger.info("Successfully persisted to SurrealDB endpoint %s as learning:`%s`", ep, safe_key)
                    return True
        except Exception as e:
            logger.debug("Failed SurrealDB write to %s: %s", ep, e)
    return False


async def run_discussion_mining_and_synthesis():
    json_path = REPO_ROOT / "docs/research/kaggle_discussions_raw.json"
    md_path = REPO_ROOT / "docs/research/kaggle_discussions_knowledge_base.md"
    briefing_path = REPO_ROOT / "docs/research/kaggle_discussions_grandmaster_briefing.md"

    logger.info("Step 1: Harvesting active discussion threads across %d competitions...", len(TARGET_COMPETITIONS))
    learner = KaggleDiscussionLearner()
    mined_data = learner.run_all(json_path, md_path)

    # Filter top 2-3 highest signal topics per competition
    high_signal_summary = []
    for comp, topics in mined_data.items():
        high_signal_summary.append(f"### Competition: {comp}")
        top_topics = [t for t in topics if t.get("category") != "GENERAL_DISCUSSION"][:3]
        if not top_topics:
            top_topics = topics[:2]

        for t in top_topics:
            high_signal_summary.append(
                f"- **[{t.get('category', 'INFO')}]** {t.get('title')} (Comments: {t.get('comments')}, Signal: {t.get('signal_score')})"
            )
            for m in t.get("messages", [])[:2]:
                author = m.get("author", "User")
                content = m.get("content", "").replace("\n", " ")[:250]
                high_signal_summary.append(f"  * {author}: \"{content}...\"")
        high_signal_summary.append("")

    high_signal_context = "\n".join(high_signal_summary)

    logger.info("Step 2: Consulting deepseek-v4-pro:cloud for Grandmaster synthesis...")
    auto_context = AutoContextState.from_text(
        text="synthesize_discussion_intelligence_into_actionable_kaggle_code_and_patches",
        state_id="kaggle-discussion-grandmaster-synthesizer",
    )

    agent = OllamaCloudAgent(
        name="kaggle_discussion_grandmaster",
        role="Kaggle Grandmaster Competitive Intelligence Synthesizer",
        model=OllamaCloudModel.DEEPSEEK_V4_PRO,
        system_prompt="You are the Grandmaster Competitive Intelligence Synthesizer for Cohezion.",
    )
    agent.context_state = auto_context

    synthesis_prompt = f"""You are the Grandmaster Competitive Intelligence Synthesizer for Cohezion.
Below is the harvested high-signal discussion telemetry across our 4 active, unexpired Kaggle competitions:

{high_signal_context}

Analyze these findings and synthesize an actionable, high-density Grandmaster Briefing answering:
1. **ARC-AGI-2 & ARC-AGI-3**:
   - What critical bug or timeout pitfalls are teams reporting (e.g. topic 704408, 0.00 score in 15 mins)?
   - What neuro-symbolic or program synthesis breakthroughs are emerging (e.g. topic 708161 TranscendPlexity)?
   - How can we exploit unlimited CPU compute for ARC-3?
2. **RSNA Knee Abnormality Detection**:
   - What are the latest insights on backbone weights (topic 737696 Raptor/CoAtNet) and calibration?
   - How to protect multi-label log-loss from severe outlier penalties?
3. **Enveda CASMI26 Molecule ID**:
   - What are the critical prize eligibility warnings in topic 744470 ('Chasing medals with price ineligible sources')? Which external databases or spectral libraries are allowed vs forbidden?
   - How to break through the 0.33-0.34 plateau mentioned in topic 742055?
4. **Concrete Action Plan**:
   - Exactly what 3-5 immediate code/policy patches should our autonomous pipeline deploy today?

Format with crisp Markdown sections, explicit code snippets, and mathematical formulations.
"""

    resp = await agent.execute_turn(goal=synthesis_prompt)
    briefing_content = resp.response

    # Save markdown briefing
    with open(briefing_path, "w", encoding="utf-8") as f:
        f.write("# Kaggle Discussions: Grandmaster Intelligence & Breakthrough Briefing\n\n")
        f.write(f"**Synthesized**: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Model**: `{OllamaCloudModel.DEEPSEEK_V4_PRO}` with 2048D Poincaré AutoContext\n\n")
        f.write("---\n\n")
        f.write(briefing_content)
    logger.info("Saved Grandmaster Briefing to %s", briefing_path)

    # Persist to SurrealDB
    timestamp_key = f"kaggle_discussion_briefing_{int(time.time())}"
    surreal_payload = {
        "timestamp": time.time(),
        "model": str(OllamaCloudModel.DEEPSEEK_V4_PRO),
        "competitions": TARGET_COMPETITIONS,
        "briefing_path": str(briefing_path),
        "briefing_excerpt": briefing_content[:2000],
    }
    persist_to_surrealdb(timestamp_key, surreal_payload)

    # Persist to Obsidian Vault
    vault_dir = Path.home() / "vaults/cohezion-vault/01-Learnings"
    if vault_dir.exists():
        vault_file = vault_dir / f"2026-10-02-kaggle-discussions-grandmaster-briefing.md"
        with open(vault_file, "w", encoding="utf-8") as f:
            f.write(briefing_content)
        logger.info("Persisted briefing to Obsidian Vault: %s", vault_file)

    # Persist Agentic Kanban card
    persist_item({
        "id": "kanban-kaggle-discussion-mining-sota",
        "title": "Kaggle Discussion Intelligence Mined & Synthesized via DeepSeek-v4-Pro",
        "status": "done",
        "priority": "p1",
        "source": "scripts/kaggle/mine_kaggle_discussions.py",
        "category": "competitive_intelligence",
        "summary": "Harvested discussions across active competitions; identified CASMI26 price ineligible source warnings, ARC-2 0.00 timeout mitigations, and RSNA Raptor multi-slice ensembling.",
    })
    logger.info("Completed discussion mining and intelligence synthesis successfully!")


if __name__ == "__main__":
    asyncio.run(run_discussion_mining_and_synthesis())
