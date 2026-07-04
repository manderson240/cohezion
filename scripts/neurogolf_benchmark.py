"""Local benchmark for NeuroGolf 2026 — fast scoring without pushing to Kaggle.

Tests fast-path detectors (identity, bijection, scale, etc.) against all 400
tasks and estimates the competition score WITHOUT exporting ONNX or submitting.

Results are logged to ~/.cohezion/neurogolf_benchmark.jsonl for tracking.

Usage:
    uv run python scripts/neurogolf_benchmark.py                  # all 400 tasks
    uv run python scripts/neurogolf_benchmark.py --task 16        # single task
    uv run python scripts/neurogolf_benchmark.py --fast-paths     # fast-paths only
    uv run python scripts/neurogolf_benchmark.py --verbose        # per-task output
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from pathlib import Path

logger = logging.getLogger("neurogolf_bench")

# ── Config ─────────────────────────────────────────────────────────────────

DATA_DIR = Path("/home/mike-anderson/dev/cohezion/.worktrees/agi-golf/data/neurogolf")
RESULTS_PATH = Path.home() / ".cohezion" / "neurogolf_benchmark.jsonl"
C = 10  # ARC color count

# ── Scoring (same formula as competition) ──────────────────────────────────

def score_params(n_params: int) -> float:
    """Score from ONNX parameter count. 0 params → 25.00 (max)."""
    if n_params == 0:
        return 25.0
    memory = n_params * 4  # float32 = 4 bytes
    return max(1.0, 25.0 - math.log(max(1.0, memory + n_params)))

# ── Task analysis ──────────────────────────────────────────────────────────

def classify_task(data: dict) -> str:
    all_same = all_up = all_down = True
    for split in ("train", "test"):
        for ex in data.get(split, []):
            if "output" not in ex:
                continue
            ih, iw = len(ex["input"]), len(ex["input"][0]) if ex["input"] else 0
            oh, ow = len(ex["output"]), len(ex["output"][0]) if ex["output"] else 0
            if ih != oh or iw != ow:
                all_same = False
            if not (oh >= ih and ow >= iw):
                all_up = False
            if not (oh <= ih and ow <= iw):
                all_down = False
    if all_same:
        return "same_size"
    if all_up:
        return "scale_up"
    if all_down:
        return "scale_down"
    return "mixed"


def detect_identity(examples: list[dict]) -> bool:
    return all(ex["input"] == ex["output"] for ex in examples if "output" in ex)


def detect_color_bijection(examples: list[dict]) -> dict | None:
    color_map: dict[int, int] = {}
    reverse_map: dict[int, int] = {}
    for ex in examples:
        if "output" not in ex:
            continue
        inp, out = ex["input"], ex["output"]
        if len(inp) != len(out):
            return None
        for r in range(len(inp)):
            row_in, row_out = inp[r], out[r]
            if len(row_in) != len(row_out):
                return None
            for c in range(len(row_in)):
                ic, oc = row_in[c], row_out[c]
                if ic in color_map:
                    if color_map[ic] != oc:
                        return None
                else:
                    color_map[ic] = oc
                if oc in reverse_map:
                    if reverse_map[oc] != ic:
                        return None
                else:
                    reverse_map[oc] = ic
    return color_map if color_map else None


def detect_integer_scale(examples: list[dict]) -> int | None:
    """Detect uniform integer up-scale factor (e.g. 2× or 3×) AND verify nearest-neighbor."""
    scale = None
    for ex in examples:
        if "output" not in ex:
            continue
        ih, iw = len(ex["input"]), len(ex["input"][0]) if ex["input"] else 0
        oh, ow = len(ex["output"]), len(ex["output"][0]) if ex["output"] else 0
        if ih == 0 or iw == 0:
            return None
        if oh % ih != 0 or ow % iw != 0:
            return None
        sr, sc = oh // ih, ow // iw
        if sr != sc:
            return None
        if scale is None:
            scale = sr
        elif scale != sr:
            return None
    if scale is None:
        return None
    # Verify nearest-neighbor pixel-repeat: output[r*s+dr][c*s+dc] == input[r][c]
    for ex in examples:
        if "output" not in ex:
            continue
        inp, out = ex["input"], ex["output"]
        ih = len(inp)
        for r in range(ih):
            iw = len(inp[r])
            for c in range(iw):
                for dr in range(scale):
                    for dc in range(scale):
                        if out[r * scale + dr][c * scale + dc] != inp[r][c]:
                            return None  # not nearest-neighbor
    return scale


def analyze_task(task_num: int, data: dict) -> dict:
    """Run all fast-path detectors and return analysis dict."""
    eval_exs = [ex for ex in data.get("train", []) + data.get("test", []) if "output" in ex]
    cls = classify_task(data)

    result = {
        "task": task_num,
        "classify": cls,
        "fast_path": None,
        "params": None,
        "estimated_score": None,
        "detail": {},
    }

    if detect_identity(eval_exs):
        result["fast_path"] = "identity"
        result["params"] = 0
        result["estimated_score"] = score_params(0)
        return result

    if cls == "same_size":
        bij = detect_color_bijection(eval_exs)
        if bij is not None:
            non_id = {k: v for k, v in bij.items() if k != v}
            result["fast_path"] = "bijection"
            result["params"] = 0  # 0-param via torch.tensor in forward()
            result["estimated_score"] = score_params(0)
            result["detail"]["color_map"] = non_id
            return result

    if cls == "scale_up":
        scale = detect_integer_scale(eval_exs)
        if scale is not None and scale in (2, 3, 4):
            result["fast_path"] = f"scale_{scale}x"
            # Scale with arange() is 0-param; check feasibility
            result["params"] = 0
            result["estimated_score"] = score_params(0)
            result["detail"]["scale_factor"] = scale
            return result

    # No fast-path detected — TinyConv fallback (estimated ~128 params)
    result["fast_path"] = "tinyconv"
    result["params"] = 128
    result["estimated_score"] = score_params(128)
    return result


# ── Main ────────────────────────────────────────────────────────────────────

def run_benchmark(
    task_nums: list[int] | None = None,
    fast_paths_only: bool = False,
    verbose: bool = False,
) -> dict:
    if not DATA_DIR.exists():
        logger.error("Data directory not found: %s", DATA_DIR)
        sys.exit(1)

    available = sorted(int(p.stem[4:]) for p in DATA_DIR.glob("task???.json"))
    targets = [n for n in available if task_nums is None or n in task_nums]
    logger.info("Benchmarking %d/%d tasks ...", len(targets), len(available))

    by_path: dict[str, list[int]] = {}
    total_score = 0.0
    results = []
    NON_FAST = {"tinyconv", "none"}

    for task_num in targets:
        path = DATA_DIR / f"task{task_num:03d}.json"
        data = json.loads(path.read_text())
        r = analyze_task(task_num, data)
        results.append(r)

        fp = r["fast_path"] or "none"
        by_path.setdefault(fp, []).append(task_num)
        total_score += r["estimated_score"] or 0.0

        if verbose and (not fast_paths_only or fp not in NON_FAST):
            pts = r["estimated_score"] or 0.0
            det = r["detail"] or {}
            logger.info(
                "  task%03d: %s → %s  %.2f pts  %s",
                task_num,
                r["classify"],
                fp,
                pts,
                det if det else "",
            )

    # Summary
    solved_fp = [r for r in results if r["fast_path"] not in ("tinyconv", "none")]
    total_pts_fp = sum(r["estimated_score"] or 0 for r in solved_fp)

    print("\n" + "=" * 60)
    print(f"NEUROGOLF BENCHMARK — {len(targets)} tasks")
    print("=" * 60)
    for fp, tasks in sorted(by_path.items(), key=lambda x: -len(x[1])):
        pts = sum(score_params(0) if fp != "tinyconv" else score_params(128)
                  for _ in tasks)
        prefix = "★" if fp not in ("tinyconv", "none") else " "
        print(f"  {prefix} {fp:<20} {len(tasks):4d} tasks  {pts:7.2f} pts")
    print("-" * 60)
    fast_path_tasks = len(solved_fp)
    print(f"  Fast-path solved:     {fast_path_tasks:4d} tasks  {total_pts_fp:7.2f} pts (avg {total_pts_fp/max(1,fast_path_tasks):.2f})")
    print(f"  Total estimated:                       {total_score:7.2f} pts")
    if len(available) > 0:
        print(f"  Coverage:             {fast_path_tasks}/{len(targets)} ({100*fast_path_tasks/len(targets):.1f}%)")
    print("=" * 60)

    # Persist
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")
    print(f"\nResults saved to {RESULTS_PATH}")

    return {"tasks": results, "total_estimated_score": total_score}


def main() -> None:
    ap = argparse.ArgumentParser(description="NeuroGolf local benchmark (no Kaggle submission)")
    ap.add_argument("--task", type=int, help="Benchmark a single task number")
    ap.add_argument("--tasks", nargs="+", type=int, help="Specific task numbers")
    ap.add_argument("--fast-paths", action="store_true", help="Show only fast-path tasks")
    ap.add_argument("--verbose", "-v", action="store_true", help="Per-task output")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    task_nums = None
    if args.task:
        task_nums = [args.task]
    elif args.tasks:
        task_nums = args.tasks

    run_benchmark(task_nums=task_nums, fast_paths_only=args.fast_paths, verbose=args.verbose)


if __name__ == "__main__":
    main()
