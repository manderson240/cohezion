"""
NexusResearchAgent - Specialized for mining arXiv, Hugging Face, and GitHub.
Implements the "Nexus Protocol": Abstract-First filtering and strict API guardrails.
"""

import arxiv
import logging
import asyncio
import time
import random
import json
import requests
from typing import Any, Dict, List, Tuple
from huggingface_hub import HfApi
from pathlib import Path

from cohezion.swarm.agents.base import BaseAgent, AgentResponse
from cohezion.swarm.swarm_types import SwarmConfig, Perspective
from cohezion.db.surreal_client import UniverseNode, PhysicsState
from cohezion.simulation.simulation_logger import SimulationLogger

logger = logging.getLogger(__name__)

class NexusResearchAgent(BaseAgent):
    """
    Agent that monitors external research platforms and filters for high-signal SOTA.
    """

    SYSTEM_PROMPT = """You are the Nexus Research Miner.
Your goal is to evaluate technical research for its alignment with the Cohezion project:
- FLUME (Fluid Latent Understanding through Manifold Encoding)
- 12D State Vectors (3 Spatial, 1 Time, 8 Brane)
- SLM Swarm Orchestration (Local efficiency, 128GB RAM context)
- Physics-Informed AI (HIHO stability, EVOs, LENR metaphors)
- Yann LeCun's World Models (JEPA architectures)
- Universe Simulation frontiers (PINNs, N-body AI, cellular automata, cosmology)

Be strict. Only rank papers > 0.85 if they offer a genuine breakthrough or efficiency gain.
"""

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="qwen3-coder:30b", # Corrected from 32b
            config=config or SwarmConfig(),
        )
        from cohezion.mcp.research_server import get_server as get_research_server
        self.research_server = get_research_server()
        self.sim_logger = SimulationLogger()

    async def process(self, task: str = "mine_daily") -> AgentResponse:
        """
        Main entry point for the agent.
        """
        logger.info(f"🔭 NexusResearchAgent starting task: {task}")

        if task == "mine_daily":
            result = await self.mine_daily()
            return AgentResponse(result)

        # If task is a specific search query
        result = await self.search_and_rank(task)
        return AgentResponse(result)

    async def mine_daily(self, limit_per_source: int = 5) -> str:
        """
        Executes a daily sweep of arXiv, HF, and GitHub.
        """
        report_entries = []

        # 1. arXiv (AI Categories)
        arxiv_papers = await self._fetch_arxiv(limit=limit_per_source)
        logger.info(f"Fetched {len(arxiv_papers)} papers from arXiv.")
        report_entries.extend(await self._process_batch(arxiv_papers))

        # 2. Hugging Face Daily Papers
        hf_papers = await self._fetch_hf_papers(limit=limit_per_source)
        logger.info(f"Fetched {len(hf_papers)} papers from Hugging Face.")
        report_entries.extend(await self._process_batch(hf_papers))

        # 3. GitHub Trending (Python)
        github_repos = await self._fetch_github_trending(limit=limit_per_source)
        logger.info(f"Fetched {len(github_repos)} repos from GitHub.")
        report_entries.extend(await self._process_batch(github_repos))

        # 4. YouTube Transcript Mining (JEPA/World Models)
        # Targeted video IDs (can be dynamic in future)
        video_ids = ["mAvvO89B2N0"] # Key Yann LeCun JEPA talk
        for vid in video_ids:
            yt_res = await self.delegate_task(vid, target_agent="YouTubeTranscriptAgent")
            if yt_res and "Mining failed" not in str(yt_res):
                report_entries.append({
                    "source": "youtube",
                    "title": f"Video {vid}",
                    "summary": str(yt_res),
                    "rank": 0.9, # High baseline for targeted curation
                    "id": vid,
                    "url": f"https://youtube.com/watch?v={vid}"
                })

        # 5. X-Scout (Twitter Alpha)
        x_res = await self.delegate_task("ylecun", target_agent="XScoutAgent")
        if x_res:
             report_entries.append({
                    "source": "x",
                    "title": "Alpha @ylecun",
                    "summary": str(x_res),
                    "rank": 0.88,
                    "id": "ylecun",
                    "url": "https://twitter.com/ylecun"
                })

        # 6. Universe Simulation Pulse (Specialized Agent Delegation)
        uni_res = await self.delegate_task("Universe Simulation cosmology PINNs N-body AI", target_agent="UniverseSimAgent")
        if uni_res:
             report_entries.append({
                    "source": "universe_sim",
                    "title": "Quantum/Cosmic Frontier Update",
                    "summary": str(uni_res),
                    "rank": 0.95,
                    "id": "universe_sim_pulse",
                    "url": "https://arxiv.org/list/astro-ph.CO/recent"
                })

        # 7. World Model Architect (Specialized Agent Delegation)
        wm_res = await self.delegate_task("World Models JEPA Latent State Prediction", target_agent="WorldModelAgent")
        if wm_res:
            report_entries.append({
                    "source": "world_models",
                    "title": "JEPA Architecture Synthesis",
                    "summary": str(wm_res),
                    "rank": 0.92,
                    "id": "world_model_pulse",
                    "url": "https://openreview.net/forum?id=V-JEPA"
                })

        if not report_entries:
            return "Sweep complete. No high-signal discoveries meeting the >0.85 threshold were found today."

        # Final Synthesis
        summary_prompt = f"Synthesize these {len(report_entries)} high-signal research discoveries into a daily mission update for the Swarm:\n"
        for entry in report_entries:
            summary_prompt += f"- [{entry['source'].upper()}] {entry['title']} (Rank: {entry['rank']:.2f})\n"

        final_report = await self._call_ollama(summary_prompt, temperature=0.3)

        # 8. Log mission to SimulationLogger for HF export compatibility
        self.sim_logger.log_cycle({
            "cycle_id": f"research_{int(time.time())}",
            "universe_domain": "external_research",
            "expert_synthesis": final_report,
            "hypothesis": "Continued research on World Models and Universe Simulations improves swarm coherence.",
            "phi_score": 0.85,
            "narration": f"NexusResearchAgent synchronized {len(report_entries)} discoveries."
        })

        return final_report

    async def search_and_rank(self, query: str) -> str:
        """Specific search for a topic."""
        papers = await self._fetch_arxiv(query=query, limit=5)
        results = await self._process_batch(papers)
        if not results:
            return f"No highly relevant research found for: {query}"

        return f"Found {len(results)} relevant items:\n" + "\n".join([f"- {r['title']} (Rank: {r['rank']:.2f})" for r in results])

    async def _fetch_arxiv(self, categories: List[str] = ["cs.AI", "cs.CL", "cs.LG"], query: str | None = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch papers from arXiv with jittered delay."""
        papers = []
        search_query = query if query else " OR ".join([f"cat:{c}" for c in categories])

        try:
            results = await asyncio.to_thread(self.research_server.search_arxiv, search_query, limit)

            for result in results:
                if "error" in result: continue
                papers.append({
                    "source": "arxiv",
                    "title": result["title"],
                    "abstract": result["summary"],
                    "url": result["url"],
                    "authors": [], # Arxiv library results were simplified in MCP
                    "id": result["id"]
                })
        except Exception as e:
            logger.error(f"arXiv fetch failed: {e}")

        return papers

    async def _fetch_hf_papers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetches daily papers from Hugging Face API."""
        papers = []
        try:
            results_data = await asyncio.to_thread(self.research_server.get_hf_trending, limit)
            for paper in results_data:
                if "error" in paper: continue
                papers.append({
                    "source": "huggingface",
                    "title": paper["title"],
                    "abstract": paper["summary"],
                    "url": paper["url"],
                    "id": paper["id"]
                })
        except Exception as e:
            logger.error(f"HF fetch failed: {e}")
        return papers

    async def _fetch_github_trending(self, language: str = "python", limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch trending repos from GitHub."""
        repos = []
        try:
            url = f"https://api.github.com/search/repositories?q=language:{language}&sort=stars&order=desc&since=daily"
            response = await asyncio.to_thread(requests.get, url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", [])[:limit]:
                    repos.append({
                        "source": "github",
                        "title": item.get("full_name"),
                        "abstract": item.get("description") or "No description.",
                        "url": item.get("html_url"),
                        "stars": item.get("stargazers_count"),
                        "id": str(item.get("id"))
                    })
        except Exception as e:
            logger.error(f"GitHub fetch failed: {e}")
        return repos

    async def _process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and rank a batch of items."""
        valid_discoveries = []
        for item in items:
            rank = await self._rank_item(item)
            if rank >= 0.85:
                logger.info(f"🌟 High-signal discovery: {item['title']} (Rank: {rank})")
                item["rank"] = rank
                # Synthesize a 12D summary
                item["summary"] = await self._synthesize_summary(item)
                # Persist to SurrealDB
                await self._persist_discovery(item)
                valid_discoveries.append(item)
        return valid_discoveries

    async def _rank_item(self, item: Dict[str, Any]) -> float:
        """Rank an item using the LLM with Abstract-First protocol."""
        prompt = f"""RANKING TASK:
Title: {item['title']}
Abstract/Description: {item['abstract']}

On a scale of 0.0 to 1.0, how relevant is this to Cohezion (FLUME, 12D manifolds, SLM Swarms, Physics metaphors)?
Output ONLY the number.
"""
        try:
            response = await self._call_ollama(prompt, system_prompt=self.SYSTEM_PROMPT, temperature=0.0, max_tokens=10)
            return float(response.strip().split()[0])
        except Exception as e:
            logger.warning(f"Ranking failed for {item['title']}: {e}")
            return 0.0

    async def _synthesize_summary(self, item: Dict[str, Any]) -> str:
        """Generate high-density summary."""
        prompt = f"""SYNTHESIZE:
Title: {item['title']}
Abstract: {item['abstract']}

Generate a 12D-aware summary (Spatial, Time, Brane implications).
Keep it dense and actionable for the swarm.
"""
        return await self._call_ollama(prompt, system_prompt=self.SYSTEM_PROMPT, temperature=0.3)

    async def _persist_discovery(self, item: Dict[str, Any]):
        """Persist to SurrealDB as a research node."""
        node_id = f"research_{item['source']}_{item['id'].replace('/', '_')}"
        try:
            await self._db.connect()
            node = UniverseNode(
                id=node_id,
                content=item["summary"],
                node_type="external_research",
                physics_state=PhysicsState(
                    coherence=item["rank"],
                    complexity=0.7
                ),
                metadata={
                    "source": item["source"],
                    "original_title": item["title"],
                    "url": item["url"],
                    "rank": item["rank"],
                    "timestamp": time.time()
                }
            )
            await self._db.store_node(node)
            await self._db.close()
        except Exception as e:
            logger.warning(f"Failed to persist research node {node_id}: {e}")

if __name__ == "__main__":
    # Quick standalone test
    async def test():
        agent = NexusResearchAgent()
        report = await agent.process("mine_daily")
        print(report)
        await agent.close()

    asyncio.run(test())
