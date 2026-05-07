"""Ablation study for ARC solver primitives."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import all defined primitive functions
from arc_solver import (
    apply_program,
    border,
    crop_to_object,
    deduplicate_cols,
    deduplicate_rows,
    diagonal_symmetry,
    downsample,
    extend_lines_h,
    extend_lines_v,
    fill_holes,
    flip_horizontal,
    flip_vertical,
    gravity_down,
    gravity_left,
    gravity_right,
    gravity_up,
    grids_equal,
    hconcat,
    identity,
    interior,
    invert_colors,
    mirror_horizontal,
    mirror_vertical,
    move_objects_up,
    order_objects_by_size,
    pad_to_object,
    remove_background,
    replace_color,
    rotate_90,
    rotate_180,
    rotate_270,
    search_program,
    tile_grid,
    transpose,
    upsample,
    vconcat,
)


def build_ops_subset() -> list:
    """Build explicit op list for ablation."""
    geo = [
        ("identity", identity),
        ("flip_h", flip_horizontal),
        ("flip_v", flip_vertical),
        ("transpose", transpose),
        ("rot90", rotate_90),
        ("rot180", rotate_180),
        ("rot270", rotate_270),
    ]
    color = [
        ("crop_obj", crop_to_object),
        ("remove_bg", remove_background),
        ("fill_holes", fill_holes),
        ("border", border),
        ("interior", interior),
        ("pad_obj", pad_to_object),
        ("invert", invert_colors),
        ("replace_color", replace_color),
    ]
    obj = [
        ("move_up", move_objects_up),
        ("order_objs", order_objects_by_size),
    ]
    gravity = [
        ("gravity_d", gravity_down),
        ("gravity_u", gravity_up),
        ("gravity_l", gravity_left),
        ("gravity_r", gravity_right),
    ]
    mirror = [
        ("mirror_h", mirror_horizontal),
        ("mirror_v", mirror_vertical),
        ("diag_sym", diagonal_symmetry),
    ]
    scale = [
        ("upsample2", upsample(2)),
        ("downsample2", downsample(2)),
    ]
    other = [
        ("dedup_rows", deduplicate_rows),
        ("dedup_cols", deduplicate_cols),
        ("hconcat", hconcat),
        ("vconcat", vconcat),
        ("extend_h", extend_lines_h),
        ("extend_v", extend_lines_v),
        ("tile", tile_grid),
    ]
    return {
        "geo": geo,
        "geo_color": geo + color,
        "geo_color_obj": geo + color + obj,
        "geo_color_obj_gravity": geo + color + obj + gravity,
        "all_but_misc": geo + color + obj + gravity + mirror + scale,
        "all": geo + color + obj + gravity + mirror + scale + other,
    }


def run_ablation(sample: int = 100) -> list[dict[str, Any]]:
    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    op_sets = build_ops_subset()

    # Use a dummy train for color_map since it needs task context

    results = []
    for name, ops in op_sets.items():
        print(f"\n=== {name} ({len(ops)} ops) ===", flush=True)
        correct = 0
        total = sample
        for idx, task_id in enumerate(sorted(challenges)[:sample]):
            task = challenges[task_id]
            task["id"] = task_id
            task_sols = solutions[task_id]

            try:
                program = search_program(task["train"], max_depth=3, budget=2000, ops=ops)
                if program and task_sols and task.get("test"):
                    pred = apply_program(task["test"][0]["input"], program)
                    if pred and grids_equal(pred, task_sols[0]):
                        correct += 1
            except Exception:
                pass

            if idx % 20 == 19:
                print(f"  {idx + 1}/{sample}: {correct} correct", flush=True)

        rate = round(correct / total * 100, 1)
        result = {"name": name, "ops": len(ops), "correct": correct, "total": total, "rate": rate}
        results.append(result)
        print(f"  RESULT: {correct}/{total} = {rate}%")

    return results


if __name__ == "__main__":
    import time

    start = time.monotonic()
    results = run_ablation(sample=1000)
    elapsed = time.monotonic() - start
    print(f"\n{'=' * 50}")
    print(f"ABLATION SUMMARY (1000 tasks, {elapsed:.1f}s)")
    print(f"{'=' * 50}")
    for r in results:
        print(
            f"  {r['name']:25s} | {r['ops']:2d} ops | {r['correct']:3d}/{r['total']} = {r['rate']:>5}%"
        )

    # Save results
    with open("ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to ablation_results.json")
