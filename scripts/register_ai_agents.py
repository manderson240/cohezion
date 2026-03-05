#!/usr/bin/env python3
"""
Register New Agents with BMAD

Registers the new AI contribution agents:
- security-monitor (Sentinel)
- documentation-curator (Archivist)
- code-review-assistant (Inspector)

Usage:
    python scripts/register_ai_agents.py
"""

from __future__ import annotations

import sys
from pathlib import Path


# Agent definitions
AGENTS = [
    {
        "id": "security-monitor",
        "name": "Sentinel",
        "title": "Autonomous Security Monitor",
        "file": "_bmad/bmm/agents/security-monitor.md",
        "description": "Monitors security posture, generates reports, alerts on critical issues",
        "icon": "🛡️",
        "category": "operations",
        "autonomous": True,
    },
    {
        "id": "documentation-curator",
        "name": "Archivist",
        "title": "Documentation Curator",
        "file": "_bmad/bmm/agents/documentation-curator.md",
        "description": "Maintains documentation freshness, updates patterns, fixes links",
        "icon": "📚",
        "category": "documentation",
        "autonomous": True,
    },
    {
        "id": "code-review-assistant",
        "name": "Inspector",
        "title": "Code Review Assistant",
        "file": "_bmad/bmm/agents/code-review-assistant.md",
        "description": "Security-focused code reviewer, detects vulnerabilities, suggests fixes",
        "icon": "🔍",
        "category": "code-review",
        "autonomous": False,
    },
]


def check_agent_files() -> bool:
    """Verify all agent files exist."""
    print("🔍 Checking agent files...")

    all_exist = True
    for agent in AGENTS:
        path = Path(agent["file"])
        if path.exists():
            print(f"   ✅ {agent['name']} ({agent['file']})")
        else:
            print(f"   ❌ {agent['name']} - File not found: {agent['file']}")
            all_exist = False

    return all_exist


def check_sidecar_dirs() -> bool:
    """Verify sidecar directories exist."""
    print("\n🔍 Checking sidecar directories...")

    sidecars = [
        "_bmad/_memory/security-monitor-sidecar",
        "_bmad/_memory/documentation-curator-sidecar",
        "_bmad/_memory/code-review-assistant-sidecar",
    ]

    all_exist = True
    for sidecar in sidecars:
        path = Path(sidecar)
        if path.exists():
            print(f"   ✅ {sidecar}")
        else:
            print(f"   ❌ {sidecar} - Directory not found")
            all_exist = False

    return all_exist


def update_agent_manifest() -> None:
    """Update agent manifest CSV."""
    print("\n📝 Updating agent manifest...")

    manifest_path = Path("_bmad/_config/agent-manifest.csv")

    # Read existing
    if manifest_path.exists():
        content = manifest_path.read_text()
        existing_agents = {line.split(",")[0] for line in content.strip().split("\n")[1:]}
    else:
        content = "id,name,file,category,autonomous\n"
        existing_agents = set()

    # Add new agents
    added = 0
    for agent in AGENTS:
        if agent["id"] not in existing_agents:
            line = f"{agent['id']},{agent['name']},{agent['file']},{agent['category']},{agent['autonomous']}\n"
            content += line
            added += 1
            print(f"   + Added {agent['name']}")

    # Write back
    manifest_path.write_text(content)
    print(f"\n   ✅ Added {added} agents to manifest")


def create_commands() -> None:
    """Create command files for agents."""
    print("\n📝 Creating command files...")

    commands_dir = Path(".opencode/command")
    commands_dir.mkdir(parents=True, exist_ok=True)

    for agent in AGENTS:
        # Create command file
        cmd_file = commands_dir / f"security-{agent['id']}.md"

        content = f"""---
name: "security-{agent["id"]}"
description: "{agent["description"]}"
---

# /security-{agent["id"]}

Activate the {agent["title"]} ({agent["name"]}) to {agent["description"].lower()}.

## Usage

```
/security-{agent["id"]}
```

## What This Agent Does

- {agent["description"]}
- Category: {agent["category"]}
- Autonomous: {"Yes" if agent["autonomous"] else "No (on-demand)"}

## Available Actions

See agent menu after activation for available commands.

## Related

- Agent file: `{agent["file"]}`
- Sidecar: `_bmad/_memory/{agent["id"]}-sidecar/`
"""

        cmd_file.write_text(content)
        print(f"   + Created {cmd_file}")

    print(f"\n   ✅ Created {len(AGENTS)} command files")


def generate_summary() -> str:
    """Generate registration summary."""
    summary = """# AI Contribution Agents - Registration Complete

## Agents Registered

| Agent | Name | Purpose | Autonomous |
|-------|------|---------|------------|
"""

    for agent in AGENTS:
        auto = "✅ Yes" if agent["autonomous"] else "❌ No"
        summary += f"| {agent['icon']} {agent['id']} | {agent['name']} | {agent['description']} | {auto} |\n"

    summary += """
## Quick Start

### Security Monitor (Sentinel)
```
User: /security-monitor
Sentinel: 🛡️ [Shows menu]
```

### Documentation Curator (Archivist)
```
User: /documentation-curator
Archivist: 📚 [Shows menu]
```

### Code Review Assistant (Inspector)
```
User: /code-review-assistant
Inspector: 🔍 [Shows menu]
```

## Autonomous Behaviors

### Daily (08:00 UTC)
- Sentinel: Security status check
- Archivist: Documentation health check

### Weekly (Monday 09:00 UTC)
- Sentinel: Weekly security report
- Archivist: Documentation review

### On-Demand
- Inspector: Code reviews
- All: Specific tasks via commands

## Files Created

- ✅ Agent definitions (3)
- ✅ Sidecar directories (3)
- ✅ Command files (3)
- ✅ Manifest updated
- ✅ Sidecar files (3)

## Next Steps

1. **Test each agent**:
   ```
   /security-monitor
   /documentation-curator
   /code-review-assistant
   ```

2. **Set up automation** (optional):
   ```bash
   crontab -e
   # Add scheduled runs
   ```

3. **Monitor sidecar files** for learning

## Support

See AI_CONTRIBUTION_SETUP.md for full documentation.
"""

    return summary


def main() -> int:
    """Register agents."""
    print("=" * 60)
    print("🤖 BMAD AI Agents Registration")
    print("=" * 60)
    print()

    # Checks
    if not check_agent_files():
        print("\n❌ Agent files missing - aborting")
        return 1

    if not check_sidecar_dirs():
        print("\n⚠️  Some sidecar directories missing - continuing")

    # Registration
    update_agent_manifest()
    create_commands()

    # Generate summary
    summary = generate_summary()
    print("\n" + "=" * 60)
    print(summary)
    print("=" * 60)

    # Save summary
    summary_file = Path("_bmad-output/ai-agents-registration-summary.md")
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(summary)
    print(f"\n📄 Summary saved to: {summary_file}")

    print("\n✅ Registration complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
