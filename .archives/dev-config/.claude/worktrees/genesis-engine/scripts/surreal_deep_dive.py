import asyncio
import json
import logging

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SurrealDeepDive")


async def deep_dive():
    client = SurrealClient()
    await client.connect()

    logger.info("🔭 Starting SurrealDB Deep Dive...")

    # helper to get result list
    def get_res(r):
        if not r:
            return []
        if isinstance(r, list):
            if len(r) > 0 and isinstance(r[0], dict) and "result" in r[0]:
                return r[0]["result"]
            return r
        return []

    # 1. Experience Statistics
    res_count = await client.query("SELECT count() FROM universe_nodes GROUP ALL")
    count_data = get_res(res_count)
    total_nodes = count_data[0].get("count", 0) if count_data else 0

    # 2. Model Distribution
    res_models = await client.query(
        "SELECT metadata.model as model, count() FROM universe_nodes GROUP BY model"
    )
    models_data = get_res(res_models)
    model_dist = {row["model"]: row["count"] for row in models_data if "model" in row}

    # 3. High-Phi Thoughts
    res_phi = await client.query(
        "SELECT content, metadata.phi_score as phi, metadata.agent as agent FROM universe_nodes WHERE metadata.phi_score > 0.85 ORDER BY metadata.phi_score DESC LIMIT 5"
    )
    phi_data = get_res(res_phi)

    # 4. Physics State Correlations
    res_stable = await client.query(
        "SELECT count() FROM universe_nodes WHERE physics_state.coherence > 0.9 AND physics_state.stability > 0.9 GROUP ALL"
    )
    stable_data = get_res(res_stable)
    stable_nodes = stable_data[0].get("count", 0) if stable_data else 0

    # 5. Gaia Lifecycle - Spawned agents
    res_gaia = await client.query(
        "SELECT count() FROM universe_nodes WHERE content CONTAINS 'Gaia spawned new agent' GROUP ALL"
    )
    gaia_data = get_res(res_gaia)
    total_spawns = gaia_data[0].get("count", 0) if gaia_data else 0

    report = {
        "summary": {
            "total_experiences": total_nodes,
            "high_coherence_states": stable_nodes,
            "gaia_agent_spawns": total_spawns,
        },
        "model_matrix": model_dist,
        "pinnacle_insights": [
            {
                "agent": t.get("agent", "unknown"),
                "phi": t.get("phi", 0.0),
                "excerpt": t.get("content", "")[:200] + "...",
            }
            for t in phi_data
        ],
    }

    with open("surreal_insights.json", "w") as f:
        json.dump(report, f, indent=4)

    logger.info(f"✅ Deep dive complete. {total_nodes} nodes analyzed.")
    await client.close()


if __name__ == "__main__":
    asyncio.run(deep_dive())
