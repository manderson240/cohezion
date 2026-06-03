---
name: cohezion-autoresearch-transcript-filter
description: |
  Filter real user prompts out of Claude Code JSONL transcript files for routing analysis.
  Use when: (1) measuring NPU/GPU routing distribution from session history,
  (2) autoresearch prompt extraction returning hook messages as "user prompts",
  (3) transcript analysis showing inflated prompt counts (148 prompts found but 144 are hooks).
  Verified: exp_FFFF3 (autoresearch Round 11, 2026-05-27) — definitive routing measurement.
author: Claude Code (autoresearch Round 11)
version: 1.0.0
---

# Autoresearch Transcript Filter

## Problem

Claude Code session transcripts (JSONL at `~/.claude/projects/*/`) contain many non-user messages:
- Pre/post hook feedback (e.g., `"Stop hook feedback: ..."`, `"Pre hook: ..."`)
- System context injections (markdown headings, YAML blocks)
- Multi-paragraph tool outputs captured as "user" role messages
- Context continuation summaries (`"This session is being continued..."`)

When doing routing analysis on prompts, these pollute the sample. In one session:
- Raw extraction: 148 "user" messages found
- After filtering: 4 real user prompts (NPU=12%, GPU=88%)
- Without filtering: routing appears much more balanced than it actually is

## Root Cause

JSONL transcript messages have `"role": "human"` for both actual user input AND system hooks
that respond to tool use. The hook messages are long and multi-line, making them easy to
mistakenly classify as real prompts without content filtering.

## Solution: `_is_real_user_prompt()`

```python
_SYSTEM_PREFIXES = (
    "stop hook feedback",
    "pre hook",
    "post hook",
    "<system",
    "[system",
    "hook feedback",
    "autoresearch-stop",
    "this session is being continued",
    "summary:",
    "---",
    "# ",        # markdown heading at line start
)
_MAX_NEWLINES_FOR_USER_PROMPT = 3

def _is_real_user_prompt(text: str) -> bool:
    """Return True if text looks like a real user message (not a hook/system message)."""
    if len(text) < 50:
        return False
    lower = text.lower()
    for prefix in _SYSTEM_PREFIXES:
        if lower.startswith(prefix):
            return False
    first_200 = text[:200]
    if first_200.count("\n") > _MAX_NEWLINES_FOR_USER_PROMPT:
        return False
    if text.startswith("#") and "\n" in text[:80]:
        return False
    if text.startswith("```"):
        return False
    return True
```

## Full Extraction Pattern

```python
import json
from pathlib import Path

def _extract_real_prompts(transcript_paths: list[Path]) -> list[str]:
    """Extract real user prompts from JSONL transcripts."""
    prompts = []
    for path in transcript_paths:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("role") not in ("human", "user"):
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle list-of-blocks format
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if _is_real_user_prompt(text):
                            prompts.append(text)
            elif isinstance(content, str) and _is_real_user_prompt(content):
                prompts.append(content)
    return prompts
```

## Transcript Location

```python
import os, glob

project_hash = os.getcwd().replace("/", "-")
transcript_dir = Path(f"~/.claude/projects/{project_hash}/").expanduser()
jsonl_files = list(transcript_dir.glob("*.jsonl"))
# Sort by mtime, take most recent N:
jsonl_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
recent = jsonl_files[:5]
```

## Verified Measurement (exp_FFFF3)

With hook-filtered extraction on 300 real prompts:
- NPU tier (short_categorical, ≤20 tokens output): **12%**
- iGPU tier (long_generation, code, analysis): **88%**
- CPU tier: **0%** (offline during measurement period)

The 88% GPU dominance is explained by long_generation task type being the most common
real user interaction (code generation, analysis, multi-step reasoning).

## References

- autoresearch.jsonl: exp_AAAA3 (Round 9, counting bug), exp_CCCC3 (Round 10, sampling fix),
  exp_FFFF3 (Round 11, definitive with hook filter)
- hiho_round11.py: `_is_real_user_prompt()` reference implementation
