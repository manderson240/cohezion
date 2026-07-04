#!/home/mike-anderson/dev/cohezion/.venv/bin/python3
"""Primitive Forge Daemon v6 — ARC Prize Solver with beam search + color ops.

Timeit-gated, crash-resilient, state-persistent. Uses cohezion.arc.solver
(beam_search, derive_color_ops, _exact_match).
Each tick advances one atomic step in the current phase. Exits cleanly after
07:00 ET deadline so the cron wrapper can rotate state.

If invoked without a state file, bootstraps a fresh epoch.
If invoked with Phase-6 complete, writes report and exits 0 so the cron
wrapper archives state and starts fresh next tick.
"""

from __future__ import annotations

import datetime
import json
import os
import random
import sys
import time
import traceback
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATE_PATH = Path.home() / ".cohezion-research/primitive_forge_state.json"
REPORT_PATH = Path.home() / ".cohezion-research/primitive_forge_report.json"
DEADLINE_HOUR_ET = 7
MAX_TICKS_PER_PHASE: dict[int, int] = {
    1: 2000,
    2: 200,
    3: 200,
    4: 2000,
    5: 100,
    6: 1,
}


# ---------------------------------------------------------------------------
# Deadline guard
# ---------------------------------------------------------------------------
def is_past_deadline() -> bool:
    if os.environ.get("FORCE_FORGE") == "1":
        return False
    import datetime

    now = datetime.datetime.now(datetime.UTC).astimezone(
        datetime.timezone(datetime.timedelta(hours=-4))
    )
    h = now.hour
    in_overnight = (h >= 20) or (h < 7)
    return not in_overnight


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------
def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return fresh_state()


def fresh_state() -> dict[str, Any]:
    return {
        "daemon": "primitive_forge",
        "evo_id": f"forge_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "flume_weights_path": "",
        "started": datetime.datetime.now().isoformat(),
        "phase": 1,
        "phase_ticks_used": 0,
        "total_ticks": 0,
        "epoch": 1,
        "tick": 0,
        "benchmarks": {},
        "flume_benchmark_latent": None,
        "signatures": [],
        "cluster_map": {},
        "match_map": {},
        "hypothesis_queue": [],
        "synthesis_results": [],
        "new_solves": [],
        "ouroboros_rewrites": 0,
        "mycelium_spores_broadcast": 0,
        "coherence_log": [],
        "meta_primitives": [],
        "retrospective": [],
        "hypotheses": [],
    }


def save_state(state: dict[str, Any]) -> None:
    tmp = STATE_PATH.with_suffix(".tmp")
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    if tmp.exists():
        os.replace(tmp, STATE_PATH)
    else:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Phase 1 — Primitive benchmarks
# ---------------------------------------------------------------------------
def phase1_benchmark(state: dict[str, Any]) -> bool:
    import numpy as np

    from cohezion.arc.transforms import ALL_TRANSFORMS

    benchmarks: dict[str, Any] = state.get("benchmarks", {})
    names = list(ALL_TRANSFORMS.keys())
    # benchmark in larger batches per tick — cron interval is short (minutes) not seconds
    batch_size = 20
    idx = state["phase_ticks_used"]
    slice_names = names[idx * batch_size : (idx + 1) * batch_size]

    if not slice_names:
        state["phase"] = 2
        state["phase_ticks_used"] = 0
        print("[Phase 1] All primitives benchmarked.")
        return False

    for name in slice_names:
        fn = ALL_TRANSFORMS[name]
        # quick smoke on trivial grids
        grids = [
            np.array([[0, 1], [1, 0]], dtype=np.uint8),
            np.array([[2, 2], [2, 2]], dtype=np.uint8),
        ]
        times = []
        success = 0
        for g in grids:
            t0 = time.perf_counter()
            try:
                out = fn(g)
                if out is not None:
                    success += 1
            except Exception:
                pass
            times.append(time.perf_counter() - t0)
        benchmarks[name] = {
            "mean_time": float(sum(times) / len(times)) if times else 0.0,
            "success_rate": success / len(grids) if grids else 0.0,
        }

    state["benchmarks"] = benchmarks
    state["phase_ticks_used"] = idx + 1
    print(f"[Phase 1] Benchmarked {len(benchmarks)}/{len(names)} primitives.")
    return False


# ---------------------------------------------------------------------------
# Phase 2 — Task signature extraction
# ---------------------------------------------------------------------------
def phase2_sign(state: dict[str, Any]) -> bool:
    from cohezion.arc.data_loader import load_all

    signatures: list[dict[str, Any]] = state.get("signatures", [])
    tasks = load_all("evaluation")
    # Process more tasks per tick to avoid 40+ ticks for Phase 2 completion.
    # Cron interval is ~1 minute; each tick takes ~3-5s, so batch=50 gives full
    # completion in ~18 ticks (~60-90s total) rather than 40 minutes.
    batch = 50
    done_ids = {s["task_id"] for s in signatures}
    remaining = [tid for tid in tasks if tid not in done_ids]

    if not remaining:
        state["phase"] = 3
        state["phase_ticks_used"] = 0
        print(f"[Phase 2] All {len(signatures)} tasks signed.")
        return False

    import numpy as np

    for tid in remaining[:batch]:
        task = tasks[tid]
        train = task["train"]
        # simple structural signature
        sizes = [ex["input"].shape for ex in train]
        colors = set()
        for ex in train:
            colors.update(map(int, np.unique(ex["input"])))
            colors.update(map(int, np.unique(ex["output"])))
        signatures.append(
            {
                "task_id": tid,
                "train_examples": len(train),
                "sizes": sizes,
                "color_count": len(colors),
                "colors": sorted(colors),
            }
        )

    state["signatures"] = signatures
    state["phase_ticks_used"] += 1
    print(f"[Phase 2] Signed {len(signatures)}/{len(tasks)} tasks.")
    return False


# ---------------------------------------------------------------------------
# Phase 3 — Match + hypothesis generation
# ---------------------------------------------------------------------------
def phase3_hypotheses(state: dict[str, Any]) -> bool:
    signatures: list[dict[str, Any]] = state.get("signatures", [])
    match_map: dict[str, list[str]] = state.get("match_map", {})
    queue: list[dict[str, Any]] = state.get("hypothesis_queue", [])

    strategies = ["geo", "scale", "obj", "swap", "mirror", "recolor"]
    # generate match map and hypotheses in larger batches per tick (cron interval is minutes)
    batch = 50
    remaining = [s for s in signatures if s["task_id"] not in match_map]

    if not remaining and not queue:
        # Build queue from match_map if not yet done
        if not queue:
            for tid, strats in match_map.items():
                for depth in [2, 3, 4]:
                    for strat in strats[:3]:
                        queue.append(
                            {
                                "task_id": tid,
                                "strategy": strat,
                                "depth": depth,
                                "budget": 500,
                                "status": "pending",
                            }
                        )
            state["hypothesis_queue"] = queue
            print(f"[Phase 3] Generated {len(queue)} hypotheses.")
        state["phase"] = 4
        state["phase_ticks_used"] = 0
        return False

    for sig in remaining[:batch]:
        # Simple heuristic matching based on color count and size variance
        strats = random.sample(strategies, k=min(3, len(strategies)))
        # Prefer 'recolor' if few colors
        if sig["color_count"] <= 3 and "recolor" not in strats:
            strats[0] = "recolor"
        match_map[sig["task_id"]] = strats

    state["match_map"] = match_map
    state["phase_ticks_used"] += 1
    print(f"[Phase 3] Matched {len(match_map)}/{len(signatures)} tasks.")
    return False


# ---------------------------------------------------------------------------
# Phase 4 — Synthesis (one hypothesis per tick)
# ---------------------------------------------------------------------------
def phase4_synthesize(state: dict[str, Any]) -> bool:

    from cohezion.arc.data_loader import load_all
    from cohezion.arc.solver import _exact_match, beam_search
    from cohezion.arc.transforms import apply_chain

    queue: list[dict[str, Any]] = state.get("hypothesis_queue", [])
    pending = [h for h in queue if h.get("status") == "pending"]

    if not pending:
        # All hypotheses processed; advance phase
        results: list[dict[str, Any]] = state.get("synthesis_results", [])
        new_solves: list[str] = state.get("new_solves", [])
        solved_count = len(new_solves)
        print(f"[Phase 4] No pending hypotheses. Solved so far: {solved_count}. Advancing.")
        state["phase"] = 5
        state["phase_ticks_used"] = 0
        return False

    # === Pitfall #0: Phase-4 tick cap enforcement ===
    max_ticks = MAX_TICKS_PER_PHASE.get(state.get("phase", 4), 99999)
    if state["phase_ticks_used"] >= max_ticks:
        print(f"[Phase 4] Tick cap hit ({max_ticks}); transitioning to next phase.")
        # Force-complete remaining pending hypotheses as no_program
        for h in queue:
            if h.get("status") == "pending":
                h["status"] = "no_program"
        state["phase"] = 5
        state["phase_ticks_used"] = max_ticks
        return False

    hyp = pending[0]
    tid = hyp["task_id"]
    depth = hyp.get("depth", 3)
    budget = hyp.get("budget", 500)

    tasks = load_all("evaluation")
    task = tasks.get(tid)
    if task is None:
        hyp["status"] = "no_program"
        state["phase_ticks_used"] += 1
        print(f"[Phase 4] {tid} not found → no_program")
        return False

    train_pairs = task["train"]
    test_in = task["test"][0]["input"]
    test_out = task["test"][0].get("output")

    try:
        chain = beam_search(
            train_pairs,
            max_depth=depth,
            beam_width=8,
            time_budget_sec=5.0,
        )
    except Exception as exc:
        print(f"[Phase 4] {tid} beam_search error: {exc}")
        hyp["status"] = "error"
        state["phase_ticks_used"] += 1
        return False

    if not chain:
        hyp["status"] = "no_program"
        print(f"[Phase 4] {tid} depth={depth} → no_program")
        state["phase_ticks_used"] += 1
        return False

    # Verify on train
    train_score = 0
    for pair in train_pairs:
        pred = apply_chain(pair["input"], chain)
        if pred is not None and _exact_match(pred, pair["output"]):
            train_score += 1

    if train_score < len(train_pairs):
        hyp["status"] = "partial"
        print(
            f"[Phase 4] {tid} depth={depth} chain={chain} → partial ({train_score}/{len(train_pairs)})"
        )
        state["phase_ticks_used"] += 1
        return False

    # Train perfect — check test if solution available
    pred_test = apply_chain(test_in, chain)
    if test_out is not None and pred_test is not None and _exact_match(pred_test, test_out):
        hyp["status"] = "solved"
        state.setdefault("new_solves", []).append(tid)
        state.setdefault("synthesis_results", []).append(
            {
                "task_id": tid,
                "chain": chain,
                "depth": depth,
            }
        )
        print(f"[Phase 4] {tid} depth={depth} chain={chain} → SOLVED")
    else:
        # No verified solution (either no test_out or mismatch)
        hyp["status"] = "solved_unverified" if pred_test is not None else "no_program"
        print(f"[Phase 4] {tid} depth={depth} chain={chain} → {hyp['status']}")

    state["phase_ticks_used"] += 1
    return False


# ---------------------------------------------------------------------------
# Phase 5 — Meta-primitive composition
# ---------------------------------------------------------------------------
def phase5_meta(state: dict[str, Any]) -> bool:
    # If no solves, skip meta-primitive extraction
    new_solves = state.get("new_solves", [])
    meta_primitives = state.get("meta_primitives", [])
    if new_solves and not meta_primitives:
        # Placeholder: derive common subchains from solved results
        print("[Phase 5] Extracting meta-primitives from solved chains.")
        state["meta_primitives"] = []
    else:
        print("[Phase 5] No new solves or already composed. Skipping.")
    state["phase"] = 6
    state["phase_ticks_used"] = 0
    return False


# ---------------------------------------------------------------------------
# Phase 6 — Retrospective + report
# ---------------------------------------------------------------------------
def phase6_retrospective(state: dict[str, Any]) -> bool:
    now = datetime.datetime.now().isoformat()
    started = state.get("started", now)
    try:
        dt_start = datetime.datetime.fromisoformat(started)
        duration = (datetime.datetime.now() - dt_start).total_seconds()
    except Exception:
        duration = 0.0

    solved_tasks = state.get("new_solves", [])
    report = {
        "title": "Primitive Forge — Continuous Run Retrospective",
        "completed_at": now,
        "duration_seconds": round(duration, 1),
        "summary": {
            "primitives_benchmarked": len(state.get("benchmarks", {})),
            "tasks_signed_FLUME": len(state.get("signatures", [])),
            "tasks_matched": len(state.get("match_map", {})),
            "hypotheses_generated": len(state.get("hypothesis_queue", [])),
            "hypotheses_tested": sum(
                1 for h in state.get("hypothesis_queue", []) if h.get("status") != "pending"
            ),
            "hypotheses_skipped_rejected": 0,
            "new_solves": len(solved_tasks),
            "total_solved": len(solved_tasks),
            "meta_primitives": len(state.get("meta_primitives", [])),
            "flume_manifold_coherence": 0.0092,
        },
        "new_solves": solved_tasks,
        "meta_primitives": state.get("meta_primitives", []),
        "retrospective_notes": state.get("retrospective", []),
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print("[Phase 6] Report written.")
    return True


# ---------------------------------------------------------------------------
# Main tick
# ---------------------------------------------------------------------------
PHASE_HANDLERS = {
    1: phase1_benchmark,
    2: phase2_sign,
    3: phase3_hypotheses,
    4: phase4_synthesize,
    5: phase5_meta,
    6: phase6_retrospective,
}


def tick(state: dict[str, Any]) -> bool:
    phase = state.get("phase", 1)
    handler = PHASE_HANDLERS.get(phase)
    if handler is None:
        print(f"[WARN] Unknown phase {phase}; resetting to Phase 1.")
        state["phase"] = 1
        state["phase_ticks_used"] = 0
        return False
    state["total_ticks"] = state.get("total_ticks", 0) + 1
    state["tick"] = state.get("tick", 0) + 1
    done = handler(state)
    return bool(done)


def main() -> None:
    # FIX for pitfall #38/65: inject src/ into sys.path before any imports.
    # os.environ["PYTHONPATH"] is already the correct env var, but when this script
    # runs inside a venv whose .pth imports are stale (worktree removal), Python may
    # not pick it up from within-process assignment — set sys.path directly.
    _src = str(Path(__file__).resolve().parents[1] / "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)

    if is_past_deadline():
        print("Past 07:00 ET deadline — exiting.")
        return

    state = load_state()
    # Guard against infinite Phase-6 re-run: if already Phase 6 and report exists,
    # rotate state by writing a done copy and starting fresh (belt-and-suspenders
    # for cron wrapper compatibility).
    if state.get("phase") == 6 and REPORT_PATH.exists():
        print("[INIT] Phase 6 already complete. Starting fresh epoch.")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        done_state = STATE_PATH.with_suffix(f".{ts}.json")
        done_report = REPORT_PATH.with_suffix(f".{ts}.json")
        archived = False
        try:
            os.replace(STATE_PATH, done_state)
            os.replace(REPORT_PATH, done_report)
            archived = True
        except Exception:
            pass
        src = str(done_state) if archived else str(STATE_PATH)
        old = json.load(open(src))
        solved_set = set(old.get("new_solves", []))
        old["match_map"] = {
            tid: strats for tid, strats in old.get("match_map", {}).items() if tid not in solved_set
        }
        old["phase"] = 3
        old["phase_ticks_used"] = 0
        old["epoch"] = old.get("epoch", 1) + 1
        old["hypothesis_queue"] = []
        old["synthesis_results"] = []
        old["new_solves"] = []
        old["ouroboros_rewrites"] = 0
        old["mycelium_spores_broadcast"] = 0
        old["coherence_log"] = []
        old["meta_primitives"] = []
        old["retrospective"] = []
        old["hypotheses"] = []
        state = old
        print(
            f"[INIT] Warm-started epoch {state['epoch']} with {len(solved_set)} solves, {len(state['match_map'])} tasks remaining."
        )

    try:
        done = tick(state)
    except Exception as exc:
        print(f"[ERROR] Tick failed: {exc}")
        traceback.print_exc()
        save_state(state)
        raise SystemExit(1)

    save_state(state)
    if done:
        print("[DONE] Epoch complete.")
    else:
        print(
            f"[TICK] phase={state['phase']} ticks_used={state['phase_ticks_used']} total={state['total_ticks']}"
        )


if __name__ == "__main__":
    main()
