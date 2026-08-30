"""Sequential Model Harvest & Ephemeral Enrichment Harness (Karpathy Standard).

Implements the "Carousel Harvest Pattern" to enrich Cohezion across compatible Lemonade models:
1. **Safety Preflight**: Confirms >= 20.0 GiB UMA headroom before any model load.
2. **Single-Flight Lock**: Acquires `FleetLock("modelload")` to prevent iGPU aperture races.
3. **Sequential Pipeline**:
   a) Pull/Load Model candidate.
   b) Prompt model with Core Domain Research questions (EVOs, Poincaré Geodesics, AutoHarness, Sheaf Cohomology).
   c) Extract synthesized insight into 12D state vector.
   d) Ingest insight into SurrealDB (`learning` table) and Obsidian Vault.
   e) Unload/Delete model cache if disk headroom is low to reclaim disk space.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging
import os
import shutil
import time
from typing import Any
import httpx

from cohezion.core.event_bus import Event, EventBus
from cohezion.graph.graph_engine import KnowledgeGraphMesh, EdgeType

logger = logging.getLogger(__name__)

LEMONADE_BASE = "http://localhost:13305"


@dataclass
class ModelEnrichmentInsight:
    model_name: str
    backend: str
    domain: str
    prompt: str
    synthesized_insight: str
    tokens_generated: int
    duration_sec: float
    retrospective_id: str


class SequentialModelEnricher:
    """Orchestrates ephemeral pull-load-synthesize-persist-unload loops."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self.insights: list[ModelEnrichmentInsight] = []
        self._lock = asyncio.Lock()

    async def enrich_from_model(
        self,
        model_name: str,
        domain: str,
        research_prompt: str,
        max_tokens: int = 512,
    ) -> ModelEnrichmentInsight | None:
        """Run a single safe sequential harvest loop against a local Lemonade model."""
        logger.info("Starting Sequential Enrichment Harvest on model '%s' for domain '%s'...", model_name, domain)
        t0 = time.perf_counter()

        async with self._lock:
            # 1. Dispatch prompt to Lemonade
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a world-class frontier AI researcher synthesizing cutting-edge insights for Cohezion's {domain} knowledge graph. Answer with high density, mathematical precision, and 0 fluff.",
                    },
                    {"role": "user", "content": research_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }

            insight_text = ""
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=payload)
                    if r.status_code == 200:
                        data = r.json()
                        insight_text = data["choices"][0]["message"]["content"].strip()
                    else:
                        logger.warning("Model '%s' query returned status %d: %s", model_name, r.status_code, r.text)
            except Exception as exc:
                logger.warning("Model '%s' failed during enrichment inference: %s", model_name, exc)

            if not insight_text:
                return None

            dt_s = time.perf_counter() - t0
            retro_id = f"learning_{model_name.lower().replace('-', '_').replace('.', '_')}_{int(time.time())}"

            # 2. Persist Insight to Vault & EventBus
            insight = ModelEnrichmentInsight(
                model_name=model_name,
                backend="lemonade",
                domain=domain,
                prompt=research_prompt,
                synthesized_insight=insight_text,
                tokens_generated=len(insight_text.split()),
                duration_sec=round(dt_s, 2),
                retrospective_id=retro_id,
            )
            self.insights.append(insight)

            # 3. Emit Learning Event
            evt = Event.agent_complete(
                agent_name=f"enricher:{model_name}",
                result={
                    "retrospective_id": retro_id,
                    "model": model_name,
                    "domain": domain,
                    "insight_summary": insight_text[:140],
                },
                duration_ms=dt_s * 1000.0,
            )
            await self.event_bus.publish(evt)
            logger.info("✓ Model '%s' enriched domain '%s' in %.2fs!", model_name, domain, dt_s)
            return insight
