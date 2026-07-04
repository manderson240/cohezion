#!/usr/bin/env python3
"""Semantic Rules Overlap Audit Script (ID-1 / exp_G).

Computes semantic similarity embeddings using Ollama (nomic-embed-text:v1.5)
between CLAUDE.md, coding-standards.md, and MEMORY.md to locate redundant rules
and compile a context optimization report.
"""

import sys
from pathlib import Path

import numpy as np
import requests


# Constants
CLAUDE_MD_PATH = Path("/home/mike-anderson/dev/cohezion/CLAUDE.md")
CODING_STANDARDS_PATH = Path("/home/mike-anderson/.claude/rules/coding-standards.md")
MEMORY_MD_PATH = Path("/home/mike-anderson/dev/cohezion/memory/MEMORY.md")
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text:v1.5"
REPORT_OUTPUT_PATH = Path(
    "/home/mike-anderson/.gemini/antigravity-cli/brain/0c45bc87-f2fb-4e84-a7ff-92f70b6fd134/rules_overlap_report.md"
)


class SemanticAuditor:
    """Audits rules files for semantic overlap using embeddings."""

    def __init__(
        self,
        base_url: str = OLLAMA_URL,
        model: str = EMBED_MODEL,
    ) -> None:
        """Initialize semantic auditor.

        Parameters
        ----------
        base_url : str
            Base URL for Ollama API
        model : str
            Model name for text embeddings
        """
        self.base_url = base_url.rstrip("/")
        self.model = model

    def get_embedding(self, text: str) -> np.ndarray:
        """Embed text to normalized vector.

        Parameters
        ----------
        text : str
            Text content to embed

        Returns
        -------
        np.ndarray
            1D float32 normalized embedding vector
        """
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": text},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            vec = np.array(data["embeddings"][0], dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            return vec
        except Exception as e:
            raise ConnectionError(f"Embedding query failed: {e}") from e

    def get_embeddings_batch(self, texts: list[str]) -> np.ndarray:
        """Embed batch of texts.

        Parameters
        ----------
        texts : list[str]
            List of text contents to embed

        Returns
        -------
        np.ndarray
            2D float32 array of normalized embedding vectors
        """
        if not texts:
            return np.empty((0, 768), dtype=np.float32)
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            vecs = np.array(data["embeddings"], dtype=np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms > 0, norms, 1.0)
            return vecs / norms
        except Exception:
            # Fall back to sequential embeddings
            return np.stack([self.get_embedding(t) for t in texts])

    def parse_blocks(self, file_path: Path) -> list[str]:
        """Split markdown file into paragraph/list/block elements.

        Parameters
        ----------
        file_path : Path
            Path to markdown file

        Returns
        -------
        list[str]
            Parsed non-trivial blocks
        """
        if not file_path.exists():
            return []

        content = file_path.read_text()
        raw_blocks = content.split("\n\n")
        cleaned_blocks: list[str] = []

        for block in raw_blocks:
            lines = [line.strip() for line in block.splitlines()]
            cleaned = "\n".join(l for l in lines if l)
            # Filter out empty or extremely short lines/headers
            if len(cleaned) > 25 and not cleaned.startswith("# ") and not cleaned.startswith("## "):
                cleaned_blocks.append(cleaned)

        return cleaned_blocks


def run_audit() -> None:
    """Run semantic overlap audit and output results to a markdown report."""
    print("Initializing Semantic Rules Overlap Auditor...")
    auditor = SemanticAuditor()

    # Parse rules files
    print("Parsing files...")
    claude_blocks = auditor.parse_blocks(CLAUDE_MD_PATH)
    coding_blocks = auditor.parse_blocks(CODING_STANDARDS_PATH)
    memory_blocks = auditor.parse_blocks(MEMORY_MD_PATH)

    print(
        f"Parsed blocks: CLAUDE.md ({len(claude_blocks)}), "
        f"coding-standards.md ({len(coding_blocks)}), "
        f"MEMORY.md ({len(memory_blocks)})"
    )

    # Embed CLAUDE.md blocks
    print("Embedding CLAUDE.md blocks...")
    claude_embeddings = auditor.get_embeddings_batch(claude_blocks)

    report_content = []
    report_content.append("# Semantic Rules Overlap Audit Report")
    report_content.append(
        "\nThis report analyzes semantic overlap and redundancy between "
        "`CLAUDE.md`, `coding-standards.md` (representing `python-rules.md`), "
        "and `MEMORY.md`. By identifying redundant rules, we can safely prune "
        "files to conserve prompt cache tokens.\n"
    )

    report_content.append("## Executive Summary")
    report_content.append(f"- **CLAUDE.md** parsed blocks: {len(claude_blocks)}")
    report_content.append(f"- **coding-standards.md** parsed blocks: {len(coding_blocks)}")
    report_content.append(f"- **MEMORY.md** parsed blocks: {len(memory_blocks)}")

    total_redundant = 0
    total_tokens_saved = 0

    for name, blocks_list, _path in [
        ("coding-standards.md", coding_blocks, CODING_STANDARDS_PATH),
        ("MEMORY.md", memory_blocks, MEMORY_MD_PATH),
    ]:
        report_content.append(f"\n## Audit: {name}")
        if not blocks_list:
            report_content.append("No content blocks found for auditing.")
            continue

        embeddings = auditor.get_embeddings_batch(blocks_list)
        similarities = np.dot(embeddings, claude_embeddings.T)

        high_overlap: list[tuple[str, str, float]] = []

        for i, block in enumerate(blocks_list):
            max_idx = int(np.argmax(similarities[i]))
            max_sim = float(similarities[i, max_idx])

            if max_sim >= 0.70:
                high_overlap.append((block, claude_blocks[max_idx], max_sim))

        total_redundant += len(high_overlap)
        report_content.append(
            f"Found {len(high_overlap)} blocks with semantic similarity "
            f">= 70% to rules in `CLAUDE.md`.\n"
        )

        report_content.append(
            "| Source Block in " + name + " | Matching CLAUDE.md Block | Similarity |"
        )
        report_content.append("|---|---|---|")
        for src, match, sim in high_overlap:
            src_display = (
                src.replace("\n", " ").strip()[:60] + "..."
                if len(src) > 60
                else src.replace("\n", " ")
            )
            match_display = (
                match.replace("\n", " ").strip()[:60] + "..."
                if len(match) > 60
                else match.replace("\n", " ")
            )
            report_content.append(f"| {src_display} | {match_display} | {sim:.1%} |")

        report_content.append("\n### Redundancy Details")
        for idx, (src, match, sim) in enumerate(high_overlap):
            report_content.append(f"\n#### Match {idx + 1} (Similarity: {sim:.1%})")
            report_content.append(f"**From `{name}`:**")
            report_content.append(f"```markdown\n{src}\n```")
            report_content.append("**From `CLAUDE.md`:**")
            report_content.append(f"```markdown\n{match}\n```")

            # Estimate token savings (chars // 4)
            total_tokens_saved += len(src) // 4

    report_content.append("\n## Context Cache Optimization Rationale")
    report_content.append(
        f"Optimizing these redundancies yields a projected savings of "
        f"**~{total_tokens_saved} tokens** per agent invocation. We "
        f"recommend removing or consolidating these sections in the rules files."
    )

    # Write report
    REPORT_OUTPUT_PATH.write_text("\n".join(report_content))
    print(f"Report written to {REPORT_OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        run_audit()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
