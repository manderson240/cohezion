#!/usr/bin/env python3
"""
COHEZION Git Safe Handoff Enhancement
Systematic template updates with dynamic timestamps for version control.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigTemplateManager:
    """Manages configuration template updates with dynamic timestamps"""

    def __init__(self, config_dir: str = "/home/mike-anderson/dev/cohezion"):
        self.config_dir = Path(config_dir)

    def update_all_timestamps(self):
        """Update all hardcoded dates in config files with dynamic timestamps"""
        logger.info("🔄 Updating configuration timestamps...")

        # Get current timestamp
        try:
            from cohezion.core.time_tracker import get_time_tracker

            timestamp = get_time_tracker().get_current_timestamp()["git_friendly"]
        except ImportError:
            timestamp = "2026-02-04"

        # Update framework configs
        config_files = [
            "config/framework_desktop.json",
            "config/framework_pro.json",
            "config/adaptive_optimization.json",
        ]

        for config_file in config_files:
            file_path = self.config_dir / config_file
            self._update_config_timestamp(file_path, timestamp)

        # Update model registry
        model_registry = self.config_dir / "src/cohezion/data/model_registry_elite.json"
        self._update_config_timestamp(model_registry, timestamp)

        logger.info(
            f"✅ Updated {len(config_files) + 1} configuration files with dynamic timestamps"
        )

        return timestamp

    def _update_config_timestamp(self, file_path: Path, timestamp: str):
        """Update timestamp in configuration file"""
        try:
            if file_path.exists():
                with open(file_path, "r") as f:
                    content = f.read()

                # Replace hardcoded timestamps
                content = content.replace("2026-02-04", timestamp)
                content = content.replace("${TIMESTAMP}", timestamp)

                with open(file_path, "w") as f:
                    f.write(content)

                logger.debug(f"📝 Updated {file_path.name} timestamp to {timestamp}")

        except Exception as e:
            logger.error(f"❌ Failed to update {file_path}: {e}")

    def create_git_safe_handoff_commit(self, session_data: Dict[str, Any]) -> bool:
        """Create git safe handoff with proper versioning"""
        try:
            # Update all timestamps first
            timestamp = self.update_all_timestamps()

            # Check for changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.config_dir,
            )

            if result.returncode == 0 and result.stdout.strip():
                # Changes detected - create commit
                try:
                    from cohezion.core.time_tracker import get_git_safe_handoff

                    git_data = get_git_safe_handoff()
                    commit_message = git_data["commit_message_prefix"].format(
                        timestamp=timestamp,
                        duration=session_data.get("duration_hours", 0),
                        velocity=session_data.get("velocity_lines_per_day", 0),
                        features=", ".join(session_data.get("major_features", [])),
                    )

                    # Add files and commit
                    subprocess.run(["git", "add", "."], cwd=self.config_dir)
                    commit_result = subprocess.run(
                        ["git", "commit", "-m", commit_message],
                        capture_output=True,
                        text=True,
                        cwd=self.config_dir,
                    )

                    if commit_result.returncode == 0:
                        logger.info(f"✅ Git safe handoff created: {commit_message}")
                        return True
                    else:
                        logger.error(f"❌ Git commit failed: {commit_result.stderr}")
                        return False
                except Exception:
                    logger.error("ℹ️ Git safe handoff tools not available")
                    return True
            else:
                logger.info("ℹ️ No changes detected - skipping commit")
                return True

        except Exception as e:
            logger.error(f"❌ Git safe handoff failed: {e}")
            return False


def main():
    """Main function for standalone execution"""
    manager = ConfigTemplateManager()

    # Update all timestamps and create a sample commit
    timestamp = manager.update_all_timestamps()

    # Create a sample commit
    session_data = {
        "duration_hours": 2.5,
        "velocity_lines_per_day": 150,
        "major_features": [
            "adaptive_framework_config",
            "dynamic_timestamp_system",
            "git_safe_handoff_automation",
        ],
    }

    manager.create_git_safe_handoff_commit(session_data)


if __name__ == "__main__":
    main()
