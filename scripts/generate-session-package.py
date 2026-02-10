#!/usr/bin/env python3
"""Auto-generate Session startup packages for minimal token overhead."""

import argparse
import subprocess
from datetime import datetime
from pathlib import Path

def get_recent_commits(n=5):
    try:
        result = subprocess.run(["git", "log", "--oneline", f"-{n}"],
            capture_output=True, text=True, cwd="/home/mike-anderson/dev/cohezion")
        return result.stdout.strip().split("\n") if result.stdout else ["(no commits)"]
    except:
        return ["(unable to fetch)"]

def generate_package(session_id, phase):
    recent = get_recent_commits(3)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""# Session {session_id} Startup Package ⚡

Generated: {now} | Phase: {phase}

## Quick Start (5 min)
```bash
SESSION_ID="{session_id}"
git worktree add ~/dev/cohezion-session-${{SESSION_ID}} -b session-${{SESSION_ID}}-{phase}
cd ~/dev/cohezion-session-${{SESSION_ID}}
./scripts/validate-session-setup.sh
uv run pytest tests/ -q
```

## Recent Work
{chr(10).join(recent)}

## This Session
Complete Phase: {phase}
Reference: STRATEGIC_OPTIMIZATION_PLAN.md
Success: Feature complete + tests + summary

Ready! Copy Quick Start and go. 🚀
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--phase", type=str, required=True)
    args = parser.parse_args()
    pkg = generate_package(args.session, args.phase)
    Path(f"SESSION_{args.session}_STARTUP_PACKAGE.md").write_text(pkg)
    print(f"✅ Generated SESSION_{args.session}_STARTUP_PACKAGE.md")
