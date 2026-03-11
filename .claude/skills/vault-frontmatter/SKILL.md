---
name: vault-frontmatter
description: |
  Inject or update YAML frontmatter fields in vault notes without corrupting formatting.
  Use when: (1) adding new fields (aspect, neural, country) to many notes at once,
  (2) existing notes have inconsistent frontmatter, (3) YAML round-trip via PyYAML
  scrambles key order, removes comments, or changes quoting style.
  Key insight: targeted string insertion before the closing '---' preserves ALL original
  formatting — never parse+dump the full YAML block.
author: Claude Code
version: 1.0.0
---

# Vault Frontmatter Injection

## Problem

Adding new fields (e.g., `aspect:`, `neural:`) to 1,000+ existing notes. PyYAML
`safe_load` + `safe_dump` round-trips destroy key order, change quoting, strip
multi-line strings, and break Obsidian's rendering.

## Core Pattern: Targeted Insertion (Not Round-Trip)

```python
import re

def find_frontmatter_bounds(content: str) -> tuple[int, int] | None:
    """Returns (start_line_idx, end_line_idx) of the frontmatter block."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return (0, i)
    return None

def has_field(content: str, field: str) -> bool:
    bounds = find_frontmatter_bounds(content)
    if not bounds:
        return False
    start, end = bounds
    lines = content.split("\n")
    fm_lines = lines[start+1:end]
    return any(line.startswith(f"{field}:") for line in fm_lines)

def inject_before_closing_dashes(content: str, new_fields: str) -> str:
    """Insert new_fields immediately before the closing '---' of frontmatter."""
    bounds = find_frontmatter_bounds(content)
    if not bounds:
        return content
    _, end = bounds
    lines = content.split("\n")
    # Insert before the closing ---
    lines.insert(end, new_fields.rstrip("\n"))
    return "\n".join(lines)
```

## Usage Pattern

```python
def add_aspect(content: str, aspect: str) -> str:
    if has_field(content, "aspect"):
        return content  # idempotent — skip if already present
    return inject_before_closing_dashes(content, f"aspect: {aspect}")

def add_neural_block(content: str, activation: float, stage: str, cluster: str) -> str:
    if has_field(content, "neural"):
        return content
    block = f"neural:\n  activation: {activation:.3f}\n  stage: {stage}\n  cluster: {cluster}"
    return inject_before_closing_dashes(content, block)
```

## Directory → Aspect Mapping (Triune Vault)

```python
DIR_TO_ASPECT = {
    "cortex": "knower", "sensory": "knower", "memory": "knower", "genome": "knower",
    "prefrontal": "thinker", "laboratory": "thinker", "cerebellum": "thinker", "benchmarks": "thinker",
    "motor": "doer", "hippocampus": "doer", "thalamus": "doer", "missions": "doer",
    "retrospectives": "doer", "Agents": "doer",
    "dreaming": "connective", "songlines": "connective", "subconscious": "connective",
    "metabolism": "connective", "visual-cortex": "connective",
}

def aspect_for_path(rel_path: str) -> str | None:
    top_dir = rel_path.split("/")[0]
    return DIR_TO_ASPECT.get(top_dir)
```

## Multi-Pass Strategy for Large Vaults

Run the script twice when adding multiple independent fields:
1. Pass 1: inject `aspect:` only — fast, no SurrealDB needed
2. Pass 2: inject `neural:` block — queries SurrealDB per note for live values

This makes each pass idempotent and safe to re-run.

## Always Use --dry-run First

```python
# Add --dry-run flag
parser.add_argument("--dry-run", action="store_true")

# In process loop:
if not dry_run:
    path.write_text(new_content, encoding="utf-8")
else:
    print(f"[DRY-RUN] Would update {path}")
```

## Verification

```bash
# Check aspect coverage
rg '^aspect:' --type md -c /path/to/vault | wc -l

# Check neural coverage
rg '^neural:' --type md -c /path/to/vault | wc -l

# Find notes missing aspect
rg -L '^aspect:' --type md /path/to/vault/cortex/ | head -10
```

## Warnings

- Skip `_index.md`, `_template.md`, `README.md`, and non-content directories
- Skip notes with no frontmatter (no opening `---`)
- The closing `---` must be on its own line for detection to work
