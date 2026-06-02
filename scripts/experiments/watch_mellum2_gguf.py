#!/usr/bin/env python3
"""Watch Hugging Face for an official (or community) Mellum-2 GGUF.

Mellum-2 (`JetBrains/Mellum2-12B-A2.5B-*`) is bf16-only at launch with no GGUF, and its
days-old MoE arch is unlikely to be supported by llama.cpp's converter yet — so it can't be
served on the lemonade fleet today. JetBrains shipped GGUFs for Mellum-4b after its release,
so they will likely do the same for Mellum-2. This watcher makes the upgrade a trigger, not a
manual rediscovery: run it daily (folded into fleet-research-daily). When a GGUF appears it
logs to the SurrealDB `fleet_research` bus and prints the one-line upgrade path.

Upgrade path when a Mellum-2 GGUF lands:
    lemonade pull <owner/repo:file.gguf>
    # then flip the CODE_GEN ModelEntry in src/cohezion/inference/registry.py:
    #   model_id -> <new lemonade id>, context_window -> 131072
    # re-run the FIM smoke (see strix-halo-fleet-orchestration skill).

Read-only: queries HF, optionally logs to the bus. Exit 0 always (cron-safe).
"""

from __future__ import annotations

import json
import sys
import urllib.request


BUS = "http://localhost:8001/sql"
BUS_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
}


def find_mellum2_gguf() -> list[str]:
    """Return repo ids of any Mellum-2 GGUF repos on HF (official JetBrains + community)."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("huggingface_hub not available; cannot check.", file=sys.stderr)
        return []
    api = HfApi()
    hits: set[str] = set()
    # Official JetBrains repos + broad community search; filter for Mellum2 + GGUF.
    for kwargs in ({"author": "JetBrains"}, {"search": "Mellum2 GGUF"}):
        try:
            for m in api.list_models(limit=200, **kwargs):
                rid = getattr(m, "id", "") or ""
                low = rid.lower()
                if "mellum2" in low.replace("-", "").replace("_", "") and "gguf" in low:
                    hits.add(rid)
        except Exception as e:  # network/API hiccup — don't crash the daily job
            print(f"  [warn] HF query failed ({kwargs}): {e}", file=sys.stderr)
    return sorted(hits)


def log_to_bus(repos: list[str]) -> None:
    payload = (
        "UPSERT fleet_research:mellum2_gguf_available CONTENT "
        f"{{ available: true, repos: {json.dumps(repos)}, "
        "note: 'Mellum-2 GGUF detected — upgrade the CODE_GEN registry entry: lemonade pull the "
        "repo, set model_id + context_window=131072, re-run FIM smoke', rec: 'UPGRADE-LANE' };"
    )
    try:
        req = urllib.request.Request(  # noqa: S310 — fixed localhost SurrealDB bus URL
            BUS, data=payload.encode(), headers=BUS_HEADERS, method="POST"
        )
        urllib.request.urlopen(req, timeout=6).read()  # noqa: S310 — controlled localhost URL
        print("  logged mellum2_gguf_available to fleet_research bus")
    except Exception as e:
        print(f"  [warn] bus log failed: {e}", file=sys.stderr)


def main() -> int:
    repos = find_mellum2_gguf()
    if repos:
        print("✅ Mellum-2 GGUF AVAILABLE:")
        for r in repos:
            print(f"   - {r}")
        print("\nUpgrade: lemonade pull <repo:file.gguf> → update the CODE_GEN ModelEntry in")
        print("src/cohezion/inference/registry.py (model_id + context_window=131072) → FIM smoke.")
        log_to_bus(repos)
    else:
        print(
            "no Mellum-2 GGUF yet (still bf16-only / arch not in llama.cpp). Mellum-4b remains the lane."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
