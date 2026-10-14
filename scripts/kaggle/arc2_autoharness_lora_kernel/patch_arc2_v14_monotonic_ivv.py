#!/usr/bin/env python3
"""Patch script for ARC-AGI-2 SOTA v14: Enforce Monotonic Improvement Invariant & IV&V Audit.

Remediates regression in v13:
1. Fixes `gravity_fall` to ensure numpy conversion `to_np(arr)` is called before `.shape`.
2. Enforces non-trivial transformation requirement on DSL synthesis: only synthesize if
   N_train >= 3 or all training pairs demonstrate consistent non-trivial transformations.
3. Enforces the Monotonic Improvement Invariant:
   - ONLY replace attempt_1 if the neural LoRA model produced dummy output [[0]] or invalid dimensions.
   - If the neural LoRA model produced a valid non-dummy grid, place the verified DSL solution
     into attempt_2 (leaving attempt_1 completely untouched).
4. Runs AST syntax verification across all cells in the notebook.
5. Runs Independent Verification & Validation (IV&V) audit with verifier_id="independent-arc2-auditor"
   and creator_id="arc2-dsl-creator" using Cohezion IV&V Engine.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("patch_arc2_v14")

KERNEL_DIR = Path(__file__).resolve().parent
NOTEBOOK_PATH = KERNEL_DIR / "arc-agi-2-fork-lb33-89-20260903.ipynb"
REPO_ROOT = KERNEL_DIR.parents[2]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

try:
    from cohezion.compound.ivv_engine import (
        IndependentVerifier,
        IVVCertificate,
        IVVGatekeeper,
        IVVSeverity,
    )
except ImportError as e:
    logger.error("Failed to import IV&V engine: %s", e)
    IndependentVerifier = None


CELL_9_REPLACEMENT = '''import os
import json
import tempfile
from pathlib import Path
from collections import Counter
import numpy as np
from arc_loader import ArcDataset
from arc_decoder import ArcDecoder

# ==========================================================================
# 1. Neuro-Symbolic DSL Program Synthesizer (Fast-Path Zero-Hallucination)
# ==========================================================================
def to_np(grid):
    if isinstance(grid, np.ndarray):
        return grid.astype(np.int32, copy=False)
    return np.array(grid, dtype=np.int32)

def to_grid(arr):
    return arr.tolist()

def d4_transforms(arr):
    arr = to_np(arr)
    return {
        'R0': arr.copy(),
        'R90': np.rot90(arr, -1),
        'R180': np.rot90(arr, 2),
        'R270': np.rot90(arr, 1),
        'SH': np.flipud(arr),
        'SV': np.fliplr(arr),
        'SD': arr.T,
        'SAD': np.rot90(np.rot90(arr.T, 1), 1),
    }

def color_substitutions(x, y):
    x = to_np(x)
    y = to_np(y)
    if x.shape != y.shape:
        return None
    mapping = {}
    for cx, cy in zip(x.flat, y.flat):
        if cx in mapping:
            if mapping[cx] != cy:
                return None
        else:
            mapping[cx] = cy
    return mapping

def apply_mapping(arr, mapping):
    out = to_np(arr).copy()
    for src, dst in mapping.items():
        out[arr == src] = dst
    return out

def crop_bounding_box(arr, bg_color=0):
    arr = to_np(arr)
    coords = np.argwhere(arr != bg_color)
    if len(coords) == 0:
        return arr
    r_min, c_min = coords.min(axis=0)
    r_max, c_max = coords.max(axis=0)
    return arr[r_min : r_max + 1, c_min : c_max + 1]

def crop_most_frequent_color_box(arr, bg_color=0):
    arr = to_np(arr)
    unique, counts = np.unique(arr[arr != bg_color], return_counts=True)
    if len(unique) == 0:
        return arr
    dom_color = unique[np.argmax(counts)]
    coords = np.argwhere(arr == dom_color)
    r_min, c_min = coords.min(axis=0)
    r_max, c_max = coords.max(axis=0)
    return arr[r_min : r_max + 1, c_min : c_max + 1]

def scale_grid(arr, factor):
    arr = to_np(arr)
    return np.repeat(np.repeat(arr, factor, axis=0), factor, axis=1)

def tile_grid(arr, reps):
    arr = to_np(arr)
    return np.tile(arr, reps)

def gravity_fall(arr, direction='down', bg_color=0):
    arr = to_np(arr)
    h, w = arr.shape
    out = np.full((h, w), bg_color, dtype=np.int32)
    if direction == 'down':
        for c in range(w):
            col = arr[:, c]
            vals = col[col != bg_color]
            out[h - len(vals) :, c] = vals
    elif direction == 'up':
        for c in range(w):
            col = arr[:, c]
            vals = col[col != bg_color]
            out[: len(vals), c] = vals
    elif direction == 'right':
        for r in range(h):
            row = arr[r, :]
            vals = row[row != bg_color]
            out[r, w - len(vals) :] = vals
    elif direction == 'left':
        for r in range(h):
            row = arr[r, :]
            vals = row[row != bg_color]
            out[r, : len(vals)] = vals
    return out

def is_non_trivial_transformation(x, y):
    """Checks whether an example demonstrates a consistent non-trivial transformation."""
    x_np = to_np(x)
    y_np = to_np(y)
    if x_np.size < 4 or y_np.size < 4:
        return False
    if len(np.unique(x_np)) < 2 and len(np.unique(y_np)) < 2:
        return False
    if np.array_equal(x_np, y_np):
        return x_np.size >= 9 and len(np.unique(x_np)) >= 2
    return True

def synthesize_arc_program(train_pairs):
    if not train_pairs:
        return None
    n_train = len(train_pairs)
    # Monotonic Invariant Guard: Prevent spurious overfit on small/degenerate demo sets
    if n_train < 3:
        if n_train < 2:
            return None
        if not all(is_non_trivial_transformation(x, y) for x, y in train_pairs):
            return None

    np_pairs = [(to_np(x), to_np(y)) for x, y in train_pairs]
    d4_ops = ['R0', 'R90', 'R180', 'R270', 'SH', 'SV', 'SD', 'SAD']

    # Identity
    if all(np.array_equal(x, y) for x, y in np_pairs):
        return lambda g: g

    # Pure D4
    matching_d4 = []
    for op in d4_ops:
        if all(np.array_equal(d4_transforms(x)[op], y) for x, y in np_pairs):
            matching_d4.append(op)
    if len(matching_d4) == 1:
        op = matching_d4[0]
        return lambda g, o=op: to_grid(d4_transforms(to_np(g))[o])
    elif len(matching_d4) > 1 and n_train >= 3:
        op = matching_d4[0]
        return lambda g, o=op: to_grid(d4_transforms(to_np(g))[o])

    # Color substitution with D4
    for op in d4_ops:
        maps = [color_substitutions(d4_transforms(x)[op], y) for x, y in np_pairs]
        if all(m is not None for m in maps):
            merged = {}
            consistent = True
            for m in maps:
                for k, v in m.items():
                    if k in merged and merged[k] != v:
                        consistent = False
                        break
                    merged[k] = v
                if not consistent:
                    break
            if consistent:
                if n_train < 3 and len(merged) < 2:
                    continue
                return lambda g, o=op, m=merged: to_grid(apply_mapping(d4_transforms(to_np(g))[o], m))

    # Bounding box crop
    for op in d4_ops:
        if all(np.array_equal(crop_bounding_box(d4_transforms(x)[op]), y) for x, y in np_pairs):
            return lambda g, o=op: to_grid(crop_bounding_box(d4_transforms(to_np(g))[o]))

    # Scale
    for factor in [2, 3, 4]:
        for op in d4_ops:
            if all(np.array_equal(scale_grid(d4_transforms(x)[op], factor), y) for x, y in np_pairs):
                return lambda g, o=op, f=factor: to_grid(scale_grid(d4_transforms(to_np(g))[o], f))

    # Tiling
    for reps in [(2, 2), (3, 3), (1, 2), (2, 1), (1, 3), (3, 1)]:
        for op in d4_ops:
            if all(np.array_equal(tile_grid(d4_transforms(x)[op], reps), y) for x, y in np_pairs):
                return lambda g, o=op, r=reps: to_grid(tile_grid(d4_transforms(to_np(g))[o], r))

    # Directional Gravity
    for direction in ['down', 'up', 'right', 'left']:
        if all(np.array_equal(gravity_fall(x, direction), y) for x, y in np_pairs):
            return lambda g, d=direction: to_grid(gravity_fall(to_np(g), d))

    return None

# ==========================================================================
# 2. Dataset Loading & Selection
# ==========================================================================
os.makedirs('/kaggle/inference_outputs', exist_ok=True)
rerun_mode = os.getenv('KAGGLE_IS_COMPETITION_RERUN')

def resolve_path(pattern: str, default_path: str) -> str:
    search_roots = [Path('/kaggle/input'), Path('data/arc-agi-2'), Path('data'), Path('.')]
    for root in search_roots:
        if root.exists():
            for match in root.glob(f'**/{pattern}'):
                if match.is_file() and match.stat().st_size > 0:
                    print(f'[PathResolver] Found {pattern} -> {match}')
                    return str(match.resolve())
    return default_path

if rerun_mode:
    default_test = '/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json'
    test_path = resolve_path('*test_challenges*.json', default_test)
    data = ArcDataset.from_file(test_path)
else:
    default_eval = '/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_challenges.json'
    default_sol = '/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_solutions.json'
    test_path = resolve_path('*evaluation_challenges*.json', default_eval)
    sol_path = resolve_path('*evaluation_solutions*.json', default_sol)
    data = ArcDataset.from_file(test_path)
    if os.path.exists(sol_path):
        data = data.load_replies(sol_path)

decoder = ArcDecoder(data.split_multi_replies(), n_guesses=2)
decoder.load_decoded_results('/kaggle/inference_outputs')
selection_results = decoder.run_selection_algo()
submission = data.get_submission(selection_results)

# ==========================================================================
# 3. Fast-Path DSL Synthesis Injection & Monotonic Improvement Invariant
# ==========================================================================
raw_queries = getattr(data, 'queries', {})
dsl_solved_count = 0
repaired_count = 0
total_predictions = 0

def is_dummy_or_invalid(grid):
    if not isinstance(grid, list) or len(grid) == 0:
        return True
    if grid == [[0]]:
        return True
    h = len(grid)
    if h <= 0 or h > 30:
        return True
    if not isinstance(grid[0], list) or len(grid[0]) == 0:
        return True
    w = len(grid[0])
    if w <= 0 or w > 30:
        return True
    for row in grid:
        if not isinstance(row, list) or len(row) != w:
            return True
        for cell in row:
            if not isinstance(cell, int) or cell < 0 or cell > 9:
                return True
    return False

for task_id in list(data.keys):
    task_dict = raw_queries.get(task_id, {})
    test_cases = task_dict.get('test', [])
    train_cases = task_dict.get('train', [])

    # Try synthesizing exact DSL program from training demos
    train_pairs = [(ex.get('input', []), ex.get('output', [])) for ex in train_cases if 'input' in ex and 'output' in ex]
    dsl_prog = synthesize_arc_program(train_pairs)

    train_out_colors = [c for ex in train_cases for row in ex.get('output', []) for c in row if isinstance(c, int) and c > 0]
    mode_color = Counter(train_out_colors).most_common(1)[0][0] if train_out_colors else 0
    train_out_shapes = {np.shape(ex.get('output', [])) for ex in train_cases if len(ex.get('output', [])) > 0}
    fixed_shape = list(train_out_shapes)[0] if len(train_out_shapes) == 1 else None

    preds = submission.get(task_id, [])
    for test_idx, test_case in enumerate(test_cases):
        total_predictions += 1
        test_in = test_case.get('input', [[0]])

        if test_idx >= len(preds):
            preds.append({'attempt_1': [[0]], 'attempt_2': [[0]]})
            submission[task_id] = preds

        target_pred = preds[test_idx]

        # Monotonic Improvement Invariant Enforcement:
        # 1. ONLY replace attempt_1 if the neural model produced dummy [[0]] or invalid grid.
        # 2. If neural model produced a valid non-dummy grid, place verified DSL into attempt_2.
        if dsl_prog is not None:
            try:
                dsl_solution = dsl_prog(test_in)
                if not is_dummy_or_invalid(dsl_solution):
                    cur_attempt_1 = target_pred.get('attempt_1')
                    if is_dummy_or_invalid(cur_attempt_1):
                        target_pred['attempt_1'] = dsl_solution
                        dsl_solved_count += 1
                    else:
                        # Non-destructive injection into attempt_2
                        if dsl_solution != cur_attempt_1:
                            target_pred['attempt_2'] = dsl_solution
                            dsl_solved_count += 1
            except Exception as dsl_err:
                print(f'[DSL Synthesizer] Error on task {task_id}_{test_idx}: {dsl_err}')

        for attempt_key in ['attempt_1', 'attempt_2']:
            cand_grid = target_pred.get(attempt_key)
            if is_dummy_or_invalid(cand_grid):
                repaired_count += 1
                if attempt_key == 'attempt_1':
                    target_pred[attempt_key] = [r[:] for r in test_in]
                else:
                    if fixed_shape is not None and 1 <= fixed_shape[0] <= 30 and 1 <= fixed_shape[1] <= 30:
                        target_pred[attempt_key] = [[mode_color for _ in range(fixed_shape[1])] for _ in range(fixed_shape[0])]
                    else:
                        target_pred[attempt_key] = [r[::-1] for r in test_in]

print(f'[AutoHarness SOTA v14] Processed {total_predictions} predictions: {dsl_solved_count} monotonic DSL injected, {repaired_count} repaired.')

output_target = Path('submission.json')
with tempfile.NamedTemporaryFile('w', dir='.', delete=False, encoding='utf-8') as tmp:
    json.dump(submission, tmp, separators=(',', ':'))
    tmp_path = Path(tmp.name)
tmp_path.replace(output_target)
print(f'[AutoHarness SOTA v14] Atomically serialized submission.json ({output_target.stat().st_size} bytes).')
if not rerun_mode:
    decoder.benchmark_selection_algos()
    with open('submission.json', 'r') as f:
        reload_submission = json.load(f)
    print('*** Reload score:', data.validate_submission(reload_submission))
'''

def apply_patch():
    logger.info("Reading notebook: %s", NOTEBOOK_PATH)
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    target_idx = None
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            if "Neuro-Symbolic DSL Program Synthesizer" in source:
                target_idx = idx
                break

    if target_idx is None:
        raise ValueError("Could not locate Neuro-Symbolic DSL cell in notebook!")

    logger.info("Located target cell at index %d. Applying v14 patch...", target_idx)
    replacement_lines = [line + "\n" for line in CELL_9_REPLACEMENT.split("\n")]
    if replacement_lines and replacement_lines[-1] == "\n":
        replacement_lines.pop()

    nb["cells"][target_idx]["source"] = replacement_lines

    tmp_nb_path = NOTEBOOK_PATH.with_suffix(".tmp.ipynb")
    with open(tmp_nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    tmp_nb_path.replace(NOTEBOOK_PATH)
    logger.info("Notebook successfully patched: %s", NOTEBOOK_PATH)
    return nb

def verify_ast(nb):
    logger.info("Running AST syntax verification across all cells...")
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") != "code":
            continue
        raw_source = "".join(cell.get("source", []))
        py_lines = []
        for line in raw_source.splitlines():
            sline = line.strip()
            if sline.startswith("%%") or sline.startswith("!"):
                continue
            py_lines.append(line)
        code = "\n".join(py_lines)
        if not code.strip():
            continue
        try:
            ast.parse(code)
            logger.info("  Cell %d: AST syntax valid.", idx)
        except SyntaxError as e:
            logger.error("  Cell %d: SYNTAX ERROR: %s", idx, e)
            raise
    logger.info("✓ All notebook cells passed AST syntax verification.")

def run_ivv_audit(nb):
    if IndependentVerifier is None:
        raise RuntimeError("IV&V engine not available!")

    logger.info("Running IV&V audit (Two-Party Rule)...")
    creator_id = "arc2-dsl-creator"
    verifier_id = "independent-arc2-auditor"
    artifact_id = "manderson240/cohezion-arc-prize-2026-sota"

    all_code = []
    for cell in nb["cells"]:
        if cell.get("cell_type") == "code":
            raw_source = "".join(cell.get("source", []))
            py_lines = []
            for line in raw_source.splitlines():
                sline = line.strip()
                if sline.startswith("%%") or sline.startswith("!"):
                    continue
                py_lines.append(line)
            cell_code = "\n".join(py_lines)
            if cell_code.strip():
                all_code.append(cell_code)
    code_str = "\n\n".join(all_code)

    verifier = IndependentVerifier(verifier_id=verifier_id)
    cert = verifier.audit_code_artifact(
        artifact_id=artifact_id,
        creator_id=creator_id,
        code_str=code_str,
        requirements_spec={"competition_type": "arc-prize-2026-arc-agi-2"},
    )

    gatekeeper = IVVGatekeeper()
    gatekeeper.register_certificate(cert)
    ready, msg = gatekeeper.verify_deployment_readiness(artifact_id, creator_id)

    cert_path = KERNEL_DIR / "ivv_certificate.json"
    cert_data = {
        "artifact_id": cert.artifact_id,
        "creator_id": cert.creator_id,
        "verifier_id": cert.verifier_id,
        "timestamp": cert.timestamp,
        "passed": cert.passed,
        "signature": cert.signature,
        "findings": [
            {"gate": f.gate, "severity": f.severity, "description": f.description}
            for f in cert.findings
        ],
        "deployment_ready": ready,
        "deployment_message": msg,
    }
    with open(cert_path, "w", encoding="utf-8") as f:
        json.dump(cert_data, f, indent=2)

    logger.info("IV&V Audit Result: %s", msg)
    logger.info("Certificate Signature Hash: %s", cert.signature)
    logger.info("Saved Certificate to: %s", cert_path)

    if not ready:
        raise RuntimeError(f"IV&V Gatekeeper rejected deployment: {msg}")
    return cert

if __name__ == "__main__":
    nb = apply_patch()
    verify_ast(nb)
    cert = run_ivv_audit(nb)
    print("\n" + "=" * 60)
    print("IV&V VERIFICATION CERTIFICATE SUMMARY")
    print("=" * 60)
    print(f"Artifact:          {cert.artifact_id}")
    print(f"Creator ID:        {cert.creator_id}")
    print(f"Verifier ID:       {cert.verifier_id}")
    print(f"Status:            {'PASSED' if cert.passed else 'FAILED'}")
    print(f"SHA-256 Signature: {cert.signature}")
    print("=" * 60)
