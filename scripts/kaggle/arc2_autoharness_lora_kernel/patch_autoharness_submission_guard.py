#!/usr/bin/env python3
"""AutoHarness SOTA Notebook Hardening Script for ARC-AGI-2.

Patches scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb:
1. Inoculates Cell 6 (arc_solver.py) and Cell 7 (starter.py) with dynamic path discovery.
2. Injects the complete AutoHarness Submission Guard into Cell 9:
   - Dynamic path resolution across /kaggle/input/** and local search roots.
   - Interception and auto-repair of dummy [[0]] placeholders caused by worker timeouts.
   - Deterministic fallback generation (Attempt 1: Input identity; Attempt 2: Calibrated shape/color projection).
   - Invariant validation: rectangularity, dimensions (1..30), valid colors (0..9).
   - Atomic serialization via tempfile replacement.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb")
BACKUP_PATH = NOTEBOOK_PATH.with_suffix(".ipynb.bak")


# Hardened Cell 9 Source Code
HARDENED_CELL_9_SOURCE = [
 "import os\n",
 "import json\n",
 "import tempfile\n",
 "from pathlib import Path\n",
 "from collections import Counter\n",
 "import numpy as np\n",
 "from arc_loader import ArcDataset\n",
 "from arc_decoder import ArcDecoder\n",
 "\n",
 "# ==========================================================================\n",
 "# AutoHarness Zero-Cost Submission Guard (Topic 704408 Hardening)\n",
 "# ==========================================================================\n",
 "os.makedirs(\"/kaggle/inference_outputs\", exist_ok=True)\n",
 "rerun_mode = os.getenv(\"KAGGLE_IS_COMPETITION_RERUN\")\n",
 "\n",
 "def resolve_path(pattern: str, default_path: str) -> str:\n",
 "    \"\"\"Dynamically searches /kaggle/input/** and local roots for dataset files.\"\"\"\n",
 "    search_roots = [Path(\"/kaggle/input\"), Path(\"data/arc-agi-2\"), Path(\"data\"), Path(\".\")]\n",
 "    for root in search_roots:\n",
 "        if root.exists():\n",
 "            for match in root.glob(f\"**/{pattern}\"):\n",
 "                if match.is_file() and match.stat().st_size > 0:\n",
 "                    print(f\"[AutoHarness PathResolver] Found '{pattern}' -> {match}\")\n",
 "                    return str(match.resolve())\n",
 "    print(f\"[AutoHarness PathResolver] WARNING: '{pattern}' not found dynamically. Using default: {default_path}\")\n",
 "    return default_path\n",
 "\n",
 "if rerun_mode:\n",
 "    default_test = \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json\"\n",
 "    test_path = resolve_path(\"*test_challenges*.json\", default_test)\n",
 "    data = ArcDataset.from_file(test_path)\n",
 "else:\n",
 "    default_eval = \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_challenges.json\"\n",
 "    default_sol = \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_solutions.json\"\n",
 "    test_path = resolve_path(\"*evaluation_challenges*.json\", default_eval)\n",
 "    sol_path = resolve_path(\"*evaluation_solutions*.json\", default_sol)\n",
 "    data = ArcDataset.from_file(test_path)\n",
 "    if os.path.exists(sol_path):\n",
 "        data = data.load_replies(sol_path)\n",
 "\n",
 "decoder = ArcDecoder(data.split_multi_replies(), n_guesses=2)\n",
 "decoder.load_decoded_results(\"/kaggle/inference_outputs\")\n",
 "\n",
 "# Generate candidate submission\n",
 "selection_results = decoder.run_selection_algo()\n",
 "submission = data.get_submission(selection_results)\n",
 "\n",
 "# ==========================================================================\n",
 "# Invariant Verification & Deterministic Fallback Auto-Repair\n",
 "# ==========================================================================\n",
 "print(f\"[AutoHarness Guard] Validating {len(submission)} tasks against silent failure mode...\")\n",
 "raw_queries = getattr(data, \"queries\", {})\n",
 "repaired_count = 0\n",
 "total_predictions = 0\n",
 "\n",
 "def is_dummy_or_invalid(grid):\n",
 "    if not isinstance(grid, list) or len(grid) == 0:\n",
 "        return True\n",
 "    # Check for un-filled ArcDataset default [[0]]\n",
 "    if grid == [[0]]:\n",
 "        return True\n",
 "    h = len(grid)\n",
 "    if h <= 0 or h > 30:\n",
 "        return True\n",
 "    if not isinstance(grid[0], list) or len(grid[0]) == 0:\n",
 "        return True\n",
 "    w = len(grid[0])\n",
 "    if w <= 0 or w > 30:\n",
 "        return True\n",
 "    for row in grid:\n",
 "        if not isinstance(row, list) or len(row) != w:\n",
 "            return True\n",
 "        for cell in row:\n",
 "            if not isinstance(cell, int) or cell < 0 or cell > 9:\n",
 "                return True\n",
 "    return False\n",
 "\n",
 "for task_id in list(data.keys):\n",
 "    task_dict = raw_queries.get(task_id, {})\n",
 "    test_cases = task_dict.get(\"test\", [])\n",
 "    train_cases = task_dict.get(\"train\", [])\n",
 "    \n",
 "    # Compute train mode color & fixed output shape for calibrated fallback\n",
 "    train_out_colors = [c for ex in train_cases for row in ex.get(\"output\", []) for c in row if isinstance(c, int) and c > 0]\n",
 "    mode_color = Counter(train_out_colors).most_common(1)[0][0] if train_out_colors else 0\n",
 "    train_out_shapes = {np.shape(ex.get(\"output\", [])) for ex in train_cases if len(ex.get(\"output\", [])) > 0}\n",
 "    fixed_shape = list(train_out_shapes)[0] if len(train_out_shapes) == 1 else None\n",
 "\n",
 "    preds = submission.get(task_id, [])\n",
 "    for test_idx, test_case in enumerate(test_cases):\n",
 "        total_predictions += 1\n",
 "        test_in = test_case.get(\"input\", [[0]])\n",
 "        \n",
 "        if test_idx >= len(preds):\n",
 "            preds.append({\"attempt_1\": [[0]], \"attempt_2\": [[0]]})\n",
 "            submission[task_id] = preds\n",
 "\n",
 "        target_pred = preds[test_idx]\n",
 "        for attempt_key in [\"attempt_1\", \"attempt_2\"]:\n",
 "            cand_grid = target_pred.get(attempt_key)\n",
 "            if is_dummy_or_invalid(cand_grid):\n",
 "                repaired_count += 1\n",
 "                if attempt_key == \"attempt_1\":\n",
 "                    # Fallback 1: Input Identity mapping (preserves canvas & bounds)\n",
 "                    target_pred[attempt_key] = [r[:] for r in test_in]\n",
 "                else:\n",
 "                    # Fallback 2: Training-calibrated shape/mode-color or flipped input\n",
 "                    if fixed_shape is not None and 1 <= fixed_shape[0] <= 30 and 1 <= fixed_shape[1] <= 30:\n",
 "                        target_pred[attempt_key] = [[mode_color for _ in range(fixed_shape[1])] for _ in range(fixed_shape[0])]\n",
 "                    else:\n",
 "                        target_pred[attempt_key] = [r[::-1] for r in test_in]\n",
 "\n",
 "print(f\"[AutoHarness Guard] Validating {total_predictions} prediction instances across {len(submission)} tasks.\")\n",
 "if repaired_count > 0:\n",
 "    print(f\"[AutoHarness Guard] REPAIRED {repaired_count} dummy/invalid candidate grids with zero-cost fallback!\")\n",
 "else:\n",
 "    print(\"[AutoHarness Guard] All predictions passed structural invariants without repair.\")\n",
 "\n",
 "# ==========================================================================\n",
 "# Atomic Submission Serialization\n",
 "# ==========================================================================\n",
 "output_target = Path(\"submission.json\")\n",
 "with tempfile.NamedTemporaryFile(\"w\", dir=\".\", delete=False, encoding=\"utf-8\") as tmp:\n",
 "    json.dump(submission, tmp, separators=(\",\", \":\"))\n",
 "    tmp_path = Path(tmp.name)\n",
 "\n",
 "tmp_path.replace(output_target)\n",
 "print(f\"[AutoHarness Guard] Atomically serialized verified submission.json ({output_target.stat().st_size} bytes).\")\n",
 "\n",
 "# Verification & Local Reload Check\n",
 "if not rerun_mode:\n",
 "    decoder.benchmark_selection_algos()\n",
 "    with open(\"submission.json\", \"r\") as f:\n",
 "        reload_submission = json.load(f)\n",
 "    print(\"*** Reload score:\", data.validate_submission(reload_submission))\n"
]


def patch_notebook():
    if not NOTEBOOK_PATH.exists():
        raise FileNotFoundError(f"Notebook not found at: {NOTEBOOK_PATH.resolve()}")

    print(f"Reading notebook from {NOTEBOOK_PATH}...")
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # 1. Create backup
    shutil.copyfile(NOTEBOOK_PATH, BACKUP_PATH)
    print(f"Created backup at {BACKUP_PATH}")

    cells = nb.get("cells", [])
    print(f"Notebook contains {len(cells)} cells.")

    # 2. Patch Cell 6 (arc_solver.py) path resolution
    cell_6_found = False
    for i, cell in enumerate(cells):
        src = "".join(cell.get("source", []))
        if "%%writefile arc_solver.py" in src and "arc-agi_test_challenges.json" in src:
            print(f"Patching Cell {i} (arc_solver.py) with dynamic path resolution...")
            old_str = (
                "    if rerun_mode:\n"
                "        test_path = \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json\"\n"
                "    else:\n"
                "        test_path = \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_challenges.json\"\n"
            )
            new_str = (
                "    from pathlib import Path\n"
                "    def _resolve_challenges(rerun):\n"
                "        pat = \"*test_challenges*.json\" if rerun else \"*evaluation_challenges*.json\"\n"
                "        for r in [Path(\"/kaggle/input\"), Path(\"data\"), Path(\".\")]:\n"
                "            if r.exists():\n"
                "                for m in r.glob(f\"**/{pat}\"):\n"
                "                    if m.is_file() and m.stat().st_size > 0: return str(m.resolve())\n"
                "        return \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/\" + (\"arc-agi_test_challenges.json\" if rerun else \"arc-agi_evaluation_challenges.json\")\n"
                "    test_path = _resolve_challenges(rerun_mode)\n"
            )
            if old_str in src:
                src = src.replace(old_str, new_str)
                cell["source"] = [src]
                cell_6_found = True
                print("  ✓ Successfully patched arc_solver.py")
            break

    # 3. Patch Cell 7 (starter.py) path resolution
    cell_7_found = False
    for i, cell in enumerate(cells):
        src = "".join(cell.get("source", []))
        if "%%writefile starter.py" in src and "arc-agi_test_challenges.json" in src:
            print(f"Patching Cell {i} (starter.py) with dynamic path resolution...")
            old_str = (
                "    if rerun_mode:\n"
                "        test_path = \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json\"\n"
                "    else:\n"
                "        test_path = \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_challenges.json\"\n"
            )
            new_str = (
                "    from pathlib import Path\n"
                "    def _resolve_starter_path(rerun):\n"
                "        pat = \"*test_challenges*.json\" if rerun else \"*evaluation_challenges*.json\"\n"
                "        for r in [Path(\"/kaggle/input\"), Path(\"data\"), Path(\".\")]:\n"
                "            if r.exists():\n"
                "                for m in r.glob(f\"**/{pat}\"):\n"
                "                    if m.is_file() and m.stat().st_size > 0: return str(m.resolve())\n"
                "        return \"/kaggle/input/competitions/arc-prize-2026-arc-agi-2/\" + (\"arc-agi_test_challenges.json\" if rerun else \"arc-agi_evaluation_challenges.json\")\n"
                "    test_path = _resolve_starter_path(rerun_mode)\n"
            )
            if old_str in src:
                src = src.replace(old_str, new_str)
                cell["source"] = [src]
                cell_7_found = True
                print("  ✓ Successfully patched starter.py")
            break

    # 4. Patch Cell 9 (Submission Generation Cell)
    cell_9_found = False
    for i, cell in enumerate(cells):
        src = "".join(cell.get("source", []))
        if "decoder.load_decoded_results" in src and "submission.json" in src:
            print(f"Patching Cell {i} with AutoHarness Submission Guard...")
            cell["source"] = HARDENED_CELL_9_SOURCE
            cell_9_found = True
            print("  ✓ Successfully replaced Cell 9 with AutoHarness Submission Guard")
            break

    if not cell_9_found:
        print("Warning: Cell 9 match string not found, updating last cell...")
        cells[-1]["source"] = HARDENED_CELL_9_SOURCE
        cell_9_found = True

    # 5. Save hardened notebook
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"\n[DONE] Notebook successfully hardened and written to: {NOTEBOOK_PATH}")
    print(f"Patched summary: arc_solver.py: {cell_6_found}, starter.py: {cell_7_found}, Cell 9 (Guard): {cell_9_found}")


if __name__ == "__main__":
    patch_notebook()
