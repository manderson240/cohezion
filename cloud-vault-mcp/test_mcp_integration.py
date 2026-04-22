#!/usr/bin/env python3
"""Test Cloud Vault MCP integration with Claude Code."""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def check_server_health(url="http://localhost:8360"):
    """Check if MCP server is running and responsive."""
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=2) as response:
            print(f"✓ Server health check: HTTP {response.status}")
            return True
    except urllib.error.URLError as e:
        print(f"✗ Server health check failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Server health check error: {e}")
        return False


def check_mcp_config():
    """Check if ~/.claude/mcp.json exists and is valid."""
    config_path = Path.home() / ".claude" / "mcp.json"

    if not config_path.exists():
        print(f"✗ MCP config not found at {config_path}")
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)

        if "cloud-vault-mcp" not in config:
            print("✗ 'cloud-vault-mcp' entry not found in mcp.json")
            return False

        mcp_config = config["cloud-vault-mcp"]
        required_keys = {"type", "url"}
        if not required_keys.issubset(mcp_config.keys()):
            print(f"✗ Missing required keys: {required_keys - mcp_config.keys()}")
            return False

        print(f"✓ MCP config valid at {config_path}")
        print(f"  - Type: {mcp_config['type']}")
        print(f"  - URL: {mcp_config['url']}")
        print(f"  - Has auth headers: {'headers' in mcp_config}")

        return True
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in mcp.json: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading mcp.json: {e}")
        return False


def check_vault_path():
    """Check if vault directory exists and is accessible."""
    vault_path = Path("/home/mike-anderson/vaults/cohezion-vault")

    if not vault_path.exists():
        print(f"✗ Vault directory not found: {vault_path}")
        return False

    if not vault_path.is_dir():
        print(f"✗ Vault path is not a directory: {vault_path}")
        return False

    # Count markdown files
    md_files = list(vault_path.glob("**/*.md"))
    print(f"✓ Vault directory accessible: {vault_path}")
    print(f"  - Contains {len(md_files)} markdown files")

    return True


def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = Path("/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env")

    if not env_path.exists():
        print(f"✗ .env file not found: {env_path}")
        return False

    try:
        with open(env_path) as f:
            content = f.read()

        required_vars = ["VAULT_PATH", "MCP_API_KEY", "MCP_PORT"]
        found = []
        missing = []

        for var in required_vars:
            if var in content:
                found.append(var)
            else:
                missing.append(var)

        if missing:
            print(f"✗ Missing environment variables in .env: {missing}")
            return False

        print(f"✓ .env file valid: {env_path}")
        print(f"  - Found variables: {', '.join(found)}")

        return True
    except Exception as e:
        print(f"✗ Error reading .env file: {e}")
        return False


def test_vault_tool(url="http://localhost:8360"):
    """Test vault_read tool via HTTP."""
    try:
        payload = json.dumps({"path": "decisions"}).encode()
        req = urllib.request.Request(
            f"{url}/call/vault_list",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode())
            print(f"✓ vault_list tool working: HTTP {response.status}")
            if isinstance(result, str) and len(result) > 0:
                print(f"  - Response: {result[:100]}...")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("⚠ vault_list endpoint not found (404) - tool may not be registered")
        else:
            print(f"✗ vault_list tool error: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"✗ vault_list tool error: {e}")
        return False


def run_integration_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("Cloud Vault MCP - Claude Code Integration Tests")
    print("=" * 60 + "\n")

    tests = [
        ("MCP Config Check", check_mcp_config),
        ("Vault Directory Check", check_vault_path),
        ("Environment File Check", check_env_file),
        ("Server Health Check", check_server_health),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test error: {e}")
            results.append((test_name, False))

    # Try tool test only if server is running
    if any(name == "Server Health Check" and passed for name, passed in results):
        print("\n[Vault Tool Test]")
        try:
            result = test_vault_tool()
            results.append(("Vault Tool Test", result))
        except Exception as e:
            print(f"✗ Test error: {e}")
            results.append(("Vault Tool Test", False))
    else:
        print("\n[Vault Tool Test]")
        print("⊘ Skipped (server not running)")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! MCP integration ready for Claude Code.")
        return 0
    else:
        print("\n✗ Some tests failed. See above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(run_integration_tests())
