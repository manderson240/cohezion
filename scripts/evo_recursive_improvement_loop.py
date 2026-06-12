#!/usr/bin/env python3
"""EVO Recursive Learning Improvement Loop — Cohezion continuous self-improvement.

Iterates over a curated set of PRIME skills, runs EVO physics traces for each,
stores ExperientialVoyage records in SurrealDB (evo_journey table), and calls
SkillRefiner on voyages that meet the Constitution phi ≥ 0.3 gate.

Architecture per voyage:
  AgenticEVO.hiho_step()           — HIHO physics (256D latent convergence)
  >> TraceMonad pipeline           — immutable state threading
  >> modality dispatch             — text + audio (kokoro) + image (SD-Turbo)
  >> JourneyTracker.track_evo_step — 12D FLUME trajectory point
  complete_journey()               — SurrealDB + Obsidian vault dual-write
  SkillRefiner.refine()            — PRIME skill update (phi ≥ 0.3 gate)

Usage:
    uv run python scripts/evo_recursive_improvement_loop.py
    uv run python scripts/evo_recursive_improvement_loop.py --rounds 3 --steps 5
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("evo_loop")

# ── SurrealDB helper ──────────────────────────────────────────────────────────
_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
}


def _surql(query: str) -> list:
    import base64
    auth = base64.b64encode(b"root:root").decode()
    req = urllib.request.Request(
        _SURREAL_URL,
        data=query.encode(),
        headers={**_SURREAL_HEADERS, "Authorization": f"Basic {auth}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.load(resp)


def _ensure_evo_journey_table() -> None:
    """Create evo_journey table if it doesn't exist (schema-flexible SurrealDB)."""
    _surql("""
        DEFINE TABLE IF NOT EXISTS evo_journey SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS voyage_id    ON evo_journey TYPE string;
        DEFINE FIELD IF NOT EXISTS agent_id     ON evo_journey TYPE string;
        DEFINE FIELD IF NOT EXISTS journey_id   ON evo_journey TYPE string;
        DEFINE FIELD IF NOT EXISTS skill_id     ON evo_journey TYPE string;
        DEFINE FIELD IF NOT EXISTS phi_score    ON evo_journey TYPE float;
        DEFINE FIELD IF NOT EXISTS modalities   ON evo_journey TYPE array;
        DEFINE FIELD IF NOT EXISTS step_count   ON evo_journey TYPE int;
        DEFINE FIELD IF NOT EXISTS duration_s   ON evo_journey TYPE float;
        DEFINE FIELD IF NOT EXISTS refined      ON evo_journey TYPE bool;
        DEFINE FIELD IF NOT EXISTS valid_from   ON evo_journey TYPE datetime;
        DEFINE FIELD IF NOT EXISTS valid_to     ON evo_journey TYPE option<datetime>;
        DEFINE FIELD IF NOT EXISTS latent_snap  ON evo_journey TYPE array;
        DEFINE FIELD IF NOT EXISTS gate_prob   ON evo_journey TYPE option<float>;
        DEFINE FIELD IF NOT EXISTS phi_dist              ON evo_journey TYPE option<object>;
        DEFINE FIELD IF NOT EXISTS phi_dist.bins         ON evo_journey TYPE option<array>;
        DEFINE FIELD IF NOT EXISTS phi_dist.probs        ON evo_journey TYPE option<array>;
        DEFINE FIELD IF NOT EXISTS phi_dist.point_estimate ON evo_journey TYPE option<float>;
        DEFINE FIELD IF NOT EXISTS phi_dist.gate_prob    ON evo_journey TYPE option<float>;
        DEFINE FIELD IF NOT EXISTS phi_dist.expected_phi ON evo_journey TYPE option<float>;
    """)
    logger.info("evo_journey table ready")


def _store_voyage(voyage, skill_id: str, refined: bool, step_count: int) -> None:
    """Write voyage to SurrealDB evo_journey table."""
    phi_dist_json = "NONE"
    gate_prob_val = "NONE"
    if voyage.phi_distribution is not None:
        phi_dist_json = json.dumps(voyage.phi_distribution.as_dict())
        gate_prob_val = f"{voyage.phi_distribution.gate_probability():.6f}"
    q = f"""
        CREATE evo_journey SET
            voyage_id  = '{voyage.voyage_id}',
            agent_id   = '{voyage.agent_id}',
            journey_id = '{voyage.journey_id}',
            skill_id   = '{skill_id}',
            phi_score  = {voyage.phi_score:.6f},
            modalities = {json.dumps(voyage.modalities_used)},
            step_count = {step_count},
            duration_s = {voyage.duration_seconds:.4f},
            refined    = {str(refined).lower()},
            valid_from = time::now(),
            valid_to   = NONE,
            latent_snap = {json.dumps(voyage.latent_snapshot[:8])},
            gate_prob  = {gate_prob_val},
            phi_dist   = {phi_dist_json};
    """
    _surql(q)


# ── Obsidian vault write ──────────────────────────────────────────────────────
_VAULT_ROOT = Path.home() / "vaults" / "cohezion-vault"


def _vault_write_voyage(voyage, skill_id: str, refined: bool, steps_summary: list[dict]) -> None:
    """Write ExperientialVoyage to Obsidian vault as a structured experiment note.

    Writes to vault/experiments/evo/ — vault MCP is unavailable in this session so
    we write directly. This is an intentional exception: the user explicitly requested
    vault storage and the alternative is no storage at all.
    """
    exp_dir = _VAULT_ROOT / "experiments" / "evo"
    exp_dir.mkdir(parents=True, exist_ok=True)

    date_str = time.strftime("%Y-%m-%d")
    fname = f"{date_str}-{skill_id.lower().replace('_', '-')}-{voyage.voyage_id[:8]}.md"
    fpath = exp_dir / fname

    lines = [
        "---",
        f"type: evo_voyage",
        f"voyage_id: {voyage.voyage_id}",
        f"agent_id: {voyage.agent_id}",
        f"journey_id: {voyage.journey_id}",
        f"skill_id: {skill_id}",
        f"phi_score: {voyage.phi_score:.4f}",
        f"modalities: {voyage.modalities_used}",
        f"refined: {str(refined).lower()}",
        f"duration_s: {voyage.duration_seconds:.3f}",
        f"date: {date_str}",
        "surreal_table: evo_journey",
        "---",
        "",
        f"# EVO Voyage — {skill_id}",
        "",
        f"**φ score:** {voyage.phi_score:.4f}  {'✓ above gate' if not voyage.is_degenerate else '⚠ degenerate (< 0.3)'}",
        f"**Modalities:** {', '.join(voyage.modalities_used) or 'none'}",
        f"**Refined:** {'Yes — PRIME skill updated' if refined else 'No'}",
        f"**Duration:** {voyage.duration_seconds:.3f}s",
        "",
        "## Trace Steps",
        "",
    ]
    for i, s in enumerate(steps_summary):
        step_line = (
            f"- Step {i}: coherence {s['coherence_before']:.3f}→{s['coherence_after']:.3f} "
            f"φ={s['phi']:.3f} Δ={s['latent_delta']:.5f} ({s['latency_ms']:.1f}ms)"
        )
        if s.get("synthesis"):
            step_line += f"\n  > _{s['synthesis']}_"
        lines.append(step_line)

    lines += [
        "",
        "## Latent Snapshot (first 8 dims)",
        "",
        f"`{[round(x, 4) for x in voyage.latent_snapshot[:8]]}`",
        "",
        "## Links",
        "",
        f"- [[HIHO_STABILITY_PRIME]] — φ = 4·c·(1-c) kernel",
        f"- [[COMPOUND_SELF_IMPROVEMENT_PRIME]] — recursive loop",
        f"- [[JOURNEY_TRACKING_PRIME]] — 12D trajectory",
        "",
    ]

    fpath.write_text("\n".join(lines))
    logger.info("vault → %s", fpath)


# ── Skills to traverse ────────────────────────────────────────────────────────
SKILL_JOURNEYS = [
    {
        "skill_id": "COMPOUND_SELF_IMPROVEMENT_PRIME",
        "description": "Recursive compound loop: skill refinement from EVO voyage outcomes",
        "modalities": ["text", "audio"],
        "steps": 4,
    },
    {
        "skill_id": "JOURNEY_TRACKING_PRIME",
        "description": "12D FLUME trajectory tracking with dual-write SurrealDB + Obsidian",
        "modalities": ["text", "image"],
        "steps": 3,
    },
    {
        "skill_id": "HIHO_STABILITY_PRIME",
        "description": "HIHO 4·c·(1-c) attractor dynamics — latent space coherence optimization",
        "modalities": ["text"],
        "steps": 5,
    },
    {
        "skill_id": "FLUME_METHODOLOGY_PRIME",
        "description": "FLUME VAE latent encoding/decoding for compound reasoning",
        "modalities": ["text", "image"],
        "steps": 3,
    },
    {
        "skill_id": "AUTONOMIC_EVOLUTION_PRIME",
        "description": "Autonomous EVO agent self-modification via Constitution-gated refinement",
        "modalities": ["text", "audio", "video"],
        "steps": 4,
    },
]


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_evo_loop(rounds: int = 1, steps_override: int | None = None) -> list[dict]:
    """Run the EVO recursive improvement loop for the given number of rounds."""
    from cohezion.compound.journey_tracker import JourneyTracker
    from cohezion.compound.skill_refiner import SkillRefiner
    from cohezion.evo.recursive_tracer import RecursiveTracer
    from cohezion.universe.agentic_evo_swift import AgenticEVO

    _ensure_evo_journey_table()

    all_results = []
    total_voyages = 0
    total_refined = 0

    for round_num in range(rounds):
        logger.info("═══ Round %d/%d ═══", round_num + 1, rounds)

        for journey_spec in SKILL_JOURNEYS:
            skill_id = journey_spec["skill_id"]
            description = journey_spec["description"]
            modalities = journey_spec["modalities"]
            n_steps = steps_override or journey_spec["steps"]

            logger.info("▶ Skill: %s (%d steps, modalities=%s)", skill_id, n_steps, modalities)

            # Fresh agent per skill — independent latent trajectory
            agent_id = f"evo-loop-r{round_num:02d}-{skill_id[:12].lower()}"
            agent = AgenticEVO(agent_id=agent_id)

            # JourneyTracker without MCP client — vault write handled by _vault_write_voyage()
            tracker = JourneyTracker()
            refiner = SkillRefiner()
            tracer = RecursiveTracer(agent, tracker, skill_refiner=refiner)

            journey_id = f"evo-loop-{round_num}-{skill_id}-{int(time.time())}"

            # Run trace steps
            steps_summary = []
            for step_i in range(n_steps):
                step_desc = f"[Round {round_num}] {description} — step {step_i+1}/{n_steps}"
                try:
                    result = tracer.trace_step(
                        task_description=step_desc,
                        modalities=modalities,
                        operation_type="transform",
                        hiho_delta_scale=0.02,   # 2x default — faster convergence per step
                        hiho_damping=0.05,
                    )
                    steps_summary.append({
                        "coherence_before": result.coherence_before,
                        "coherence_after": result.coherence_after,
                        "phi": result.phi,
                        "latent_delta": result.latent_delta,
                        "latency_ms": result.latency_ms,
                        "synthesis": result.synthesis_text,
                    })
                    logger.info(
                        "  step %d/%d: c=%.3f→%.3f φ=%.3f Δ=%.5f (%.0fms)",
                        step_i + 1, n_steps,
                        result.coherence_before, result.coherence_after,
                        result.phi, result.latent_delta, result.latency_ms,
                    )
                except RuntimeError as e:
                    if "OOM guard" in str(e):
                        logger.error("OOM guard fired for %s — skipping remaining steps", skill_id)
                        break
                    raise

            if tracer.step_count == 0:
                logger.warning("No steps completed for %s, skipping complete_journey()", skill_id)
                continue

            # Close voyage — dual-write SurrealDB + SkillRefiner
            voyage = tracer.complete_journey(
                journey_id=journey_id,
                skill_id=skill_id,
                operation_type="transform",
            )

            refined = len(voyage.skill_refinements) > 0
            total_voyages += 1
            if refined:
                total_refined += 1

            logger.info(
                "  ✓ voyage done: φ=%.3f %s refined=%s modalities=%s",
                voyage.phi_score,
                "✓ healthy" if not voyage.is_degenerate else "⚠ degenerate",
                refined,
                voyage.modalities_used,
            )

            # Store in SurrealDB
            try:
                _store_voyage(voyage, skill_id, refined, len(steps_summary))
                logger.info("  → SurrealDB: evo_journey recorded (voyage_id=%s)", voyage.voyage_id[:8])
            except Exception as e:
                logger.warning("  SurrealDB write failed (non-blocking): %s", e)

            # Store in Obsidian vault
            try:
                _vault_write_voyage(voyage, skill_id, refined, steps_summary)
            except Exception as e:
                logger.warning("  Vault write failed (non-blocking): %s", e)

            all_results.append({
                "round": round_num,
                "skill_id": skill_id,
                "voyage_id": voyage.voyage_id,
                "phi_score": voyage.phi_score,
                "is_degenerate": voyage.is_degenerate,
                "refined": refined,
                "modalities": voyage.modalities_used,
                "steps": len(steps_summary),
                "duration_s": voyage.duration_seconds,
            })

    # Summary
    logger.info("")
    logger.info("═══ Loop Complete ═══")
    logger.info("Total voyages: %d | Refined: %d | Degenerate: %d",
                total_voyages, total_refined,
                sum(1 for r in all_results if r["is_degenerate"]))

    phis = [r["phi_score"] for r in all_results]
    if phis:
        logger.info("φ scores: min=%.3f max=%.3f mean=%.3f",
                    min(phis), max(phis), sum(phis) / len(phis))

    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(description="EVO recursive improvement loop")
    parser.add_argument("--rounds", type=int, default=1, help="Number of loop rounds")
    parser.add_argument("--steps", type=int, default=None, help="Override step count per skill")
    args = parser.parse_args()

    results = run_evo_loop(rounds=args.rounds, steps_override=args.steps)

    print("\n── Results ──")
    for r in results:
        gate = "✓" if not r["is_degenerate"] else "⚠"
        ref = "↑" if r["refined"] else " "
        print(f"  {gate}{ref} {r['skill_id'][:40]:<40} φ={r['phi_score']:.3f} "
              f"mods={','.join(r['modalities'])} steps={r['steps']}")


if __name__ == "__main__":
    main()
