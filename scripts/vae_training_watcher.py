#!/usr/bin/env python3
"""VAE Training Watcher - Real-time convergence analysis for FLUME VAE training.

Polls a training_metrics.jsonl file for new epoch entries and periodically
calls phi3:mini via the local Ollama HTTP API to assess convergence,
detect mode collapse or plateaus, and suggest hyperparameter adjustments.

Runs as a separate process alongside train_flume.py.

Usage:
    uv run python scripts/vae_training_watcher.py
    uv run python scripts/vae_training_watcher.py --metrics-file data/flume/checkpoints/training_metrics.jsonl
    uv run python scripts/vae_training_watcher.py --analysis-interval 5 --poll-interval 10
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("vae_training_watcher")
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Globals for signal handling
# ---------------------------------------------------------------------------

_shutdown_requested = False


def _handle_signal(signum: int, _frame: object) -> None:
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, shutting down gracefully...")
    _shutdown_requested = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OLLAMA_TIMEOUT_S = 120
MAX_CONSECUTIVE_FAILURES = 5
MIN_AVAILABLE_RAM_GB = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_available_ram_gb() -> float:
    """Read available RAM from /proc/meminfo (Linux only)."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    return kb / (1024 * 1024)
    except (OSError, ValueError, IndexError):
        pass
    return 999.0


def ram_is_safe() -> bool:
    """Check if enough RAM is available for Ollama inference."""
    available = get_available_ram_gb()
    if available < MIN_AVAILABLE_RAM_GB:
        logger.warning(f"Low RAM: {available:.1f} GB available (need {MIN_AVAILABLE_RAM_GB} GB). Skipping Ollama call.")
        return False
    return True


def read_metrics(metrics_file: Path) -> list[dict]:
    """Read all epoch metrics from JSONL file.

    Each line should be a JSON object with keys:
    epoch, mse, kl, coherence_loss, total, lr, elapsed_s
    """
    if not metrics_file.exists():
        return []

    entries: list[dict] = []
    with open(metrics_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"Skipping malformed line {line_num} in {metrics_file}")
    return entries


def build_prompt(current: dict, initial: dict, total_epochs: int | None) -> str:
    """Build the convergence assessment prompt for Ollama."""
    epoch = current.get("epoch", "?")
    total = total_epochs or "?"
    mse = current.get("mse", 0.0)
    kl = current.get("kl", 0.0)
    coh = current.get("coherence_loss", 0.0)
    lr = current.get("lr", 0.0)
    init_mse = initial.get("mse", 0.0)

    return (
        f"FLUME VAE Training (epoch {epoch}/{total}):\n"
        f"MSE: {mse:.4f} (initial: {init_mse:.4f}), "
        f"KL: {kl:.4f}, Coherence: {coh:.4f}, LR: {lr:.6f}\n"
        f"Assess: Is training converging? Any signs of mode collapse or plateau?\n"
        f"Suggest: Should learning rate or KL weight be adjusted?"
    )


def call_ollama_sync(
    client: httpx.Client,
    prompt: str,
    ollama_host: str,
) -> str | None:
    """Call Ollama /api/generate synchronously. Returns response text or None."""
    if not ram_is_safe():
        return None

    try:
        resp = client.post(
            f"{ollama_host}/api/generate",
            json={
                "model": "phi3:mini",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 256,
                },
            },
            timeout=OLLAMA_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
    except httpx.TimeoutException:
        logger.warning(f"Ollama timed out after {OLLAMA_TIMEOUT_S}s")
        return None
    except (httpx.HTTPStatusError, httpx.ConnectError) as e:
        logger.warning(f"Ollama call failed: {e}")
        return None


def write_analysis(output_file: Path, epoch: int, analysis_text: str) -> None:
    """Append an analysis entry to the output JSONL file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "epoch": epoch,
        "analysis_text": analysis_text,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    with open(output_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def check_ollama_health(client: httpx.Client, ollama_host: str) -> bool:
    """Check if Ollama is running and responsive."""
    try:
        resp = client.get(f"{ollama_host}/api/tags", timeout=5.0)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_watcher(args: argparse.Namespace) -> int:
    """Main polling loop."""
    metrics_file = Path(args.metrics_file)
    output_file = Path(args.output_file)
    poll_interval: int = args.poll_interval
    analysis_interval: int = args.analysis_interval
    ollama_host: str = args.ollama_host

    logger.info("VAE Training Watcher starting")
    logger.info(f"  Metrics file:      {metrics_file}")
    logger.info(f"  Output file:       {output_file}")
    logger.info(f"  Poll interval:     {poll_interval}s")
    logger.info(f"  Analysis interval: every {analysis_interval} epochs")
    logger.info(f"  Ollama host:       {ollama_host}")

    client = httpx.Client()
    last_analyzed_epoch = 0
    initial_metrics: dict | None = None
    total_epochs: int | None = None
    consecutive_failures = 0
    waiting_for_file = True

    # Check Ollama health at start
    if check_ollama_health(client, ollama_host):
        logger.info("Ollama health check: OK")
    else:
        logger.warning("Ollama not reachable at startup. Will retry when analysis is needed.")

    try:
        while not _shutdown_requested:
            entries = read_metrics(metrics_file)

            if not entries:
                if waiting_for_file:
                    logger.info(f"Waiting for metrics file: {metrics_file}")
                    waiting_for_file = False
                time.sleep(poll_interval)
                continue

            if waiting_for_file:
                waiting_for_file = False

            # Cache initial metrics for comparison
            if initial_metrics is None:
                initial_metrics = entries[0]
                logger.info(
                    f"Initial metrics captured (epoch {initial_metrics.get('epoch', 1)}): "
                    f"MSE={initial_metrics.get('mse', 0):.4f}"
                )

            latest = entries[-1]
            latest_epoch = int(latest.get("epoch", len(entries)))

            # Infer total epochs from config if present, else from max epoch seen
            if total_epochs is None:
                total_epochs = latest.get("total_epochs")

            # Check if we need to analyze
            if latest_epoch > last_analyzed_epoch and latest_epoch % analysis_interval == 0:
                logger.info(
                    f"Epoch {latest_epoch}: MSE={latest.get('mse', 0):.4f} "
                    f"KL={latest.get('kl', 0):.4f} "
                    f"Coh={latest.get('coherence_loss', 0):.4f} "
                    f"LR={latest.get('lr', 0):.6f}"
                )
                logger.info(f"Requesting Ollama analysis for epoch {latest_epoch}...")

                prompt = build_prompt(latest, initial_metrics, total_epochs)
                analysis = call_ollama_sync(client, prompt, ollama_host)

                if analysis:
                    consecutive_failures = 0
                    write_analysis(output_file, latest_epoch, analysis)
                    logger.info(f"Analysis written for epoch {latest_epoch} ({len(analysis)} chars)")
                    # Print a preview
                    preview = analysis[:200].replace("\n", " ")
                    logger.info(f"  Preview: {preview}...")
                    last_analyzed_epoch = latest_epoch
                else:
                    consecutive_failures += 1
                    logger.warning(
                        f"Analysis failed for epoch {latest_epoch} ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})"
                    )
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        logger.error(f"Too many consecutive failures ({MAX_CONSECUTIVE_FAILURES}). Exiting.")
                        return 1
                    # Still mark as analyzed to avoid retrying the same epoch
                    last_analyzed_epoch = latest_epoch

            # Detect training completion: if latest epoch equals total_epochs
            if total_epochs and latest_epoch >= total_epochs:
                # Do one final analysis if we haven't already
                if last_analyzed_epoch < latest_epoch:
                    logger.info(f"Training complete at epoch {latest_epoch}. Final analysis...")
                    prompt = build_prompt(latest, initial_metrics, total_epochs)
                    analysis = call_ollama_sync(client, prompt, ollama_host)
                    if analysis:
                        write_analysis(output_file, latest_epoch, analysis)
                        logger.info(f"Final analysis written ({len(analysis)} chars)")

                logger.info("Training complete. Watcher exiting.")
                return 0

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        client.close()
        logger.info("Watcher shut down.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch FLUME VAE training and analyze convergence via Ollama")
    parser.add_argument(
        "--metrics-file",
        default="data/flume/checkpoints/training_metrics.jsonl",
        help="Path to training metrics JSONL file (default: data/flume/checkpoints/training_metrics.jsonl)",
    )
    parser.add_argument(
        "--output-file",
        default="data/flume/training_analysis.jsonl",
        help="Path to output analysis JSONL file (default: data/flume/training_analysis.jsonl)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=15,
        help="Seconds between polls for new metrics (default: 15)",
    )
    parser.add_argument(
        "--analysis-interval",
        type=int,
        default=10,
        help="Analyze every N epochs (default: 10)",
    )
    parser.add_argument(
        "--ollama-host",
        default="http://localhost:11434",
        help="Ollama API base URL (default: http://localhost:11434)",
    )
    args = parser.parse_args()
    return run_watcher(args)


if __name__ == "__main__":
    sys.exit(main())
