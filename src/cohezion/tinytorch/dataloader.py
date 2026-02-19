"""TinyTorch dataloader module.

Extracted from CS249R Module 05: Data Loading.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np

from cohezion.tinytorch.tensor import Tensor


class Dataset:
    """Base dataset class. Subclass and implement __getitem__ and __len__."""

    def __getitem__(self, idx: int) -> tuple:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError


class TensorDataset(Dataset):
    """Dataset wrapping tensors. Each sample is a tuple of corresponding elements."""

    def __init__(self, *tensors: Tensor):
        assert all(t.shape[0] == tensors[0].shape[0] for t in tensors)
        self.tensors = tensors

    def __getitem__(self, idx: int) -> tuple[Tensor, ...]:
        return tuple(Tensor(t.data[idx]) for t in self.tensors)

    def __len__(self) -> int:
        return self.tensors[0].shape[0]


class DataLoader:
    """Iterable data loader with batching and shuffling."""

    def __init__(self, dataset: Dataset, batch_size: int = 32, shuffle: bool = True):
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle

    def __iter__(self):
        n = len(self.dataset)
        indices = np.arange(n)
        if self.shuffle:
            np.random.shuffle(indices)

        for start in range(0, n, self.batch_size):
            batch_indices = indices[start:start + self.batch_size]
            batch = [self.dataset[i] for i in batch_indices]

            # Collate: stack each element across the batch
            collated = []
            for elem_idx in range(len(batch[0])):
                stacked = np.stack([b[elem_idx].data for b in batch])
                collated.append(Tensor(stacked))

            yield tuple(collated)

    def __len__(self) -> int:
        return (len(self.dataset) + self.batch_size - 1) // self.batch_size


def train_test_split(
    *arrays: Tensor,
    test_size: float = 0.2,
    seed: int | None = None,
) -> list[Tensor]:
    """Split arrays into train and test sets."""
    if seed is not None:
        np.random.seed(seed)

    n = arrays[0].shape[0]
    indices = np.random.permutation(n)
    split_idx = int(n * (1 - test_size))
    train_idx, test_idx = indices[:split_idx], indices[split_idx:]

    result = []
    for arr in arrays:
        result.append(Tensor(arr.data[train_idx]))
        result.append(Tensor(arr.data[test_idx]))
    return result
