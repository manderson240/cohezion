"""EVO (Exotic Vacuum Object) Pipeline — agentic journey → FLUME latent → SurrealDB + Obsidian.

An Exotic Vacuum Object is the low-energy FLUME latent representation of a completed
agentic journey. The 256D mu vector from JourneyToFlumeEncoder encodes the trajectory's
essential character: what the agent did, how it did it, and how well it performed.

Pipeline:
  JourneyTracker.Journey → TrajectoryStep[] → JourneyToFlumeEncoder → (mu, log_var)
  → evo_vacuum record in SurrealDB → Obsidian note in vault

The stored EVOs are consumed by ManifoldEnv as curriculum data: past high-coherence
journeys seed the initial state distribution, accelerating future agents.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np


if TYPE_CHECKING:
    from cohezion.compound.journey_tracker import Journey

logger = logging.getLogger(__name__)

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "vault"
VAULT_EVO_DIR = Path.home() / "vaults" / "cohezion-vault" / "EVOs"


def _surreal_query(sql: str) -> dict:
    req = urllib.request.Request(
        SURREAL_URL,
        data=sql.encode(),
        headers={
            "Content-Type": "text/plain",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
            "Accept": "application/json",
            "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
        },
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def _journey_to_agent_trajectory(journey: Journey) -> Any:
    """Convert JourneyTracker.Journey → AgentTrajectory for FLUME encoding."""
    from cohezion.universe.llm_training_bridge import AgentTrajectory, TrajectoryStep

    steps = []
    for point in journey.points:
        dims = point.dimensions
        state_12d = dims[:12].tolist() if len(dims) >= 12 else (dims.tolist() + [0.5] * (12 - len(dims)))
        # Dimensions 10-11 proxy for spin/tempic when available
        spin_coherence = float(dims[10]) if len(dims) > 10 else point.coherence
        tempic_field = float(dims[11]) if len(dims) > 11 else 1.0 - point.efficiency
        reward = point.coherence * point.efficiency
        steps.append(
            TrajectoryStep(
                state_12d=state_12d,
                action=point.operation_type,
                coherence=point.coherence,
                spin_coherence=spin_coherence,
                tempic_field=tempic_field,
                reward=reward,
            )
        )

    final_coherence = float(np.mean([p.coherence for p in journey.points])) if journey.points else 0.5
    return AgentTrajectory(
        agent_id=journey.execution_id,
        task_description=journey.task_description,
        steps=steps,
        final_coherence=final_coherence,
        total_reward=sum(s.reward for s in steps),
    )


def encode_journey_as_evo(journey: Journey) -> dict[str, Any] | None:
    """Encode a completed Journey as an Exotic Vacuum Object.

    Returns the EVO record dict, or None if encoding fails.
    """
    try:
        import torch

        from cohezion.flume.journey_encoder import JourneyToFlumeEncoder
    except ImportError as e:
        logger.warning("EVO encoding skipped — torch/journey_encoder not available: %s", e)
        return None

    if not journey.points:
        return None

    trajectory = _journey_to_agent_trajectory(journey)

    encoder = JourneyToFlumeEncoder()
    encoder.eval()
    with torch.no_grad():
        mu, log_var = encoder.encode_trajectory(trajectory)

    mu_np = mu.squeeze(0).numpy().tolist()
    log_var_np = log_var.squeeze(0).numpy().tolist()

    # Trajectory fingerprint for dedup
    traj_hash = hashlib.sha256(
        json.dumps(mu_np[:8]).encode()  # first 8 dims as fingerprint
    ).hexdigest()[:16]

    evo = {
        "id": f"evo_vacuum:{traj_hash}",
        "execution_id": journey.execution_id,
        "task": journey.task_description[:200],
        "operation_type": journey.operation_type,
        "phi_score": journey.phi_score,
        "coherence": float(np.mean([p.coherence for p in journey.points])),
        "efficiency": float(np.mean([p.efficiency for p in journey.points])),
        "n_steps": len(journey.points),
        "success": journey.final_success,
        "mu_256d": mu_np,
        "log_var_256d": log_var_np,
        "traj_hash": traj_hash,
        "created": datetime.now(UTC).isoformat(),
    }
    return evo


def persist_evo_to_surreal(evo: dict[str, Any]) -> bool:
    """Store EVO record in SurrealDB evo_vacuum table."""
    try:
        safe = {k: v for k, v in evo.items() if k not in ("mu_256d", "log_var_256d")}
        safe["mu_norm"] = float(np.linalg.norm(evo["mu_256d"]))
        # Store compressed: first 32 dims + norm (full 256 dims are too large for inline SQL)
        safe["mu_32d_preview"] = evo["mu_256d"][:32]
        sql = f"CREATE evo_vacuum:{evo['traj_hash']} CONTENT {json.dumps(safe)};"
        _surreal_query(sql)
        return True
    except Exception as e:
        logger.warning("EVO SurrealDB persist failed: %s", e)
        return False


def persist_evo_to_obsidian(evo: dict[str, Any]) -> Path | None:
    """Write an Obsidian note for the EVO."""
    try:
        VAULT_EVO_DIR.mkdir(parents=True, exist_ok=True)
        note_path = VAULT_EVO_DIR / f"evo_{evo['traj_hash']}.md"
        mu_preview = evo["mu_256d"][:8]
        mu_norm = float(np.linalg.norm(evo["mu_256d"]))
        note = f"""---
type: evo
traj_hash: {evo['traj_hash']}
execution_id: {evo['execution_id']}
phi_score: {evo['phi_score']:.4f}
coherence: {evo['coherence']:.4f}
efficiency: {evo['efficiency']:.4f}
n_steps: {evo['n_steps']}
success: {evo['success']}
mu_norm: {mu_norm:.4f}
created: {evo['created']}
tags: [evo, flume, agentic-journey]
---

# EVO {evo['traj_hash']}

**Task**: {evo['task']}
**Operation**: {evo['operation_type']}
**φ-score**: {evo['phi_score']:.4f} | **Coherence**: {evo['coherence']:.4f} | **Efficiency**: {evo['efficiency']:.4f}

## Latent Preview (first 8 of 256 dims)
`{mu_preview}`

## Connections
- SurrealDB: `evo_vacuum:{evo['traj_hash']}`
- Execution: `{evo['execution_id']}`

## Notes
High-coherence EVOs (φ > 0.7) seed ManifoldEnv initial state distribution.
"""
        note_path.write_text(note)
        return note_path
    except Exception as e:
        logger.warning("EVO Obsidian note failed: %s", e)
        return None


def capture_evo(journey: Journey) -> dict[str, Any] | None:
    """Full pipeline: Journey → encode → persist SurrealDB + Obsidian.

    Returns the EVO record or None on failure.
    """
    evo = encode_journey_as_evo(journey)
    if evo is None:
        return None

    surreal_ok = persist_evo_to_surreal(evo)
    note_path = persist_evo_to_obsidian(evo)

    logger.info(
        "EVO captured: %s | φ=%.3f | surreal=%s | obsidian=%s",
        evo["traj_hash"],
        evo["phi_score"],
        surreal_ok,
        note_path is not None,
    )
    return evo
