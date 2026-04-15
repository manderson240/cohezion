import ast
import os
from pathlib import Path
from typing import List, Tuple
from cohezion.governance.guardian import Guardian


class AsyncGuard(Guardian):
    """Guard to detect blocking I/O anti-patterns in async subsystems."""

    def __init__(self):
        super().__init__("async-guard")
        self.target_dirs = ["src/cohezion/api/", "src/cohezion/swarm/"]
        self.exclude_patterns = ["/tests/", "/scripts/", "test_"]
        self.blocking_calls = [
            "requests.get",
            "requests.post",
            "requests.put",
            "requests.delete",
            "requests.request",
            "time.sleep",
            "urllib.request",
        ]

    def scan_file(self, filepath: Path) -> List[Tuple[int, str]]:
        violations = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if not content:
                return []
            tree = ast.parse(content, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError):
            return []
        except Exception as e:
            self.logger.error(f"Error reading {filepath}: {e}")
            return []

        class AsyncVisitor(ast.NodeVisitor):
            def __init__(self, guard_instance):
                self.violations = []
                self.in_async_def = False
                self.guard = guard_instance

            def visit_AsyncFunctionDef(self, node):
                old = self.in_async_def
                self.in_async_def = True
                self.generic_visit(node)
                self.in_async_def = old

            def visit_Call(self, node):
                func = node.func
                call_path = []
                curr = func
                while isinstance(curr, ast.Attribute):
                    call_path.insert(0, curr.attr)
                    curr = curr.value
                if isinstance(curr, ast.Name):
                    call_path.insert(0, curr.id)

                full_call = ".".join(call_path)

                if any(
                    full_call == p or full_call.startswith(p + ".")
                    for p in self.guard.blocking_calls
                ):
                    self.violations.append((node.lineno, full_call))
                elif full_call == "sleep":
                    self.violations.append((node.lineno, "sleep (likely time.sleep)"))
                elif full_call == "open" and self.in_async_def:
                    self.violations.append((node.lineno, "blocking open() in async function"))

                self.generic_visit(node)

        visitor = AsyncVisitor(self)
        visitor.visit(tree)
        return visitor.violations

    def run(self, auto_heal: bool = False) -> bool:
        for target_dir in self.target_dirs:
            abs_target = self.project_root / target_dir
            if not abs_target.exists():
                continue

            for root, dirs, files in os.walk(abs_target):
                rel_root = os.path.relpath(root, self.project_root)
                if any(exclude in f"/{rel_root}/" for exclude in self.exclude_patterns):
                    continue

                for file in files:
                    if not file.endswith(".py"):
                        continue
                    if any(exclude in file for exclude in self.exclude_patterns):
                        continue

                    filepath = Path(root) / file
                    violations = self.scan_file(filepath)
                    for lineno, msg in violations:
                        self.log_violation(f"{msg}", location=f"{filepath}:{lineno}")

        return len(self.violations) == 0

if __name__ == "__main__":
    guard = AsyncGuard()
    success = guard.run()
    guard.report()
