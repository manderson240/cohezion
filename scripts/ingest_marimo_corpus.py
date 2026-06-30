#!/usr/bin/env python3
"""Local-inference learning-corpus builder for the marimo docs — $0, NO Claude.

Fetches docs.marimo.io/guides/ pages, synthesizes each via lemonade :13305 (local GGUF),
writes Obsidian notes to the vault. The orchestration is deterministic Python; the reasoning
is local inference. Run:  uv run python scripts/ingest_marimo_corpus.py
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import httpx

VAULT = Path.home() / "vaults" / "cohezion-vault" / "Research" / "marimo"
LEMONADE = "http://localhost:13305/api/v1/chat/completions"
MODEL = "Gemma-4-26B-A4B-it-GGUF"  # non-thinking instruct on :13305; confirmed available
BASE = "https://docs.marimo.io/guides/"


def fetch(url: str) -> str:
    return httpx.get(url, timeout=30, follow_redirects=True).text


def strip_html(html: str) -> str:
    html = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def synth(title: str, text: str) -> str:
    prompt = (
        "You are documenting marimo (reactive Python notebooks) for a developer who embeds LOCAL "
        "LLM inference in notebooks. Summarize this guide as concise markdown bullets: the key "
        f"concepts + the most useful APIs/patterns.\n\nGUIDE: {title}\n\n{text[:6000]}\n\nBullets only."
    )
    try:
        r = httpx.post(
            LEMONADE,
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 1024, "temperature": 0.2},
            timeout=180,
        )
        return r.json()["choices"][0]["message"]["content"].strip() or "(empty synthesis)"
    except Exception as e:  # fail-open: keep the source even if synthesis fails
        return f"(synthesis failed: {e})"


def main() -> None:
    VAULT.mkdir(parents=True, exist_ok=True)
    # Robust discovery via the sitemap (the index is JS-rendered; raw HTML has no /guides hrefs).
    sm = fetch("https://docs.marimo.io/sitemap.xml")
    links = sorted(set(re.findall(r"https://docs\.marimo\.io/guides/[a-z0-9_/-]+", sm)))
    links.sort(key=lambda u: (u.count("/"), u))  # foundational (shallow) first
    links = [u for u in links if u.rstrip("/") != "https://docs.marimo.io/guides"][:30]
    print(f"found {len(links)} guide pages (from sitemap)")
    notes: list[tuple[str, str]] = []
    for url in links:
        slug = url.rstrip("/").split("/")[-1]
        try:
            text = strip_html(fetch(url))
        except Exception as e:
            print(f"  skip {slug}: {e}")
            continue
        if len(text) < 200:
            print(f"  skip {slug}: thin page")
            continue
        title = slug.replace("-", " ").title()
        summary = synth(title, text)
        (VAULT / f"{slug}.md").write_text(
            f"---\ntype: corpus\nsource: {url}\ntopic: marimo\n---\n# marimo — {title}\n\n{summary}\n\n[source]({url})\n"
        )
        notes.append((slug, title))
        print(f"  ingested {slug} ({len(summary)} chars)")
        time.sleep(0.2)
    (VAULT / "_index.md").write_text(
        "---\ntype: corpus-index\ntopic: marimo\n---\n# marimo Guides — Learning Corpus\n\n"
        + "\n".join(f"- [[{s}|{t}]]" for s, t in notes)
        + f"\n\nSource: {BASE} · {len(notes)} notes · built on local inference ($0)\n"
    )
    print(f"DONE: {len(notes)} notes -> {VAULT}")


if __name__ == "__main__":
    main()
