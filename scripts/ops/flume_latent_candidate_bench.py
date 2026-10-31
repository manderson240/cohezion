"""Score candidate text latents on labelled paraphrase / hard-negative / unrelated pairs.

Usage (repo .venv, PYTHONPATH=<clone>/src):
    python scripts/ops/flume_latent_candidate_bench.py [--include-nomic]

Arms: hash (negative control), minilm (native, truncated-256, projected-256),
embed-gemma-300m-FLM via the router (NPU), and with --include-nomic the CPU nomic GGUF
plus ep21_distilled on top of it. The nomic arm is OFF by default: on the shared box the
gems-desk hook allows FLM models only (a CPU GGUF filled the lemond cgroup 2026-10-15).
Arms that cannot be reached print UNKNOWN, never a score.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests" / "fixtures"))
from flume_latent_pairs import HARD_NEG, PARAPHRASE, UNRELATED  # noqa: E402


ROUTER = "http://localhost:13305/v1/embeddings"
NOMIC_MODEL = "nomic-embed-text-v2-moe-GGUF"
GEMMA_MODEL = "embed-gemma-300m-FLM"


def router_embed(model: str, texts: list[str]) -> np.ndarray:
    out = []
    for t in texts:
        req = urllib.request.Request(
            ROUTER,
            data=json.dumps({"model": model, "input": t}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            out.append(json.load(r)["data"][0]["embedding"])
    arr = np.asarray(out, dtype=np.float32)
    if not np.isfinite(arr).all() or (np.linalg.norm(arr, axis=1) < 1e-6).any():
        raise RuntimeError(f"{model}: zero/non-finite vector returned")
    return arr


def unit(a: np.ndarray) -> np.ndarray:
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)


def project(a: np.ndarray, dim: int = 256, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    p = rng.standard_normal((a.shape[1], dim)).astype(np.float32) / np.sqrt(dim)
    return unit(a @ p)


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    wins = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(wins / (len(pos) * len(neg)))


def score(vecs: dict[str, np.ndarray]) -> dict[str, float]:
    def cos(pairs):
        return np.array([float(vecs[a] @ vecs[b]) for a, b in pairs])

    p, h, u = cos(PARAPHRASE), cos(HARD_NEG), cos(UNRELATED)
    neg = np.concatenate([h, u])
    thr = float(neg.max()) + 1e-6  # lowest threshold with zero false hits on this set
    return {
        "auc_all": auc(p, neg),
        "auc_hard": auc(p, h),
        "auc_unrel": auc(p, u),
        "thr_unrel": float(u.max()) + 1e-6,
        "recall_at_thr_unrel": float((p > u.max() + 1e-6).mean()),
        "hard_fp_at_thr_unrel": float((h > u.max() + 1e-6).mean()),
        "cos_para": float(p.mean()),
        "cos_hard": float(h.mean()),
        "cos_unrel": float(u.mean()),
        "thr_zero_fp": thr,
        "recall_at_zero_fp": float((p > thr).mean()),
        "recall_at_0.80": float((p >= 0.80).mean()),
        "fp_at_0.80": float((neg >= 0.80).mean()),
    }


def all_texts() -> list[str]:
    seen: dict[str, None] = {}
    for grp in (PARAPHRASE, HARD_NEG, UNRELATED):
        for a, b in grp:
            seen[a] = None
            seen[b] = None
    return list(seen)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-nomic", action="store_true")
    args = ap.parse_args()
    texts = all_texts()
    arms: dict[str, dict[str, np.ndarray] | str] = {}

    hash_enc = __import__("hashlib")
    arms["hash256 (control)"] = {t: _hash(t, hash_enc) for t in texts}

    try:
        from sentence_transformers import SentenceTransformer

        m = unit(SentenceTransformer("all-MiniLM-L6-v2", device="cpu").encode(texts))
        arms["minilm384 native"] = dict(zip(texts, m, strict=True))
        arms["minilm256 truncated"] = dict(zip(texts, unit(m[:, :256]), strict=True))
        arms["minilm256 projected"] = dict(zip(texts, project(m), strict=True))
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        arms["minilm"] = f"UNKNOWN: {type(exc).__name__}: {exc}"

    try:
        g = unit(router_embed(GEMMA_MODEL, texts))
        arms["embed-gemma768 (FLM)"] = dict(zip(texts, g, strict=True))
        arms["embed-gemma256 projected"] = dict(zip(texts, project(g), strict=True))
    except Exception as exc:  # noqa: BLE001
        arms["embed-gemma"] = f"UNKNOWN: {type(exc).__name__}: {exc}"

    if args.include_nomic:
        try:
            n = unit(router_embed(NOMIC_MODEL, texts))
            arms["nomic768"] = dict(zip(texts, n, strict=True))
            arms["nomic256 projected"] = dict(zip(texts, project(n), strict=True))
            import torch

            ckpt = torch.load(
                "/home/mike-anderson/dev/cohezion/data/flume/checkpoints/flume_vae_ep21_distilled.pt",
                map_location="cpu",
                weights_only=True,
            )
            enc = torch.nn.Sequential(
                torch.nn.Linear(768, 384),
                torch.nn.ReLU(),
                torch.nn.Linear(384, 256),
                torch.nn.ReLU(),
            )
            enc.load_state_dict(ckpt["encoder"])
            mu = torch.nn.Linear(256, 256)
            mu.load_state_dict(ckpt["mu_head"])
            with torch.no_grad():
                z = mu(enc(torch.tensor(n))).numpy()
            arms["ep21_distilled(nomic)"] = dict(zip(texts, unit(z), strict=True))
        except Exception as exc:  # noqa: BLE001
            arms["nomic/ep21"] = f"UNKNOWN: {type(exc).__name__}: {exc}"
    else:
        arms["nomic768"] = "UNKNOWN: not run (FLM-only hook); rerun with --include-nomic"
        arms["ep21_distilled(nomic)"] = "UNKNOWN: needs nomic vectors"

    print(
        "arm                          AUCunr AUChard cosP  cosH  cosU  thrU  recP@thrU hardFP@thrU | recP@.80 fpAll@.80"
    )
    for name, v in arms.items():
        if isinstance(v, str):
            print(f"{name:28s} {v}")
            continue
        s = score(v)
        print(
            f"{name:28s} {s['auc_unrel']:.3f}  {s['auc_hard']:.3f}  {s['cos_para']:.3f} "
            f"{s['cos_hard']:.3f} {s['cos_unrel']:.3f} {s['thr_unrel']:.3f} {s['recall_at_thr_unrel']:.2f}      "
            f"{s['hard_fp_at_thr_unrel']:.2f}        | {s['recall_at_0.80']:.2f}     {s['fp_at_0.80']:.2f}"
        )
    return 0


def _hash(text: str, hashlib) -> np.ndarray:
    """The pre-fix FlumeVAEEncoder._hash_encode, reproduced as the negative control."""
    d = hashlib.sha256(text.encode()).digest()
    e = np.array([d[i % 32] / 255.0 for i in range(256)], dtype=np.float32)
    return e / np.linalg.norm(e)


if __name__ == "__main__":
    raise SystemExit(main())
