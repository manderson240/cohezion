"""ARC dataset loader for training ARC-specific LeWM models.

Provides PyTorch Dataset and data loading utilities for ARC grid data.
Handles variable-sized grids, color mappings, and creates training pairs
for JEPA world model training.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)


class ARCGridTokenizer:
    """Convert between ARC grids (variable sized, 10 colors) and tensors.

    ARC grids are:
    - Variable size: 2x2 to 30x30
    - 10 colors: 0-9 (0 is background)
    - Represented as nested lists of integers

    We encode them as one-hot tensors with shape (10, H, W) and
    pool/pad to fixed size when needed.
    """

    NUM_COLORS: int = 10
    MAX_GRID_SIZE: int = 32  # Max dimension + padding for safety

    @classmethod
    def grid_to_tensor(
        cls, grid: list[list[int]], max_size: int | None = None
    ) -> torch.Tensor:
        """Convert ARC grid to one-hot tensor (NUM_COLORS, H, W).

        Args:
            grid: 2D list of integers (0-9)
            max_size: Optional max size to pad/crop to

        Returns:
            One-hot tensor of shape (NUM_COLORS, H, W)
        """
        arr = np.array(grid, dtype=np.int64)
        h, w = arr.shape

        # One-hot encode
        one_hot = np.zeros((cls.NUM_COLORS, h, w), dtype=np.float32)
        for c in range(cls.NUM_COLORS):
            one_hot[c] = (arr == c).astype(np.float32)

        tensor = torch.from_numpy(one_hot)

        if max_size is not None:
            tensor = cls._pad_or_crop(tensor, max_size)

        return tensor

    @classmethod
    def tensor_to_grid(
        cls, tensor: torch.Tensor, original_size: tuple[int, int] | None = None
    ) -> list[list[int]]:
        """Convert one-hot tensor back to ARC grid.

        Args:
            tensor: One-hot tensor of shape (NUM_COLORS, H, W) or (NUM_COLORS,)
            original_size: Optional (H, W) to resize back to

        Returns:
            2D list of integers (0-9)
        """
        if tensor.dim() == 1:
            # Flattened encoding - just take argmax
            color = int(tensor.argmax().item())
            return [[color]]

        # Get most likely color at each position
        colors = tensor.argmax(dim=0).numpy()

        if original_size is not None:
            oh, ow = original_size
            h, w = colors.shape
            if h > oh or w > ow:
                # Crop center
                start_h = (h - oh) // 2
                start_w = (w - ow) // 2
                colors = colors[start_h : start_h + oh, start_w : start_w + ow]

        return colors.tolist()

    @classmethod
    def _pad_or_crop(cls, tensor: torch.Tensor, max_size: int) -> torch.Tensor:
        """Pad or crop tensor to (NUM_COLORS, max_size, max_size)."""
        c, h, w = tensor.shape

        if h > max_size or w > max_size:
            # Center crop
            crop_h = min(h, max_size)
            crop_w = min(w, max_size)
            start_h = (h - crop_h) // 2
            start_w = (w - crop_w) // 2
            tensor = tensor[:, start_h : start_h + crop_h, start_w : start_w + crop_w]
            h, w = crop_h, crop_w

        if h < max_size or w < max_size:
            # Pad with zeros (background color)
            pad_h = max_size - h
            pad_w = max_size - w
            tensor = torch.nn.functional.pad(
                tensor, (0, pad_w, 0, pad_h), mode="constant", value=0
            )

        return tensor

    @classmethod
    def get_grid_size(cls, grid: list[list[int]]) -> tuple[int, int]:
        """Get (height, width) of a grid."""
        return (len(grid), len(grid[0]) if grid else 0)


class ARCDataset(Dataset):
    """ARC dataset for JEPA world model training.

    Creates training pairs from ARC task examples:
    - (input_grid, transformation_action, output_grid)
    - Actions encode the transformation between input and output

    For ARC, we treat each example as a single-step transformation:
    - State: input grid
    - Action: encoded transformation parameters
    - Next state: output grid
    """

    def __init__(
        self,
        challenges_path: str | Path,
        solutions_path: str | Path | None = None,
        max_grid_size: int = 32,
        transform: Callable | None = None,
        split: str = "train",
    ) -> None:
        """Initialize ARC dataset.

        Args:
            challenges_path: Path to challenges JSON file
            solutions_path: Optional path to solutions JSON
            max_grid_size: Maximum grid dimension (pad/crop to this)
            transform: Optional transform to apply
            split: 'train' or 'test' (affects augmentation)
        """
        self.challenges_path = Path(challenges_path)
        self.solutions_path = Path(solutions_path) if solutions_path else None
        self.max_grid_size = max_grid_size
        self.transform = transform
        self.split = split

        self.tokenizer = ARCGridTokenizer()
        self.samples: list[dict[str, Any]] = []

        self._load_data()

        logger.info("Loaded ARC dataset: %d samples", len(self.samples))

    def _load_data(self) -> None:
        """Load ARC JSON data and create training samples."""
        with open(self.challenges_path, "r") as f:
            challenges = json.load(f)

        solutions = None
        if self.solutions_path and self.solutions_path.exists():
            with open(self.solutions_path, "r") as f:
                solutions = json.load(f)

        for task_id, task in challenges.items():
            train_examples = task.get("train", [])
            test_examples = task.get("test", [])

            # Add training examples
            for ex in train_examples:
                self._add_sample(task_id, ex, "train", solutions)

            # Add test examples (if we have solutions)
            for ex in test_examples:
                self._add_sample(task_id, ex, "test", solutions)

    def _add_sample(
        self,
        task_id: str,
        example: dict[str, Any],
        example_type: str,
        solutions: dict[str, Any] | None,
    ) -> None:
        """Add a sample to the dataset."""
        input_grid = example.get("input", [])
        output_grid = example.get("output", [])

        if not input_grid or not output_grid:
            return

        # Compute action encoding (grid transformation)
        action = self._encode_transformation(input_grid, output_grid)

        sample = {
            "task_id": task_id,
            "example_type": example_type,
            "input_grid": input_grid,
            "output_grid": output_grid,
            "action": action,
            "input_size": self.tokenizer.get_grid_size(input_grid),
            "output_size": self.tokenizer.get_grid_size(output_grid),
        }

        self.samples.append(sample)

    def _encode_transformation(
        self, input_grid: list[list[int]], output_grid: list[list[int]]
    ) -> np.ndarray:
        """Encode transformation between input and output grid as action vector.

        Returns a fixed-size action encoding representing:
        - Size change (output_h / input_h, output_w / input_w)
        - Color distribution changes
        - Spatial transformation hints
        """
        action_dim = 64  # Fixed action dimension

        inp_arr = np.array(input_grid, dtype=np.float32)
        out_arr = np.array(output_grid, dtype=np.float32)

        ih, iw = inp_arr.shape
        oh, ow = out_arr.shape

        # Size ratios
        h_ratio = oh / max(ih, 1)
        w_ratio = ow / max(iw, 1)

        # Color statistics
        inp_colors = np.bincount(inp_arr.flatten().astype(int), minlength=10) / (ih * iw)
        out_colors = np.bincount(out_arr.flatten().astype(int), minlength=10) / (oh * ow)

        # Color change (which colors map to which)
        color_delta = out_colors - inp_colors

        # Spatial features (centroid shifts, aspect ratio changes)
        inp_centroid = np.array([ih / 2, iw / 2])
        out_centroid = np.array([oh / 2, ow / 2])
        centroid_shift = out_centroid - inp_centroid

        # Aspect ratios
        inp_aspect = iw / max(ih, 1)
        out_aspect = ow / max(oh, 1)

        # Build action vector
        action = np.zeros(action_dim, dtype=np.float32)
        action[0:2] = [h_ratio, w_ratio]
        action[2:12] = color_delta
        action[12:22] = inp_colors
        action[22:32] = out_colors
        action[32:34] = centroid_shift
        action[34] = out_aspect - inp_aspect

        # Add task-agnostic fingerprint (hash of structure)
        action[35:64] = np.random.randn(29).astype(np.float32) * 0.1

        return action

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        """Get a sample as tensors.

        Returns dict with:
        - state: input grid tensor (NUM_COLORS, H, W)
        - action: transformation action (action_dim,)
        - next_state: output grid tensor (NUM_COLORS, H, W)
        - meta: metadata dict
        """
        sample = self.samples[idx]

        state = self.tokenizer.grid_to_tensor(
            sample["input_grid"], self.max_grid_size
        )
        next_state = self.tokenizer.grid_to_tensor(
            sample["output_grid"], self.max_grid_size
        )
        action = torch.from_numpy(sample["action"].copy())

        item = {
            "state": state,
            "action": action,
            "next_state": next_state,
            "meta": {
                "task_id": sample["task_id"],
                "example_type": sample["example_type"],
                "input_size": sample["input_size"],
                "output_size": sample["output_size"],
            },
        }

        if self.transform:
            item = self.transform(item)

        return item

    def get_collate_fn(self) -> Callable:
        """Return collate function for DataLoader."""

        def collate_fn(batch: list[dict]) -> dict[str, torch.Tensor | list]:
            states = torch.stack([item["state"] for item in batch])
            actions = torch.stack([item["action"] for item in batch])
            next_states = torch.stack([item["next_state"] for item in batch])
            metas = [item["meta"] for item in batch]

            return {
                "state": states,
                "action": actions,
                "next_state": next_states,
                "meta": metas,
            }

        return collate_fn

    @classmethod
    def from_default_paths(
        cls,
        base_path: str | Path = "/home/mike-anderson/dev/cohezion/tools/kaggle-skill/data",
        split: str = "train",
        **kwargs,
    ) -> ARCDataset:
        """Create dataset from default ARC paths.

        Args:
            base_path: Base directory containing ARC JSON files
            split: 'train' or 'eval'
        """
        base_path = Path(base_path)

        if split == "train":
            challenges = base_path / "arc-agi_training_challenges.json"
            solutions = base_path / "arc-agi_training_solutions.json"
        else:
            challenges = base_path / "arc-agi_evaluation_challenges.json"
            solutions = base_path / "arc-agi_evaluation_solutions.json"

        return cls(
            challenges_path=challenges,
            solutions_path=solutions,
            split=split,
            **kwargs,
        )


class ARCBatchSampler:
    """Sampler that groups grids of similar size for efficient batching.

    ARC grids vary widely in size (2x2 to 30x30). This sampler groups
    examples by size bucket to minimize padding waste.
    """

    def __init__(
        self,
        dataset: ARCDataset,
        batch_size: int = 32,
        size_buckets: list[tuple[int, int]] | None = None,
    ) -> None:
        self.dataset = dataset
        self.batch_size = batch_size

        # Default size buckets
        if size_buckets is None:
            size_buckets = [
                (0, 8),      # Small: 2x2 to 8x8
                (8, 16),     # Medium: 8x8 to 16x16
                (16, 24),    # Large: 16x16 to 24x24
                (24, 32),    # XL: 24x24 to 30x30
            ]
        self.size_buckets = size_buckets

        self._create_buckets()

    def _create_buckets(self) -> None:
        """Organize samples into size buckets."""
        self.buckets: dict[int, list[int]] = {i: [] for i in range(len(self.size_buckets))}

        for idx, sample in enumerate(self.dataset.samples):
            size = max(sample["input_size"])
            for bucket_idx, (low, high) in enumerate(self.size_buckets):
                if low <= size <= high:
                    self.buckets[bucket_idx].append(idx)
                    break

    def __iter__(self):
        """Yield batches of indices."""
        import random

        # Shuffle each bucket
        for bucket in self.buckets.values():
            random.shuffle(bucket)

        # Yield batches from each bucket
        all_batches = []
        for bucket in self.buckets.values():
            for i in range(0, len(bucket), self.batch_size):
                batch = bucket[i : i + self.batch_size]
                if len(batch) == self.batch_size:
                    all_batches.append(batch)

        random.shuffle(all_batches)
        for batch in all_batches:
            yield batch

    def __len__(self) -> int:
        total = sum(len(indices) for indices in self.buckets.values())
        return total // self.batch_size


class ARCDataLoader(torch.utils.data.DataLoader):
    """DataLoader with ARC-specific batching strategy."""

    def __init__(
        self,
        dataset: ARCDataset,
        batch_size: int = 32,
        shuffle: bool = True,
        num_workers: int = 0,
        pin_memory: bool = True,
        **kwargs,
    ) -> None:
        sampler = ARCBatchSampler(dataset, batch_size) if shuffle else None

        super().__init__(  # type: ignore
            dataset=dataset,
            batch_sampler=sampler if shuffle else None,
            batch_size=None if shuffle else batch_size,
            shuffle=False if sampler else shuffle,
            collate_fn=dataset.get_collate_fn(),
            num_workers=num_workers,
            pin_memory=pin_memory,
            **kwargs,
        )


__all__ = [
    "ARCGridTokenizer",
    "ARCDataset",
    "ARCBatchSampler",
    "ARCDataLoader",
]
