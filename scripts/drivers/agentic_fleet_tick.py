#!/usr/bin/env python3
"""Agentic fleet tick — drive the compound loop across the local silicon fleet.

Runs one agent-governed tick whose improvement work is DISTRIBUTED across the local
AMD silicon (NPU / iGPU / CPU) using ALREADY-LOADED lemonade models — $0 and OOM-safe:

  - Chronos resource-gates the tick (defers under CRITICAL memory pressure).
  - Vault Keeper owns the knowledge step (A2A capability routing).
  - Each tier uses only what is *already resident* (queried per port) — never a new
    load, so the per-command OOM gate + Chronos keep the box safe. Router-centric
    aware: discovers residents and fails soft when a tier is down (e.g. CPU :13309
    with nothing loaded is honestly skipped, not faked).

Usage:
    uv run python scripts/drivers/agentic_fleet_tick.py
    uv run python scripts/drivers/agentic_fleet_tick.py "your task prompt"
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request

from cohezion.compound.agentic_loop import agentic_tick


# Router-centric topology: NPU is its own daemon; the iGPU + full catalog are served
# by the router on :13305; the CPU lane lives on :13309 when a CPU model is loaded.
TIERS: list[tuple[str, int]] = [
    ("NPU", 13306),
    ("iGPU", 13305),
    ("CPU", 13309),
]

# Preferred resident model per tier (substring match, in priority order). The tier
# uses the first PREFERENCE that is actually loaded; else any non-embedding resident;
# else the tier is skipped. Never triggers a load.
_TIER_PREF: dict[str, list[str]] = {
    "NPU": ["FLM", "llama3.2-1b"],
    "iGPU": ["Granite", "Gemma-4-E4B", "8B", "Qwen3"],
    "CPU": ["31B", "30B", "27B"],
}

# Role + token budget per tier (NPU = fast classify, iGPU = generate, CPU = reason).
_TIER_ROLE: dict[str, tuple[str, int]] = {
    "NPU": ("classify", 8),
    "iGPU": ("generate", 48),
    "CPU": ("reason", 64),
}


def pick_model(loaded: list[str], prefs: list[str]) -> str | None:
    """Choose a resident model for a tier: first matching preference, else any
    non-embedding resident, else None. Pure (no I/O) — the testable core."""
    for pref in prefs:
        for m in loaded:
            if pref.lower() in m.lower() and "embed" not in m.lower():
                return m
    for m in loaded:
        if m and "embed" not in m.lower():
            return m
    return None


def loaded_models(port: int) -> list[str]:
    """Resident model names on a port (empty list if the tier is down). No new loads."""
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/v1/health", timeout=3) as r:
            data = json.load(r)
        return [m.get("model_name", "") for m in data.get("all_models_loaded", [])]
    except Exception:
        return []


def _ask(port: int, model: str, q: str, max_tokens: int) -> tuple[str, float]:
    t = time.time()
    req = urllib.request.Request(
        f"http://localhost:{port}/api/v1/chat/completions",
        data=json.dumps(
            {"model": model, "messages": [{"role": "user", "content": q}], "max_tokens": max_tokens}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = json.load(urllib.request.urlopen(req, timeout=30))  # noqa: S310  (localhost fleet)
    return r["choices"][0]["message"]["content"].strip(), (time.time() - t) * 1000


def _role_prompt(role: str, prompt: str) -> str:
    if role == "classify":
        return f"One word (data/ui/other): classify this task: {prompt}"
    if role == "reason":
        return f"In two sentences, reason about: {prompt}"
    return f"In one sentence: {prompt}"


def fleet_improvement(prompt: str):
    """Build the improvement_fn: distribute `prompt` across resident silicon tiers."""

    def _work(_ctx) -> list[str]:
        steps: list[str] = []
        for name, port in TIERS:
            role, budget = _TIER_ROLE.get(name, ("generate", 32))
            model = pick_model(loaded_models(port), _TIER_PREF.get(name, []))
            if model is None:
                steps.append(f"{name:4s} [{role:8s}] -> (tier down / no resident model — skipped)")
                continue
            try:
                out, ms = _ask(port, model, _role_prompt(role, prompt), budget)
                steps.append(f"{name:4s} [{role:8s}] {model} {ms:.0f}ms -> {out[:56]!r}")
            except Exception as exc:
                steps.append(f"{name:4s} [{role:8s}] {model} -> ERR {type(exc).__name__}")
        return steps

    return _work


def main() -> int:
    prompt = (
        sys.argv[1] if len(sys.argv) > 1 else "federate the canonical data products across domains"
    )
    result = agentic_tick(improvement_fn=fleet_improvement(prompt), context_fn=lambda: [])
    print("=== AGENTIC FLEET TICK (local silicon, already-loaded models, $0) ===")
    chronos = "headroom OK" if result.ran else f"DEFERRED {result.deferred_jobs}"
    print(f"  prompt: {prompt!r}")
    print(f"  ran: {result.ran} | Chronos: {chronos} | knowledge_owner: {result.knowledge_owner}")
    for line in result.work_summary or []:
        print(f"    {line}")
    if not result.ran:
        print("  (Chronos held the tick under memory pressure — OOM-safe)")
    print("  cost: $0.00 — no new model loads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
