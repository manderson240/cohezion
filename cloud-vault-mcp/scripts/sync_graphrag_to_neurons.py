#!/usr/bin/env python3
"""
Sync vault_memory → neuron + synapse tables.

Bridges the GraphRAG import system (vault_memory, informed_by) with the
MCP graph tools (neuron, synapse) so that graph_search, graph_neighborhood,
graph_hops, etc. can query the full vault.

Usage:
    cd cloud-vault-mcp && uv run python scripts/sync_graphrag_to_neurons.py
"""

import asyncio
import logging
import math
import time
from datetime import date

import httpx


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SURREALDB_URL = "http://localhost:8001"
NAMESPACE = "cohezion"
DATABASE = "vault"
AUTH = ("root", "root")

LAMBDA_DECAY = 0.05  # Half-life ~14 days


# ── Computation helpers (match reactor.py) ──────────────────────────────────


def derive_cluster(path: str) -> str:
    """Derive cluster_id from vault_memory path."""
    if path.startswith("cortex/"):
        return "cortex"
    elif path.startswith("cerebellum/"):
        return "cerebellum"
    elif path.startswith("decisions/"):
        return "decisions"
    elif path.startswith("patterns/"):
        return "patterns"
    return ""


def derive_aspect(cluster: str) -> str:
    """Cortex = knower (knowledge), cerebellum = thinker (operational)."""
    if cluster == "cortex":
        return "knower"
    elif cluster == "cerebellum":
        return "thinker"
    return "connective"


def compute_stage(word_count: int) -> str:
    if word_count < 100:
        return "embryo"
    elif word_count < 400:
        return "growing"
    return "mature"


def compute_activation(word_count: int, stage: str, tags: list, created_at: str) -> float:
    """Composite activation score matching reactor.py logic."""
    stage_scores = {"embryo": 0.1, "seedling": 0.3, "growing": 0.6, "mature": 1.0}
    stage_score = stage_scores.get(stage, 0.2)
    word_score = min(word_count / 400.0, 1.0)
    tag_score = min(len(tags) / 4.0, 1.0)
    completion = 0.5 * word_score + 0.3 * stage_score + 0.2 * tag_score

    # Recency from created_at
    recency = 0.0
    if created_at:
        try:
            d = date.fromisoformat(str(created_at)[:10])
            days = (date.today() - d).days
            recency = math.exp(-LAMBDA_DECAY * max(days, 0))
        except (ValueError, TypeError):
            pass

    return round(0.7 * completion + 0.3 * recency, 4)


def vault_memory_id_to_neuron_id(vm_id: str) -> str:
    """Convert vault_memory:slug → neuron:slug_md."""
    # vault_memory:agent_architecture → neuron:agent_architecture_md
    slug = vm_id.replace("vault_memory:", "")
    return f"neuron:{slug}_md"


def escape(text: str) -> str:
    """Escape for SurrealQL string literals."""
    return text.replace("\\", "\\\\").replace("'", "\\'")


# ── SurrealDB HTTP helpers ──────────────────────────────────────────────────


async def query(client: httpx.AsyncClient, sql: str) -> list[dict]:
    """Execute SurrealQL and return results (skipping USE statement result)."""
    resp = await client.post(
        f"{SURREALDB_URL}/sql",
        headers={
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "surreal-ns": NAMESPACE,
            "surreal-db": DATABASE,
        },
        auth=AUTH,
        content=sql,
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


# ── Main sync logic ─────────────────────────────────────────────────────────


async def main():
    start = time.time()
    logger.info("=" * 60)
    logger.info("SYNC vault_memory → neuron + synapse")
    logger.info("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Get pre-sync counts
        pre = await query(client, "SELECT count() FROM neuron GROUP ALL; SELECT count() FROM synapse GROUP ALL;")
        pre_neurons = pre[0]["result"][0]["count"] if pre[0]["result"] else 0
        pre_synapses = pre[1]["result"][0]["count"] if pre[1]["result"] else 0
        logger.info(f"Pre-sync: {pre_neurons} neurons, {pre_synapses} synapses")

        # 2. Fetch all vault_memory records
        vm_result = await query(client, "SELECT id, type, path, title, content, tags, created_at FROM vault_memory;")
        records = vm_result[0]["result"]
        logger.info(f"Found {len(records)} vault_memory records")

        # 3. Build neuron UPSERT queries in batches
        batch_size = 50
        neuron_count = 0
        id_map = {}  # vault_memory:x → neuron:x_md

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            statements = []

            for rec in batch:
                vm_id = rec["id"]
                path = rec.get("path", "")
                title = rec.get("title", "")
                content = rec.get("content", "")
                tags = rec.get("tags") or []
                created_at = rec.get("created_at", "")

                cluster = derive_cluster(path)
                aspect = derive_aspect(cluster)
                word_count = len(content.split()) if content else 0
                stage = compute_stage(word_count)
                activation = compute_activation(word_count, stage, tags, created_at)

                neuron_id = vault_memory_id_to_neuron_id(vm_id)
                id_map[vm_id] = neuron_id

                stmt = f"""UPSERT {neuron_id} SET
                    title = '{escape(title)}',
                    path = '{escape(path)}',
                    cluster_id = '{cluster}',
                    aspect = '{aspect}',
                    stage = '{stage}',
                    word_count = {word_count},
                    activation = {activation},
                    dim_completion = {round(min(word_count / 400.0, 1.0) * 0.5 + {"embryo": 0.1, "seedling": 0.3, "growing": 0.6, "mature": 1.0}.get(stage, 0.2) * 0.3 + min(len(tags) / 4.0, 1.0) * 0.2, 4)},
                    dim_recency = 0.0,
                    dim_bridging = 0.0,
                    tags = {tags},
                    synapse_in = 0,
                    synapse_out = 0,
                    created = time::now(),
                    modified = time::now(),
                    last_fired = time::now();"""

                statements.append(stmt)

            sql = "\n".join(statements)
            results = await query(client, sql)
            ok_count = sum(1 for r in results if r.get("status") == "OK")
            neuron_count += ok_count

            logger.info(f"  Batch {i // batch_size + 1}: {ok_count}/{len(batch)} neurons upserted")

        logger.info(f"Total neurons upserted: {neuron_count}")

        # 4. Fetch informed_by edges and convert to synapses
        logger.info("\nSyncing edges: informed_by → synapse...")
        edge_result = await query(client, "SELECT in, out FROM informed_by;")
        edges = edge_result[0]["result"]
        logger.info(f"Found {len(edges)} informed_by edges")

        # Delete existing synapse edges first (clean slate)
        await query(client, "DELETE synapse;")

        synapse_count = 0
        for i in range(0, len(edges), batch_size):
            batch = edges[i : i + batch_size]
            statements = []

            for edge in batch:
                source_vm = edge.get("in")
                target_vm = edge.get("out")
                if not source_vm or not target_vm:
                    continue

                # Convert vault_memory IDs to neuron IDs
                source_vm_str = str(source_vm) if not isinstance(source_vm, str) else source_vm
                target_vm_str = str(target_vm) if not isinstance(target_vm, str) else target_vm

                source_id = id_map.get(source_vm_str)
                target_id = id_map.get(target_vm_str)

                if not source_id or not target_id:
                    continue

                stmt = f"RELATE {source_id}->synapse->{target_id} SET link_type = 'explicit', created = time::now();"
                statements.append(stmt)

            if statements:
                sql = "\n".join(statements)
                results = await query(client, sql)
                ok_count = sum(1 for r in results if r.get("status") == "OK")
                synapse_count += ok_count

            logger.info(f"  Edge batch {i // batch_size + 1}: {min(len(batch), len(statements))} processed")

        logger.info(f"Total synapses created: {synapse_count}")

        # 5. Update synapse_in/synapse_out counts on neurons
        logger.info("\nUpdating synapse counts...")
        await query(client, """
            UPDATE neuron SET synapse_out = (SELECT count() FROM synapse WHERE in = $parent.id GROUP ALL)[0].count ?? 0;
            UPDATE neuron SET synapse_in = (SELECT count() FROM synapse WHERE out = $parent.id GROUP ALL)[0].count ?? 0;
        """)

        # 6. Post-sync counts
        post = await query(client, """
            SELECT count() FROM neuron GROUP ALL;
            SELECT count() FROM synapse GROUP ALL;
            SELECT cluster_id, count() AS n FROM neuron GROUP BY cluster_id ORDER BY n DESC;
            SELECT stage, count() AS n FROM neuron GROUP BY stage;
        """)
        post_neurons = post[0]["result"][0]["count"] if post[0]["result"] else 0
        post_synapses = post[1]["result"][0]["count"] if post[1]["result"] else 0

        elapsed = time.time() - start
        logger.info(f"\n{'=' * 60}")
        logger.info("SYNC COMPLETE")
        logger.info(f"{'=' * 60}")
        logger.info(f"  Neurons:  {pre_neurons} → {post_neurons}")
        logger.info(f"  Synapses: {pre_synapses} → {post_synapses}")
        logger.info(f"\n  By cluster:")
        for r in post[2]["result"]:
            cid = r.get("cluster_id") or "(none)"
            logger.info(f"    {cid:20s}: {r['n']}")
        logger.info(f"\n  By stage:")
        for r in post[3]["result"]:
            logger.info(f"    {r['stage']:20s}: {r['n']}")
        logger.info(f"\n  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
