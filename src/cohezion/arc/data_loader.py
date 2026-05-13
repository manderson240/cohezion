"""ARC Data Loader — public ARC-AGI training data.

Fetches from https://github.com/fchollet/ARC-AGI (MIT-ish, public domain).
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np


ARC_DATA_DIR = Path(os.environ.get("ARC_DATA_DIR", "data/arc"))
ARC_REPO_URL = "https://raw.githubusercontent.com/fchollet/ARC-AGI/master/data/"


def _download(name: str, subset: str) -> dict[str, Any]:
    local = ARC_DATA_DIR / f"{name}_{subset}.json"
    if local.exists():
        return json.loads(local.read_text())
    url = f"{ARC_REPO_URL}{subset}/{name}.json"
    urllib.request.urlretrieve(url, local)
    return json.loads(local.read_text())


def list_tasks(subset: str = "training") -> list[str]:
    """Return ARC task IDs for given subset."""
    ARC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = ARC_DATA_DIR / f"{subset}_manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text())
    # Scrape via GH API (lightweight)
    api = f"https://api.github.com/repos/fchollet/ARC-AGI/contents/data/{subset}"
    try:
        with urllib.request.urlopen(api, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return []
    ids = [item["name"].replace(".json", "") for item in data if item["name"].endswith(".json")]
    manifest.write_text(json.dumps(ids))
    return ids


def load_task(task_id: str, subset: str = "training") -> dict[str, Any]:
    raw = _download(task_id, subset)

    def convert_grid(g: list[list[int]]) -> np.ndarray:
        return np.array(g, dtype=np.uint8)

    return {
        "train": [{"input": convert_grid(ex["input"]), "output": convert_grid(ex["output"])} for ex in raw["train"]],
        "test": [{"input": convert_grid(ex["input"]), "output": convert_grid(ex["output"])} for ex in raw["test"]],
    }


def load_all(subset: str = "training", limit: int | None = None) -> dict[str, dict[str, Any]]:
    tasks = list_tasks(subset)[:limit] if limit else list_tasks(subset)
    return {tid: load_task(tid, subset) for tid in tasks}


if __name__ == "__main__":
    training_ids = list_tasks("training")
    print(f"ARC training tasks available: {len(training_ids)}")
    if training_ids:
        t = load_task(training_ids[0])
        print(f"First task: {len(t['train'])} train, {len(t['test'])} test examples")
