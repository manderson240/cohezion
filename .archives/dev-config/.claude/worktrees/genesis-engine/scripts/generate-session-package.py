#!/usr/bin/env python3
"""Generate personalized Session XX Startup Package."""

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def get_recent_commits(n: int = 5) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{n}"],
            capture_output=True,
            text=True,
            cwd="/home/mike-anderson/dev/cohezion",
        )
        return result.stdout.strip().split("\n")
    except Exception:
        return ["(unable to fetch commits)"]


def generate_package(session_id: int, phase: str) -> str:
    recent_commits = get_recent_commits(3)
    now = datetime.now()

    package = f"""# Session {session_id} Startup Package ⚡

**Generated**: {now.strftime("%Y-%m-%d %H:%M:%S")}
**Phase**: {phase}
**Time to Read**: 2 minutes | **Time to Setup**: 5 minutes

---

## 🚀 Quick Start

```bash
SESSION_ID="{session_id}"
PHASE="{phase}"

git worktree add ~/dev/cohezion-session-${{SESSION_ID}} -b session-${{SESSION_ID}}-${{PHASE}}
cd ~/dev/cohezion-session-${{SESSION_ID}}
./scripts/validate-session-setup.sh
uv run pytest tests/ -q
```

---

## ✅ Pre-Work Checklist

- [ ] Worktree created and validated
- [ ] Baseline tests passing
- [ ] MEMORY.md reviewed
- [ ] Recent commits understood

---

## 📖 Recent Work

{chr(10).join(recent_commits)}

---

## 🎯 This Session

**Phase**: {phase}
**Expected**: See STRATEGIC_OPTIMIZATION_PLAN.md Phase A
**Success**: Feature complete + tests passing + summary created

---

## 📚 Quick Reference

- CLAUDE.md: Project rules
- SESSION_TEMPLATE.md: Workflow
- GIT_WORKTREE_ENFORCEMENT.md: Git help
- MEMORY.md: Architecture

You're ready! Copy Quick Start above and go. 🚀
"""
    return package


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--phase", type=str, required=True)
    args = parser.parse_args()

    package = generate_package(args.session, args.phase)
    output_file = Path(f"/home/mike-anderson/dev/cohezion/SESSION_{args.session}_STARTUP_PACKAGE.md")
    output_file.write_text(package)
    print(f"✅ Generated: {output_file}")


if __name__ == "__main__":
    main()
