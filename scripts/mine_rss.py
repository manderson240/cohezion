#!/usr/bin/env python3
"""Mine an OSS-discovery RSS feed via LOCAL inference — $0, out of Claude's context.

User directive 2026-06-07: "can we leverage opensourceprojects.dev/rss". The feed is a
5-minute-fresh stream of new GitHub projects; reading the raw XML (and each linked post) in
the agent's context would burn the Claude plan quota the throttle exists to protect. So the
BULK relevance filtering runs on the local fleet (lemonade :13305): fetch RSS → one batched
local-LLM pass over all item titles+descriptions → emit only the cohezion-relevant ones with a
`[VERIFY: <post-url>]` tag. The AGENT then does verify-before-cite on the few survivors
(fetch the post, extract the GitHub repo, confirm it exists via the GitHub API — the SkillClaw
pattern) before anything lands in docs/research/BLEEDING_EDGE_FEED.md.

Division of labor: local LLM = cheap recall filter over many items; agent = rigorous
verification over the handful that pass. Neither step puts the raw feed into Claude's context.

Usage:
    python scripts/mine_rss.py [feed_url] [out.md] [model]
Defaults: https://opensourceprojects.dev/rss , docs/research/OSS_FEED_DIGEST.md ,
          Gemma-4-26B-A4B-it-GGUF (a currently-loaded, instruction-following local model).
"""

from __future__ import annotations

import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx


LEMONADE = "http://localhost:13305/api/v1/chat/completions"
DEFAULT_FEED = "https://opensourceprojects.dev/rss"
# Quality > speed (we are not in a hurry): default to the CAPABLE model with thinking suppressed
# (`chat_template_kwargs.enable_thinking=False`, set in llm_triage). Measured 2026-06-07 on the
# Phoronix triage: Gemma-26B thinking-ON → 0 picks (CoT eats the budget); thinking-OFF → higher
# precision than no-thinking Granite-8B (dropped HDMI/display/non-x86 noise, accurate reasoning).
# 26B-A4B is MoE (~4B active params/token) so it is fast despite the 15.7 GB footprint, and it is
# already loaded on :13305. Override via argv[3]; Granite remains a valid no-thinking fallback.
DEFAULT_MODEL = "Gemma-4-26B-A4B-it-GGUF"

# Cheap keyword prefilter — used to RANK/annotate, and as the sole filter if the fleet is down.
# Two complementary lenses: (1) AI-tooling (opensourceprojects.dev-style feeds) and (2) the fleet's
# HARDWARE SUBSTRATE (phoronix-style feeds) — kernel/driver/ROCm news that affects whether the fleet runs.
_RELEVANT_HINTS = (
    # AI tooling
    "local", "on-device", "llama.cpp", "gguf", "gemma", "qwen", "npu", "igpu", "inference",
    "agent", "agentic", "llm", "context", "compress", "cache", "quantiz", "speculative",
    "moe", "optimizer", "training", "fine-tun", "lora", "kaggle", "rag", "embedding", "skill",
    "self-host", "privacy-first", "mcp", "router", "token",
    # hardware substrate (Strix Halo: gfx1151 iGPU + XDNA2 NPU on Linux)
    "amd", "rocm", "ryzen", "radeon", "strix", "gfx", "xdna", "rdna", "amdgpu", "kernel",
    "mesa", "radv", "vulkan", "s2idle", "power management", "driver", "ai max",
)

_PROMPT = (
    "You are triaging a feed for a developer running a LOCAL AMD Strix Halo inference fleet "
    "(Ryzen AI MAX+ 395: gfx1151 iGPU + XDNA2 NPU, on Linux; $0 local-first, cloud only as fallback), "
    "an agentic compound-engineering loop, a Claude-usage budget, and Kaggle/hackathon money tracks. "
    "You are given a numbered list of headlines (open-source projects OR Linux-hardware news). "
    "Output ONLY the numbers genuinely relevant to EITHER: "
    "(A) local/on-device models (GGUF/llama.cpp/Gemma/Qwen/small models), agentic coding tools, "
    "context compression/caching, speculative decoding/quantization, training-efficiency "
    "(optimizers, LoRA, MoE), cost/usage monitoring, self-improving agents, RAG/embeddings, "
    "competitions/grants; OR "
    "(B) the fleet's COMPUTE SUBSTRATE — ROCm, gfx1151/RDNA3.5 GPU-compute, XDNA2/NPU, llama.cpp/"
    "Vulkan compute, AMD GAIA/Ryzen-AI, or Linux-kernel/Mesa/AMDGPU changes that affect AMD COMPUTE "
    "or Strix Halo specifically, or s2idle power management on this APU. "
    "For each relevant one output exactly one line: "
    "'<n> | <why it matters to THIS AMD inference fleet, one clause>'. Do NOT output a line for an "
    "irrelevant item (no 'None' lines) — just omit it. Skip gaming (anti-lag/FSR), display/HDMI, "
    "non-x86 (POWER/ARM), generic distro news, and anything unrelated. If none are relevant, output "
    "exactly 'NONE'. Do not invent items that are not in the list."
)


def fetch_items(feed_url: str) -> list[dict[str, str]]:
    req = urllib.request.Request(feed_url, headers={"User-Agent": "cohezion-research/1.0"})  # noqa: S310
    raw = urllib.request.urlopen(req, timeout=20).read()  # noqa: S310 (fixed https research feed)
    root = ET.fromstring(raw)  # noqa: S314 (public RSS, not attacker-controlled; defusedxml not a dep)
    items = []
    for it in root.findall(".//item"):
        items.append(
            {
                "title": (it.findtext("title") or "").strip(),
                "desc": (it.findtext("description") or "").strip(),
                "link": (it.findtext("link") or "").strip(),
            }
        )
    return items


def keyword_relevant(item: dict[str, str]) -> bool:
    blob = f"{item['title']} {item['desc']}".lower()
    return any(h in blob for h in _RELEVANT_HINTS)


def llm_triage(items: list[dict[str, str]], model: str) -> dict[int, str]:
    """Return {item_index: why} for LLM-judged relevant items. Empty dict on any failure."""
    listing = "\n".join(
        f"{i}. {it['title']} — {it['desc'][:160]}" for i, it in enumerate(items)
    )
    try:
        r = httpx.post(
            LEMONADE,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _PROMPT},
                    {"role": "user", "content": listing},
                ],
                "max_tokens": 900,
                "temperature": 0.1,
                # Quality > speed (not in a hurry): use the CAPABLE model with thinking SUPPRESSED.
                # Measured 2026-06-07: Gemma-26B thinking-ON returns 0 content (CoT eats the budget);
                # thinking-OFF gives higher precision than no-thinking Granite-8B. enable_thinking=False
                # is the correct fix, NOT dropping to a weaker model. (Granite ignores this flag, so it
                # also works as a fallback.)
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=180.0,
        )
        r.raise_for_status()
        out = (r.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:  # local probe; report, do not crash the batch
        print(f"[local-inference unavailable: {type(exc).__name__}: {exc}] → keyword prefilter only")
        return {}
    if out.upper().startswith("NONE"):
        return {}
    picks: dict[int, str] = {}
    for line in out.splitlines():
        if "|" not in line:
            continue
        num, _, why = line.partition("|")
        num = num.strip().lstrip("-* ").rstrip(".")
        why = why.strip()
        # Guard: a small local model sometimes lists irrelevant items with a "None (...)" reason
        # instead of omitting them. Drop those — keep only genuine relevance clauses.
        if not why or why.lower().startswith("none"):
            continue
        if num.isdigit() and int(num) < len(items):
            picks[int(num)] = why
    return picks


def main() -> int:
    feed = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FEED
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/research/OSS_FEED_DIGEST.md")
    model = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODEL
    try:
        items = fetch_items(feed)
    except Exception as exc:  # feed fetch is best-effort; report, do not crash
        print(f"feed fetch failed: {type(exc).__name__}: {exc}")
        return 1
    print(f"fetched {len(items)} items from {feed}")
    picks = llm_triage(items, model)
    used = "local-LLM"
    if not picks:  # fleet down or NONE → fall back to keyword prefilter (never silent-empty)
        picks = {i: "(keyword-matched)" for i, it in enumerate(items) if keyword_relevant(it)}
        used = "keyword-prefilter"
    lines = [
        f"# OSS feed digest (local-inference-mined) — {feed}",
        f"_filter: {used} · {len(picks)}/{len(items)} relevant · agent must VERIFY each GitHub repo before citing_",
        "",
    ]
    for i in sorted(picks):
        it = items[i]
        lines.append(f"- **{it['title']}** — {picks[i]}  [VERIFY: {it['link']}]")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(picks)} relevant → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
