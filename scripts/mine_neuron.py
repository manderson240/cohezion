#!/usr/bin/env python3
"""Mine 'The Neuron' (and similar) newsletters via LOCAL inference — $0, out of Claude's context.

User directive 2026-06-07: "mine The Neuron newsletters." Newsletters are ~120KB HTML each;
reading them in the agent's context burns the Claude plan quota the throttle exists to protect.
This cleans each saved Gmail `get_thread` JSON (bs4 → visible text) and runs it through the local
lemonade fleet (Granite on :13305) to extract items relevant to the cohezion program — local
inference / agentic coding / cost-monitoring / Kaggle money tracks — writing a compact digest.

Usage:
    # 1) in the agent: call get_thread(FULL_CONTENT) for each newsletter (saves a tool-result file)
    # 2) python scripts/mine_neuron.py <tool-results-dir> [out.md]
The agent then reads only the small digest, not the raw HTML.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

LEMONADE = "http://localhost:13305/api/v1/chat/completions"
MODEL = "Granite-4.1-8B-GGUF"

_PROMPT = (
    "You are mining an AI-news newsletter for a developer running a LOCAL AMD inference fleet "
    "(NPU/iGPU/CPU, $0 local-first, cloud only as fallback), an agentic compound-engineering loop, "
    "a Claude-usage budget, and Kaggle/hackathon money tracks. From the newsletter text, extract "
    "ONLY items genuinely relevant to: local/on-device models (esp. GGUF/llama.cpp/Gemma/Qwen/"
    "small models), agentic coding tools, speculative decoding/quantization, cost/usage monitoring, "
    "self-improving agents, or competitions/grants. For each, output one line: '- <headline> — "
    "<why it matters to a local-first agent fleet> [VERIFY: <what to confirm>]'. Skip ads, sponsors, "
    "memes, politics, and generic hype. If nothing is relevant, output exactly 'NONE'. Max 5 items."
)


def clean(html_body: str) -> str:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_body, "html.parser")
        for t in soup(["style", "script", "head"]):
            t.decompose()
        txt = soup.get_text("\n", strip=True)
    except ImportError:
        txt = re.sub(r"(?is)<(style|script|head)[^>]*>.*?</\1>", " ", html_body)
        txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = re.sub(r"[ \t‌]+", " ", txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    lines = [
        ln.strip()
        for ln in txt.splitlines()
        if len(ln.strip()) > 3 and not re.search(r"unsubscribe|advertis|sponsor", ln, re.I)
    ]
    return "\n".join(lines)


def mine_one(text: str, subject: str) -> str:
    body = text[:8000]  # cap per-issue context for the local model
    try:
        r = httpx.post(
            LEMONADE,
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": _PROMPT},
                    {"role": "user", "content": f"SUBJECT: {subject}\n\n{body}"},
                ],
                "max_tokens": 400,
                "temperature": 0.2,
            },
            timeout=120.0,
        )
        r.raise_for_status()
        return (r.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:  # noqa: BLE001 — local probe; report, don't crash the batch
        return f"[local-inference error: {type(exc).__name__}: {exc}]"


def main() -> int:
    tool_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/research/NEURON_DIGEST.md")
    # optional 3rd arg: only mine messages whose sender contains this substring
    sender_filter = sys.argv[3] if len(sys.argv) > 3 else ""
    files = sorted(tool_dir.glob("*get_thread*.txt"))
    if not files:
        print(f"No get_thread result files in {tool_dir}")
        return 1
    sections = [f"# Newsletter digest (local-inference-mined){' — ' + sender_filter if sender_filter else ''}", ""]
    for f in files:
        try:
            d = json.loads(f.read_text())
            m = d["messages"][0]
        except Exception:  # noqa: S112 — skip unreadable result files
            continue
        if sender_filter and sender_filter.lower() not in (m.get("sender") or "").lower():
            continue
        subject = m.get("subject", "(no subject)")
        body = m.get("htmlBody") or m.get("plaintextBody") or ""
        digest = mine_one(clean(body), subject)
        if digest and digest.strip().upper() != "NONE":
            sections.append(f"## {subject}  ({m.get('date','')[:10]})")
            sections.append(digest)
            sections.append("")
        print(f"mined: {subject} -> {len(digest)} chars")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(sections), encoding="utf-8")
    print(f"\nDigest written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
