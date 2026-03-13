"""Shared helper functions for vault sync."""

import hashlib
import re

from .config import SKIP_DIRS

_NEURAL_BLOCK_RE = re.compile(
    r"^neural:\s*\n(?:[ \t]+\S.*\n)*",
    re.MULTILINE,
)


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter as dict. Lightweight — no yaml dependency."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    result = {}
    for line in text[3:end].split("\n"):
        if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.startswith("[") and val.endswith("]"):
                val = [x.strip().strip('"').strip("'")
                       for x in val[1:-1].split(",") if x.strip()]
            result[key] = val
    return result


def compute_activation(word_count: int, synapse_count: int,
                       days_since_modified: int) -> float:
    content_score = min(word_count / 2000.0, 1.0) * 0.4
    link_score = min(synapse_count / 20.0, 1.0) * 0.3
    recency = max(0.0, 1.0 - (days_since_modified / 60.0)) * 0.3
    return round(min(content_score + link_score + recency, 1.0), 3)


def compute_stage(synapse_count: int, word_count: int, activation: float,
                  days_since_modified: int) -> str:
    if synapse_count < 3 and word_count < 500:
        return "embryo"
    if activation < 0.2 and days_since_modified > 30:
        return "resting"
    if synapse_count >= 10 and word_count >= 500:
        return "mature"
    return "growing"


def sanitize_id(path: str) -> str:
    return (
        path.replace("/", "_").replace(".", "_").replace(" ", "_")
        .replace("-", "_").replace("(", "").replace(")", "")
        .replace("'", "").replace('"', "").replace("`", "")
        .replace(";", "").replace("\\", "").lower()
    )


def is_content_file(rel_path: str) -> bool:
    if not rel_path.endswith(".md"):
        return False
    parts = rel_path.split("/")
    return parts[0] not in SKIP_DIRS and not parts[-1].startswith("_")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def content_hash_sans_neural(text: str) -> str:
    """Hash file content excluding the neural: frontmatter block.

    Scoped to frontmatter only — neural: in body text is preserved in hash.
    """
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            body = text[end:]
            fm_stripped = _NEURAL_BLOCK_RE.sub("", fm)
            to_hash = "---" + fm_stripped + body
        else:
            to_hash = text
    else:
        to_hash = text
    return hashlib.sha256(to_hash.encode()).hexdigest()[:16]


# Paths recently written by NeuralWriteBack — sync_file() skips these
_writeback_paths: set[str] = set()
