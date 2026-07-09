# URL open targets are internal/config-allowlisted, not user-supplied
"""Training history API routes — expose SurrealDB training_run data.

Enables Anima Dashboard to visualize compound training loop progression.
"""

from __future__ import annotations

import logging
from base64 import b64encode
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel


logger = logging.getLogger(__name__)

training_router = APIRouter(prefix="/api/training", tags=["training"])

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_HEADERS = {
    "Accept": "application/json",
    "surreal-ns": "cohezion",
    "surreal-db": "cohezion",
    "Authorization": "Basic " + b64encode(b"root:root").decode(),
}


async def _surreal_query(sql: str) -> list[dict[str, Any]]:
    """Execute SurrealQL and return results."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SURREAL_URL,
                content=sql.encode(),
                headers=SURREAL_HEADERS,
                timeout=5.0,
            )
            data = resp.json()
            if data and data[0].get("status") == "OK":
                return data[0].get("result", [])
    except Exception as e:
        logger.debug("SurrealDB query failed: %s", e)
    return []


class TrainingRun(BaseModel):
    algorithm: str | None = None
    timesteps: int | None = None
    reward_mode: str | None = None
    reward: float | None = None
    coherence: float | None = None
    stability: float | None = None
    convergence_rate: float | None = None
    random_reward: float | None = None
    greedy_reward: float | None = None
    diagnostic: str | None = None


class TrainingHistoryResponse(BaseModel):
    runs: list[TrainingRun]
    best_reward: float | None = None
    best_algorithm: str | None = None
    total_runs: int = 0


@training_router.get("/history", response_model=TrainingHistoryResponse)
async def get_training_history():
    """Get all training runs from SurrealDB, ordered by reward descending."""
    rows = await _surreal_query(
        "SELECT algorithm, timesteps, reward_mode, reward, coherence, stability, "
        "convergence_rate, random_reward, greedy_reward, diagnostic "
        "FROM training_run ORDER BY reward DESC;"
    )

    runs = [TrainingRun(**{k: v for k, v in r.items() if k != "id"}) for r in rows]
    best = runs[0] if runs else None

    return TrainingHistoryResponse(
        runs=runs,
        best_reward=best.reward if best else None,
        best_algorithm=f"{best.algorithm}+{best.reward_mode}" if best else None,
        total_runs=len(runs),
    )


@training_router.get("/best", response_model=TrainingRun)
async def get_best_run():
    """Get the single best training run by reward."""
    rows = await _surreal_query(
        "SELECT algorithm, timesteps, reward_mode, reward, coherence, stability, "
        "convergence_rate, random_reward, greedy_reward, diagnostic "
        "FROM training_run ORDER BY reward DESC LIMIT 1;"
    )
    if rows:
        return TrainingRun(**{k: v for k, v in rows[0].items() if k != "id"})
    return TrainingRun()


@training_router.get("/matrix")
async def get_algorithm_reward_matrix():
    """Get the 2x2 algorithm-reward matrix (best run per algo+reward combo)."""
    rows = await _surreal_query(
        "SELECT algorithm, reward_mode, math::max(reward) as best_reward, count() as runs "
        "FROM training_run GROUP BY algorithm, reward_mode;"
    )
    return {"matrix": rows}
