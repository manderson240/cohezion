#!/usr/bin/env python3
"""Apply local-first auxiliary routing to ~/.hermes/config.yaml.

ollama-cloud has no public API for usage/quota, so the only way to
reduce cloud call count is to route more of them to local lemonade
(:13305). The Hermes config schema lets you override each auxiliary
task individually. This script:

1. Loads ~/.hermes/config.yaml (creating a backup first)
2. Sets auxiliary.{compression,vision,embedding,web_extract,moa}.provider
   to "lemonade-local" (creates the auxiliary: {} block if missing)
3. Sets base_url to http://localhost:13305/v1 for each
4. Sets model.max_tokens = 600 to cap output cost
5. Idempotent: re-running is safe (overwrites, doesn't duplicate)

Safe to re-run. Reversible by editing config.yaml or running with
--revert to delete the auxiliary block.
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

CONFIG = Path.home() / ".hermes" / "config.yaml"
BACKUP_DIR = Path.home() / ".hermes" / "backups"
LEMONADE = "lemonade-local"
LEMONADE_URL = "http://localhost:13305/v1"
AUX_TASKS = ["compression", "vision", "embedding", "web_extract", "moa"]

def load_yaml(p: Path) -> dict:
    try:
        import yaml
    except ImportError:
        print("PyYAML not installed; install with: uv pip install pyyaml", file=sys.stderr)
        sys.exit(2)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}

def dump_yaml(p: Path, data: dict) -> None:
    import yaml
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))

def backup(p: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"config.{ts}.yaml"
    shutil.copy2(p, dest)
    return dest

def apply(cfg: dict) -> dict:
    aux = cfg.setdefault("auxiliary", {})
    for task in AUX_TASKS:
        block = aux.setdefault(task, {})
        block["provider"] = LEMONADE
        block["base_url"] = LEMONADE_URL
    model = cfg.setdefault("model", {})
    if "max_tokens" not in model or model["max_tokens"] is None or model["max_tokens"] > 600:
        model["max_tokens"] = 600
    return cfg

def revert(cfg: dict) -> dict:
    cfg.pop("auxiliary", None)
    return cfg

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--revert", action="store_true", help="remove the auxiliary block we added")
    ap.add_argument("--dry-run", action="store_true", help="print diff without writing")
    args = ap.parse_args()

    if not CONFIG.exists():
        print(f"no config at {CONFIG}; nothing to patch", file=sys.stderr)
        return 1

    cfg = load_yaml(CONFIG)
    new_cfg = revert(cfg) if args.revert else apply(cfg)
    if new_cfg == cfg:
        print(f"{CONFIG} already in target state; no changes")
        return 0

    if args.dry_run:
        print("--- proposed change ---")
        for k in AUX_TASKS:
            print(f"  auxiliary.{k}.provider = {LEMONADE}")
            print(f"  auxiliary.{k}.base_url = {LEMONADE_URL}")
        print(f"  model.max_tokens = 600")
        return 0

    bp = backup(CONFIG)
    dump_yaml(CONFIG, new_cfg)
    print(f"backed up to {bp}")
    print(f"patched {CONFIG}")
    if args.revert:
        print("(reverted auxiliary block)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
