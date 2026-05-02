---
name: research-config-path-validation
description: |
  Fix for ResearchConfig raising ValueError when test paths point outside the
  data/ directory. Use when: (1) ResearchConfig(experiment_log=...) raises
  "experiment_log must be within the data/ directory", (2) tests use
  tempfile.TemporaryDirectory() or /tmp/ paths for experiment_log or
  checkpoint_dir, (3) integration tests for ResearchAgent fail at config
  construction before any execution begins. Root cause: security fix in
  config.py validates all file paths must resolve within Path("data").resolve().
author: Claude Code
version: 1.0.0
---

# ResearchConfig Path Validation

## Problem

`ResearchConfig` enforces that `experiment_log` and `checkpoint_dir` must be
within the `data/` directory (relative to CWD). This was added as a security
fix (Issue #12) to prevent path traversal.

Tests using `tempfile.TemporaryDirectory()` fail because `/tmp/...` paths are
outside `data/`:

```python
# FAILS — /tmp path rejected
with tempfile.TemporaryDirectory() as tmp:
    config = ResearchConfig(
        experiment_log=Path(tmp) / "experiments.jsonl",  # raises ValueError
        checkpoint_dir=Path(tmp) / "checkpoints",
    )
```

Error: `ValueError: experiment_log must be within the data/ directory`

## Solution

Route test paths through `data/test_runs/<unique-id>/` and clean up after:

```python
import shutil
import uuid
from pathlib import Path

@pytest.fixture
def data_temp_dir():
    """Create temp dir under data/test_runs/ (satisfies ResearchConfig path validation)."""
    test_dir = Path("data") / "test_runs" / uuid.uuid4().hex[:8]
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)

# In test:
def test_research_agent(data_temp_dir):
    config = ResearchConfig(
        experiment_time_budget=10.0,
        max_experiments=3,
        experiment_log=data_temp_dir / "experiments.jsonl",
        checkpoint_dir=data_temp_dir / "checkpoints",
    )
```

## Where the Validation Lives

`src/cohezion/research/config.py` (around lines 69-77):

```python
data_dir = Path("data").resolve()
for field_name, path in [("experiment_log", ...), ("checkpoint_dir", ...)]:
    resolved = Path(path).resolve()
    if not str(resolved).startswith(str(data_dir)):
        raise ValueError(f"{field_name} must be within the data/ directory")
```

## Also: target_metric Validation

`ResearchConfig` also validates `target_metric` against a whitelist. If tests use
`target_metric="coherence"`, ensure `"coherence"` is in `config.py`'s `valid_metrics`
list. As of the research-squad integration, it was added:

```python
valid_metrics = ["val_bpb", "val_loss", "train_loss", "accuracy", "f1", "coherence"]
```

If you add new metric names in tests, add them to this list first.

## Verification

```bash
uv run pytest tests/research/test_compound_integration.py -q --tb=short
# All integration tests should pass; no ValueError at config construction
```
