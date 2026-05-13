import abc
import logging
import os
import re
import sys
from pathlib import Path


# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Guardian(abc.ABC):
    """Base class for all Cohezion Guards."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self.project_root = PROJECT_ROOT
        self.violations: list[str] = []

    @abc.abstractmethod
    def run(self, auto_heal: bool = False) -> bool:
        """Execute the guard logic. Returns True if successful (no violations)."""
        pass

    def log_violation(self, message: str, location: str | None = None, fatal: bool = True):
        """Record a violation."""
        full_msg = f"{location}: {message}" if location else message
        if fatal:
            self.violations.append(full_msg)
            self.logger.error(f"FATAL Violation: {full_msg}")
        else:
            self.logger.warning(f"Non-Fatal Violation: {full_msg}")

    def report(self):
        """Print a summary of violations."""
        if self.violations:
            self.logger.error(f"Found {len(self.violations)} violations in {self.name}:")
            for v in self.violations:
                print(f"  [!] {v}")
        else:
            self.logger.info(f"✓ {self.name} checks passed.")


class GuardianRegistry:
    """Registry to manage and run all Cohezion Guards."""

    def __init__(self):
        self.guards: list[Guardian] = []

    def register(self, guard: Guardian):
        self.guards.append(guard)

    def discover_and_register_all(self, scripts_dir: Path | None = None):
        """Dynamically discover and register all Guardian subclasses in the given directory."""
        import importlib.util
        import inspect

        if scripts_dir is None:
            scripts_dir = PROJECT_ROOT / "src" / "cohezion" / "governance" / "scripts"

        if not scripts_dir.exists():
            logging.warning(f"Scripts directory not found: {scripts_dir}")
            return

        for filename in os.listdir(scripts_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"cohezion.governance.scripts.{filename[:-3]}"
                filepath = scripts_dir / filename

                try:
                    spec = importlib.util.spec_from_file_location(module_name, filepath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)

                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if issubclass(obj, Guardian) and obj is not Guardian and obj.__module__ == module_name:
                                try:
                                    self.register(obj())
                                except Exception as e:
                                    logging.error(f"Failed to instantiate Guardian {name}: {e}")
                except Exception as e:
                    logging.error(f"Failed to load module {module_name}: {e}")

    def run_all(self, auto_heal: bool = False) -> bool:
        """Run all registered guards. Returns True if ALL pass."""
        success = True
        for guard in self.guards:
            if not guard.run(auto_heal=auto_heal):
                success = False
            guard.report()
        return success


def slugify(text: str) -> str:
    """Utility to slugify strings for cross-platform compatibility."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def get_guardian_cli():
    """Simple CLI runner for the guardian system."""
    import argparse

    parser = argparse.ArgumentParser(description="Cohezion Guardian System")
    parser.add_argument("--all", action="store_true", help="Run all guards")
    parser.add_argument("--heal", action="store_true", help="Attempt to auto-heal violations")
    parser.add_argument("--guard", type=str, help="Run a specific guard by name")

    return parser.parse_args()
