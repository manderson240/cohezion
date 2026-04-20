"""Export mass simulation checkpoints to numpy arrays for training.

Bridges the gap between simulation output (Python lists in SurrealDB/JSONL)
and the FlumeTrajectoryDataset which expects .npy files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    from cohezion.mass_sim.config import UniverseResult



logger = logging.getLogger(__name__)


class CheckpointExporter:
    """Export simulation checkpoint data to numpy arrays.

    Parameters
    ----------
    output_dir : str or Path
        Directory to write .npy files to.
    """

    def __init__(self, output_dir: str | Path = "data/mass_sim/artifacts") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_universe_to_npy(
        self,
        result: UniverseResult,
        include_checkpoints: bool = True,
    ) -> list[Path]:
        """Export a universe's checkpoint sample states to .npy files.

        Parameters
        ----------
        result : UniverseResult
            Complete results from simulating one universe.
        include_checkpoints : bool
            If True, export sample_states from each checkpoint.
            If False, only export the final checkpoint.

        Returns
        -------
        list[Path]
            Paths to generated .npy files.
        """
        exported: list[Path] = []

        checkpoints = result.checkpoints
        if not include_checkpoints and checkpoints:
            checkpoints = [checkpoints[-1]]

        for ckpt in checkpoints:
            if ckpt.sample_states is None:
                continue

            arr = np.array(ckpt.sample_states, dtype=np.float32)
            if arr.ndim != 2:
                logger.warning(f"Skipping checkpoint epoch {ckpt.epoch}: unexpected shape {arr.shape}")
                continue

            filename = f"{result.universe_id}_ep{ckpt.epoch}.npy"
            path = self.output_dir / filename
            np.save(path, arr)
            exported.append(path)

        if exported:
            logger.info(f"Exported {len(exported)} checkpoint arrays for {result.universe_id} to {self.output_dir}")

        return exported

    def export_final_states(
        self,
        universe_id: str,
        states: np.ndarray,
    ) -> Path:
        """Export the full final agent state array to .npy.

        Parameters
        ----------
        universe_id : str
            Universe identifier.
        states : np.ndarray
            Shape [n_agents, z_dim], final agent states.

        Returns
        -------
        Path
            Path to the saved .npy file.
        """
        path = self.output_dir / f"{universe_id}_final.npy"
        np.save(path, states.astype(np.float32))
        logger.info(f"Exported final states {states.shape} to {path}")
        return path

    def export_from_jsonl(
        self,
        jsonl_dir: str | Path,
        z_dim: int = 256,
    ) -> list[Path]:
        """Export sample states from JSONL checkpoint fallback files.

        Parameters
        ----------
        jsonl_dir : str or Path
            Directory containing JSONL fallback files.
        z_dim : int
            Expected latent dimensionality.

        Returns
        -------
        list[Path]
            Paths to generated .npy files.
        """
        jsonl_dir = Path(jsonl_dir)
        exported: list[Path] = []

        for jsonl_file in sorted(jsonl_dir.glob("sim_checkpoint*.jsonl")):
            vectors: list[list[float]] = []
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        record = json.loads(line)
                        if record.get("sample_states"):
                            for state in record["sample_states"]:
                                if len(state) == z_dim:
                                    vectors.append(state)
            except Exception as e:
                logger.warning(f"Failed to read {jsonl_file}: {e}")
                continue

            if vectors:
                arr = np.array(vectors, dtype=np.float32)
                out_path = self.output_dir / f"{jsonl_file.stem}.npy"
                np.save(out_path, arr)
                exported.append(out_path)
                logger.info(f"Exported {len(vectors)} vectors from {jsonl_file}")

        return exported
