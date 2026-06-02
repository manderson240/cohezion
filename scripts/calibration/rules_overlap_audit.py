#!/usr/bin/env python3
"""Rules Overlap Audit Script (ID-1 / exp_G).

Computes textual and semantic overlap between CLAUDE.md and rules files
in ~/.claude/rules/ to locate redundant instructions.
"""

import os
from pathlib import Path

CLAUDE_MD_PATH = Path("/home/mike-anderson/dev/cohezion/CLAUDE.md")
RULES_DIR = Path("/home/mike-anderson/.claude/rules")


def clean_line(line: str) -> str:
    """Normalize whitespace and lowercase a line for comparison."""
    return " ".join(line.strip().lower().split())


def get_token_count(text: str) -> int:
    """Rough estimation of token count (chars // 4)."""
    return len(text) // 4


def audit_overlap():
    if not CLAUDE_MD_PATH.exists():
        print(f"CLAUDE.md not found at {CLAUDE_MD_PATH}")
        return

    if not RULES_DIR.exists():
        print(f"Rules folder not found at {RULES_DIR}")
        return

    claude_lines = [clean_line(l) for l in CLAUDE_MD_PATH.read_text().splitlines() if l.strip()]
    claude_set = set(claude_lines)

    print("=== .claude/rules/ vs CLAUDE.md Overlap Audit ===")
    print(f"CLAUDE.md total lines: {len(claude_lines)}")
    print(f"CLAUDE.md estimated tokens: {get_token_count(CLAUDE_MD_PATH.read_text()):,}\n")

    print("| Rule File | Total Tokens | Overlap Lines | Duplicate % | Est. Savings (Tokens) |")
    print("|---|---|---|---|---|")

    total_potential_savings = 0

    for fname in sorted(os.listdir(RULES_DIR)):
        if not fname.endswith(".md"):
            continue

        fpath = RULES_DIR / fname
        content = fpath.read_text()
        lines = [clean_line(l) for l in content.splitlines() if l.strip()]

        if not lines:
            continue

        duplicates = 0
        duplicate_content_len = 0
        for orig_line in content.splitlines():
            cleaned = clean_line(orig_line)
            if cleaned and cleaned in claude_set:
                duplicates += 1
                duplicate_content_len += len(orig_line)

        dup_pct = (duplicates / len(lines)) * 100
        tokens = get_token_count(content)
        saved_tokens = duplicate_content_len // 4
        total_potential_savings += saved_tokens

        print(
            f"| {fname} | {tokens:,} | {duplicates}/{len(lines)} | "
            f"{dup_pct:.1f}% | {saved_tokens:,} |"
        )

    print(f"\n**Total Potential Context Savings:** ~{total_potential_savings:,} tokens")


if __name__ == "__main__":
    audit_overlap()
