#!/usr/bin/env python3
"""
MCP Guard v3.0 - Systems Engineering Enforcement & Harness Factory.

Capabilities:
1. Syncs mcp_registry.json with actual @app.tool signatures.
2. Syncs cross-platform configs (.gemini, .claude, .opencode, .pi).
3. Detects startup latency violations.
4. Enforces the Harness Factory (Integration Verification) mandate.
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("mcp-guard")

# Path configuration
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
REGISTRY_PATH = PROJECT_ROOT / "src/cohezion/mcp/mcp_registry.json"
GEMINI_SETTINGS = PROJECT_ROOT / ".gemini/settings.json"
CLAUDE_SETTINGS = PROJECT_ROOT / ".claude/mcp.json"
OPENCODE_SETTINGS = PROJECT_ROOT / ".opencode/mcp.json"
PI_SETTINGS = PROJECT_ROOT / ".pi/mcp.json"
SRC_PATH = PROJECT_ROOT / "src"
HARNESS_DIR = PROJECT_ROOT / "tests/harnesses"

# Anti-patterns to detect
LATENCY_PATTERNS = [
    (re.compile(r"^[A-Z_]+\s*=\s*get_credentials\(\)"), "Top-level get_credentials() call detected (Startup Latency)"),
    (re.compile(r"^[A-Z_]+\s*=\s*get_vault\(\)"), "Top-level get_vault() call detected (Startup Latency)"),
    (re.compile(r"print\("), "Use of print() instead of stderr logging (Protocol Noise)"),
]

def check_latency_violations(file_path: Path) -> list[str]:
    """Scan file for startup latency anti-patterns."""
    violations = []
    try:
        content = file_path.read_text()
        lines = content.splitlines()
        for i, line in enumerate(lines):
            for pattern, msg in LATENCY_PATTERNS:
                if pattern.search(line.strip()):
                    violations.append(f"L{i+1}: {msg}")
    except Exception as e:
        logger.warning(f"Could not scan {file_path}: {e}")
    return violations

def check_harness_exists(tool_name: str) -> bool:
    """Verify if a deterministic test harness exists for the tool."""
    harness_path = HARNESS_DIR / f"test_{tool_name}_harness.py"
    return harness_path.exists()

def extract_tools_from_file(file_path: Path) -> list[str]:
    """Extract tool names using regex pattern matching."""
    tools = []
    try:
        content = file_path.read_text()
        # Match @app.tool() or @app.tool(name="...")
        patterns = [
            re.compile(r"@app\.tool\(\s*name\s*=\s*[\"']([^\"']+)[\"']"),
            re.compile(r"async def\s+([a-zA-Z0-9_]+)\("),
        ]
        
        # We look for functions decorated with @app.tool
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "@app.tool" in line:
                # Check next line for def
                next_line = lines[i+1] if i+1 < len(lines) else ""
                match = re.search(r"async def\s+([a-zA-Z0-9_]+)\(", next_line)
                if match:
                    tools.append(match.group(1))
                
                # Check current line for name=
                match = re.search(r"name\s*=\s*[\"']([^\"']+)[\"']", line)
                if match:
                    tools.append(match.group(1))
                    
        return sorted(list(set(tools)))
    except Exception as e:
        logger.error(f"Regex tool extraction failed for {file_path}: {e}")
        return []

def sync_registry():
    """Update mcp_registry.json."""
    if not REGISTRY_PATH.exists():
        logger.error(f"Registry not found at {REGISTRY_PATH}")
        return False

    with open(REGISTRY_PATH, "r") as f:
        registry = json.load(f)

    changed = False
    for entry in registry.get("internal", []):
        server_path = entry.get("path")
        if not server_path: continue
            
        full_path = SRC_PATH / "cohezion" / server_path
        
        violations = check_latency_violations(full_path)
        if violations:
            logger.warning(f"⚠️ {entry['name']} has optimization violations:")
            for v in violations: logger.warning(f"  {v}")
            
        actual_tools = extract_tools_from_file(full_path)
        
        # Harness Factory Check
        for tool in actual_tools:
            if not check_harness_exists(tool):
                logger.warning(f"🚨 Integration Verification Failure: Missing harness for tool '{tool}' in {entry['name']}")
        
        if actual_tools and actual_tools != entry.get("tools"):
            logger.info(f"Updating tools for {entry['name']}")
            entry["tools"] = actual_tools
            changed = True

    if changed:
        with open(REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=4)
        logger.info("✅ Registry updated.")
    return True

def sync_platform_settings(settings_path: Path, platform_name: str):
    """Ensure all internal servers in registry are in the platform's MCP settings."""
    if not REGISTRY_PATH.exists():
        return

    # Create directory if missing for new platforms
    if not settings_path.parent.exists():
        settings_path.parent.mkdir(parents=True)

    with open(REGISTRY_PATH, "r") as f: registry = json.load(f)

    if not settings_path.exists():
        logger.info(f"Initializing missing {platform_name} settings at {settings_path}")
        settings = {"mcpServers": {}}
    else:
        with open(settings_path, "r") as f: settings = json.load(f)

    mcp_servers = settings.get("mcpServers", {})
    changed = False

    for entry in registry.get("internal", []):
        name = entry["name"]
        target_name = name.replace("cohezion-", "") if platform_name in ["Claude", "OpenCode", "Pi"] else name
        
        if platform_name == "Pi" and name in ["cohezion-research"]:
            continue

        config = {
            "command": f"{PROJECT_ROOT}/.venv/bin/python",
            "args": ["-m", f"cohezion.{entry['path'].replace('/', '.').replace('.py', '')}"],
            "env": {
                "PYTHONPATH": str(SRC_PATH),
                "MCP_TRANSPORT": "stdio",
                "BMAD_DATA_PATH": f"{PROJECT_ROOT}/_bmad"
            }
        }
        
        if "vault" in entry["path"]:
            vault_mcp_path = PROJECT_ROOT / "cloud-vault-mcp"
            if vault_mcp_path.exists():
                config["env"]["PYTHONPATH"] = f"{SRC_PATH}:{vault_mcp_path}/src"
            config["env"]["VAULT_PATH"] = f"{PROJECT_ROOT.parent}/vaults/cohezion-vault"
        
        if platform_name == "Gemini":
            config["description"] = entry.get("description", "")
        else:
            config["name"] = name
            config["description"] = entry.get("description", "")

        if target_name not in mcp_servers or mcp_servers[target_name] != config:
            logger.info(f"Updating server in {platform_name} settings: {target_name}")
            mcp_servers[target_name] = config
            changed = True

    if changed:
        settings["mcpServers"] = mcp_servers
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        logger.info(f"✅ {platform_name} settings synchronized.")

if __name__ == "__main__":
    sync_registry()
    sync_platform_settings(GEMINI_SETTINGS, "Gemini")
    sync_platform_settings(CLAUDE_SETTINGS, "Claude")
    sync_platform_settings(OPENCODE_SETTINGS, "OpenCode")
    sync_platform_settings(PI_SETTINGS, "Pi")
