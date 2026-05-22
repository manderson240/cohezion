"""HIHO-LM Training Script — AMD Strix Halo (iGPU ROCm + CPU AVX-512).

Usage:
    uv run python src/cohezion/model/train.py --size mini --steps 500 --lr 3e-4
    uv run python src/cohezion/model/train.py --size small --steps 2000 --device cpu

Hardware targets:
  - iGPU (Radeon 8060S, ROCm): HIHO-Mini / HIHO-Small training
  - CPU (Ryzen AI MAX+ 395, AVX-512): HIHO-Base (slow but OOM-safe)
  - NPU: inference only (GGUF export via llama.cpp ROCm after training)

OOM safety:
  - Mini  (~10M): ~200MB GPU RAM — safe on 8060S
  - Small (~45M): ~800MB GPU RAM — safe
  - Base  (~110M): ~2GB GPU RAM — tight; prefer CPU or gradient checkpointing
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path


logger = logging.getLogger(__name__)


def _get_device(requested: str):
    import torch

    if requested == "auto":
        if torch.cuda.is_available():  # ROCm also exposes cuda device
            return torch.device("cuda")
        return torch.device("cpu")
    return torch.device(requested)


def train(
    size: str = "mini",
    steps: int = 500,
    lr: float = 3e-4,
    batch_size: int = 4,
    seq_len: int = 128,
    device_str: str = "auto",
    save_dir: str | None = None,
    log_every: int = 50,
) -> dict:
    """Train CohezionLM and return final metrics.

    Returns dict with keys: steps, final_loss, elapsed_s, device.
    """
    try:
        import torch
        import torch.optim as optim
    except ImportError:
        logger.error("PyTorch not available. Install: uv pip install torch")
        return {"error": "torch not installed"}

    from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig
    from cohezion.model.training_data import build_balanced_training_dataset

    device = _get_device(device_str)
    logger.info("Training on device: %s", device)

    config = getattr(CohezionLMConfig, size)()
    model = CohezionLM(config).to(device)

    param_count = sum(p.numel() for p in model.parameters())
    logger.info(
        "Model: %s | params: %dM | device: %s", config.model_name, param_count // 1_000_000, device
    )

    # Load balanced training data (includes q=0.5 HIHO-band synthetic examples for max gradient weight)
    dataset = build_balanced_training_dataset()
    logger.info(
        "Training dataset: %d examples, mean quality=%.3f, mean_hiho_weight=%.4f",
        len(dataset),
        dataset.mean_quality,
        sum(e.hiho_weight for e in dataset.examples) / max(1, len(dataset.examples)),
    )

    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=steps, eta_min=lr * 0.1)

    def _tokenize(text: str) -> "torch.Tensor":
        """Byte-level tokenizer: each UTF-8 byte → token id in [0, 255]."""
        enc = text.encode("utf-8")[: seq_len + 1]
        ids = list(enc) + [0] * max(0, seq_len + 1 - len(enc))
        return torch.tensor(ids[: seq_len + 1], dtype=torch.long, device=device)

    # Cycle training examples for multi-epoch coverage
    pool = dataset.examples * (max(1, (steps * batch_size) // max(1, len(dataset.examples)) + 2))

    model.train()
    t0 = time.perf_counter()
    losses: list[float] = []
    initial_loss: float = 0.0

    for step in range(steps):
        start = (step * batch_size) % max(1, len(pool) - batch_size + 1)
        batch_examples = pool[start : start + batch_size]

        if batch_examples:
            ids_list = [_tokenize(f"{ex.instruction} {ex.response}") for ex in batch_examples]
            weights = torch.tensor(
                [ex.hiho_weight for ex in batch_examples], dtype=torch.float32, device=device
            )
            ids_batch = torch.stack(ids_list)  # (B, seq_len+1)
        else:
            ids_batch = torch.randint(
                0, config.vocab_size, (batch_size, seq_len + 1), device=device
            )
            weights = torch.ones(batch_size, dtype=torch.float32, device=device)

        input_ids = ids_batch[:, :-1]
        target_ids = ids_batch[:, 1:]

        # HIHO-weighted loss: gradient signal proportional to 4q(1-q)
        loss = model.loss(input_ids, target_ids)
        weighted_loss = (loss * weights.mean()).clamp(min=1e-8)

        optimizer.zero_grad()
        weighted_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        loss_val = loss.item()
        losses.append(loss_val)
        if step == 0:
            initial_loss = loss_val

        if (step + 1) % log_every == 0:
            avg_loss = sum(losses[-log_every:]) / len(losses[-log_every:])
            elapsed = time.perf_counter() - t0
            logger.info(
                "step %d/%d | loss=%.4f | lr=%.2e | elapsed=%.1fs",
                step + 1,
                steps,
                avg_loss,
                scheduler.get_last_lr()[0],
                elapsed,
            )

    elapsed_s = time.perf_counter() - t0
    final_loss = sum(losses[-min(50, len(losses)) :]) / min(50, len(losses))
    logger.info(
        "Training complete: steps=%d initial_loss=%.4f final_loss=%.4f elapsed=%.1fs",
        steps,
        initial_loss,
        final_loss,
        elapsed_s,
    )

    if save_dir:
        save_path = Path(save_dir) / f"{config.model_name}-step{steps}.pt"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "config": config,
                "model_state_dict": model.state_dict(),
                "final_loss": final_loss,
                "steps": steps,
            },
            save_path,
        )
        logger.info("Model saved: %s", save_path)

    return {
        "steps": steps,
        "steps_run": steps,
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "loss_converging": final_loss < initial_loss,
        "elapsed_s": elapsed_s,
        "device": str(device),
        "model_name": config.model_name,
        "param_count_m": param_count // 1_000_000,
        "examples_seen": min(steps * batch_size, len(pool)),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Train Cohezion HIHO-LM")
    parser.add_argument("--size", choices=["mini", "small", "base", "byte_level"], default="mini")
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--device", default="auto", help="cpu / cuda / auto")
    parser.add_argument("--save-dir", default=None, help="Directory to save checkpoint")
    parser.add_argument("--log-every", type=int, default=50)
    args = parser.parse_args()

    result = train(
        size=args.size,
        steps=args.steps,
        lr=args.lr,
        batch_size=args.batch_size,
        seq_len=args.seq_len,
        device_str=args.device,
        save_dir=args.save_dir,
        log_every=args.log_every,
    )
    print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
