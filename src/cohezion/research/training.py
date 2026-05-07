# ruff: noqa: S110  # best-effort: ignored exceptions are intentional in init/cleanup paths
"""Training execution utilities for ResearchAgent.

Handles actual LLM training with time budget constraints.
Integrates with Cohezion's FLUME and training infrastructure.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch
import torch.nn as nn


if TYPE_CHECKING:
    from torch.utils.data import DataLoader


logger = logging.getLogger(__name__)


def _python_exec() -> str:
    """Resolve the venv python; fall back to sys.executable."""
    repo_root = Path(__file__).resolve().parents[3]
    venv_py = repo_root / ".venv" / "bin" / "python3"
    if venv_py.exists():
        return str(venv_py)
    return shutil.which("python3") or sys.executable


class TrainingExecutor:
    """Execute training runs with time budget.

    Clean implementation following elegant simplification.
    """

    def __init__(self, time_budget: float = 300.0):
        self.time_budget = time_budget
        self.start_time: float = 0.0

    def execute(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        optimizer: torch.optim.Optimizer,
    ) -> dict[str, Any]:
        """Execute training run with time budget.

        Args:
            model: PyTorch model
            train_loader: Training data loader
            val_loader: Validation data loader
            optimizer: Optimizer instance

        Returns:
            Dictionary with metrics: val_bpb, train_loss, val_loss
        """
        self.start_time = time.time()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)

        best_val_loss = float("inf")
        train_losses = []
        step = 0

        try:
            while time.time() - self.start_time < self.time_budget:
                # Training loop
                model.train()
                for batch in train_loader:
                    # Check time budget
                    if time.time() - self.start_time >= self.time_budget:
                        break

                    # Forward pass
                    inputs = batch.to(device)
                    optimizer.zero_grad()
                    outputs = model(inputs)
                    loss = outputs.loss

                    # Backward pass
                    loss.backward()
                    optimizer.step()

                    train_losses.append(loss.item())
                    step += 1

                    # Periodic validation
                    if step % 100 == 0:
                        val_loss = self._validate(model, val_loader, device)
                        best_val_loss = min(best_val_loss, val_loss)

                        logger.debug(
                            f"Step {step}: train_loss={loss.item():.4f}, val_loss={val_loss:.4f}"
                        )

            # Final validation
            final_val_loss = self._validate(model, val_loader, device)

            # Calculate bits per byte
            val_bpb = final_val_loss / 0.693147  # Convert to bits

            return {
                "val_bpb": val_bpb,
                "train_loss": sum(train_losses) / len(train_losses) if train_losses else 0.0,
                "val_loss": final_val_loss,
                "steps": step,
            }

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {
                "val_bpb": float("inf"),
                "train_loss": float("inf"),
                "val_loss": float("inf"),
                "error": str(e),
            }

    def _validate(
        self,
        model: nn.Module,
        val_loader: DataLoader,
        device: torch.device,
    ) -> float:
        """Run validation and return average loss."""
        model.eval()
        total_loss = 0.0
        count = 0

        with torch.no_grad():
            for batch in val_loader:
                if time.time() - self.start_time >= self.time_budget:
                    break

                inputs = batch.to(device)
                outputs = model(inputs)
                total_loss += outputs.loss.item()
                count += 1

        return total_loss / count if count > 0 else float("inf")

    def save_checkpoint(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        path: Path,
    ) -> None:
        """Save model checkpoint."""
        checkpoint = {
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "timestamp": time.time(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, path)
        logger.info(f"Checkpoint saved: {path}")

    def load_checkpoint(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        path: Path,
    ) -> bool:
        """Load model checkpoint."""
        if not path.exists():
            return False

        try:
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
            model.load_state_dict(checkpoint["model_state"])
            optimizer.load_state_dict(checkpoint["optimizer_state"])
            logger.info(f"Checkpoint loaded: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False


class SimpleTrainingRunner:
    """Simplified training runner for basic use cases."""

    def __init__(self, time_budget: float = 300.0):
        self.time_budget = time_budget

    def run(
        self,
        train_script: Path = Path("train.py"),
    ) -> dict[str, Any]:
        """Run training script with time budget.

        Simplified version using subprocess.
        """
        # Validate script path stays within project
        allowed_root = Path(__file__).resolve().parent.parent.parent
        resolved = train_script.resolve()
        if not str(resolved).startswith(str(allowed_root)):
            raise ValueError(f"Script path outside allowed root: {train_script}")

        start_time = time.time()

        try:
            result = subprocess.run(  # noqa: S603 - resolved is validated to stay within allowed_root above
                [
                    _python_exec(),
                    str(resolved),
                    "--time_budget",
                    str(self.time_budget),
                ],
                capture_output=True,
                text=True,
                timeout=self.time_budget + 60,
            )

            duration = time.time() - start_time

            if result.returncode != 0:
                return {
                    "val_bpb": float("inf"),
                    "error": result.stderr,
                    "duration": duration,
                }

            # Parse metrics from output
            metrics = self._parse_output(result.stdout)
            metrics["duration"] = duration

            return metrics

        except subprocess.TimeoutExpired:
            return {
                "val_bpb": float("inf"),
                "error": "Training timeout",
                "duration": self.time_budget + 60,
            }
        except Exception as e:
            return {
                "val_bpb": float("inf"),
                "error": str(e),
                "duration": time.time() - start_time,
            }

    def _parse_output(self, output: str) -> dict[str, Any]:
        """Parse training output for metrics."""
        metrics = {
            "val_bpb": float("inf"),
            "train_loss": 0.0,
            "val_loss": float("inf"),
        }

        # Look for JSON metrics in output
        for line in output.split("\n"):
            if "METRICS:" in line:
                try:
                    json_str = line.split("METRICS:")[1]
                    parsed = json.loads(json_str)
                    metrics.update(parsed)
                except Exception:
                    pass

        return metrics
