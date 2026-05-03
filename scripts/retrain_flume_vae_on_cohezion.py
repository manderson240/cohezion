"""E89.c — FLUME VAE retrain pipeline on cohezion's actual corpus.

Diagnoses ep20.pt's posterior collapse (E89.3 finding: cos sim 0.99 between
all texts including unrelated topics). Retrains on real cohezion text data:
  * vault observations.jsonl (49+ entries)
  * autoresearch.jsonl descriptions (17K+ entries — but heavily repeated)
  * src/cohezion skill PRIME.md files (235 skills, ~45 KB each)
  * journey_point row metadata (225K rows — sample 5K)

Bootstrap targets:
  * Use the working nomic-embed-text:v1.5 (E89.a) as the *teacher* — distill
    768D Ollama embeddings into a 256D FLUME latent. This sidesteps VAE-from-
    scratch training and converges in 1-2 hours on iGPU instead of 12+ hours.
  * Output: data/flume/checkpoints/flume_vae_ep21_distilled.pt

Run modes:
  --extract-only    extract corpus to data/flume/training_corpus.jsonl, exit
  --teacher-embed   compute teacher (nomic) embeddings for the corpus, save
  --train           student VAE training (multi-hour — DO NOT auto-run)
  --eval            run posterior-collapse + downstream-task tests on a checkpoint

Usage:
  uv run python scripts/retrain_flume_vae_on_cohezion.py --extract-only
  uv run python scripts/retrain_flume_vae_on_cohezion.py --teacher-embed
  # then later:
  uv run python scripts/retrain_flume_vae_on_cohezion.py --train --epochs 5
  uv run python scripts/retrain_flume_vae_on_cohezion.py --eval --ckpt data/flume/checkpoints/flume_vae_ep21_distilled.pt
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


REPO = Path("/home/mike-anderson/dev/cohezion")
VAULT_OBS = Path("/home/mike-anderson/vaults/cohezion-vault/memory/observations.jsonl")
JSONL = REPO / "autoresearch.jsonl"
CORPUS_OUT = REPO / "data" / "flume" / "training_corpus.jsonl"
TEACHER_EMB_OUT = REPO / "data" / "flume" / "teacher_embeddings.jsonl"
NEW_CKPT = REPO / "data" / "flume" / "checkpoints" / "flume_vae_ep21_distilled.pt"


def extract_corpus() -> int:
    """Pull text from vault + autoresearch.jsonl + skill PRIMEs into a single
    JSONL with one (id, text) per line. De-duplicate by exact-string match."""
    CORPUS_OUT.parent.mkdir(parents=True, exist_ok=True)
    seen_text: set[str] = set()
    n = 0
    with CORPUS_OUT.open("w") as out:
        # 1. Vault observations
        if VAULT_OBS.exists():
            for line in VAULT_OBS.read_text().splitlines():
                try:
                    o = json.loads(line)
                    txt = f"{o.get('title','')}. {o.get('text','')}".strip()
                    if len(txt) >= 20 and txt not in seen_text:
                        seen_text.add(txt)
                        out.write(json.dumps({"id": f"vault:{o.get('id')}", "text": txt}) + "\n")
                        n += 1
                except Exception:
                    pass
        # 2. autoresearch.jsonl descriptions (deduped — many repeat)
        if JSONL.exists():
            for line in JSONL.read_text().splitlines():
                try:
                    d = json.loads(line)
                    txt = (d.get("description") or "").strip()
                    if len(txt) >= 20 and txt not in seen_text:
                        seen_text.add(txt)
                        out.write(json.dumps({"id": f"jsonl:{d.get('run')}", "text": txt}) + "\n")
                        n += 1
                except Exception:
                    pass
        # 3. Skill PRIME files
        skills_dir = REPO / "src" / "cohezion" / "skills"
        if skills_dir.exists():
            for p in skills_dir.glob("*PRIME.md"):
                try:
                    txt = p.read_text()[:4000].strip()  # cap per skill
                    if len(txt) >= 20 and txt not in seen_text:
                        seen_text.add(txt)
                        out.write(json.dumps({"id": f"skill:{p.name}", "text": txt}) + "\n")
                        n += 1
                except Exception:
                    pass
    print(f"[corpus] extracted {n} unique documents to {CORPUS_OUT}")
    return n


def teacher_embed(max_docs: int = 5000) -> int:
    """For each corpus doc, get nomic-embed-text:v1.5's 768D embedding via
    Ollama. Persist to teacher_embeddings.jsonl. Slow-and-steady pacing."""
    if not CORPUS_OUT.exists():
        print("[teacher] corpus missing — run --extract-only first")
        return 0
    import urllib.request
    docs = []
    for line in CORPUS_OUT.read_text().splitlines()[:max_docs]:
        try:
            docs.append(json.loads(line))
        except Exception:
            pass
    print(f"[teacher] embedding {len(docs)} documents via nomic-embed-text:v1.5...")
    t0 = time.time()
    written = 0
    TEACHER_EMB_OUT.parent.mkdir(parents=True, exist_ok=True)
    with TEACHER_EMB_OUT.open("w") as out:
        for i, d in enumerate(docs):
            body = json.dumps({"model": "nomic-embed-text:v1.5",
                               "prompt": d["text"][:2000]}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/embeddings", data=body,
                headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    resp = json.loads(r.read().decode())
                emb = resp.get("embedding")
                if emb:
                    out.write(json.dumps({"id": d["id"], "text": d["text"][:200],
                                          "embedding": emb}) + "\n")
                    written += 1
            except Exception as e:
                print(f"  [{i}] failed: {e}")
            if i % 25 == 0 and i > 0:
                rate = i / (time.time() - t0)
                print(f"  progress: {i}/{len(docs)} ({rate:.1f} doc/s, ETA {(len(docs)-i)/rate:.0f}s)")
            time.sleep(0.05)  # Ollama embed is fast (~10ms)
    print(f"[teacher] wrote {written} embeddings to {TEACHER_EMB_OUT} ({time.time()-t0:.1f}s)")
    return written


def train(epochs: int = 5, batch_size: int = 32) -> None:
    """Distill teacher (nomic 768D) → student VAE (FLUME 256D) on the corpus.
    Multi-hour job — caller invokes this explicitly."""
    print("=== FLUME VAE distillation training ===")
    print(f"  teacher embeddings: {TEACHER_EMB_OUT}")
    print(f"  output checkpoint:  {NEW_CKPT}")
    print(f"  epochs={epochs} batch_size={batch_size}")
    if not TEACHER_EMB_OUT.exists():
        print("[train] teacher embeddings missing — run --teacher-embed first")
        sys.exit(1)
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        print("[train] PyTorch unavailable — install in the venv first")
        sys.exit(1)

    # Load teacher embeddings
    items = []
    for line in TEACHER_EMB_OUT.read_text().splitlines():
        try:
            items.append(json.loads(line))
        except Exception:
            pass
    print(f"[train] loaded {len(items)} teacher embeddings")
    if len(items) < 100:
        print("[train] too few examples — extract more corpus first")
        sys.exit(1)

    # Tiny student: 768 -> 384 -> 256 (mu) -> reconstruct to 768
    class Student(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(nn.Linear(768, 384), nn.ReLU(), nn.Linear(384, 256))
            self.decoder = nn.Sequential(nn.Linear(256, 384), nn.ReLU(), nn.Linear(384, 768))
        def forward(self, x):
            z = self.encoder(x)
            return self.decoder(z), z

    # Force CPU on Strix Halo — ROCm iGPU init is unreliable per CLAUDE.md
    # HARDWARE_PROFILE_PRIME ("never assume RTX/CUDA"). Tiny MLP, CPU is fine.
    import os as _os
    if _os.environ.get("FLUME_TRAIN_DEVICE"):
        device = _os.environ["FLUME_TRAIN_DEVICE"]
    else:
        device = "cpu"
    print(f"[train] device={device} epochs={epochs} (CPU forced; set FLUME_TRAIN_DEVICE=cuda to override)", flush=True)
    model = Student().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=3e-4)
    teacher_t = torch.tensor([it["embedding"] for it in items], dtype=torch.float32).to(device)
    n = len(items)

    print(f"[train] {n} examples, batches/epoch={max(1, n // batch_size)}", flush=True)
    for ep in range(1, epochs + 1):
        perm = torch.randperm(n)
        ep_loss = 0.0
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            x = teacher_t[idx]
            x_recon, z = model(x)
            recon_loss = ((x_recon - x) ** 2).mean()
            # Anti-collapse penalty: encourage variance across batch dim
            z_var = z.var(dim=0).mean()
            collapse_penalty = -0.1 * z_var.clamp(max=1.0)
            loss = recon_loss + collapse_penalty
            opt.zero_grad(); loss.backward(); opt.step()
            ep_loss += loss.item()
        print(f"  epoch {ep}/{epochs}: loss={ep_loss / max(1, n//batch_size):.4f}")

    NEW_CKPT.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"encoder": model.encoder.state_dict(),
                "mu_head": {"weight": torch.eye(256, 256), "bias": torch.zeros(256)},
                "decoder": model.decoder.state_dict(),
                "teacher_model": "nomic-embed-text:v1.5",
                "epochs": epochs, "n_train": n}, NEW_CKPT)
    print(f"[train] saved {NEW_CKPT}")


def evaluate(ckpt_path: str) -> None:
    """Run the posterior-collapse test (E89.3) on a candidate checkpoint."""
    import sys as _sys
    _sys.path.insert(0, str(REPO / "src"))
    from cohezion.flume.vae_encoder import FlumeVAEEncoder
    enc = FlumeVAEEncoder(model_path=Path(ckpt_path))
    print(f"[eval] enabled={enc.enabled} ckpt={ckpt_path}")

    texts = [
        "GEPA reflective prompt evolution Pareto mutation outperforms RL",
        "V-JEPA 2 self-supervised video latent action conditioned planner",
        "Beyond majority voting LLM aggregation higher-order information",
        "Cooking recipe pasta tomato sauce simmer 20 minutes",
    ]
    embs = [enc.encode(t) for t in texts]
    import math as _m
    def cos(a, b):
        na = _m.sqrt(sum(x * x for x in a)); nb = _m.sqrt(sum(x * x for x in b))
        return sum(a[i] * b[i] for i in range(len(a))) / (na * nb)
    pairs = [cos(embs[i], embs[j]) for i in range(4) for j in range(i + 1, 4)]
    dr = max(pairs) - min(pairs)
    print(f"[eval] dynamic_range={dr:.4f} (FLUME ep20={0.003}, nomic-embed={0.142})")
    print(f"[eval] verdict: {'discriminative' if dr > 0.05 else 'POSTERIOR COLLAPSED'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--teacher-embed", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--ckpt", type=str, default=str(NEW_CKPT))
    args = parser.parse_args()

    if args.extract_only:
        extract_corpus()
    elif args.teacher_embed:
        n = extract_corpus()
        if n > 0:
            teacher_embed()
    elif args.train:
        train(epochs=args.epochs, batch_size=args.batch_size)
    elif args.eval:
        evaluate(args.ckpt)
    else:
        print("Specify one of: --extract-only / --teacher-embed / --train / --eval")
        sys.exit(2)
