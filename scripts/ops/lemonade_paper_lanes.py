#!/usr/bin/env python3
"""Generic local-inference research lanes over one arXiv paper. $0 on :13305.

Written on the third near-duplicate (rule of three). Supersedes the per-paper scripts
lemonade_quipu_research.py and lemonade_physics_of_agents.py, which hard-coded their abstract
and questions.

Usage:
    lemonade_paper_lanes.py --id 2608.16565 --lane "name:question" [--lane ...] [--model M]
    lemonade_paper_lanes.py --self-test

FOUR FAILURE MODES ARE BAKED IN AS DEFAULTS, each measured on this box 2026-08-19:

1. max_tokens covers REASONING, not output. At 1800 a triage batch returned 2 HTTP 500s and a
   truncation carrying 3,859 chars of reasoning with ZERO content — 1 of 8 lanes usable. A short
   answer does not make a thinking model think less. Default 6000.
2. Small models fabricate on long multi-constraint prompts. gpt-oss-20b, given an abstract plus a
   15-line context block plus a 5-line output format, described a RAG paper as "a benchmark for
   RL agents in cooking scenarios" — a different paper in the same batch. Context bleed was
   tested and REFUTED, so it is a capability limit. Default model is the 35B, and each lane asks
   ONE question.
3. Truncation can surface as HTTP 500 rather than a clean finish_reason. Both are reported as
   instrument failures, never scored as verdicts.
4. Lanes are independent, so they run in parallel — but they SHARE the router, and this box was
   hard-frozen once by over-subscription (2026-08-15 OOM). Concurrency capped at 2.

(A fifth, not fixable here: `cmd &` inside a normal tool call gets reaped. Run in the foreground.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from durable_swarm_output import DurableRun
from untrusted_content import wrap_untrusted


LOCAL_URL = "http://localhost:13305/api/v1/chat/completions"
ARXIV_API = "https://export.arxiv.org/api/query?id_list={}"  # https + follow redirects
DEFAULT_MODEL = "Qwen3.6-35B-A3B-MTP-GGUF"
MAX_CONCURRENCY = 2
DEFAULT_MAX_TOKENS = 6000

_CLOSERS = (r"<\|?channel\|>", r"</think>")


def strip_reasoning(text: str) -> str:
    """Drop the reasoning prefix. Family-specific closers; rsplit on the LAST one."""
    for closer in _CLOSERS:
        parts = re.split(closer, text)
        if len(parts) > 1:
            text = parts[-1]
    return text.strip()


def fetch_paper(arxiv_id: str, timeout: int = 60) -> dict:
    """Title/authors/abstract from the arXiv export API.

    NOTE the https and the redirect-following: querying http:// without -L returns 301 with an
    EMPTY body, which reads as 'the API is down'. That false negative was recorded and corrected
    on 2026-08-19 — the API was healthy the whole time.
    """
    with urllib.request.urlopen(ARXIV_API.format(arxiv_id), timeout=timeout) as r:  # noqa: S310
        xml = r.read().decode("utf-8", errors="replace")

    def grab(pattern: str) -> str:
        m = re.search(pattern, xml, re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

    return {
        "id": arxiv_id,
        "title": grab(r"<entry>.*?<title>(.*?)</title>"),
        "abstract": grab(r"<summary>(.*?)</summary>"),
        "authors": re.findall(r"<name>(.*?)</name>", xml),
        "published": grab(r"<published>(.*?)</published>"),
    }


def call(model: str, prompt: str, max_tokens: int, timeout: int = 900) -> tuple[str, str]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
    ).encode()
    req = urllib.request.Request(
        LOCAL_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        d = json.loads(r.read())
    ch = d["choices"][0]
    text = strip_reasoning(ch["message"].get("content") or "")
    if not text and ch.get("finish_reason") == "length":
        n = len(ch["message"].get("reasoning_content") or "")
        return "", f"TRUNCATED: budget spent reasoning ({n} chars), no content"
    return text, ""


def parse_lane(spec: str) -> tuple[str, str]:
    name, _, question = spec.partition(":")
    if not question:
        raise ValueError(f"lane must be 'name:question', got {spec!r}")
    return name.strip(), question.strip()


def self_test() -> int:
    ok = True
    cases = [
        ("plain text passes through", "hello world", "hello world"),
        ("think block stripped", "<think>musing</think>ANSWER", "ANSWER"),
        ("last closer wins", "a</think>b</think>FINAL", "FINAL"),
    ]
    for name, raw, want in cases:
        got = strip_reasoning(raw)
        flag = "ok  " if got == want else "FAIL"
        ok &= got == want
        print(f"  [{flag}] {name}: {got!r}")
    try:
        parse_lane("noquestion")
        print("  [FAIL] malformed lane spec was accepted")
        ok = False
    except ValueError:
        print("  [ok  ] malformed lane spec rejected")
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="arXiv id, e.g. 2608.16565")
    ap.add_argument("--lane", action="append", default=[], help="'name:question', repeatable")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--slug", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.id or not args.lane:
        ap.error("--id and at least one --lane are required")

    paper = fetch_paper(args.id)
    if not paper["abstract"]:
        print(f"FAILED to fetch abstract for {args.id} — refusing to run lanes on nothing")
        return 1
    # The abstract is fetched from the open web: untrusted text that may address a model directly.
    header = (
        f'"{paper["title"]}" ({", ".join(paper["authors"][:6])}'
        f'{" et al." if len(paper["authors"]) > 6 else ""} — arXiv:{args.id}, '
        f'{paper["published"][:10]}).\n\n'
        + wrap_untrusted(paper["abstract"], "ABSTRACT")
    )
    print(f"paper : {paper['title'][:70]}")
    print(f"authors: {len(paper['authors'])} | abstract: {len(paper['abstract'])} chars")

    lanes = [parse_lane(s) for s in args.lane]
    run = DurableRun.attach(args.slug or f"paper-{args.id.replace('.', '-')}")
    print(f"run   : {run.dir}")
    print(f"lanes : {len(lanes)} on {args.model}, concurrency {MAX_CONCURRENCY}\n", flush=True)

    def go(spec: tuple[str, str]) -> dict:
        name, question = spec
        t0 = time.time()
        try:
            text, err = call(args.model, f"{header}\n\n{question}", args.max_tokens)
        except Exception as e:
            text, err = "", f"{type(e).__name__}: {e}"[:180]
        return {
            "lane": name,
            "paper": args.id,
            "model": args.model,
            "elapsed_s": round(time.time() - t0, 1),
            "chars": len(text),
            "error": err,
            "text": text,
        }

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as ex:
        for r in ex.map(go, lanes):
            run.record_lane(r)
            print(f"  {r['lane']:10} {r['chars']:6}ch {r['elapsed_s']:6.1f}s {r['error']}", flush=True)
    print(f"\nwall-clock {time.time() - t0:.0f}s -> {run.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
