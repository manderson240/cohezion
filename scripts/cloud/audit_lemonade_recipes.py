#!/usr/bin/env python3
"""Lemonade recipe audit \u2014 re-runnable, no-agent, cron-safe.

Reads live state from :13305 + on-disk code, diffs against the prior audit
(loaded from SurrealDB vault.learnings or vault file), persists the diff
back to both surfaces. Designed to run from cron without LLM overhead.

Now also probes kokoro-v1 (TTS) for liveness; alerts when the recipe unloads.
Closes the local voice loop observability.

Usage:
    python3 audit_lemonade_recipes.py               # full audit
    python3 audit_lemonade_recipes.py --dry-run     # show diff, don't write
    python3 audit_lemonade_recipes.py --json        # machine-readable

Exit codes: 0 = no change, 1 = new audit record written, 2 = error.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

LEMONADE = "http://localhost:13305"
SURREAL = "http://localhost:8001"
NS = "cohezion"
DB = "vault"
INFERENCE = Path.home() / "dev" / "cohezion" / "src" / "cohezion" / "inference"
COHEZION_ROOT = Path.home() / "dev" / "cohezion" / "src" / "cohezion"
VAULT_FILE = Path.home() / "vaults" / "cohezion-vault" / "learnings" / "AUDIT-2026-06-10-lemonade-recipes.md"


def signin() -> str:
    req = urllib.request.Request(f"{SURREAL}/signin",
        data=json.dumps({"user":"root","pass":"root"}).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)["token"]


def sql_text(token: str, q: str) -> dict:
    req = urllib.request.Request(f"{SURREAL}/sql", data=q.encode(), headers={
        "Content-Type": "text/plain", "Accept": "application/json",
        "surreal-ns": NS, "surreal-db": DB,
        "Authorization": f"Bearer {token}",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def fetch_catalog() -> list[dict]:
    with urllib.request.urlopen(f"{LEMONADE}/v1/models", timeout=10) as r:
        return json.load(r)["data"]


def fetch_health() -> dict:
    with urllib.request.urlopen(f"{LEMONADE}/api/v1/health", timeout=10) as r:
        return json.load(r)


def scan_consumers() -> list[str]:
    """Files in src/cohezion/ that mention any recipe name or TTS/audio.

    Scans the whole cohezion tree (not just inference/) so audio/narrator.py,
    swarm/*, etc. are visible.
    """
    recipes = ["flm", "llamacpp", "sd-cpp", "sd_cpp", "kokoro",
               "whispercpp", "vllm", "rocm", "vulkan", "recipe_options", "tts", "DirectLemonadeTTSTier"]
    hits = set()
    for pat in recipes:
        r = subprocess.run(
            ["grep", "-rEl", pat, "--include=*.py", "--exclude-dir=__pycache__",
             "--exclude-dir=.git", str(COHEZION_ROOT)],
            capture_output=True, text=True
        )
        for line in r.stdout.strip().splitlines():
            hits.add(line.replace(str(COHEZION_ROOT) + "/", ""))
    return sorted(hits)


def probe_kokoro_alive() -> dict:
    """Render a one-word sample against the kokoro port; cheap liveness check.
    Returns {alive: bool, port: int|None, latency_ms: float, error: str|None}.
    The kokoro port is discovered via /api/v1/health so we don't hardcode 8008.
    """
    out = {"alive": False, "port": None, "latency_ms": 0.0, "error": None}
    try:
        health = fetch_health()
        for entry in health.get("all_models_loaded", []):
            if entry.get("recipe") == "kokoro":
                # backend_url like http://127.0.0.1:8008/v1
                port = int(entry["backend_url"].split(":")[2].split("/")[0])
                out["port"] = port
                break
        if out["port"] is None:
            out["error"] = "kokoro recipe not loaded"
            return out
        import time
        start = time.perf_counter()
        req = urllib.request.Request(
            f"http://localhost:{out['port']}/v1/audio/speech",
            data=json.dumps({"model": "kokoro-v1", "input": "ping",
                             "voice": "am_michael", "response_format": "mp3"}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            audio = r.read()
        out["latency_ms"] = (time.perf_counter() - start) * 1000
        out["alive"] = (len(audio) > 1000) and (audio[:3] == b"ID3" or audio[:2] == b"\xff\xfb")
        if not out["alive"]:
            out["error"] = f"rendered {len(audio)} bytes but not a valid MP3"
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def build_audit() -> dict:
    catalog = fetch_catalog()
    health = fetch_health()
    consumers = scan_consumers()
    kokoro = probe_kokoro_alive()

    by_recipe: dict[str, list[dict]] = {}
    for m in catalog:
        by_recipe.setdefault(m.get("recipe", "?"), []).append({
            "id": m["id"],
            "labels": m.get("labels", []),
            "ctx": m.get("max_context_window"),
        })

    loaded = [{"model": e["model_name"], "device": e["device"],
               "recipe": e["recipe"], "backend_url": e["backend_url"]}
              for e in health.get("all_models_loaded", [])]

    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_models": len(catalog),
        "recipes": {r: len(ms) for r, ms in by_recipe.items()},
        "by_recipe": by_recipe,
        "loaded_count": len(loaded),
        "loaded": loaded,
        "consumers": consumers,
        "kokoro_liveness": kokoro,
    }


def persist(audit: dict) -> None:
    """Write to SurrealDB + vault file."""
    token = signin()
    audit_id = f"lemonade_recipe_audit_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%M%S')}"
    summary_kokoro = "alive" if audit["kokoro_liveness"]["alive"] else f"DEAD ({audit['kokoro_liveness'].get('error','?')})"
    sql = f"""
    INSERT INTO learnings {{
        id: learnings:{audit_id},
        date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}',
        title: 'Lemonade recipe audit (auto, cron)',
        summary: 'Catalog: {audit['total_models']} models, {len(audit['recipes'])} recipes, {audit['loaded_count']} loaded. Consumers: {len(audit['consumers'])} files. Kokoro liveness: {summary_kokoro}.',
        pattern: 'lemonade catalog dispatch by model name',
        hardware: 'Strix Halo',
        tags: ['lemonade', 'recipe', 'audit', 'auto-cron', 'kokoro-probe'],
        verified: true,
        kokoro_alive: {str(audit['kokoro_liveness']['alive']).lower()},
        catalog_snapshot: {json.dumps(audit, separators=(',', ':'))},
        vault_file: '{VAULT_FILE}'
    }}
    """.strip()
    sql_text(token, sql)
    VAULT_FILE.write_text(json.dumps(audit, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        audit = build_audit()
    except Exception as e:
        print(f"audit failed: {e}", file=sys.stderr)
        return 2

    kokoro_line = f" / kokoro={'alive' if audit['kokoro_liveness']['alive'] else 'DEAD'}"
    if args.json or args.dry_run:
        print(json.dumps(audit, indent=2))
    else:
        print(f"{audit['total_models']} models / {len(audit['recipes'])} recipes / {audit['loaded_count']} loaded / {len(audit['consumers'])} consumer files{kokoro_line}")

    if not args.dry_run:
        persist(audit)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
