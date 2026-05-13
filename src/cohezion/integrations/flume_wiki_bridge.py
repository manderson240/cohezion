"""FLUME (VAE) + Wiki + Ouroboros Unified Integration.

Fluid Latent Understanding Through Manifold Encoding + Persistent Knowledge
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import torch

from cohezion.flume.bridge import HFEmbeddingBridge
from cohezion.flume.vae import FlumeVAE, FlumeVAEConfig
from cohezion.integrations.obsidian_wiki import ObsidianWiki
from cohezion.integrations.wiki_mirix_bridge import WikiMirixBridge
from cohezion.learning.ouroboros import ExecutionExhaust


logger = logging.getLogger(__name__)


class FlumeWikiBridge:
    """Bridge FLUME VAE embeddings with wiki-based knowledge management.

    This integration enables:
    - Embedding wiki pages as 256D thought vectors
    - Trajectory capture through wiki navigation
    - Semantic search using latent space similarity
    - Knowledge distillation from FLUME to wiki

    The 256D latent space represents the "Thinker" manifold where
    wiki knowledge, execution exhaust, and system state coexist.
    """

    def __init__(
        self,
        vault_path: Path | None = None,
        wiki: ObsidianWiki | None = None,
        vae_model: FlumeVAE | None = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        if wiki:
            self.wiki = wiki
        elif vault_path:
            self.wiki = ObsidianWiki(vault_path)
        else:
            raise ValueError("Must provide wiki or vault_path")

        self.vault_path = self.wiki.vault_path
        self.mirix_bridge = WikiMirixBridge(self.wiki)

        # Initialize FLUME components
        self.embedding_bridge = HFEmbeddingBridge(model_name=embedding_model, target_dim=256)

        if vae_model:
            self.vae = vae_model
        else:
            config = FlumeVAEConfig(z_dim=256, embed_dim=256)
            self.vae = FlumeVAE(config)
            self.vae.eval()

        self._init_structure()

    def _init_structure(self) -> None:
        """Create FLUME-specific wiki directories."""
        dirs = [
            self.vault_path / "wiki" / "flume" / "embeddings",
            self.vault_path / "wiki" / "flume" / "trajectories",
            self.vault_path / "wiki" / "flume" / "manifolds",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    async def embed_wiki_page(self, page_path: str | Path) -> torch.Tensor:
        """Embed a wiki page into the 256D FLUME latent space.

        Process:
        1. Read wiki page content
        2. Encode via sentence transformer (384D)
        3. Project to 256D
        4. Optional: Pass through VAE encoder for latent representation

        Returns:
            256D thought vector in the Thinker manifold
        """
        if isinstance(page_path, str):
            page_path = Path(page_path)

        # Get page content
        page = self.wiki._parse_page(page_path)
        content = page.content

        # Embed (384D -> 256D via projection)
        embedding = await self.embedding_bridge.get_flume_input(content)

        # Pass through VAE for latent representation
        with torch.no_grad():
            z, _mu, _logvar = self.vae.encoder(embedding.unsqueeze(0))
            latent = z.squeeze(0)

        # Store embedding reference in wiki
        embed_path = self.vault_path / "wiki" / "flume" / "embeddings" / f"{page_path.stem}.vec"
        torch.save(latent, embed_path)

        return latent

    async def search_by_embedding(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[Path, float]]:
        """Semantic search using FLUME embeddings.

        Returns wiki pages closest in latent space to query.
        """
        # Embed query
        query_emb = await self.embedding_bridge.get_flume_input(query)

        # Search all wiki pages
        results = []
        for category_dir in self.wiki.wiki_dir.iterdir():
            if not category_dir.is_dir():
                continue
            for md_file in category_dir.rglob("*.md"):
                try:
                    page_emb = await self.embed_wiki_page(md_file)
                    # Cosine similarity
                    similarity = torch.nn.functional.cosine_similarity(
                        query_emb.unsqueeze(0), page_emb.unsqueeze(0)
                    ).item()
                    results.append((md_file, similarity))
                except Exception as e:
                    logger.debug(f"Failed to embed {md_file}: {e}")

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def capture_trajectory(
        self,
        agent_id: str,
        path: list[Path],
        task: str,
    ) -> dict[str, Any]:
        """Capture agent trajectory through wiki as FLUME trajectory.

        A trajectory is a sequence of 256D vectors as the agent navigates
        the knowledge manifold.
        """
        from cohezion.flume.domain_encoder import EncodedTrajectoryPoint

        trajectory = []
        for i, page_path in enumerate(path):
            latent = await self.embed_wiki_page(page_path)
            point = EncodedTrajectoryPoint(
                timestamp=i,
                coords=latent.tolist(),
                action=f"read_{page_path.stem}",
                context={"task": task, "step": i},
            )
            trajectory.append(point)

        # Store trajectory in wiki
        traj_path = (
            self.vault_path / "wiki" / "flume" / "trajectories" / f"{agent_id}_{task[:30]}.md"
        )
        content = f"""# Trajectory: {agent_id}

## Task
{task}

## Path
""" + "\n".join([f"{i}. [[{p.stem}]]" for i, p in enumerate(path)])

        await self.wiki.create_wiki_page(
            path=str(traj_path.relative_to(self.vault_path)),
            content=content,
            category="trajectory",
            tags=["flume", "trajectory", agent_id],
        )

        return {
            "agent_id": agent_id,
            "task": task,
            "length": len(trajectory),
            "trajectory": trajectory,
            "path": path,
        }

    async def distill_knowledge(
        self,
        source_category: str = "exhaust",
        target_category: str = "distilled",
    ) -> Path:
        """Distill knowledge from FLUME embeddings to wiki synthesis.

        Process:
        1. Collect embeddings from source category
        2. Find clusters (semantic similarity)
        3. Generate synthesis pages capturing patterns
        """
        # Collect all embeddings from source
        source_dir = self.wiki.wiki_dir / source_category
        if not source_dir.exists():
            return None

        embeddings = []
        pages = []
        for md_file in source_dir.rglob("*.md"):
            try:
                emb = await self.embed_wiki_page(md_file)
                embeddings.append(emb)
                pages.append(md_file)
            except Exception:
                pass

        if not embeddings:
            return None

        # Simple centroid-based clustering (placeholder for real clustering)
        import torch

        vectors = torch.stack(embeddings)
        centroid = vectors.mean(dim=0)

        # Find closest to centroid
        similarities = torch.nn.functional.cosine_similarity(centroid.unsqueeze(0), vectors)
        representative_idx = similarities.argmax().item()
        representative = pages[representative_idx]

        # Create synthesis
        synthesis = await self.wiki.create_wiki_page(
            path=f"synthesis/distilled_{source_category}.md",
            content=f"""# Distilled: {source_category}

## Pattern Summary
Based on {len(pages)} source documents distilled via FLUME 256D manifold.

## Representative Source
[[{representative.stem}]]

## Key Themes
*Automatically extracted from latent space clustering*

## Recommendations
*Suggestions for system improvement*
""",
            category="synthesis",
            tags=["flume", "distilled", source_category],
        )

        return synthesis.path

    async def encode_exhaust(self, exhaust: ExecutionExhaust) -> torch.Tensor:
        """Encode execution exhaust as FLUME thought vector.

        Allows Ouroboros exhaust to be embedded in latent space for
        pattern recognition and clustering.
        """
        # Create text representation of exhaust
        text = f"""
Task: {exhaust.task_id}
Error: {exhaust.error_message or "No error"}
Coherence drop: {exhaust.coherence_drop}
Component: {exhaust.diagnostics.get("component", "unknown")}
Severity: {exhaust.diagnostics.get("severity", "low")}
"""

        embedding = await self.embedding_bridge.get_flume_input(text)

        # Store in embedding space
        filename = f"exhaust_{exhaust.task_id.replace('/', '_')[:50]}"
        embed_path = self.vault_path / "wiki" / "flume" / "embeddings" / f"{filename}.vec"
        torch.save(embedding, embed_path)

        return embedding


class FlumeOuroborosBridge(FlumeWikiBridge):
    """Extended bridge integrating FLUME with Ouroboros self-improvement.

    The Ouroboros loop now operates on the FLUME manifold:
    - Exhaust → 256D latent representation
    - Pattern detection via manifold clustering
    - Rewrite rules informed by latent space navigation
    """

    async def analyze_exhaust_patterns(self, component: str | None = None) -> dict:
        """Analyze failure patterns in FLUME latent space.

        Returns cluster info and anomalies detected.
        """
        # Collect exhaust embeddings
        embed_dir = self.vault_path / "wiki" / "flume" / "embeddings"
        if not embed_dir.exists():
            return {}

        embeddings = []
        for vec_file in embed_dir.glob("exhaust_*.vec"):
            emb = torch.load(vec_file)
            embeddings.append(emb)

        if len(embeddings) < 2:
            return {"clusters": 0, "anomalies": 0}

        # Simple centroid analysis
        vectors = torch.stack(embeddings)
        centroid = vectors.mean(dim=0)

        # Distance from centroid for anomaly detection
        distances = torch.norm(vectors - centroid, dim=1)

        # Anomalies: points > 2 std from mean
        mean_dist = distances.mean()
        std_dist = distances.std()
        anomalies = (distances > (mean_dist + 2 * std_dist)).sum().item()

        return {
            "clusters": 1,  # Placeholder for real clustering
            "total_points": len(embeddings),
            "anomalies": anomalies,
            "mean_distance": mean_dist.item(),
        }

    async def generate_trajectory_rewrite(
        self,
        exhaust: ExecutionExhaust,
        trajectory: list[torch.Tensor],
    ) -> str:
        """Generate rewrite rule based on FLUME trajectory analysis.

        Uses the latent space path to suggest system improvements.
        """
        # Analyze trajectory in latent space
        if len(trajectory) < 2:
            return "Insufficient trajectory data for rewrite"

        # Calculate trajectory smoothness
        vectors = torch.stack(trajectory)
        deltas = torch.diff(vectors, dim=0)
        avg_step = torch.norm(deltas, dim=1).mean()

        # Jumps (discontinuities) in latent space
        jumps = (torch.norm(deltas, dim=1) > avg_step * 2).sum().item()

        # Generate rule based on analysis
        if jumps > 0:
            return f"""
Trajectory shows {jumps} discontinuities.
Recommendation: Add intermediate steps for task {exhaust.task_id}
Coherence threshold: {exhaust.target_coherence}
"""

        return f"""
Smooth trajectory detected. Standard execution path validated.
Component: {exhaust.diagnostics.get("component", "unknown")}
"""
