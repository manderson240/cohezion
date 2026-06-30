#!/usr/bin/env python3
"""Local-inference storage manager — INDEX + TIERING PLAN. Report-only ($0, no Claude).

NON-DESTRUCTIVE: never moves or deletes. It indexes the HuggingFace model cache (the 220GB
elephant), flags models NOT in the live :13305 fleet as archive candidates, computes reclaimable
space, and writes a tiering manifest (hot=NVMe / warm=WD MyBook / cold=Google Drive). You confirm
+ run the archival commands it prints. Run:  uv run python scripts/storage_manager.py
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

HF = Path.home() / ".cache" / "huggingface" / "hub"
MANIFEST = Path.home() / ".cohezion" / "storage_manifest.json"
IDLE_DAYS = 14


def du_gb(p: Path) -> float:
    try:
        out = subprocess.run(["du", "-sb", str(p)], capture_output=True, text=True, timeout=90).stdout
        return int(out.split()[0]) / 1e9
    except Exception:
        return 0.0


def active_fleet() -> set[str]:
    try:
        import httpx

        d = httpx.get("http://localhost:13305/api/v1/models", timeout=5).json()
        return {m["id"].lower() for m in d.get("data", [])}
    except Exception:
        return set()


def is_active(model: str, fleet: set[str]) -> bool:
    leaf = model.split("/")[-1].lower()
    return any(leaf in a or a in model.lower() for a in fleet)


def main() -> None:
    if not HF.exists():
        print(f"no HF cache at {HF}")
        return
    fleet = active_fleet()
    rows = []
    for d in sorted(HF.glob("models--*")):
        model = d.name.replace("models--", "").replace("--", "/")
        gb = du_gb(d)
        idle = round((time.time() - d.stat().st_mtime) / 86400, 1)  # dir mtime ≈ last touched (fast)
        rows.append({"model": model, "gb": round(gb, 2), "idle_days": idle,
                     "active": is_active(model, fleet), "path": str(d)})
    rows.sort(key=lambda r: -r["gb"])
    total = sum(r["gb"] for r in rows)
    candidates = [r for r in rows if not r["active"] and r["idle_days"] > IDLE_DAYS]
    reclaim = sum(r["gb"] for r in candidates)

    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps({
        "generated": time.strftime("%Y-%m-%d"),
        "hf_total_gb": round(total, 1),
        "fleet_size": len(fleet),
        "tiers": {
            "hot_keep_nvme": [r for r in rows if r["active"]],
            "warm_archive_mybook": candidates,
            "cold_drive": "surreal backups, old checkpoints, rarely-touched artifacts",
        },
        "potential_reclaim_gb": round(reclaim, 1),
        "all_models": rows,
    }, indent=2))

    print(f"HF cache: {total:.0f} GB / {len(rows)} models · live fleet on :13305 = {len(fleet)} models")
    print(f"ARCHIVE CANDIDATES (not in fleet, idle >{IDLE_DAYS}d): {len(candidates)} models, "
          f"{reclaim:.0f} GB reclaimable")
    for r in candidates[:20]:
        print(f"  {r['gb']:6.1f}G  idle {r['idle_days']:5.0f}d  {r['model']}")
    print(f"\nmanifest -> {MANIFEST}")
    print("ARCHIVE (after `sudo mount /dev/sdX1 /mnt/mybook`):")
    print("  rsync -a --remove-source-files <path>/ /mnt/mybook/hf-archive/<model>/   # warm tier")
    print("NON-DESTRUCTIVE: this script moved/deleted nothing. Review the manifest, confirm, then archive.")


if __name__ == "__main__":
    main()
