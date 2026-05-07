# ruff: noqa: N806  # math/physics: T, F, B, P, S, G, R, A — single-letter conventions
"""Trajectory sequence dataset for FLUME Phase 2 temporal encoder training.

Reads data/overnight/journeys.jsonl (or any compatible JSONL), groups records
by session_id, and returns variable-length step sequences as [T, 29] tensors.

Step vector layout (29D):
  [0:12]   12D trajectory (unit-normalized 12D position)
  [12:24]  12 scalar metrics (coherence, novelty, improvement, etc.)
  [24:29]  5D operation type one-hot
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from cohezion.flume.experience_encoder import OPERATION_TYPES


STEP_DIM = 29  # 12 traj + 12 metrics + 5 op_type

# Metric extraction order (fills dims 12-23)
_METRIC_KEYS = (
    "coherence",
    "novelty",
    "improvement",
    "phase",
    "recursion_level",
    "metric_5",
    "metric_6",
    "metric_7",
    "metric_8",
    "metric_9",
    "metric_10",
    "metric_11",
)


def _record_to_step(record: dict) -> np.ndarray:
    """Convert a single journey record to a 29D step vector."""
    step = np.zeros(STEP_DIM, dtype=np.float32)

    # [0:12] trajectory
    traj = record.get("trajectory") or []
    arr = np.asarray(traj, dtype=np.float32)
    n = min(len(arr), 12)
    step[:n] = arr[:n]

    # [12:24] metrics
    for i, key in enumerate(_METRIC_KEYS):
        val = record.get(key, 0.0)
        if val is not None:
            step[12 + i] = float(val)

    # [24:29] op_type one-hot from "skill" field
    skill = str(record.get("skill", ""))
    # Map skill name to op_type: check if any op_type token appears in skill name
    op_type = "generate"  # default
    for ot in OPERATION_TYPES:
        if ot in skill.lower():
            op_type = ot
            break
    # Also handle common skill name patterns
    if "analyz" in skill.lower() or "retrospect" in skill.lower():
        op_type = "analyze"
    elif "search" in skill.lower():
        op_type = "search"
    elif "transform" in skill.lower() or "refactor" in skill.lower():
        op_type = "transform"
    elif "persist" in skill.lower() or "save" in skill.lower():
        op_type = "persist"

    if op_type in OPERATION_TYPES:
        step[24 + OPERATION_TYPES.index(op_type)] = 1.0
    else:
        step[24] = 1.0  # default to generate

    return step


def _load_sessions(jsonl_path: Path) -> dict[str, list[dict]]:
    """Load JSONL and group records by session_id, sorted by iteration."""
    sessions: dict[str, list[dict]] = defaultdict(list)
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                sid = record.get("session_id", "default")
                sessions[sid].append(record)
            except json.JSONDecodeError:
                continue

    # Sort each session by iteration
    for sid in sessions:
        sessions[sid].sort(key=lambda r: r.get("iteration", 0))

    return dict(sessions)


class TrajectorySequenceDataset(Dataset):
    """PyTorch Dataset yielding trajectory step sequences as [T, 29] tensors.

    Parameters
    ----------
    jsonl_path : Path
        Path to journeys JSONL file.
    max_seq_len : int
        Maximum sequence length (truncates longer sessions).
    """

    def __init__(self, jsonl_path: Path | str, max_seq_len: int = 256) -> None:
        self.max_seq_len = max_seq_len
        sessions = _load_sessions(Path(jsonl_path))
        # Convert each session to an array of step vectors
        self._sequences: list[torch.Tensor] = []
        for records in sessions.values():
            steps = [_record_to_step(r) for r in records[:max_seq_len]]
            if steps:
                self._sequences.append(torch.from_numpy(np.stack(steps)))

    @classmethod
    def from_records(
        cls,
        records: list[dict],
        max_seq_len: int = 256,
    ) -> TrajectorySequenceDataset:
        """Construct dataset from an in-memory list of records."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            tmp_path = Path(f.name)
        try:
            return cls(tmp_path, max_seq_len=max_seq_len)
        finally:
            tmp_path.unlink(missing_ok=True)

    def __len__(self) -> int:
        return len(self._sequences)

    def __getitem__(self, idx: int) -> torch.Tensor:
        """Return step sequence tensor [T, STEP_DIM]."""
        return self._sequences[idx]


def collate_sequences(
    batch: list[torch.Tensor],
) -> tuple[torch.Tensor, torch.Tensor]:
    """Collate variable-length sequences into a padded batch.

    Returns
    -------
    sequences : FloatTensor [B, T_max, STEP_DIM]
        Zero-padded sequences.
    padding_mask : BoolTensor [B, T_max]
        True = padding position (to be ignored by Transformer).
    """
    max_len = max(seq.shape[0] for seq in batch)
    B = len(batch)
    step_dim = batch[0].shape[1]

    padded = torch.zeros(B, max_len, step_dim, dtype=torch.float32)
    mask = torch.ones(B, max_len, dtype=torch.bool)  # True = padding

    for i, seq in enumerate(batch):
        T = seq.shape[0]
        padded[i, :T] = seq
        mask[i, :T] = False  # valid positions

    return padded, mask
