#!/usr/bin/env python3
"""Git-safe handoff system for benchmark improvement project.

Provides checkpoint/commit system for token-efficient agent handoffs.
"""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class HandoffCheckpoint:
    """A checkpoint for agent handoff."""

    milestone: str
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    key_files: dict[str, str] = field(default_factory=dict)
    context_summary: str = ""
    decisions: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


class GitHandoff:
    """Git-based handoff system for agent continuity."""

    def __init__(self, project_root: str = "/home/mike-anderson/dev/cohezion"):
        self.project_root = Path(project_root)
        self.checkpoints_dir = self.project_root / ".handoffs"

    def create_checkpoint(self, checkpoint: HandoffCheckpoint) -> str:
        """Create a checkpoint file for handoff.

        Returns:
            Checkpoint file path
        """
        self.checkpoints_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{checkpoint.milestone}_{timestamp}.json"
        filepath = self.checkpoints_dir / filename

        with open(filepath, "w") as f:
            json.dump(checkpoint.__dict__, f, indent=2)

        # Also update latest pointer
        latest = self.checkpoints_dir / f"latest_{checkpoint.milestone}.json"
        with open(latest, "w") as f:
            json.dump(checkpoint.__dict__, f, indent=2)

        print(f"Checkpoint saved: {filepath}")
        return str(filepath)

    def commit_checkpoint(self, checkpoint: HandoffCheckpoint, message: str) -> str:
        """Commit checkpoint changes to git.

        Returns:
            Commit hash
        """
        # Stage changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.project_root,
            capture_output=True,
        )

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Commit warning: {result.stderr}")
            return ""

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        commit_hash = result.stdout.strip()[:8]
        print(f"Committed: {commit_hash} - {message}")
        return commit_hash

    def tag_milestone(self, milestone: str) -> None:
        """Tag current commit as milestone.

        Args:
            milestone: Milestone name (e.g., 'milestone-1-complete')
        """
        result = subprocess.run(
            ["git", "tag", "-a", milestone, "-m", f"Milestone: {milestone}"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"Tagged: {milestone}")
        else:
            print(f"Tag warning: {result.stderr}")

    def load_latest(self, milestone: str) -> HandoffCheckpoint | None:
        """Load latest checkpoint for a milestone.

        Args:
            milestone: Milestone name

        Returns:
            Checkpoint or None
        """
        latest = self.checkpoints_dir / f"latest_{milestone}.json"
        if not latest.exists():
            return None

        with open(latest) as f:
            data = json.load(f)

        return HandoffCheckpoint(**data)


def main():
    """CLI for handoff operations."""
    if len(sys.argv) < 2:
        print("Usage: handoff.py <create|commit|tag|load> [args...]")
        sys.exit(1)

    handoff = GitHandoff()
    command = sys.argv[1]

    if command == "create":
        milestone = sys.argv[2]
        checkpoint = HandoffCheckpoint(
            milestone=milestone,
            completed_tasks=sys.argv[3].split(",") if len(sys.argv) > 3 else [],
            pending_tasks=sys.argv[4].split(",") if len(sys.argv) > 4 else [],
            context_summary=sys.argv[5] if len(sys.argv) > 5 else "",
        )
        handoff.create_checkpoint(checkpoint)

    elif command == "commit":
        message = sys.argv[2]
        checkpoint = HandoffCheckpoint(
            milestone="current",
            context_summary=message,
        )
        handoff.commit_checkpoint(checkpoint, message)

    elif command == "tag":
        milestone = sys.argv[2]
        handoff.tag_milestone(milestone)

    elif command == "load":
        milestone = sys.argv[2]
        checkpoint = handoff.load_latest(milestone)
        if checkpoint:
            print(json.dumps(checkpoint.__dict__, indent=2))
        else:
            print(f"No checkpoint found for {milestone}")


if __name__ == "__main__":
    main()
