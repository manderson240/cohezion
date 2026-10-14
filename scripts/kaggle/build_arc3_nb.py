import json
from pathlib import Path

# Load engine code
engine_path = Path("src/cohezion/arc/tracks/arc_agi_3_sota_engine.py")
with open(engine_path) as f:
    engine_code = f.read()

# Strip __future__ from engine_code so it does not appear after other statements
engine_code_clean = "\n".join([line for line in engine_code.splitlines() if not line.startswith("from __future__")])

cell_0_src = """# 1. Install arc-agi runtime from offline competition wheelhouse
import os, sys, glob, subprocess

print("Installing arc-agi runtime from offline wheelhouse...")
wheel_dirs = glob.glob("/kaggle/input/**/arc_agi_3_wheels", recursive=True)
if wheel_dirs:
    wheel_dir = wheel_dirs[0]
    print(f"Found wheels directory: {wheel_dir}")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--find-links", wheel_dir, "arc-agi", "python-dotenv", "pillow"], check=False)
else:
    print("arc_agi_3_wheels not found in /kaggle/input; dependencies should be pre-installed.")
"""

cell_1_src = f"""# 2. Cohezion ARC-AGI-3 Dual-Mode SOTA Engine (v24)
# Direct Cayley Permutation Graph Search + Geodesic Navigation + BlueQubit QUBO Anti-Oscillation
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sys
import time
import glob
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import numpy as np

import arc_agi
import arcengine
from arcengine import GameAction, GameState

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CohezionARC3")

{engine_code_clean}
"""

cell_2_src = """# 3. Competition Arcade Master Orchestrator (v24)
import os, sys, glob, time, urllib.request
from pathlib import Path
from arcengine import GameAction, GameState

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
    env_dirs = glob.glob("/kaggle/input/**/environment_files", recursive=True) + glob.glob("**/environment_files", recursive=True)
    env_dir = env_dirs[0] if env_dirs else "data/arc_prize/environment_files"
    print(f"Running in OFFLINE mode using environments from: {env_dir}")
    arcade = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=env_dir,
    )

card_id = arcade.create_scorecard()
print(f"Opened Scorecard: {card_id}")

envs = arcade.get_environments()
print(f"Discovered {len(envs)} environments to solve.")

# In offline commit mode, run the first 2 environments quickly to pass commit verification
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
        agent = ARCSOTAAgent(game_id, seed=idx * 100)
        obs = env.reset()

        current_level = 0
        level_step = 0
        max_per_level = 35  # Strict horizon to protect quadratic action ratio (H_l / A_l)^2

        while obs and obs.state not in (GameState.WIN, GameState.GAME_OVER):
            if getattr(obs, "levels_completed", 0) != current_level:
                print(f"  Level {current_level} completed in {level_step} steps! Advanced to Level {obs.levels_completed}", flush=True)
                current_level = obs.levels_completed
                level_step = 0

            if level_step >= max_per_level:
                print(f"  Level {current_level} reached {level_step} steps. Loss truncation.", flush=True)
                break

            act, data = agent.choose_action(obs)
            obs = env.step(act, data=data)
            level_step += 1

        print(f"  -> {game_id} finished. State: {obs.state if obs else None}, Levels: {obs.levels_completed if obs else 0}")
    except Exception as exc:
        print(f"  Error on {game_id}: {exc}")

sc = arcade.close_scorecard(card_id)
print(f"✓ Closed Scorecard {card_id}. Total actions: {sc.total_actions if sc else 0}, Completed: {sc.total_levels_completed if sc else 0}, Score: {sc.score if sc else 0.0}")
"""

cell_3_src = """# 4. Commit Validator Parquet Handler
# During commit (not TRUE_SUBMISSION), generates initial valid parquet so Kaggle enables Submit.
# During competition rerun (TRUE_SUBMISSION), Kaggle evaluates against gateway scorecard.
import os
import pandas as pd
from pathlib import Path

target_dir = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(".")
target_file = target_dir / "submission.parquet"

if not TRUE_SUBMISSION:
    print("Generating commit-time validator submission.parquet...")
    commit_df = pd.DataFrame(
        data=[["1_0", "1", True, 1]],
        columns=["row_id", "game_id", "end_of_game", "score"]
    )
    commit_df.to_parquet(target_file, index=False)
    print(f"✓ Commit validator submission.parquet written ({target_file.stat().st_size} bytes).")
else:
    print("TRUE_SUBMISSION rerun complete. Gateway recorded scorecard for evaluation.")
"""

nb = {
    "cells": [
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": cell_0_src.splitlines(keepends=True)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": cell_1_src.splitlines(keepends=True)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": cell_2_src.splitlines(keepends=True)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": cell_3_src.splitlines(keepends=True)},
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbformat": 4,
            "nbformat_minor": 2
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

nb_path = Path("scripts/kaggle/arc3_autoharness_kernel/arc-agi-3-autoharness-agent.ipynb")
with open(nb_path, "w") as f:
    json.dump(nb, f, indent=1)

print(f"Successfully wrote {nb_path} ({nb_path.stat().st_size} bytes).")
