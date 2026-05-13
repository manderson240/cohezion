"""Training data pipeline for FLUME VAE v2.

Generates synthetic task descriptions across 5 operation types,
embeds unique texts, augments with noise to create training diversity,
and mines contrastive pairs from paraphrase groups.

Supports disk caching: embed once with Ollama, save to .npz, load instantly.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    from cohezion.flume.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)

# Task templates organized by operation type and paraphrase group.
# Each group contains semantically equivalent descriptions.
_TASK_TEMPLATES: dict[str, list[list[str]]] = {
    "generate": [
        ["generate a summary report", "create a summary report", "produce summary report"],
        ["write unit tests", "create unit tests", "generate test cases"],
        ["generate API documentation", "create API docs", "produce API reference"],
        ["build a data pipeline", "create data pipeline", "construct data pipeline"],
        ["generate embeddings for text", "create text embeddings", "produce vector embeddings"],
        ["write a CLI script", "create a command-line tool", "build a CLI application"],
        ["generate training data", "create synthetic dataset", "produce training samples"],
        ["write a configuration file", "create config template", "generate settings file"],
    ],
    "analyze": [
        ["analyze code quality", "assess code quality", "evaluate code quality"],
        [
            "analyze performance bottlenecks",
            "identify performance issues",
            "find performance problems",
        ],
        ["review pull request changes", "analyze PR diff", "evaluate pull request"],
        ["analyze test coverage", "assess test coverage", "evaluate test coverage gaps"],
        ["analyze error patterns", "investigate error trends", "examine failure patterns"],
        ["profile memory usage", "analyze memory consumption", "check memory allocation"],
        ["audit security vulnerabilities", "scan for security issues", "check for CVE exposure"],
        ["measure latency distribution", "analyze response times", "profile request latency"],
    ],
    "search": [
        ["search for relevant documentation", "find related docs", "look up documentation"],
        ["search codebase for pattern", "find code matching pattern", "grep for code pattern"],
        ["search for similar issues", "find related bugs", "look up similar problems"],
        ["search vault for decisions", "find past decisions", "query decision history"],
        ["search for API endpoints", "find available endpoints", "discover API routes"],
        ["find unused imports", "search for dead code", "locate unreferenced modules"],
        ["search logs for errors", "find error entries in logs", "grep log files for failures"],
        ["search for configuration keys", "find environment variables", "locate config settings"],
    ],
    "transform": [
        [
            "refactor the authentication module",
            "restructure auth module",
            "reorganize authentication code",
        ],
        ["transform data format to JSON", "convert data to JSON", "serialize data as JSON"],
        ["migrate database schema", "update database schema", "transform DB schema"],
        ["transform config to YAML", "convert configuration to YAML", "reformat config as YAML"],
        ["normalize the input data", "standardize input format", "clean and normalize inputs"],
        ["compress the model weights", "quantize model parameters", "reduce model size"],
        ["flatten nested dictionary", "convert nested dict to flat", "unnest hierarchical data"],
        ["encode text as tokens", "tokenize the input string", "convert text to token IDs"],
    ],
    "persist": [
        ["save checkpoint to disk", "write checkpoint file", "persist model checkpoint"],
        ["store results in database", "save results to DB", "persist results in storage"],
        ["cache embeddings locally", "store embeddings in cache", "persist embedding vectors"],
        ["log experiment results", "record experiment outcome", "persist experiment data"],
        ["save session state", "persist session context", "store session snapshot"],
        ["export metrics to CSV", "write metrics report", "dump metrics to file"],
        ["archive old logs", "compress and store logs", "rotate and persist log files"],
        ["backup the database", "create DB snapshot", "dump database state"],
    ],
}


class SyntheticTaskGenerator:
    """Generate synthetic task descriptions from templates."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def generate(self, n: int = 5000) -> list[dict[str, str]]:
        """Generate n task descriptions with operation types and group IDs.

        Each generated sample is a unique text (no duplicates within the output).
        Templates are augmented with prefix/suffix variations to ensure uniqueness.
        """
        # Flatten templates into (op_type, group_id, text) triples
        all_items: list[tuple[str, str, str]] = []
        for op_type, groups in _TASK_TEMPLATES.items():
            for g_idx, group in enumerate(groups):
                group_id = f"{op_type}_{g_idx}"
                for text in group:
                    all_items.append((op_type, group_id, text))

        # Generate augmented variants to reach n unique texts
        tasks: list[dict[str, str]] = []
        seen_texts: set[str] = set()

        # First pass: add all base templates
        for item in all_items:
            text = item[2]
            if text not in seen_texts:
                seen_texts.add(text)
                tasks.append({"text": text, "op_type": item[0], "group_id": item[1]})

        # Second pass: augment with variations until we have n samples
        _prefixes = ["please ", "now ", "quickly ", "carefully ", ""]
        _suffixes = [
            "",
            " now",
            " immediately",
            " for the project",
            " for production",
            " in the codebase",
            " as needed",
        ]

        attempt = 0
        while len(tasks) < n and attempt < n * 10:
            item = self._rng.choice(all_items)
            prefix = self._rng.choice(_prefixes)
            suffix = self._rng.choice(_suffixes)
            text = f"{prefix}{item[2]}{suffix}".strip()
            if text not in seen_texts:
                seen_texts.add(text)
                tasks.append({"text": text, "op_type": item[0], "group_id": item[1]})
            attempt += 1

        self._rng.shuffle(tasks)
        return tasks[:n]


class ContrastivePairMiner:
    """Mine positive (same-group) pairs for contrastive learning."""

    def mine_pairs(
        self,
        tasks: list[dict],
        max_pairs_per_group: int = 50,
        seed: int | None = None,
    ) -> list[tuple[int, int]]:
        """Return (anchor_idx, positive_idx) pairs from same group.

        Limits pairs per group to avoid quadratic explosion with large groups.
        """
        rng = random.Random(seed)
        groups: dict[str, list[int]] = {}
        for idx, t in enumerate(tasks):
            gid = t["group_id"]
            groups.setdefault(gid, []).append(idx)

        pairs: list[tuple[int, int]] = []
        for indices in groups.values():
            if len(indices) < 2:
                continue
            all_combos = list(itertools.combinations(indices, 2))
            if len(all_combos) <= max_pairs_per_group:
                pairs.extend(all_combos)
            else:
                pairs.extend(rng.sample(all_combos, max_pairs_per_group))

        return pairs


_DEFAULT_CACHE_DIR = Path("data/flume/embedding_cache")


def _cache_key(texts: list[str], seed: int | None) -> str:
    """Deterministic cache key from sorted text list and seed."""
    content = json.dumps(sorted(set(texts)) + [str(seed)], sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class TrainingDataPipeline:
    """Full data preparation: generate tasks → embed → augment → mine pairs."""

    def __init__(self, embedding_provider: EmbeddingProvider, seed: int | None = None) -> None:
        self._provider = embedding_provider
        self._task_gen = SyntheticTaskGenerator(seed=seed)
        self._pair_miner = ContrastivePairMiner()
        self._seed = seed

    def _embed_with_disk_cache(
        self,
        texts: list[str],
        batch_size: int,
        cache_dir: Path | None,
    ) -> np.ndarray:
        """Embed texts, using disk cache if available."""
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            key = _cache_key(texts, self._seed)
            cache_path = cache_dir / f"embeddings_{key}.npz"

            if cache_path.exists():
                data = np.load(cache_path)
                cached_emb = data["embeddings"]
                if cached_emb.shape[0] == len(texts):
                    logger.info("Loaded cached embeddings from %s (%d samples)", cache_path, len(texts))
                    return cached_emb
                logger.warning("Cache shape mismatch, re-embedding")

        # Embed in batches
        all_embeddings: list[np.ndarray] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            emb = self._provider.embed_batch(batch)
            all_embeddings.append(emb)
            if (i // batch_size) % 5 == 0:
                logger.info(
                    "Embedded batch %d/%d",
                    i // batch_size + 1,
                    (len(texts) + batch_size - 1) // batch_size,
                )

        embeddings = np.concatenate(all_embeddings, axis=0)

        # Save to disk cache
        if cache_dir is not None:
            key = _cache_key(texts, self._seed)
            cache_path = cache_dir / f"embeddings_{key}.npz"
            np.savez_compressed(cache_path, embeddings=embeddings)
            logger.info("Saved embeddings cache to %s", cache_path)

        return embeddings

    def prepare(
        self,
        n_synthetic: int = 5000,
        batch_size: int = 5,
        noise_std: float = 0.02,
        augment_factor: int = 1,
        cache_dir: Path | None = _DEFAULT_CACHE_DIR,
    ) -> dict:
        """Generate tasks, embed them, optionally augment, and mine pairs.

        Args:
            n_synthetic: Number of unique task texts to generate.
            batch_size: Batch size for embedding API calls.
            noise_std: Std of Gaussian noise for augmented copies.
            augment_factor: Extra copies per sample (with noise). 0 = no augmentation.
            cache_dir: Directory for disk-cached embeddings. None to disable.

        Returns dict with 'embeddings' (N x dim), 'texts', 'tasks', 'pairs'.
        """
        tasks = self._task_gen.generate(n=n_synthetic)
        texts = [t["text"] for t in tasks]

        embeddings = self._embed_with_disk_cache(texts, batch_size, cache_dir)

        # Augment with noisy copies (same group assignment)
        if augment_factor > 0 and noise_std > 0:
            rng = np.random.RandomState(self._seed)
            aug_embeddings = [embeddings]
            aug_tasks = list(tasks)
            aug_texts = list(texts)
            for _ in range(augment_factor):
                noise = rng.randn(*embeddings.shape).astype(np.float32) * noise_std
                noisy = embeddings + noise
                # Re-normalize
                norms = np.linalg.norm(noisy, axis=1, keepdims=True)
                norms = np.where(norms > 0, norms, 1.0)
                noisy = noisy / norms
                aug_embeddings.append(noisy)
                aug_tasks.extend(tasks)
                aug_texts.extend(texts)

            embeddings = np.concatenate(aug_embeddings, axis=0)
            tasks = aug_tasks
            texts = aug_texts

        pairs = self._pair_miner.mine_pairs(tasks, max_pairs_per_group=50, seed=self._seed)

        logger.info(
            "Prepared %d samples (%dD), %d contrastive pairs",
            len(texts),
            embeddings.shape[1],
            len(pairs),
        )

        return {
            "embeddings": embeddings,
            "texts": texts,
            "tasks": tasks,
            "pairs": pairs,
        }
