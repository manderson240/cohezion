#!/usr/bin/env python3
"""Live compound engineering with FLUME journey tracking.

Exercises the full Phase 6 pipeline:
  1. Select PRIME skills
  2. Execute via CompoundExecutor (with per-operation model routing)
  3. Track each execution as a FLUME journey (12D/2048D trajectory)
  4. Detect inflection points (coherence drops, score shifts)
  5. Persist journeys to SurrealDB (JSONL fallback)
  6. Load experience guidance from past journeys
  7. Report compound metrics + journey summaries

Usage:
  uv run python scripts/compound_live.py --skills 3 --model phi3:mini
  uv run python scripts/compound_live.py --skills 5 --model qwen3-coder:30b -v
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.inflection_detector import InflectionDetector
from cohezion.compound.journey_persistence import JourneyPersistence
from cohezion.compound.metrics import reset_collector
from cohezion.core.template_engine import TemplateEngine


logger = logging.getLogger(__name__)


def select_skills(n: int) -> list[tuple[str, str]]:
    """Select N PRIME skills with instructions.

    Returns list of (skill_name, first_instruction) tuples.
    """
    engine = TemplateEngine()
    specs = engine.parse_all()
    with_instructions = [s for s in specs if s.instructions]
    selected = with_instructions[:n]
    return [(s.name, s.instructions[0] if s.instructions else s.name) for s in selected]


async def run_live_cycle(
    num_skills: int = 3,
    model: str = "phi3:mini",
    verbose: bool = False,
) -> dict:
    """Run a live compound cycle with full journey tracking."""
    t0 = time.monotonic()

    # Reset singletons for clean state
    reset_collector()

    print(f"\n{'=' * 70}")
    print("  COMPOUND ENGINEERING — LIVE CYCLE WITH FLUME JOURNEYS")
    print(f"  Model: {model} | Skills: {num_skills}")
    print(f"{'=' * 70}\n")

    # --- Step 1: Select skills ---
    skills = select_skills(num_skills)
    print(f"[1/6] Selected {len(skills)} PRIME skills:")
    for name, inst in skills:
        print(f"  - {name}: {inst[:80]}...")

    # --- Step 2: Load experience guidance from past journeys ---
    jp = JourneyPersistence()
    print("\n[2/6] Loading experience guidance from past journeys...")
    all_guidance: dict[str, list] = {}
    for name, _ in skills:
        guidance = await jp.get_experience_guidance(name, limit=3)
        if guidance:
            all_guidance[name] = guidance
            best = max(guidance, key=lambda g: g.get("phi_score", 0))
            print(f"  {name}: {len(guidance)} past runs, best phi={best.get('phi_score', 0):.4f}")
        else:
            print(f"  {name}: no prior experience")

    # --- Step 3: Execute skills via CompoundExecutor ---
    from cohezion.compound.config import CompoundConfig
    from cohezion.swarm.compound_client import create_compound_client

    config = CompoundConfig(default_model=model)
    token_client = create_compound_client(
        ollama_host="http://localhost:11434",
        cache_max_size=256,
    )
    executor = CompoundExecutor(config=config, token_client=token_client)
    inflection = InflectionDetector()

    print(f"\n[3/6] Executing {len(skills)} skills with journey tracking...")
    results = []
    for i, (name, input_text) in enumerate(skills):
        print(f"\n  --- Skill {i + 1}/{len(skills)}: {name} ---")
        step_t0 = time.monotonic()

        try:
            result = await executor.execute_skill(
                skill_name=name,
                input_text=input_text,
                model=model,
                track_journey=True,
            )
            elapsed = time.monotonic() - step_t0
            results.append({"name": name, "result": result})
            print(f"  Output: {result.final_output[:120]}...")
            print(f"  Steps: {len(result.steps)} | Tokens: {result.total_tokens} | {elapsed:.1f}s")

            # Check for step-level inflection events
            for step in result.steps:
                inflection.check_step_failure(
                    step.get("tokens_used", 0),
                    step.get("step_index", 0),
                    name,
                )

        except KeyError as exc:
            print(f"  SKIPPED: {exc}")
        except Exception as exc:
            logger.exception("Execution failed for %s", name)
            print(f"  ERROR: {type(exc).__name__}: {exc}")

    # --- Step 4: Load persisted journeys ---
    print("\n[4/6] Loading persisted FLUME journeys...")
    recent_journeys = await jp.load_journeys(limit=len(skills))
    for j in recent_journeys:
        jid = j.get("id", j.get("journey_id", "?"))
        print(f"  Journey {str(jid)[:16]}...")
        print(f"    Skill: {j.get('intent', '?')[:50]}")
        print(f"    Status: {j.get('status', '?')}")
        print(f"    Coherence: {j.get('final_coherence', 0):.4f}")
        print(f"    Phi: {j.get('final_phi_score', 0):.4f}")
        traj_count = j.get("trajectory_count", 0)
        print(f"    Trajectory points: {traj_count}")

    if not recent_journeys:
        print("  (no persisted journeys found)")

    # --- Step 5: Inflection report ---
    history = inflection.get_history()
    print(f"\n[5/6] Inflection events: {len(history)}")
    for evt in history:
        print(f"  [{evt['severity']}] {evt['event_type']}: {json.dumps(evt['details'], default=str)[:100]}")

    # --- Step 6: Token metrics ---
    metrics = token_client.get_metrics()
    print("\n[6/6] Token efficiency metrics:")
    print(f"  Total calls: {metrics.get('total_calls', 0)}")
    print(f"  Cache hit rate: {metrics.get('cache_hit_rate', 0):.1%}")
    print(f"  Tokens saved: {metrics.get('tokens_saved', 0)}")
    print(f"  Model usage: {json.dumps(metrics.get('model_usage', {}))}")

    total_elapsed = time.monotonic() - t0
    total_tokens = sum(r["result"].total_tokens for r in results)
    skills_ok = len(results)

    print(f"\n{'=' * 70}")
    print(f"  CYCLE COMPLETE in {total_elapsed:.1f}s")
    print(f"  Skills: {skills_ok}/{len(skills)} succeeded")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Journeys persisted: {len(recent_journeys)}")
    print(f"  Inflection events: {len(history)}")
    print(f"  Experience guidance: {sum(len(v) for v in all_guidance.values())} records")
    print(f"{'=' * 70}\n")

    return {
        "skills_executed": skills_ok,
        "total_tokens": total_tokens,
        "total_duration_s": round(total_elapsed, 2),
        "journeys_persisted": len(recent_journeys),
        "inflection_events": len(history),
        "token_metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Live compound cycle with FLUME journeys")
    parser.add_argument("--skills", type=int, default=3, help="Number of skills")
    parser.add_argument("--model", type=str, default="phi3:mini", help="Ollama model")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")

    asyncio.run(
        run_live_cycle(
            num_skills=args.skills,
            model=args.model,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
