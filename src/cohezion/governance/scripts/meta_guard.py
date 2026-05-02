import ast
import os
from pathlib import Path

from cohezion.governance.guardian import Guardian


class MetaGuard(Guardian):
    """
    Guard to audit the Guardian system itself (Meta-Dogfooding).

    Invariants:
    1. Every script in governance/scripts must inherit from Guardian.
    2. No hardcoded PROJECT_ROOT or PROJECT_DIR strings (must use self.project_root).
    3. (Removed) Dynamic modularity is now in effect.
    """

    def __init__(self):
        super().__init__("meta-guard")
        self.scripts_dir = self.project_root / "src/cohezion/governance/scripts"

    def scan_guard_file(self, filepath: Path):
        try:
            content = filepath.read_text()
            tree = ast.parse(content)
        except:
            return

        # 1. Check inheritance
        has_guardian_base = False
        class_name = ""
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                for base in node.bases:
                    if (isinstance(base, ast.Name) and base.id == "Guardian") or (
                        isinstance(base, ast.Attribute) and base.attr == "Guardian"
                    ):
                        has_guardian_base = True
                        break

        if class_name and not has_guardian_base:
            self.log_violation(
                f"Class '{class_name}' does not inherit from Guardian.", location=str(filepath)
            )

        # 2. Check for hardcoded roots
        hardcoded_patterns = ["PROJECT_ROOT =", "ROOT_DIR =", "BASE_DIR ="]
        for i, line in enumerate(content.splitlines()):
            if any(p in line for p in hardcoded_patterns):
                if "self.project_root" not in line and "Path(__file__)" in line:
                    self.log_violation(
                        "Hardcoded project root detected. Use 'self.project_root' instead.",
                        location=f"{filepath}:{i + 1}",
                    )

    def run(self, auto_heal: bool = False) -> bool:
        if not self.scripts_dir.exists():
            return True

        for root, _, files in os.walk(self.scripts_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__") and file != "guardian_cli.py":
                    self.scan_guard_file(Path(root) / file)

        return len(self.violations) == 0


if __name__ == "__main__":
    guard = MetaGuard()
    success = guard.run()
    guard.report()
    if not success:
        import sys

        sys.exit(1)
