import json
import logging
import os
import time
from pathlib import Path

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


# Configuration
SKILLS_DIR = "src/cohezion/skills"
REGISTRY_FILE = "src/cohezion/registry/skill_registry.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SkillWatchdog")


class SkillRegistrar(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            logger.info(f"Skill modified: {event.src_path}")
            self.update_skill(event.src_path)

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            logger.info(f"New skill detected: {event.src_path}")
            self.update_skill(event.src_path)

    def update_skill(self, file_path):
        try:
            content = Path(file_path).read_text()
            # Extract YAML frontmatter
            if content.startswith("---"):
                end_idx = content.find("---", 3)
                if end_idx != -1:
                    yaml_content = content[3:end_idx]
                    metadata = yaml.safe_load(yaml_content)

                    if metadata:
                        self.register_to_json(metadata, file_path)
            else:
                # Try pattern matching for old style
                pass

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

    def register_to_json(self, metadata, file_path):
        """Update the central registry JSON."""
        name = metadata.get("name") or Path(file_path).stem

        # Determine path relative to project root for portability
        try:
            rel_path = str(Path(file_path).resolve().relative_to(Path.cwd()))
        except ValueError:
            # Fallback if somehow outside cwd (symlinks etc)
            rel_path = file_path

        entry = {
            "name": name,
            "description": metadata.get("description", "No description"),
            "path": rel_path,
            "version": metadata.get("version", "0.1"),
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        try:
            data = {}
            if os.path.exists(REGISTRY_FILE):
                with open(REGISTRY_FILE) as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}

            data[name] = entry

            with open(REGISTRY_FILE, "w") as f:
                json.dump(data, f, indent=4)

            logger.info(f"Registered skill: {name}")

        except Exception as e:
            logger.error(f"Registry update failed: {e}")


if __name__ == "__main__":
    logger.info(f"Starting Skill Watchdog for {SKILLS_DIR}...")

    # Ensure registry dir exists
    Path(REGISTRY_FILE).parent.mkdir(parents=True, exist_ok=True)

    event_handler = SkillRegistrar()
    observer = Observer()
    observer.schedule(event_handler, SKILLS_DIR, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
