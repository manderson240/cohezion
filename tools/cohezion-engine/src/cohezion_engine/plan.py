"""Plan file lifecycle management for cohezion-engine."""
import json
import re
from pathlib import Path

from cohezion_engine.session import get_session_dir


def parse_plan_frontmatter(plan_path: Path) -> dict:
    """Parse simple key: value frontmatter from a plan file.

    Returns a dict of field name -> value strings. Returns {} if file not found.
    """
    if not plan_path.exists():
        return {}

    fields = {}
    for line in plan_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Only capture known plan header fields
            if key in ("Status", "Approved", "Iterations", "Worktree", "Created"):
                fields[key] = value
        # Stop at the first blank line after headers (body starts)
        if not line and fields:
            break
    return fields


def register_plan(path: str, status: str, base_dir: Path | None = None) -> Path:
    """Associate a plan with the current session.

    Stores a plan.json in the session directory.
    Returns the path to the plan.json file.
    """
    session_dir = get_session_dir(base_dir)
    plan_json = session_dir / "plan.json"
    data = {"path": path, "registered_status": status}
    plan_json.write_text(json.dumps(data, indent=2))
    return plan_json


def get_plan_status(base_dir: Path | None = None) -> dict | None:
    """Return current plan info for this session, including parsed frontmatter.

    Returns None if no plan has been registered.
    """
    session_dir = get_session_dir(base_dir)
    plan_json = session_dir / "plan.json"
    if not plan_json.exists():
        return None

    data = json.loads(plan_json.read_text())
    plan_path = Path(data["path"])
    frontmatter = parse_plan_frontmatter(plan_path)
    data["frontmatter"] = frontmatter
    return data
