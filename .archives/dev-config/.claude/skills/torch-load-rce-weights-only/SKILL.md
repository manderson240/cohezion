---
name: torch-load-rce-weights-only
description: |
  Fix for torch.load() RCE (remote code execution) via Python object deserialization.
  Use when: (1) reviewing ML codebases for security, (2) loading model checkpoints from
  untrusted or user-supplied sources, (3) security review flags torch.load without
  weights_only=True, (4) CI/CodeQL reports unsafe deserialization in .pt/.pth files.
  Key insight: torch.load defaults to weights_only=False which executes arbitrary Python
  via the default serialization backend — passing weights_only=True restricts to safe
  tensor-only loading and prevents arbitrary code execution.
author: Claude Code
version: 1.0.0
---

# torch.load RCE via Python Object Deserialization

## Problem

`torch.load()` uses Python's native object serialization format by default
(`weights_only=False`). Loading a maliciously crafted `.pt` checkpoint file
executes arbitrary Python code — including shell commands, file writes, or
network calls — on the machine loading the checkpoint.

This is a **silent RCE vector**: no error, no warning, the checkpoint loads
"successfully" while running attacker-controlled code.

## Context / Trigger Conditions

- Any `torch.load(path)` call without `weights_only=True`
- Loading checkpoints from: user uploads, downloaded models, CI artifacts, shared paths
- CodeQL rule: `py/unsafe-deserialization`
- Security review finding: "unsafe torch.load" or "unsafe deserialization"

## Solution

```python
# VULNERABLE — executes arbitrary Python via default serialization
model_state = torch.load(path)
model_state = torch.load(path, map_location="cpu")

# SAFE — restricts to tensor-only loading (no arbitrary code execution)
model_state = torch.load(path, map_location="cpu", weights_only=True)
```

**If `weights_only=True` breaks loading** (legacy checkpoints with custom classes):
```python
# Option 1: Migrate checkpoint to safe format (save tensors-only copy)
torch.save(model.state_dict(), "safe_checkpoint.pt")  # state_dict is always safe

# Option 2: Allowlist known-safe classes (PyTorch >= 2.0)
torch.serialization.add_safe_globals([MyKnownClass])
model_state = torch.load(path, weights_only=True)
```

## Verification

Audit all torch.load calls in the codebase:

```python
import ast, pathlib

for f in pathlib.Path("src").rglob("*.py"):
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = getattr(node.func, 'attr', '') or getattr(node.func, 'id', '')
            if func == 'load':
                kwargs = {kw.arg for kw in node.keywords}
                if 'weights_only' not in kwargs:
                    print(f"UNSAFE: {f}:{node.lineno}")
```

## Example (from Cohezion)

In `src/cohezion/research/training.py`:
```python
# Before (vulnerable):
checkpoint = torch.load(path, map_location="cpu")

# After (safe):
checkpoint = torch.load(path, map_location="cpu", weights_only=True)
```

## References

- PyTorch docs: https://pytorch.org/docs/stable/generated/torch.load.html
- `weights_only=True` introduced in PyTorch 1.13; default changes planned for PyTorch 2.x
- Related CVE patterns: arbitrary object deserialization via model checkpoint loading
