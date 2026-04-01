#!/usr/bin/env python3
"""CLI for training the FLUME VAE autoencoder.

Usage:
    uv run python scripts/train_flume.py --epochs 50
    uv run python scripts/train_flume.py --load-data embeddings.npz --epochs 10
    uv run python scripts/train_flume.py --epochs 0  # skip training, eval-only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser (exported for testing)."""
    parser = argparse.ArgumentParser(description="Train FLUME VAE autoencoder")
    # Core training
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--z-dim", type=int, default=256)
    parser.add_argument("--n-samples", type=int, default=10000)
    # I/O
    parser.add_argument("--checkpoint-dir", default="data/flume/checkpoints")
    parser.add_argument("--load-data", default=None, metavar="PATH",
                        help="Load pre-computed embeddings from .npz instead of generating them")
    parser.add_argument("--save-data", default=None, metavar="PATH",
                        help="Save embeddings to .npz after generation / loading")
    parser.add_argument("--load-checkpoint", default=None, metavar="PATH",
                        help="Resume from a saved checkpoint (.pt)")
    # Behaviour flags
    parser.add_argument("--evaluate", action="store_true",
                        help="Write evaluation_results.json after training")
    parser.add_argument("--require-ollama", action="store_true",
                        help="Fail with exit 1 if Ollama is not reachable")
    # Legacy / compat
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data")
    return parser


def _load_npz(path: str):
    """Load embeddings (and optional pairs) from a .npz file."""
    import numpy as np
    d = np.load(path)
    embeddings = d["embeddings"]
    pairs = d["pairs"] if "pairs" in d else None
    return embeddings, pairs


def _build_dataset(args: argparse.Namespace):
    """Return (embeddings np.ndarray, pairs | None) according to CLI flags."""
    import numpy as np

    if args.load_data:
        log.info("Loading pre-computed embeddings from %s", args.load_data)
        return _load_npz(args.load_data)

    # Check Ollama availability
    if args.require_ollama:
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        except Exception as exc:
            log.error("Ollama not reachable and --require-ollama was set: %s", exc)
            sys.exit(1)

    if args.synthetic:
        rng = np.random.default_rng(42)
        embeddings = rng.standard_normal((args.n_samples, 768)).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings /= np.where(norms > 0, norms, 1.0)
        return embeddings, None

    # Default: try Ollama / embedding provider, fall back gracefully
    try:
        from cohezion.flume.data_pipeline import TrainingDataPipeline
        from cohezion.flume.embedding_provider import OllamaEmbeddingProvider
        provider = OllamaEmbeddingProvider()
        pipeline = TrainingDataPipeline(embedding_provider=provider)
        result = pipeline.prepare(n_synthetic=args.n_samples)
        embeddings = result["embeddings"]
        return embeddings, None
    except (ImportError, OSError, RuntimeError) as exc:
        log.warning("Embedding generation failed (%s). Use --load-data or --synthetic.", exc)
        if args.require_ollama:
            sys.exit(1)
        rng = np.random.default_rng(0)
        embeddings = rng.standard_normal((min(args.n_samples, 1000), 768)).astype(np.float32)
        return embeddings, None


def _train(model, embeddings, pairs, args: argparse.Namespace, checkpoint_dir: Path):
    """Run training loop; return final metrics dict."""
    import torch
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    x = torch.from_numpy(embeddings).float()
    dataset = TensorDataset(x)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=False)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    best_loss = float("inf")
    metrics: dict = {}

    for epoch in range(args.epochs):
        model.train()
        total_loss = total_kl = total_recon = 0.0
        n = 0
        for (batch,) in loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            mu, logvar = model.encode(batch)
            z = model.reparameterize(mu, logvar)
            recon = model.decode(z)
            recon_loss = F.mse_loss(recon, batch)
            kl = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp()).sum(dim=1).mean()
            loss = recon_loss + 0.1 * kl
            loss.backward()
            optimizer.step()
            bs = batch.size(0)
            total_loss += loss.item() * bs
            total_kl += kl.item() * bs
            total_recon += recon_loss.item() * bs
            n += bs

        epoch_loss = total_loss / n
        metrics = {"epoch": epoch + 1, "loss": epoch_loss,
                   "kl": total_kl / n, "recon": total_recon / n}
        log.info("Epoch %d/%d | loss=%.4f | kl=%.4f | recon=%.4f",
                 epoch + 1, args.epochs, epoch_loss, total_kl / n, total_recon / n)

        if epoch_loss < best_loss:
            best_loss = epoch_loss

    # Save final checkpoint
    ckpt_path = checkpoint_dir / "flume_vae_latest.pt"
    torch.save({"model_state_dict": model.state_dict(), "metrics": metrics}, ckpt_path)
    log.info("Checkpoint saved to %s", ckpt_path)
    return metrics


def _evaluate(model, embeddings, checkpoint_dir: Path):
    """Run quick evaluation and write evaluation_results.json."""
    import torch
    import torch.nn.functional as F

    device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(embeddings[:min(200, len(embeddings))]).float().to(device)
        mu, logvar = model.encode(x)
        z = model.reparameterize(mu, logvar)
        recon = model.decode(z)
        kl = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp()).sum(dim=1).mean().item()
        cos_sim = F.cosine_similarity(recon, x, dim=1).mean().item()

    n_passed = sum([
        kl > 0.01,
        cos_sim > 0.5,
    ])
    results = {
        "kl_value": round(kl, 6),
        "reconstruction_cosine_sim": round(cos_sim, 6),
        "n_passed": n_passed,
    }
    out = checkpoint_dir / "evaluation_results.json"
    out.write_text(json.dumps(results, indent=2))
    log.info("Evaluation: kl=%.4f cos_sim=%.4f n_passed=%d — written to %s",
             kl, cos_sim, n_passed, out)
    return results


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Load or generate embeddings
    try:
        embeddings, pairs = _build_dataset(args)
    except SystemExit:
        raise
    except Exception as exc:
        log.error("Failed to build dataset: %s", exc)
        return 1

    # Optionally save embeddings
    if args.save_data:
        import numpy as np
        save_path = Path(args.save_data)
        save_kwargs: dict = {"embeddings": embeddings}
        if pairs is not None:
            save_kwargs["pairs"] = pairs
        np.savez_compressed(save_path, **save_kwargs)
        log.info("Embeddings saved to %s", save_path)

    # Build model
    import torch

    from cohezion.flume.vae import FlumeVAE

    input_dim = embeddings.shape[1]
    model = FlumeVAE(input_dim=input_dim, latent_dim=args.z_dim)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    # Optionally load checkpoint
    if args.load_checkpoint:
        ckpt_path = Path(args.load_checkpoint)
        if not ckpt_path.exists():
            log.error("Checkpoint not found: %s", ckpt_path)
            return 1
        state = torch.load(ckpt_path, map_location=device)
        sd = state.get("model_state_dict", state)
        model.load_state_dict(sd)
        log.info("Loaded checkpoint from %s", ckpt_path)

    # Training
    if args.epochs > 0:
        try:
            _train(model, embeddings, pairs, args, checkpoint_dir)
        except Exception as exc:
            log.error("Training failed: %s", exc)
            return 1
    else:
        log.info("--epochs 0: skipping training")

    # Evaluation
    if args.evaluate:
        try:
            _evaluate(model, embeddings, checkpoint_dir)
        except Exception as exc:
            log.error("Evaluation failed: %s", exc)
            return 1

    log.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
