#!/usr/bin/env python3
"""Routine run: FLUME VAE hyperparameter autoresearch.

Companion to routine_skill_geometry.py. One experiment per invocation:
  1. Read data/flume_vae_autoresearch.jsonl for current best hyperparameters
  2. Perturb kl_weight / z_dim to generate next candidate (or use search grid)
  3. Run a short 5-epoch training pass in a child subprocess (isolated crash domain)
  4. Parse recon_loss + kl_div from child output
  5. Append WIN (beats prior best recon_loss) or LOSS to JSONL

A3 invariant: kl_weight clamped to ≤ 0.01 (posterior collapse guard).
  LFQ variants are exempt — no KL term, no collapse risk.
A4 note: optimal is 2-layer decoder, hidden_dim=4096 per autoresearch canon —
  FlumeVAETrainer uses hidden=z_dim*2 internally; hidden_dim is recorded as the
  effective hidden (z_dim*2) rather than the canonical 4096 to maintain
  measurement integrity.

Only inference port used: :13305 (OmniRouter), for optional hypothesis summary.
Sweep dims (VAE): kl_weight ∈ {0.001, 0.003, 0.005, 0.007, 0.010},
                  z_dim ∈ {128, 256, 512}
Sweep dims (LFQ): n_bits ∈ {8, 16, 32}, z_dim=256 (UniAR-style, no KL)

Run manually:
    uv run python scripts/drivers/routine_flume_variate.py

Schedule via CronCreate (from an interactive Claude Code session):
    CronCreate(
        schedule="0 7 * * *",  # 07:00 UTC daily
        prompt="Run FLUME VAE autoresearch: uv run python scripts/drivers/routine_flume_variate.py"
    )
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AUTORESEARCH_JSONL = _REPO_ROOT / "data" / "flume_vae_autoresearch.jsonl"
_LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
_NPU_MODEL = "llama3.2-1b-FLM"

# ── A3 invariant: kl_weight must never exceed this ───────────────────────────
_KL_WEIGHT_MAX = 0.01

# ── Search grid (exhausted in order; perturbation after all grid points tried) ─
# VAE entries: kl_weight × z_dim (A3 invariant: kl_weight ≤ 0.01)
# LFQ entries: use_lfq=True, n_bits ∈ {8,16,32} (no KL term, A3 exempt)
_GRID: list[dict] = [
    {"kl_weight": 0.007, "z_dim": 256},          # near-optimal from autoresearch canon
    {"kl_weight": 0.005, "z_dim": 256},
    {"kl_weight": 0.003, "z_dim": 256},
    {"kl_weight": 0.010, "z_dim": 256},           # A3 ceiling
    {"kl_weight": 0.001, "z_dim": 256},           # minimum: very low beta
    {"kl_weight": 0.007, "z_dim": 128},           # smaller latent
    {"kl_weight": 0.007, "z_dim": 512},           # larger latent
    {"kl_weight": 0.005, "z_dim": 128},
    {"kl_weight": 0.005, "z_dim": 512},
    {"kl_weight": 0.003, "z_dim": 128},
    {"kl_weight": 0.003, "z_dim": 512},
    {"kl_weight": 0.010, "z_dim": 128},
    {"kl_weight": 0.010, "z_dim": 512},
    # LFQ sweep: UniAR-style bitwise quantization, no KL (2606.18249)
    {"use_lfq": True, "n_bits": 16, "z_dim": 256},  # medium — baseline LFQ
    {"use_lfq": True, "n_bits": 32, "z_dim": 256},  # light quantization
    {"use_lfq": True, "n_bits": 8,  "z_dim": 256},  # heavy — max compression
]

# ── Subprocess child script (runs inside .venv) ───────────────────────────────
_CHILD_TEMPLATE = """\
import json, sys
from pathlib import Path

_REPO_ROOT = Path({repo_root!r})
sys.path.insert(0, str(_REPO_ROOT / "src"))

from cohezion.flume.dataset import RealSkillStateDataset
from cohezion.flume.training import FlumeVAETrainer, TrainConfig

cfg = TrainConfig(
    z_dim={z_dim},
    epochs={epochs},
    kl_weight={kl_weight},
    batch_size=64,
    lr=1e-3,
    log_interval=1,
    checkpoint_dir=str(_REPO_ROOT / "data" / "flume" / "checkpoints" / "autoresearch"),
    data_dir=str(_REPO_ROOT / "data" / "mass_sim" / "artifacts"),
    max_samples=2000,
)

# Ground training in real vault_neuron outcomes; falls back to synthetic if SurrealDB offline.
dataset = RealSkillStateDataset(n_samples=2000, z_dim={z_dim}, seed=42)

trainer = FlumeVAETrainer(config=cfg)
metrics = trainer.train(dataset=dataset)

last = metrics[-1]
result = {{
    "recon_loss": round(float(last["mse"]), 6),
    "kl_div":     round(float(last["kl"]), 6),
    "total_loss": round(float(last["total"]), 6),
    "epoch":      int(last["epoch"]),
}}
print("__RESULT__" + json.dumps(result))
"""

# ── LFQ subprocess child script ───────────────────────────────────────────────
# Self-contained: trains LFQLayer directly, no FlumeVAETrainer dependency.
# Uses RealSkillStateDataset (falls back to synthetic if SurrealDB offline).
_LFQ_CHILD_TEMPLATE = """\
import json, sys
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from torch.utils.data import DataLoader

_REPO_ROOT = Path({repo_root!r})
sys.path.insert(0, str(_REPO_ROOT / "src"))

from cohezion.flume.vae import LFQLayer
from cohezion.flume.dataset import RealSkillStateDataset

input_dim = {z_dim}
n_bits = {n_bits}
hidden = input_dim * 2
epochs = {epochs}

encoder = nn.Sequential(
    nn.Linear(input_dim, hidden), nn.ReLU(),
    nn.Linear(hidden, hidden), nn.ReLU(),
)
# LFQ operates on encoder output dimension (hidden), not input_dim
lfq = LFQLayer(hidden, n_bits=n_bits)
decoder = nn.Sequential(
    nn.Linear(hidden, hidden), nn.ReLU(),
    nn.Linear(hidden, hidden), nn.ReLU(),
    nn.Linear(hidden, input_dim),
)
params = list(encoder.parameters()) + list(lfq.parameters()) + list(decoder.parameters())
opt = torch.optim.Adam(params, lr=1e-3)

# Ground training in real vault_neuron outcomes; falls back to synthetic if SurrealDB offline.
dataset = RealSkillStateDataset(n_samples=2000, z_dim=input_dim, seed=42)
loader = DataLoader(dataset, batch_size=64, shuffle=True)

history = []
for epoch in range(1, epochs + 1):
    total_recon = total_commit = n_batches = 0
    for batch in loader:
        x = (batch[0] if isinstance(batch, (list, tuple)) else batch).float()
        h = encoder(x)
        z, commit_loss = lfq(h)
        recon = decoder(z)
        recon_loss = F.mse_loss(recon, x)
        loss = recon_loss + 0.25 * commit_loss
        opt.zero_grad()
        loss.backward()
        opt.step()
        total_recon += recon_loss.item()
        total_commit += commit_loss.item()
        n_batches += 1
    history.append({{
        "epoch": epoch,
        "mse": total_recon / n_batches,
        "commit": total_commit / n_batches,
        "total": (total_recon + 0.25 * total_commit) / n_batches,
    }})

last = history[-1]
result = {{
    "recon_loss":  round(float(last["mse"]), 6),
    "kl_div":      0.0,
    "commit_loss": round(float(last["commit"]), 6),
    "total_loss":  round(float(last["total"]), 6),
    "epoch":       int(last["epoch"]),
}}
print("__RESULT__" + json.dumps(result))
"""

# ── Lemonade query (optional) ─────────────────────────────────────────────────

def _query_lemonade(prompt: str, *, timeout: float = 15.0) -> str | None:
    """POST to :13305 for a quick text summary. Returns None if offline."""
    payload = json.dumps({
        "model": _NPU_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120,
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(  # noqa: S310
        _LEMONADE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read())
        choices = data.get("choices", [{}])
        msg = choices[0].get("message", {})
        return (msg.get("content") or msg.get("reasoning_content") or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


# ── State helpers ──────────────────────────────────────────────────────────────

def _read_records() -> list[dict]:
    """Return all records from the autoresearch JSONL, or []."""
    if not _AUTORESEARCH_JSONL.exists():
        return []
    records = []
    for line in _AUTORESEARCH_JSONL.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def _tried_variants(records: list[dict]) -> set[tuple]:
    """Return set of variant keys already attempted.

    VAE key: ("vae", kl_weight_rounded, z_dim)
    LFQ key: ("lfq", n_bits, z_dim)
    """
    seen: set[tuple] = set()
    for r in records:
        res = r.get("result", {})
        if res.get("use_lfq"):
            nb = res.get("n_bits")
            z = res.get("z_dim")
            if nb is not None and z is not None:
                seen.add(("lfq", int(nb), int(z)))
        else:
            kl = res.get("kl_weight")
            z = res.get("z_dim")
            if kl is not None and z is not None:
                seen.add(("vae", round(float(kl), 6), int(z)))
    return seen


def _best_winner(records: list[dict]) -> dict | None:
    """Return the result dict of the best (lowest recon_loss) WIN record."""
    wins = [r for r in records if r.get("status") == "WIN"]
    if not wins:
        return None
    return min(wins, key=lambda r: r.get("result", {}).get("recon_loss", float("inf")))


def _next_exp_id(records: list[dict]) -> str:
    for r in reversed(records):
        exp = r.get("exp", "")
        if exp.startswith("exp_FLUME_VAE_"):
            try:
                n = int(exp.split("_")[-1]) + 1
                return f"exp_FLUME_VAE_{n:04d}"
            except ValueError:
                pass
    return "exp_FLUME_VAE_0001"


def _pick_variant(records: list[dict]) -> dict:
    """Pick the next hyperparameter candidate.

    Priority:
      1. First untried grid point (deterministic, exhausts search space first)
      2. Perturb the best winner (Gaussian walk within valid range, VAE only)
      3. Wrap around to grid start if all grid points exhausted
    """
    tried = _tried_variants(records)

    # Walk the predefined grid first
    for g in _GRID:
        if g.get("use_lfq"):
            key = ("lfq", int(g["n_bits"]), int(g["z_dim"]))
        else:
            key = ("vae", round(g["kl_weight"], 6), int(g["z_dim"]))
        if key not in tried:
            return dict(g)

    # All grid points tried — perturb the best winner
    best = _best_winner(records)
    if best is not None:
        import random
        res = best.get("result", {})
        base_kl = float(res.get("kl_weight", 0.007))
        base_z = int(res.get("z_dim", 256))

        # Perturb kl_weight within [0.001, _KL_WEIGHT_MAX]
        rng = random.Random(int(time.monotonic() * 1e6) & 0xFFFFFFFF)
        delta_kl = rng.gauss(0, 0.002)
        kl_new = round(max(0.001, min(_KL_WEIGHT_MAX, base_kl + delta_kl)), 4)

        # Optionally flip z_dim
        z_choices = [128, 256, 512]
        z_new = rng.choice(z_choices) if rng.random() < 0.3 else base_z

        candidate = {"kl_weight": kl_new, "z_dim": z_new}
        key = (round(kl_new, 6), int(z_new))
        if key not in tried:
            return candidate

    # Fall back to first grid point (wrap around)
    return dict(_GRID[0])


# ── Subprocess training ────────────────────────────────────────────────────────

def _python_exec() -> str:
    """Return the venv Python path if it exists, else fall back to 'python3'."""
    venv_py = _REPO_ROOT / ".venv" / "bin" / "python3"
    if venv_py.exists():
        return str(venv_py)
    return "python3"


def _run_training(variant: dict, epochs: int = 5, timeout_s: float = 540.0) -> dict | None:
    """Run a training pass in a subprocess. Returns parsed metrics or None on failure."""
    python = _python_exec()
    use_lfq = variant.get("use_lfq", False)
    z = variant["z_dim"]

    if use_lfq:
        n_bits = variant["n_bits"]
        child_code = _LFQ_CHILD_TEMPLATE.format(
            repo_root=str(_REPO_ROOT),
            z_dim=z,
            n_bits=n_bits,
            epochs=epochs,
        )
        print(f"  [TRAIN] LFQ n_bits={n_bits}, z_dim={z}, epochs={epochs} via {Path(python).name}")
    else:
        kl = variant["kl_weight"]
        child_code = _CHILD_TEMPLATE.format(
            repo_root=str(_REPO_ROOT),
            z_dim=z,
            epochs=epochs,
            kl_weight=kl,
        )
        print(f"  [TRAIN] kl_weight={kl}, z_dim={z}, epochs={epochs} via {Path(python).name}")

    try:
        proc = subprocess.run(
            [python, "-c", child_code],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(_REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        print(f"  [TRAIN] TIMEOUT after {timeout_s:.0f}s — recording LOSS", file=sys.stderr)
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"  [TRAIN] subprocess error: {exc}", file=sys.stderr)
        return None

    if proc.returncode != 0:
        print(f"  [TRAIN] child exited {proc.returncode}", file=sys.stderr)
        if proc.stderr:
            print(proc.stderr[-800:], file=sys.stderr)
        return None

    # Parse sentinel line
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith("__RESULT__"):
            try:
                return json.loads(line[len("__RESULT__"):])
            except json.JSONDecodeError:
                pass

    print("  [TRAIN] no __RESULT__ sentinel in output", file=sys.stderr)
    if proc.stdout:
        print(proc.stdout[-400:], file=sys.stderr)
    return None


# ── Result persistence ─────────────────────────────────────────────────────────

def _append_record(
    exp_id: str,
    variant: dict,
    metrics: dict | None,
    status: str,
    best_before: dict | None,
    notes: str,
) -> None:
    z = variant["z_dim"]
    use_lfq = variant.get("use_lfq", False)
    if use_lfq:
        result_dict: dict = {
            "use_lfq": True,
            "n_bits": variant["n_bits"],
            "z_dim": z,
            "recon_loss": metrics.get("recon_loss") if metrics else None,
            "commit_loss": metrics.get("commit_loss") if metrics else None,
            "kl_div": 0.0,
            "total_loss": metrics.get("total_loss") if metrics else None,
            "epochs_run": metrics.get("epoch") if metrics else None,
        }
    else:
        kl = variant["kl_weight"]
        result_dict = {
            "kl_weight": kl,
            "z_dim": z,
            "effective_hidden_dim": z * 2,  # FlumeVAETrainer: hidden = z_dim*2
            "recon_loss": metrics.get("recon_loss") if metrics else None,
            "kl_div": metrics.get("kl_div") if metrics else None,
            "total_loss": metrics.get("total_loss") if metrics else None,
            "epochs_run": metrics.get("epoch") if metrics else None,
        }
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "exp": exp_id,
        "status": status,
        "result": result_dict,
        "prior_best_recon_loss": (
            best_before.get("result", {}).get("recon_loss") if best_before else None
        ),
        "notes": notes,
        "next": "continue autoresearch loop",
    }
    _AUTORESEARCH_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(_AUTORESEARCH_JSONL, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[RESULT] Appended {status} record: {exp_id}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    t0 = time.monotonic()
    print(f"[START] FLUME VAE autoresearch — {datetime.now(timezone.utc).isoformat()}")

    records = _read_records()
    best_before = _best_winner(records)
    print(
        f"  Prior records: {len(records)}, "
        f"best recon_loss: {best_before['result']['recon_loss'] if best_before else 'none'}"
    )

    variant = _pick_variant(records)
    exp_id = _next_exp_id(records)

    # A3 hard clamp applies to VAE variants only (LFQ has no KL term)
    if not variant.get("use_lfq"):
        variant["kl_weight"] = min(variant["kl_weight"], _KL_WEIGHT_MAX)

    if variant.get("use_lfq"):
        print(f"[VARIANT] {exp_id}: LFQ n_bits={variant['n_bits']}, z_dim={variant['z_dim']}")
    else:
        print(f"[VARIANT] {exp_id}: kl_weight={variant['kl_weight']}, z_dim={variant['z_dim']}")

    metrics = _run_training(variant, epochs=5)

    if metrics is None:
        notes = "Training subprocess failed or timed out."
        _append_record(exp_id, variant, None, "LOSS", best_before, notes)
        print(f"[DONE] {exp_id} LOSS (training failed) in {time.monotonic()-t0:.1f}s")
        return 0

    recon_loss = metrics["recon_loss"]
    kl_div = metrics["kl_div"]
    use_lfq = variant.get("use_lfq", False)
    if use_lfq:
        commit_loss = metrics.get("commit_loss", 0.0)
        print(f"  [METRICS] recon_loss={recon_loss:.6f}, commit_loss={commit_loss:.6f} (LFQ)")
    else:
        print(f"  [METRICS] recon_loss={recon_loss:.6f}, kl_div={kl_div:.6f}")

    # KL collapse guard applies only to VAE variants (LFQ always has kl_div=0.0 by design)
    kl_collapsed = (not use_lfq) and (kl_div < 0.002)

    if kl_collapsed:
        status = "LOSS"
        notes = (
            f"KL collapse: kl_div={kl_div:.6f} < 0.002 floor. "
            f"recon_loss={recon_loss:.6f}. Not a valid training outcome."
        )
    elif best_before is None:
        # First result with valid KL — always a WIN (establishes baseline)
        status = "WIN"
        notes = (
            f"First valid result — baseline established. "
            f"recon_loss={recon_loss:.6f}, kl_div={kl_div:.6f}."
        )
    elif recon_loss < best_before["result"]["recon_loss"]:
        status = "WIN"
        prior = best_before["result"]["recon_loss"]
        notes = (
            f"Beats prior best recon_loss {prior:.6f} → {recon_loss:.6f}. "
            f"kl_div={kl_div:.6f}."
        )
    else:
        status = "LOSS"
        prior = best_before["result"]["recon_loss"]
        notes = (
            f"Did not beat prior best recon_loss {prior:.6f} "
            f"(this={recon_loss:.6f}). kl_div={kl_div:.6f}."
        )

    # Optional: ask local Lemonade for a one-liner about this outcome
    if use_lfq:
        lemonade_prompt = (
            f"FLUME LFQ training: n_bits={variant['n_bits']}, z_dim={variant['z_dim']}, "
            f"recon_loss={recon_loss:.4f}, commit_loss={metrics.get('commit_loss', 0):.4f}, "
            f"status={status}. One sentence on what n_bits to try next."
        )
    else:
        lemonade_prompt = (
            f"FLUME VAE training: kl_weight={variant['kl_weight']}, z_dim={variant['z_dim']}, "
            f"recon_loss={recon_loss:.4f}, kl_div={kl_div:.4f}, status={status}. "
            f"One sentence on what to try next."
        )
    lemonade_note = _query_lemonade(lemonade_prompt, timeout=12.0)
    if lemonade_note:
        notes += f" LLM: {lemonade_note}"

    _append_record(exp_id, variant, metrics, status, best_before, notes)
    elapsed = time.monotonic() - t0
    print(f"[DONE] {exp_id} {status} in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
