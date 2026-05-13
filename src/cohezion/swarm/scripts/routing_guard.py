#!/usr/bin/env python3
"""Unified Model Routing Guard.

Synchronizes provider and tier configurations across master (config/providers.yaml)
and platform-specific settings (.gemini, .claude, .pi).
"""

import json
import logging
import re
from pathlib import Path

import yaml


# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
PROVIDERS_YAML = PROJECT_ROOT / "config/providers.yaml"
MODEL_POOL_PY = PROJECT_ROOT / "src/cohezion/swarm/model_pool_config.py"
PLATFORM_CONFIGS = {
    ".gemini/settings.json": PROJECT_ROOT / ".gemini/settings.json",
    ".claude/settings.json": PROJECT_ROOT / ".claude/settings.json",
    ".pi/settings.json": PROJECT_ROOT / ".pi/settings.json",
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("routing-guard")


def extract_models_from_py(file_path: Path) -> dict[str, list[str]]:
    """Extract model lists from Python config using regex."""
    content = file_path.read_text()
    models = {}

    patterns = {
        "hot": r"hot_models:\s*list\[str\]\s*=\s*\[(.*?)\]",
        "warm": r"warm_models:\s*list\[str\]\s*=\s*\[(.*?)\]",
        "cold": r"cold_models:\s*list\[str\]\s*=\s*\[(.*?)\]",
    }

    for tier, pattern in patterns.items():
        match = re.search(pattern, content, re.DOTALL)
        if match:
            # Extract strings within quotes
            list_str = match.group(1)
            model_list = re.findall(r'"([^"]+)"', list_str)
            models[tier] = model_list

    return models


def get_master_models() -> list[str]:
    """Aggregate models from all tiers in master configs."""
    all_models = set()

    # 1. From providers.yaml
    if PROVIDERS_YAML.exists():
        with open(PROVIDERS_YAML) as f:
            providers = yaml.safe_load(f)
            if "tier_mappings" in providers:
                for _tier, types in providers["tier_mappings"].items():
                    for _m_type, m_name in types.items():
                        all_models.add(m_name)

    # 2. From model_pool_config.py
    if MODEL_POOL_PY.exists():
        py_models = extract_models_from_py(MODEL_POOL_PY)
        for _tier, m_list in py_models.items():
            for m in m_list:
                all_models.add(m)

    return sorted(list(all_models))


def sync_platform_config(config_path: Path, master_models: list[str]):
    """Sync a single platform configuration file."""
    if not config_path.exists():
        logger.warning(f"Platform config not found: {config_path}")
        return

    try:
        with open(config_path) as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read {config_path}: {e}")
        return

    master_models_str = ",".join(master_models)
    current_models = config.get("models")

    if current_models != master_models_str:
        logger.info(f"Syncing models in {config_path}...")
        config["models"] = master_models_str
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Successfully updated {config_path}")
        except Exception as e:
            logger.error(f"Failed to write to {config_path}: {e}")
    else:
        logger.info(f"Models in {config_path} are already in sync.")


def run_guard():
    """Main execution function."""
    logger.info("Starting Unified Model Routing Guard...")

    master_models = get_master_models()
    logger.info(f"Master model list: {master_models}")

    if not master_models:
        logger.warning("No models found in master configurations.")
        return

    for _name, path in PLATFORM_CONFIGS.items():
        sync_platform_config(path, master_models)

    logger.info("Model Routing Guard execution complete.")


if __name__ == "__main__":
    run_guard()
