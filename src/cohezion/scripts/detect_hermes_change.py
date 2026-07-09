#!/usr/bin/env python3
"""Detect Hermes config/model changes and auto-apply tuned settings.

Changes are detected via: hermes version, config mtime, model name, or provider setup.
On change detection (auto-apply mode), reapplies the local-first routing policy.
Then runs `hermes doctor` to surface remaining issues.
Output is logged; notification only on actual changes.
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time


CONFIG_PATH = os.path.expanduser("~/.hermes/config.yaml")
STATE_DB = os.path.expanduser("~/.hermes/.detect_state.json")
LOGGING_FILE = os.path.expanduser("~/.hermes/logs/detect_hermes_change.log")

logger = logging.getLogger("detect_hermes_change")


def setup_logging():
    log_dir = os.path.dirname(LOGGING_FILE)
    os.makedirs(log_dir, exist_ok=True)
    logger.setLevel(logging.INFO)
    fh_log = logging.FileHandler(LOGGING_FILE)
    fh_log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    fh_log.setFormatter(fmt)
    # Also add console handler at WARNING level for noisy output suppression
    hc = logging.StreamHandler(sys.stdout)
    hc.setLevel(logging.WARNING)
    hc.setFormatter(fmt)
    logger.addHandler(hc)
    logger.addHandler(fh_log)


def get_hermes_version():
    try:
        result = subprocess.run(["hermes", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return "unknown"


def get_config_mtime():
    try:
        return os.path.getmtime(CONFIG_PATH)
    except FileNotFoundError:
        return 0.0


def get_model_info():
    """Extract model name + provider from config.yaml."""
    import re

    try:
        with open(CONFIG_PATH) as f:
            content = f.read()

        # Parse smart_model_routing section for cheap-model routing
        m_route = re.search(
            r"smart_model_routing:\n.*?cheap_model:\s*\n.*?model:\s*(.+?)\n", content, re.DOTALL
        )
        model_name = m_route.group(1).strip() if m_route else None

        p_route = re.search(
            r"smart_model_routing:\n.*?cheap_model:\s*\n.*?provider:\s*(.+?)\n", content, re.DOTALL
        )
        provider = p_route.group(1).strip() if p_route else None

        # Also check top-level model block
        m_top = re.search(r"(?:^|\s+)default:\s*([^\n]+)", content)
        if not model_name and m_top:
            model_name = m_top.group(1).strip().strip("'\"")

        p_top = re.search(r"(?:^|\s+)provider:\s*([^\n]+)", content)
        # Filter out non-provider providers like top-level provider:
        if not provider and p_top:
            candidate = p_top.group(1).strip().strip("'\"")
            # Avoid matching 'providers:' block lines
            if "model" not in candidate.lower() and "api" not in candidate.lower():
                provider = candidate

        return model_name or "unknown", provider or "unknown"
    except Exception as e:
        logger.warning(f"Could not read config for model info: {e}")
        return "unknown", "unknown"


def get_providers():
    """List configured provider names from config.yaml."""
    import yaml

    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
        providers_section = cfg.get("providers")
        if isinstance(providers_section, dict):
            return sorted(providers_section.keys())
    except Exception as e:
        logger.warning(f"Could not read providers: {e}")
    return []


def compute_change_hash():
    """Compute an md5 hash of all relevant config/state aspects."""
    version = get_hermes_version()
    mtime = os.path.getmtime(CONFIG_PATH) if os.path.isfile(CONFIG_PATH) else 0.0
    model, provider = get_model_info()
    providers_list = sorted(get_providers())

    data = f"{version}|{mtime:.2f}|{model}|{provider}|{providers_list}"
    return hashlib.md5(data.encode()).hexdigest()[:16]


def load_state():
    try:
        with open(STATE_DB) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(change_hash, changed_since=None):
    state = {"change_hash": change_hash, "updated_at": time.time()}
    if changed_since:
        state["changed_since"] = changed_since
    os.makedirs(os.path.dirname(STATE_DB), exist_ok=True)
    with open(STATE_DB, "w") as f:
        json.dump(state, f, indent=2)


def check_for_changes():
    """Check if any significant config change has occurred since last run.

    Returns (changed: bool, reason: str, details: str).
    """
    import yaml

    state = load_state()
    current_hash = compute_change_hash()
    prev_hash = state.get("change_hash", "")

    if not prev_hash:
        return True, "initial_run", f"prev=null; curr={current_hash}"

    if current_hash != prev_hash:
        # Determine what changed by inspecting config and comparing fields
        try:
            with open(CONFIG_PATH) as f:
                yaml.safe_load(f) or {}
        except Exception:
            pass

        diff_parts = []
        model_curr, prov_curr = get_model_info()
        ver_curr = get_hermes_version()

        if state.get("hermes_version") != ver_curr:
            diff_parts.append(f"ver:{state.get('hermes_version', '?')}->{ver_curr}")
        if state.get("model") != model_curr:
            diff_parts.append(f"model:{state.get('model', '?')}->{model_curr}")
        if state.get("provider") != prov_curr:
            diff_parts.append(f"prov:{state.get('provider', '?')}->{prov_curr}")

        reason = ", ".join(diff_parts) if diff_parts else "hash_mismatch"
        return True, reason, f"prev={prev_hash}; curr={current_hash}"

    return False, "no_change", f"hash={current_hash}"


def apply_tuned_settings():
    """Apply tuned settings via hermes config set commands."""
    logger.info("Applying tuned settings...")

    settings = {
        "compression.threshold": 0.35,
        "compression.target_ratio": 0.5,
        "memory.memory_char_limit": 3000,
        "memory.user_char_limit": 2000,
        "delegation.max_spawn_depth": 2,
        "delegation.max_concurrent_children": 6,
        "delegation.orchestrator": True,
        "browser.inactivity_timeout": 30,
        "terminal.timeout": 300,
        "display.streaming": True,
        "display.show_cost": True,
        "display.show_reasoning": True,
    }

    changed_count = 0
    failed_keys = []
    for key, value in settings.items():
        try:
            shell_cmd = f"hermes config set \"{key}\" '{value}'"
            result = subprocess.run(
                ["bash", "-c", shell_cmd],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                logger.debug(f"Applied: {key}={value}")
                changed_count += 1
            else:
                stderr = result.stderr.strip() or "empty stderr"
                logger.warning(f"Set failed for {key}: {stderr[:200]}")
                failed_keys.append(key)
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout applying {key}")
            failed_keys.append(key)
        except Exception as e:
            logger.error(f"Error applying {key}: {e}")
            failed_keys.append(key)

    if not failed_keys:
        logger.info(f"All {changed_count} settings applied successfully.")
    else:
        logger.warning(f"{len(failed_keys)} settings could not be applied via CLI:")
        for k in failed_keys:
            logger.warning(f"  - {k}")


def apply_routing_policy():
    """Force local-first routing with ollama-launch as advisory fallback only."""
    import yaml

    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        cfg = {}

    # Ensure smart_model_routing enabled
    if "smart_model_routing" not in cfg:
        cfg["smart_model_routing"] = {}
    cfg["smart_model_routing"]["enabled"] = True

    # Guard against accidental cloud-provider drift
    curr_provider = (cfg.get("model") or {}).get("provider", "")
    if curr_provider and any(
        block in str(curr_provider) for block in ["openrouter", "grok", "cohere"]
    ):
        logger.info(f"Drift detected: provider={curr_provider} -> reverting to local-first")
        cfg.setdefault("model", {})["provider"] = "lemonade-local"

    # Ensure fallback_providers uses only local + advisory ollama-launch (no quota burn)
    fb_val = json.dumps(["lemonade-local", "ollama-launch"])
    if isinstance(cfg.get("fallback_providers"), str):
        if cfg["fallback_providers"] != fb_val:
            logger.info(f"Updating fallback_providers -> {fb_val}")
    else:
        cfg["fallback_providers"] = fb_val

    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)

    new_provider = (cfg.get("model") or {}).get("provider", "?")
    logger.info(f"Routing policy locked. Provider={new_provider}")


def run_hermes_doctor():
    """Run hermes doctor to surface remaining issues."""
    logger.info("Running hermes doctor...")
    try:
        result = subprocess.run(["hermes", "doctor"], capture_output=True, text=True, timeout=30)
        output = result.stdout.strip()
        if output:
            for line in output.split("\n"):
                print(f"[doctor] {line}")
        if result.returncode != 0:
            err = result.stderr.strip()
            if err:
                logger.warning(f"doctor non-zero exit with stderr: {err[:500]}")
    except subprocess.TimeoutExpired:
        logger.error("hermes doctor timed out after 30s")
    except FileNotFoundError:
        logger.error("hermes CLI not found — skipping doctor")


def auto_apply_mode():
    """Main entry for --auto-apply."""
    changed, reason, details = check_for_changes()

    if not changed:
        logger.info(f"NO CHANGE detected. Skipping. ({details})")
        return False

    logger.info(f"CHANGES DETECTED. Reason={reason} {details}")
    apply_tuned_settings()
    apply_routing_policy()
    run_hermes_doctor()

    # Persist state
    new_hash = compute_change_hash()
    model, provider = get_model_info()
    version = get_hermes_version()

    state = load_state()
    state.update(
        {
            "change_hash": new_hash,
            "hermes_version": version,
            "model": model,
            "provider": provider,
            "config_mtime": os.path.getmtime(CONFIG_PATH) if os.path.isfile(CONFIG_PATH) else 0.0,
            "changed_since": reason,
            "last_applied": time.time(),
        }
    )
    save_state(new_hash)
    logger.info(f"State persisted. hash={new_hash}")
    return True


def check_only_mode():
    """Dry-run: report changes without applying."""
    changed, reason, details = check_for_changes()

    if not changed:
        logger.info(f"NO CHANGE detected. skipping. ({details})")
        print("No changes since last check.")
        return False

    model, provider = get_model_info()
    ver = get_hermes_version()

    print("Changes detected:")
    print(f"  Reason:  {reason}")
    print(f"  Details: {details}")
    print(f"  Version:   {ver}")
    print(f"  Model:     {model}")
    print(f"  Provider:  {provider}")
    print()
    print("To apply, re-run with --auto-apply")
    return True


def state_report():
    """Debug / display current state."""
    ver = get_hermes_version()
    mtime = os.path.getmtime(CONFIG_PATH) if os.path.isfile(CONFIG_PATH) else 0.0
    model, provider = get_model_info()
    providers = sorted(get_providers())
    hsh = compute_change_hash()

    print(f"Hermes version : {ver}")
    print(f"Config mtime   : {mtime:.2f} ({time.ctime(mtime)})")
    print(f"Model / provider: {model} / {provider}")
    print(f"Providers cfg'd : {providers}")
    print(f"Change hash     : {hsh}")

    state = load_state()
    if state:
        print("\nLast check (state DB):")
        for k, v in sorted(state.items()):
            print(f"  {k}: {v}")
    else:
        print("\nNo previous state — first run expected.")


def main():
    parser = argparse.ArgumentParser(
        description="Detect Hermes config/model changes and auto-apply tuned settings",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--auto-apply", action="store_true", help="Detect + reapply settings + run hermes doctor"
    )
    group.add_argument("--check", action="store_true", help="Dry-run: detect only, no apply")
    group.add_argument(
        "--state",
        "--config-state",
        action="store_true",
        help="Report current config state + last check",
    )

    args = parser.parse_args()

    setup_logging()
    logger.info(f"Started detect_hermes_change {vars(args)}")

    if args.auto_apply:
        changed = auto_apply_mode()
        sys.exit(0 if not changed else 1)  # non-zero = changes were applied
    elif args.check:
        found = check_only_mode()
        sys.exit(0 if not found else 1)
    else:
        state_report()


if __name__ == "__main__":
    main()
