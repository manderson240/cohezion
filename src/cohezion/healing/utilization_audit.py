"""
Utilization Audit Script.

Analyzes:
1. Skill usage in codebase
2. MCP server existence
3. Tool usage
"""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path


logger = logging.getLogger(__name__)


def analyze_utilization():
    base_path = Path("src/cohezion")
    skills_path = base_path / "skills"

    # 1. Get all skills
    skills = [f.stem.replace("_PRIME", "") for f in skills_path.glob("*.md")]

    # 2. Search codebase for skill usage
    skill_usage = dict.fromkeys(skills, 0)

    for root, _dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py") or file.endswith(".md"):
                path = Path(root) / file
                if "skills" in str(path):
                    continue

                try:
                    content = path.read_text()
                    for skill in skills:
                        if skill in content:
                            skill_usage[skill] += 1
                except (OSError, UnicodeDecodeError) as e:
                    logger.debug("Failed to read %s: %s", path, e)

    # 3. Check MCP Servers
    mcp_registry_path = base_path / "mcp" / "mcp_registry.json"
    mcp_status = {}
    if mcp_registry_path.exists():
        with open(mcp_registry_path) as f:
            registry = json.load(f)

        for server in registry.get("internal", []):
            path = base_path / server.get("path", "")
            mcp_status[server["name"]] = "Exists" if path.exists() else "MISSING"

    # Generate Report
    unused_skills = [s for s, c in skill_usage.items() if c == 0]
    used_skills = [s for s, c in skill_usage.items() if c > 0]

    report = f"""# Cohezion Utilization Audit
**Timestamp:** {datetime.now(UTC).isoformat()}

## MCP Server Status
| Server | Status |
|--------|--------|
"""
    for name, status in mcp_status.items():
        report += f"| {name} | {status} |\n"

    report += f"""
## Skill Utilization
- **Total Skills:** {len(skills)}
- **Used Skills:** {len(used_skills)}
- **Unused Skills:** {len(unused_skills)}

### Unused Skills (Opportunities)
"""
    for skill in unused_skills:
        report += f"- {skill}\n"

    print(report)

    # Save Report
    output_dir = base_path / "knowledge_graph" / "audits"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"utilization_audit_{int(datetime.now().timestamp())}.md"
    report_path.write_text(report)
    print(f"\nSaved to {report_path}")


if __name__ == "__main__":
    analyze_utilization()
