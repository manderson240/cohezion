#!/usr/bin/env python3
"""Register new models into the Lemonade :13305 OmniRouter catalog.

Usage:
    uv run python scripts/register_lemonade_models.py add phi4-mini
    uv run python scripts/register_lemonade_models.py add mistral-small-3.2
    uv run python scripts/register_lemonade_models.py add qwythos-9b        # convert + register
    uv run python scripts/register_lemonade_models.py watch smollm3         # poll until GGUF ready
    uv run python scripts/register_lemonade_models.py status                # show catalog + registered
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

LEMONADE_CACHE = Path.home() / ".cache" / "lemonade"
USER_MODELS_JSON = LEMONADE_CACHE / "user_models.json"
CUSTOM_MODELS_DIR = LEMONADE_CACHE / "custom_models"
LLAMA_CONVERT = Path.home() / "src" / "llama.cpp" / "convert_hf_to_gguf.py"
LLAMA_QUANTIZE = LEMONADE_CACHE / "bin" / "llamacpp" / "vulkan" / "llama-quantize"
LEMONADE_API = "http://localhost:13305"

# --- Model registry -----------------------------------------------------------
# Each entry describes how to register the model.
# "checkpoint" entries are downloaded by Lemonade on first load.
# "convert_from" entries require local conversion (no GGUF exists yet).

MODELS = {
    "phi4-mini": {
        "name": "Phi-4-mini-instruct-GGUF",
        "checkpoint": "lmstudio-community/phi-4-mini-instruct-GGUF:Phi-4-mini-instruct-Q4_K_M.gguf",
        "recipe": "llamacpp",
        "recipe_options": {"ctx_size": 32768, "llamacpp_backend": "vulkan"},
        "labels": ["custom", "fast-iGPU", "reasoning"],
        "notes": "3.8B, 2.49GB Q4_K_M, 128K context, MIT. Routes: autoharness, mcp-specialist",
    },
    "mistral-small-3.2": {
        "name": "Mistral-Small-3.2-24B-Instruct-GGUF",
        "checkpoint": "lmstudio-community/Mistral-Small-3.2-24B-Instruct-2506-GGUF:Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf",
        "recipe": "llamacpp",
        "recipe_options": {"ctx_size": 32768, "llamacpp_backend": "vulkan"},
        "labels": ["custom", "cpu-tier", "vision", "tool-calling"],
        "notes": "24B, ~14GB Q4_K_M, 131K ctx, Apache 2.0. Routes: cso, mcp-specialist (vision+tool-calling)",
    },
    "qwythos-9b": {
        "name": "Qwythos-9B-Claude-Mythos-5-1M-GGUF",
        "convert_from": "empero-ai/Qwythos-9B-Claude-Mythos-5-1M",
        "recipe": "llamacpp",
        "recipe_options": {"ctx_size": 32768, "llamacpp_backend": "vulkan"},
        "labels": ["custom", "iGPU", "security", "long-context"],
        "notes": "9B, ~5.5GB Q4_K_M, 1M ctx (YaRN), Apache 2.0. Routes: cso, compound-engineering",
    },
}

# Models to watch for GGUF availability (not in MODELS until GGUF ships)
WATCH = {
    "smollm3": {
        "hf_id": "HuggingFaceTB/SmolLM3-3B-Instruct",
        "gguf_repos": [
            "bartowski/SmolLM3-3B-Instruct-GGUF",
            "unsloth/SmolLM3-3B-Instruct-GGUF",
            "lmstudio-community/SmolLM3-3B-Instruct-GGUF",
        ],
        "notes": "3B, ~1.8GB Q4_K_M, 64K/128K ctx, thinking mode. Target: smart iGPU router",
    }
}


def load_user_models() -> dict:
    if USER_MODELS_JSON.exists():
        return json.loads(USER_MODELS_JSON.read_text())
    return {}


def save_user_models(data: dict) -> None:
    USER_MODELS_JSON.write_text(json.dumps(data, indent=2) + "\n")
    print(f"[saved] {USER_MODELS_JSON}")


def register_checkpoint(key: str) -> None:
    spec = MODELS[key]
    models = load_user_models()
    name = spec["name"]
    if name in models:
        print(f"[skip] {name} already registered")
        return

    entry = {
        "checkpoint": spec["checkpoint"],
        "recipe": spec["recipe"],
        "recipe_options": spec["recipe_options"],
        "labels": spec.get("labels", ["custom"]),
        "suggested": True,
    }
    models[name] = entry
    save_user_models(models)
    print(f"[registered] {name}")
    print(f"  checkpoint: {spec['checkpoint']}")
    print(f"  notes: {spec.get('notes', '')}")
    print(f"\nLoad now: curl -s -X POST {LEMONADE_API}/api/v1/load \\")
    print(f'  -H "Content-Type: application/json" \\')
    print(f'  -d \'{{"model_name": "{name}", "ctx_size": {spec["recipe_options"]["ctx_size"]}, "save_options": true}}\'')


def convert_and_register(key: str) -> None:
    spec = MODELS[key]
    name = spec["name"]
    hf_id = spec["convert_from"]

    print(f"[convert] {hf_id} → GGUF")
    print("  Step 1: download safetensors")

    from huggingface_hub import snapshot_download  # noqa: PLC0415

    local_path = snapshot_download(
        repo_id=hf_id,
        local_dir=str(CUSTOM_MODELS_DIR / f"{name}-src"),
        ignore_patterns=["*.md", "*.png", "*.svg", "evals/*"],
    )
    print(f"  downloaded to: {local_path}")

    print("  Step 2: convert to F16 GGUF")
    f16_path = CUSTOM_MODELS_DIR / f"{name}-F16.gguf"
    subprocess.run(
        [sys.executable, str(LLAMA_CONVERT), local_path, "--outfile", str(f16_path), "--outtype", "f16"],
        check=True,
    )
    print(f"  converted: {f16_path}")

    print("  Step 3: quantize to Q4_K_M")
    q4_path = CUSTOM_MODELS_DIR / f"{name}-Q4_K_M.gguf"
    subprocess.run(
        [str(LLAMA_QUANTIZE), str(f16_path), str(q4_path), "Q4_K_M"],
        check=True,
    )
    print(f"  quantized: {q4_path} ({q4_path.stat().st_size / 1e9:.2f} GB)")
    f16_path.unlink()  # remove intermediate
    print(f"  removed intermediate F16 file")

    print("  Step 4: register in user_models.json")
    models = load_user_models()
    models[name] = {
        "checkpoint": str(q4_path),
        "recipe": spec["recipe"],
        "recipe_options": spec["recipe_options"],
        "labels": spec.get("labels", ["custom"]),
        "suggested": True,
    }
    save_user_models(models)
    print(f"[done] {name} registered at {q4_path}")


def watch_gguf(key: str) -> None:
    from huggingface_hub import list_repo_files  # noqa: PLC0415

    spec = WATCH[key]
    print(f"[watch] checking GGUF availability for {spec['hf_id']}")
    for repo in spec["gguf_repos"]:
        try:
            files = [f for f in list_repo_files(repo) if "Q4_K_M" in f]
            if files:
                print(f"  [FOUND] {repo}: {files[0]}")
                print(f"  Add to MODELS dict and run: register_lemonade_models.py add {key}")
                return
            print(f"  [not ready] {repo} — no Q4_K_M yet")
        except Exception:
            print(f"  [missing] {repo}")
    print(f"[watch] No GGUF found yet. Re-check in a few days.")
    print(f"  Notes: {spec['notes']}")


def show_status() -> None:
    import urllib.request  # noqa: PLC0415

    print("=== Lemonade catalog ===")
    try:
        with urllib.request.urlopen(f"{LEMONADE_API}/api/v1/models", timeout=3) as r:
            data = json.load(r)
            models = data.get("data", []) or data.get("models", [])
            for m in models:
                name = m.get("id") or m.get("name")
                size = m.get("size", "?")
                print(f"  {name} ({size} GB)")
            print(f"  Total: {len(models)} models")
    except Exception as e:
        print(f"  [offline] {e}")

    print("\n=== user_models.json (custom registrations) ===")
    for name, entry in load_user_models().items():
        src = entry.get("checkpoint", entry.get("convert_from", "?"))
        print(f"  {name}")
        print(f"    checkpoint: {src}")
        print(f"    ctx_size: {entry.get('recipe_options', {}).get('ctx_size', '?')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Lemonade model registrations")
    sub = parser.add_subparsers(dest="cmd")

    add_p = sub.add_parser("add", help="Register a model")
    add_p.add_argument("model", choices=list(MODELS))

    watch_p = sub.add_parser("watch", help="Poll for GGUF availability")
    watch_p.add_argument("model", choices=list(WATCH))

    sub.add_parser("status", help="Show catalog and custom registrations")

    args = parser.parse_args()
    if args.cmd == "add":
        spec = MODELS[args.model]
        if "checkpoint" in spec:
            register_checkpoint(args.model)
        else:
            convert_and_register(args.model)
    elif args.cmd == "watch":
        watch_gguf(args.model)
    elif args.cmd == "status":
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
