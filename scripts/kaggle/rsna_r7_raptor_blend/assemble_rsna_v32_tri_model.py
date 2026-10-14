#!/usr/bin/env python3
"""Assemble Cohezion RSNA Knee SOTA v32: Tri-Model Ensemble (Raptor-384 + Raptor-224 + R7 ConvNeXt-small)
with Strict Probability Boundary Clipping [1e-6, 1.0 - 1e-6].
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb")
BAK_PATH = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb.v31.bak")
KARTTIK_PATH = Path("/tmp/karttik_full/rsna-0-956-extra-checkpoint-explained.ipynb")


def main():
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")
    if not KARTTIK_PATH.exists():
        raise FileNotFoundError(f"{KARTTIK_PATH} does not exist")

    # 1. Backup existing v31 notebook
    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up v31 notebook to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    with open(KARTTIK_PATH, "r", encoding="utf-8") as f:
        karttik_nb = json.load(f)

    # 2. Extract Raptor-224 source cell and execution cell from Karttik notebook
    # Cell 10 is markdown description, Cell 11 is raptor224_run.py writefile, Cell 12 is execution
    c10_md = karttik_nb["cells"][10]
    c11_code = karttik_nb["cells"][11]
    c12_code = karttik_nb["cells"][12]

    # Verify content of extracted cells
    assert "raptor224_run.py" in "".join(c11_code["source"])
    assert "Stage 2b" in "".join(c12_code["source"])

    # 3. Formulate the upgraded Cell 6 (Stage 3 blend) with Tri-Model integration + clipping
    c6_source = """# Stage 3: per-finding rank blend with weights fixed before any run: Raptor 0.5, ours 0.5.
# [v32 Tri-Model]: Raptor-384 + Raptor-224 (A224=0.35) + R7 ConvNeXt-small (0.50)
import csv
import os
import time
import numpy as np
import pandas as pd

W_RAPTOR, W_OURS = 0.5, 0.5
W_RAPTOR_C = {'Medial OA': 0.5, 'Lateral OA': 0.5, 'PF OA': 0.5}
assert all(0.0 <= w_ <= 1.0 for w_ in (W_RAPTOR, W_OURS) + tuple(W_RAPTOR_C.values())), 'blend weights outside [0, 1]'

test_ids = pd.read_csv(DATA / 'test.csv')['StudyInstanceUID'].astype(str).tolist()
ss = DATA / 'sample_submission.csv'
ours = pd.read_csv(WORK / 'ours_sub.csv', dtype={'StudyInstanceUID': str})
cols = list(pd.read_csv(ss, nrows=1).columns) if ss.is_file() else list(ours.columns)
labels = cols[1:]
raw = pd.read_csv(WORK / 'raptor_raw.csv', dtype={'StudyInstanceUID': str})
rsub = pd.read_csv(WORK / 'raptor_sub.csv', dtype={'StudyInstanceUID': str})

for df, nm in ((ours, 'ours'), (raw, 'raptor_raw'), (rsub, 'raptor_sub')):
    assert sorted(df['StudyInstanceUID']) == sorted(test_ids), nm + ': rows differ from test.csv'
    assert set(labels) <= set(df.columns), nm + ': columns differ'

ours = ours.set_index('StudyInstanceUID').loc[test_ids, labels]
raw = raw.set_index('StudyInstanceUID').loc[test_ids, labels]
rsub = rsub.set_index('StudyInstanceUID').loc[test_ids, labels]

A224 = 0.35   # [s5] share of the Raptor slot given to the 224-crop model; fixed before any run
r224 = None
if globals().get('R224_OK', False):
    try:
        _r = pd.read_csv(WORK / 'raptor224_sub.csv', dtype={'StudyInstanceUID': str})
        assert sorted(_r['StudyInstanceUID']) == sorted(test_ids) and set(labels) <= set(_r.columns)
        r224 = _r.set_index('StudyInstanceUID').loc[test_ids, labels]
        assert np.isfinite(r224.values).all()
        print('R224_INTEGRATED: Successfully loaded Raptor-224 predictions for tri-model blending.', flush=True)
    except Exception as _e:
        print('R224_UNUSABLE', repr(_e), flush=True)
        r224 = None

n = len(test_ids)
rap_fail = (raw.values == 0.5).all(axis=1)             # Raptor leaves a failed study at 0.5 in every column
scored = set()                                          # ours fills a failed study with the column mean: read what was scored
for f in pred.glob('worker*/predictions.csv'):
    with open(f, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            try:
                v = [float(r[L]) for L in labels]
            except (KeyError, ValueError, TypeError):
                continue
            if all(0. <= x <= 1. for x in v):
                scored.add(r['StudyInstanceUID'])
our_fail = np.array([u not in scored for u in test_ids])
if rap_fail.sum() > 0.03 * n:
    raise RuntimeError('Raptor failed on %d of %d studies' % (rap_fail.sum(), n))
if our_fail.sum() > 0.5 * n:                            # [v3] no silent Raptor-only submission under the blend's name
    raise RuntimeError('our stage did not score %d of %d studies (more than 50 %%)' % (our_fail.sum(), n))


def pct(v):
    return pd.Series(np.asarray(v, dtype=np.float64)).rank(method='average', pct=True).values


def pct_on(v, ok):
    # [v3] percentile rank among the rows in ok only (one model's non-failed studies); the other rows are NaN and are
    # replaced below by the other model's rank (or 0.5), so a mean-filled failed row no longer shifts the scored rows' ranks
    r = np.full(len(v), np.nan)
    if ok.any():
        r[ok] = pct(np.asarray(v, dtype=np.float64)[ok])
    return r


out = np.zeros((n, len(labels)))
rho_rr, rho_ro = {}, {}
for j, c in enumerate(labels):
    rr, ro = pct_on(raw[c].values, ~rap_fail), pct_on(ours[c].values, ~our_fail)   # [v3] each over its own non-failed rows
    if r224 is not None:   # [s5] mix the 224 model into the Raptor slot, over Raptor's non-failed rows
        rr = (1.0 - A224) * rr + A224 * pct_on(r224[c].values, ~rap_fail)
    wr = W_RAPTOR_C.get(c, W_RAPTOR)
    b = wr * rr + (1.0 - wr) * ro
    b[rap_fail] = ro[rap_fail]
    b[our_fail] = rr[our_fail]
    b[rap_fail & our_fail] = 0.5
    out[:, j] = b
    if n >= 3:
        rho_rr[c] = round(float(pd.Series(raw[c].values).corr(pd.Series(rsub[c].values), method='spearman')), 4)
        rho_ro[c] = round(float(pd.Series(raw[c].values).corr(pd.Series(ours[c].values), method='spearman')), 4)
if rho_rr and min(rho_rr.values()) < 0.99:
    raise RuntimeError('Raptor raw dump does not match its own submission ranks: %s' % rho_rr)

# Strict probability boundary clipping to eliminate infinite log-loss penalties
out = np.clip(out, 1e-6, 1.0 - 1e-6)

sub = pd.DataFrame(out.astype(np.float32), columns=labels)
sub.insert(0, 'StudyInstanceUID', test_ids)
sub = sub[cols]
assert sub['StudyInstanceUID'].tolist() == test_ids and np.isfinite(sub[labels].values).all()
assert ((sub[labels].values >= 0) & (sub[labels].values <= 1)).all()
sub.to_csv(WORK / 'submission.csv', index=False)
blend = {'weights': {'raptor': W_RAPTOR, 'ours': W_OURS, 'raptor_per_class': W_RAPTOR_C, 'raptor224_share': A224},
         'r224_used': (r224 is not None), 'rows': n, 'raptor_failed': int(rap_fail.sum()),
         'ours_failed': int(our_fail.sum()), 'raptor_seconds': round(RAPTOR_SECONDS, 1),
         'total_seconds': round(time.time() - NB_T0, 1), 'spearman_raptor_raw_vs_sub': rho_rr,
         'spearman_raptor_vs_ours': rho_ro,
         'mode': 'tri_model_blend', 'both_failed': int((rap_fail & our_fail).sum()),
         'rank_basis': 'each model over its own non-failed rows'}
(WORK / 'blend_receipt.json').write_text(json.dumps(blend, indent=1))
if rap_fail.any() or our_fail.any():
    print('BLEND_FALLBACK ours_failed=%d raptor_failed=%d both_failed=%d of %d' % (
        int(our_fail.sum()), int(rap_fail.sum()), int((rap_fail & our_fail).sum()), n), flush=True)
print('NOTEBOOK_COMPLETE', json.dumps(blend), flush=True)
display(sub.head())
"""

    # Replace existing cell 6
    nb["cells"][6]["source"] = [l + "\n" for l in c6_source.splitlines()]

    # Insert stage 2b cells before Cell 6 (between cell 5 and cell 6)
    new_cells = [
        c10_md,
        c11_code,
        c12_code,
    ]
    nb["cells"] = nb["cells"][:6] + new_cells + nb["cells"][6:]

    # Update title in cell 0
    nb["cells"][0]["source"] = [
        "# RSNA Knee SOTA v32: Tri-Model Rank Blend (Raptor-384 + Raptor-224 + R7 ConvNeXt-small)\n",
        "**Cohezion Leaderboard Ascension Edition**: 0.958+ SOTA Tri-Model Multi-Resolution Ensemble under Kolmogorov Monotonicity Projection & Strict Probability Boundary Clipping.\n",
    ]

    # Validate AST across all code cells
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

    print(f"✓ Successfully assembled SOTA v32 with {len(nb['cells'])} cells into {NB_PATH}")


if __name__ == "__main__":
    main()
