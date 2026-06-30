#!/usr/bin/env python3
"""Local-inference research/audit tool — $0, NO Claude. Fetch a URL (GitHub repo → raw README),
synthesize an audit via lemonade :13305, write to the vault. The budget-correct replacement for a
cloud research subagent. Usage:  uv run python scripts/local_research.py <url> [topic]
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import httpx

LEMONADE = "http://localhost:13305/api/v1/chat/completions"
MODEL = "Gemma-4-26B-A4B-it-GGUF"
VAULT = Path.home() / "vaults" / "cohezion-vault" / "reports"


def fetch(url: str) -> str:
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/?$", url)
    if m:  # GitHub repo → try the raw README (not JS-rendered)
        for br in ("main", "master"):
            try:
                t = httpx.get(f"https://raw.githubusercontent.com/{m[1]}/{m[2]}/{br}/README.md",
                              timeout=20, follow_redirects=True).text
                if len(t) > 100:
                    return t
            except Exception:
                pass
    h = httpx.get(url, timeout=25, follow_redirects=True).text
    h = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: local_research.py <url> [topic]")
        return
    url = sys.argv[1]
    topic = sys.argv[2] if len(sys.argv) > 2 else url.rstrip("/").split("/")[-1]
    text = fetch(url)[:7000]
    prompt = (
        "Audit this for the Cohezion project (local-first compound-AI engine: 235 PRIME skills + a "
        "skill registry + BMAD skills, $0 local inference on AMD Strix Halo). "
        f"SOURCE: {url}\n\n{text}\n\n"
        "Give concise markdown: (1) what it is, (2) the relevant format/spec/API, (3) how it maps to "
        "Cohezion + the injection point, (4) honest ADOPT / REFERENCE / SKIP verdict with one reason."
    )
    out = httpx.post(LEMONADE, json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                                     "max_tokens": 1600, "temperature": 0.2}, timeout=420
                     ).json()["choices"][0]["message"]["content"].strip()
    VAULT.mkdir(parents=True, exist_ok=True)
    p = VAULT / f"{topic}-localaudit-{time.strftime('%Y%m%d')}.md"
    p.write_text(f"---\ntype: local-audit\nsource: {url}\ntopic: {topic}\n---\n# {topic}\n\n{out}\n")
    print(out)
    print(f"\n-> {p}")


if __name__ == "__main__":
    main()
