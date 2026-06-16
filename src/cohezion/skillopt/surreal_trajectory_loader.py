"""Load SkillOpt training trajectories from Cohezion's SurrealDB execution traces.

Maps SurrealDB execution records → SkillOpt trajectory format so
`skillopt_sleep` can use the existing trace corpus without re-running agents.

SurrealDB query pattern (ns=cohezion, db=main):
    SELECT skill_name, input, output, score, status
    FROM execution_trace
    WHERE skill_name = $skill AND status != 'error'
    ORDER BY created_at DESC
    LIMIT 200;
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_SURREAL_URL = "http://127.0.0.1:8001/sql"
_SURREAL_AUTH = ("root", "root")
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
}


def _query(sql: str) -> list[dict[str, Any]]:
    resp = httpx.post(
        _SURREAL_URL,
        content=sql,
        headers=_SURREAL_HEADERS,
        auth=_SURREAL_AUTH,
        timeout=30.0,
    )
    resp.raise_for_status()
    results = resp.json()
    if isinstance(results, list) and results:
        return results[0].get("result", [])
    return []


def load_trajectories(skill_name: str, limit: int = 200) -> list[dict[str, Any]]:
    """Return SkillOpt-format trajectories for a given skill from SurrealDB traces."""
    rows = _query(
        f"SELECT skill_name, input, output, score, status, created_at "
        f"FROM execution_trace "
        f"WHERE skill_name = '{skill_name}' AND status != 'error' "
        f"ORDER BY created_at DESC "
        f"LIMIT {limit};"
    )
    trajectories = []
    for row in rows:
        trajectories.append(
            {
                "input": row.get("input", ""),
                "output": row.get("output", ""),
                "score": float(row.get("score") or 0.0),
                "metadata": {"skill": skill_name, "status": row.get("status")},
            }
        )
    logger.debug("Loaded %d trajectories for skill '%s'", len(trajectories), skill_name)
    return trajectories


def dump_corpus(skill_name: str, output_dir: Path, limit: int = 200) -> Path:
    """Write trajectories as JSONL corpus file for skillopt_sleep."""
    output_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = output_dir / f"{skill_name}_corpus.jsonl"
    trajectories = load_trajectories(skill_name, limit=limit)
    with corpus_path.open("w") as f:
        for t in trajectories:
            f.write(json.dumps(t) + "\n")
    logger.info("Wrote %d trajectories to %s", len(trajectories), corpus_path)
    return corpus_path


def list_skills_with_traces(min_traces: int = 10) -> list[str]:
    """Return skill names that have enough traces for SkillOpt training."""
    rows = _query(
        f"SELECT skill_name, count() AS n "
        f"FROM execution_trace "
        f"GROUP BY skill_name "
        f"HAVING n >= {min_traces} "
        f"ORDER BY n DESC;"
    )
    return [r["skill_name"] for r in rows if r.get("skill_name")]
