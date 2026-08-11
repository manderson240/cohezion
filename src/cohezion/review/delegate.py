"""Run `ocr`'s review spec through OUR inference path instead of its own.

`ocr` (alibaba/open-code-review) can call an OpenAI endpoint directly, and pointing it at
:13305 does work. We deliberately do not do that. A raw OpenAI call from a Node process is
un-routed (no local-first cascade), un-ledgered (no record_local/record_cloud), and un-gated —
exactly the seam ``scripts/ci/check_local_llm_chokepoint.sh`` exists to catch. Even when such a
call is local-only today, it is an un-instrumented path through which a cloud escalation can
later appear unobserved.

So we use ``ocr delegate``, which emits the file set, mode, background, and the full review
rule corpus with NO LLM involved, and we do the inference ourselves through the blessed shim.
Deterministic work stays in the deterministic tool; inference stays on the instrumented path.

PROMPT ORDER IS LOAD-BEARING. ``build_prompt`` puts the rule corpus and background FIRST and
the file's diff LAST, so every file in a review shares a byte-identical prefix. llama.cpp can
then reuse the cached KV for that prefix instead of re-prefilling several thousand tokens per
file. Reordering these sections would not change any single review's content, and would
silently destroy the cache hit — hence ``test_prompt_prefix_is_stable_across_files``.

Inference and git access are both injected (``chat_fn``, ``diff_fn``) so this module has no
network or repo dependency of its own and is testable without either.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)

_OCR_BIN = "ocr"
_TIMEOUT_S = 120

# "  - `src/cohezion/knowledge/corpus.py` [added] +141/-0"
_FILE_RE = re.compile(
    r"^\s*-\s+`(?P<path>[^`]+)`\s+\[(?P<status>\w+)\]\s+\+(?P<ins>\d+)/-(?P<dels>\d+)"
)
_META_RE = re.compile(r"^-\s+(?P<key>mode|commit|total_insertions|total_deletions):\s*(?P<val>.*)$")


@dataclass(frozen=True)
class ReviewFile:
    """One reviewable file as `ocr delegate preview` reported it."""

    path: str
    status: str
    insertions: int
    deletions: int


@dataclass
class DelegatedReview:
    """The LLM-free review spec: what to review, and the rules to review it against."""

    mode: str = ""
    ref: str = ""
    background: str = ""
    rules: str = ""
    files: list[ReviewFile] = field(default_factory=list)


def _run_ocr(args: list[str], cwd: Path | None = None) -> str:
    """Invoke `ocr` and return stdout, or "" if it is unavailable or fails.

    Fail-soft: a missing binary or a non-zero exit yields an empty spec rather than an
    exception, so a caller that merely wanted a review is never taken down by tooling.
    """
    try:
        proc = subprocess.run(
            [_OCR_BIN, *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("ocr %s unavailable: %s", " ".join(args), exc)
        return ""
    if proc.returncode != 0:
        logger.debug("ocr %s exited %d: %s", " ".join(args), proc.returncode, proc.stderr[:200])
        return ""
    return proc.stdout


def parse_preview(text: str) -> DelegatedReview:
    """Parse `ocr delegate preview` markdown into a DelegatedReview (rules not yet filled).

    The background block is free-form multi-line prose (it is the commit message), so it runs
    from the ``- background:`` line until the next recognised metadata key or the file list.
    """
    review = DelegatedReview()
    background: list[str] = []
    in_background = False

    for line in text.splitlines():
        file_match = _FILE_RE.match(line)
        if file_match:
            in_background = False
            review.files.append(
                ReviewFile(
                    path=file_match["path"],
                    status=file_match["status"],
                    insertions=int(file_match["ins"]),
                    deletions=int(file_match["dels"]),
                )
            )
            continue

        meta = _META_RE.match(line)
        if meta:
            in_background = False
            key, val = meta["key"], meta["val"].strip()
            if key == "mode":
                review.mode = val
            elif key == "commit":
                review.ref = val
            continue

        if line.startswith("- background:"):
            in_background = True
            background.append(line[len("- background:") :].strip())
            continue

        if in_background:
            background.append(line)

    review.background = "\n".join(background).strip()
    return review


def collect(
    *,
    commit: str | None = None,
    from_ref: str | None = None,
    to_ref: str | None = None,
    cwd: Path | None = None,
) -> DelegatedReview:
    """Build the full review spec via two LLM-free `ocr delegate` calls."""
    scope: list[str] = []
    if commit:
        scope = ["--commit", commit]
    elif from_ref and to_ref:
        scope = ["--from", from_ref, "--to", to_ref]

    review = parse_preview(_run_ocr(["delegate", "preview", *scope], cwd=cwd))
    if review.files:
        # One call for all paths: the rules are shared, so fetching per-file would both waste
        # work and risk the prefix differing between files.
        review.rules = _run_ocr(
            ["delegate", "rule", *(f.path for f in review.files)], cwd=cwd
        ).strip()
    return review


def build_prompt(review: DelegatedReview, file: ReviewFile, diff: str) -> str:
    """Compose the per-file prompt with the STABLE sections first.

    Everything above the FILE UNDER REVIEW marker is identical for every file in a review.
    That is what lets the inference server reuse cached KV rather than re-prefilling the whole
    rule corpus per file, and it is asserted by a test rather than left to convention.
    """
    header = [
        "You are reviewing a code change. Apply the rules below exactly.",
        "",
        "## REVIEW RULES",
        review.rules,
    ]
    if review.background:
        header += ["", "## CHANGE BACKGROUND", review.background]
    header += [
        "",
        "## OUTPUT FORMAT",
        "For each defect: `path:line — severity — one-sentence description`.",
        "Report nothing if the change is sound. Do not restate the diff.",
        "",
        "## FILE UNDER REVIEW",
        f"{file.path} [{file.status}] +{file.insertions}/-{file.deletions}",
        "",
        diff,
    ]
    return "\n".join(header)


def run_review(
    review: DelegatedReview,
    chat_fn,
    diff_fn,
) -> dict[str, str]:
    """Review each file sequentially, returning {path: findings}.

    Sequential on purpose. `ocr`'s own default is 8 concurrent file reviews, which is tuned for
    a cloud API; against a local server with `-np 2` slots the requests starve each other until
    they all hit the deadline together. Going one at a time also keeps the shared prefix warm
    in a single slot instead of forcing a separate KV copy per slot.

    A failure on one file is recorded and does not abort the rest — a partial review is useful,
    a lost review is not.
    """
    results: dict[str, str] = {}
    for file in review.files:
        try:
            results[file.path] = chat_fn(build_prompt(review, file, diff_fn(file.path))).strip()
        # Broad on purpose: any single-file failure (timeout, malformed response, transport)
        # must degrade to a recorded error, never lose the other files' reviews.
        except Exception as exc:
            logger.warning("review failed for %s: %s", file.path, exc)
            results[file.path] = f"ERROR: {exc}"
    return results
