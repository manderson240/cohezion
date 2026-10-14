#!/usr/bin/env python3
"""Upgrade ARC-AGI-3 to SOTA v32: RHAE 35-Step Hard Cap + Liveness Watchdog + Finally Scorecard Guard.

Mathematical Rationale (Theorem RHAE Marginal Step Utility):
- Score(l) = min(1.0, (N_human / N_AI)^2)
- d/dN_AI RHAE = -2 * N_human^2 / N_AI^3
- Wandering to 150 steps incurs near-zero score ((10/150)^2 = 0.004) and burns time.
- Truncating exploration at step < 35 (exact v15/v27 lineage) bounds the denominator
  and preserves time for high-probability solvable environments.
- Liveness watchdog terminates early if 4 consecutive cycle traps are encountered.
- Encloses loop in try...finally to guarantee scorecard is always closed.
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb")
BAK_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb.v31.bak")

def main():
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")
    
    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up {NB_PATH} to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # 1. Update Cell 2 with RHAE 35-step hard cap, watchdog, and try...finally scorecard closing
    c2_code = '''# 3. Competition Arcade Master Orchestrator (SOTA v32: RHAE 35-Step Cap + Liveness Watchdog)
import os, sys, glob, time, urllib.request
from pathlib import Path

TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}
print(f"Cohezion ARC-AGI-3 Master Orchestrator: TRUE_SUBMISSION={TRUE_SUBMISSION}")

GATEWAY_URL = os.environ.get("ARC_BASE_URL", "http://gateway:8001/")
MAX_TOTAL_RUNTIME_S = 8.5 * 3600
START_TIME = time.time()

def wait_for_gateway(base_url: str, max_wait_s: int = 300) -> bool:
    print(f"Polling gateway at {base_url}api/games (up to {max_wait_s}s)...", flush=True)
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{base_url}api/games")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print("✓ Gateway is online and ready!", flush=True)
                    return True
        except Exception:
            pass
        time.sleep(3)
    print("Warning: Gateway polling timed out.", flush=True)
    return False

if TRUE_SUBMISSION:
    wait_for_gateway(GATEWAY_URL)
    arcade = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.COMPETITION,
        arc_base_url=GATEWAY_URL,
        arc_api_key="test-key-123",
    )
else:
    env_dirs = glob.glob("/kaggle/input/**/environment_files", recursive=True)
    env_dir = env_dirs[0] if env_dirs else "data/arc_prize/environment_files"
    print(f"Running in OFFLINE mode using environments from: {env_dir}")
    arcade = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=env_dir,
    )

card_id = arcade.create_scorecard()
print(f"Opened Scorecard: {card_id}")

try:
    envs = arcade.get_environments()
    print(f"Discovered {len(envs)} environments to solve.")

    # In offline commit mode, run 2 environments quickly to pass the commit gate
    if not TRUE_SUBMISSION:
        envs = envs[:2]

    for idx, env_info in enumerate(envs):
        elapsed = time.time() - START_TIME
        if elapsed > MAX_TOTAL_RUNTIME_S:
            print(f"Time budget reached ({elapsed:.1f}s). Finalizing scorecard.")
            break

        game_id = env_info.game_id
        print(f"[{idx+1}/{len(envs)}] Playing {game_id} (Elapsed: {elapsed:.1f}s)...", flush=True)
        try:
            env = arcade.make(game_id, scorecard_id=card_id)
            if env is None:
                continue
            agent = CohezionGoExploreAgent(game_id, seed=idx * 100)
            obs = env.reset()

            step = 0
            # SOTA v32 RHAE Action Invariant: Cap at 35 steps to preserve quadratic efficiency (N_human / N_AI)^2
            while obs and obs.state not in (GameState.WIN, GameState.GAME_OVER) and step < 35:
                # Liveness Watchdog: Breakout if stuck in 4 consecutive cycle traps (wall collision / orbit)
                if getattr(agent, "consecutive_loops", 0) >= 4:
                    print(f"  Watchdog: 4 consecutive cycle traps on {game_id} at step {step}. Early terminating to preserve RHAE.")
                    break
                act, data = agent.choose_action(obs)
                obs = env.step(act, data=data)
                step += 1

            print(f"  -> {game_id} finished in {step} steps. State: {obs.state if obs else None}, Levels: {obs.levels_completed if obs else 0}")
        except Exception as exc:
            print(f"  Error on {game_id}: {exc}")
finally:
    sc = arcade.close_scorecard(card_id)
    print(f"✓ Closed Scorecard {card_id}. Total actions: {sc.total_actions if sc else 0}, Completed: {sc.total_levels_completed if sc else 0}")
'''
    nb["cells"][2]["source"] = [l + "\n" for l in c2_code.splitlines()]

    # Validate AST across all cells
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            cleaned = []
            for line in src.splitlines():
                if line.strip().startswith("!") or line.strip().startswith("%"):
                    cleaned.append(f"# {line}")
                else:
                    cleaned.append(line)
            try:
                ast.parse("\n".join(cleaned))
            except SyntaxError as e:
                raise RuntimeError(f"Syntax error in Cell {idx}: {e}")

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"✓ Successfully upgraded {NB_PATH} to SOTA v32 (RHAE 35-step cap + liveness watchdog + finally scorecard guard).")

if __name__ == "__main__":
    main()
