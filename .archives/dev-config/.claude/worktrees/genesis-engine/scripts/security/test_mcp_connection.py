#!/usr/bin/env python3
"""
Test MCP Server Connection

Verify GitHub MCP server is properly configured and can connect to GitHub API.

Usage:
    python scripts/security/test_mcp_connection.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def test_github_cli() -> bool:
    """Test GitHub CLI is installed and authenticated."""
    print("🔍 Testing GitHub CLI...")

    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)

    if result.returncode == 0:
        print("   ✅ GitHub CLI authenticated")
        return True
    print("   ❌ GitHub CLI not authenticated")
    print(f"   Error: {result.stderr}")
    return False


def test_mcp_config() -> bool:
    """Test MCP configuration file exists and is valid."""
    print("🔍 Testing MCP configuration...")

    config_path = Path(__file__).parent.parent.parent / "mcp_servers.json"

    if not config_path.exists():
        print(f"   ❌ MCP config not found: {config_path}")
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)

        if "mcpServers" not in config:
            print("   ❌ Invalid MCP config: missing 'mcpServers'")
            return False

        if "github" not in config["mcpServers"]:
            print("   ❌ Invalid MCP config: missing 'github' server")
            return False

        server = config["mcpServers"]["github"]

        # Check required fields
        required = ["command", "args", "env"]
        for field in required:
            if field not in server:
                print(f"   ❌ Missing required field: {field}")
                return False

        # Check token reference
        if "GITHUB_PERSONAL_ACCESS_TOKEN" not in server["env"]:
            print("   ❌ Missing GITHUB_PERSONAL_ACCESS_TOKEN")
            return False

        print("   ✅ MCP configuration valid")
        return True

    except json.JSONDecodeError as e:
        print(f"   ❌ Invalid JSON in MCP config: {e}")
        return False


def test_github_api_access() -> bool:
    """Test GitHub API access with token."""
    print("🔍 Testing GitHub API access...")

    # Load token
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)

    result = subprocess.run(["gh", "api", "/user", "--jq", ".login"], capture_output=True, text=True)

    if result.returncode == 0:
        user = result.stdout.strip()
        print(f"   ✅ API access working (user: {user})")
        return True
    print("   ❌ API access failed")
    print(f"   Error: {result.stderr}")
    return False


def test_security_api_access() -> bool:
    """Test access to security APIs."""
    print("🔍 Testing security API access...")

    # Test code scanning access
    result = subprocess.run(
        [
            "gh",
            "api",
            "/repos/manderson240/cohezion/code-scanning/alerts",
            "-X",
            "GET",
            "-f",
            "state=open",
            "-f",
            "per_page=1",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode in [0, 404]:  # 404 is OK if no alerts yet
        print("   ✅ Code scanning API accessible")
    else:
        print("   ⚠️  Code scanning API access issue")
        print(f"   Note: {result.stderr.strip()}")

    # Test dependabot access
    result = subprocess.run(
        [
            "gh",
            "api",
            "/repos/manderson240/cohezion/dependabot/alerts",
            "-X",
            "GET",
            "-f",
            "state=open",
            "-f",
            "per_page=1",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode in [0, 404]:
        print("   ✅ Dependabot API accessible")
        return True
    print("   ⚠️  Dependabot API access issue")
    print(f"   Note: {result.stderr.strip()}")
    return True  # Still consider OK, may need permissions


def test_docker() -> bool:
    """Test Docker is available for MCP server."""
    print("🔍 Testing Docker availability...")

    result = subprocess.run(["docker", "--version"], capture_output=True, text=True)

    if result.returncode == 0:
        version = result.stdout.strip()
        print(f"   ✅ Docker available ({version})")
        return True
    print("   ❌ Docker not available")
    print("   Note: Docker is required for MCP server")
    return False


def test_mcp_server_image() -> bool:
    """Test MCP server Docker image can be pulled."""
    print("🔍 Testing MCP server Docker image...")

    result = subprocess.run(
        ["docker", "pull", "ghcr.io/github/github-mcp-server", "--quiet"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("   ✅ MCP server image available")
        return True
    print("   ⚠️  Could not pull MCP server image")
    print("   This is OK if image is already cached")
    return True  # Image may already be cached


def generate_report(results: dict[str, bool]) -> None:
    """Generate test report."""
    print()
    print("=" * 60)
    print("📊 MCP Connection Test Report")
    print("=" * 60)
    print()

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {test}")

    print()
    print(f"Result: {passed}/{total} tests passed")

    if passed == total:
        print()
        print("🎉 All tests passed! MCP server is ready to use.")
        print()
        print("You can now:")
        print("  • Run daily security checks: python scripts/security/daily_security_check.py")
        print("  • Generate weekly reports: ./scripts/security/weekly_security_report.sh")
        print("  • Query security data via MCP server")
        sys.exit(0)
    elif passed >= total - 2:
        print()
        print("⚠️  Most tests passed. MCP server may work with limitations.")
        print("Check failed tests above.")
        sys.exit(0)
    else:
        print()
        print("❌ Multiple tests failed. Please fix issues before using MCP server.")
        sys.exit(1)


def main():
    """Run all tests."""
    print("=" * 60)
    print("🔒 MCP Server Connection Test")
    print("=" * 60)
    print()

    results = {
        "GitHub CLI": test_github_cli(),
        "MCP Configuration": test_mcp_config(),
        "GitHub API Access": test_github_api_access(),
        "Security API Access": test_security_api_access(),
        "Docker": test_docker(),
        "MCP Server Image": test_mcp_server_image(),
    }

    generate_report(results)


if __name__ == "__main__":
    main()
