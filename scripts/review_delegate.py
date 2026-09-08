#!/usr/bin/env -S uv run python
"""Drive a delegated code review: `ocr delegate` spec -> our blessed local inference.

One worker = one model = one substrate. Fan out by launching several of these in tmux with
different --model / --shard values, so panes land on DIFFERENT lemonade backends rather than
piling concurrent submissions onto one iGPU (that is the MES-ring wedge pattern).

  scripts/review_delegate.py --commit HEAD --model Gemma-4-26B-A4B-it-GGUF
  scripts/review_delegate.py --commit HEAD --shard 0/2 --model A &
  scripts/review_delegate.py --commit HEAD --shard 1/2 --model B &

Only ALREADY-RESIDENT models should be passed; this script never loads one, so it cannot
trip the N3 weights-vs-RAM rule on its own.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cohezion.review.delegate import collect, run_review  # noqa: E402


def _git_diff(commit: str):
    """Return a diff_fn bound to one commit, so run_review stays repo-agnostic."""

    def diff_fn(path: str) -> str:
        proc = subprocess.run(
            ["git", "show", f"{commit}", "--", path],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
        return proc.stdout[:40000]

    return diff_fn


def _chat_fn(model: str, max_tokens: int):
    """The blessed local path: build_gaia_llm_tier -> :13305.

    Use the BUILDER, never a hand-rolled _GaiaLLMClientShim. The builder is what applies
    reasoning_format="none" for thinking models (defect 4dd925b0081f) and resolves the model's
    card sampling defaults. Constructing the shim directly skips both: a first attempt at this
    driver did exactly that and every file came back empty, because Gemma-4-26B streamed the
    whole answer to reasoning_content with finish_reason='length' and content "".
    """
    from cohezion.inference.gaia_adapter import build_gaia_llm_tier

    tier = build_gaia_llm_tier(model, max_tokens=max_tokens)
    return tier.agent.prompt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--model", default="Gemma-4-26B-A4B-it-GGUF")
    ap.add_argument("--shard", default="", help="i/n — review only this slice of the files")
    # Generous on purpose. With reasoning_format="none" the chain-of-thought lands IN content
    # and counts against this budget, so a frugal cap truncates mid-thought and yields an empty
    # or half-finished review. Local inference is $0; the only cost of headroom is latency.
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--dry-run", action="store_true", help="print the spec, run no inference")
    args = ap.parse_args()

    review = collect(commit=args.commit, cwd=REPO)
    if not review.files:
        print("no reviewable files (is `ocr` installed and is this a git repo?)")
        return 1

    if args.shard:
        i, n = (int(x) for x in args.shard.split("/"))
        review.files = [f for idx, f in enumerate(review.files) if idx % n == i]

    print(f"[{args.model}] {len(review.files)} file(s), rules={len(review.rules)} chars")
    if args.dry_run:
        for f in review.files:
            print(f"  - {f.path} [{f.status}] +{f.insertions}/-{f.deletions}")
        return 0

    # Time each call. The rule prefix is identical for every file, so if llama.cpp's per-slot
    # prompt cache is hitting, file 1 pays the full prefill and files 2..N should be markedly
    # cheaper. That is the only way to tell a real cache hit from a plausible story about one.
    base_chat = _chat_fn(args.model, args.max_tokens)
    timings: list[float] = []

    def timed_chat(prompt: str) -> str:
        start = time.monotonic()
        try:
            return base_chat(prompt)
        finally:
            timings.append(time.monotonic() - start)

    results = run_review(review, chat_fn=timed_chat, diff_fn=_git_diff(args.commit))
    for path, findings in results.items():
        print(f"\n{'=' * 70}\n{path}\n{'=' * 70}\n{findings or '(no output)'}")

    if timings:
        print(f"\n--- timings (s) --- {' '.join(f'{t:.1f}' for t in timings)}")
        if len(timings) > 1:
            warm = sum(timings[1:]) / len(timings[1:])
            print(
                f"cold(first)={timings[0]:.1f}  warm(mean rest)={warm:.1f}  ratio={timings[0] / warm:.2f}x"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
