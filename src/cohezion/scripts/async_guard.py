import ast
import os
import sys


# Directories to scan for async anti-patterns
TARGET_DIRS = ["src/cohezion/api/", "src/cohezion/swarm/"]

# Patterns to exclude from scanning (e.g., tests, designated sync scripts)
EXCLUDE_PATTERNS = ["/tests/", "/scripts/", "test_"]

# Anti-patterns to look for
BLOCKING_CALLS = [
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.delete",
    "requests.request",
    "time.sleep",
    "urllib.request",
]


class AsyncGuard(ast.NodeVisitor):
    def __init__(self, filepath):
        self.filepath = filepath
        self.violations = []
        self.in_async_def = False

    def visit_AsyncFunctionDef(self, node):
        old_in_async_def = self.in_async_def
        self.in_async_def = True
        self.generic_visit(node)
        self.in_async_def = old_in_async_def

    def visit_Call(self, node):
        func = node.func
        call_path = []

        # Resolve the call path, e.g., requests.get -> ["requests", "get"]
        curr = func
        while isinstance(curr, ast.Attribute):
            call_path.insert(0, curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            call_path.insert(0, curr.id)

        full_call = ".".join(call_path)

        # Check against anti-patterns
        if any(
            full_call == pattern or full_call.startswith(pattern + ".")
            for pattern in BLOCKING_CALLS
        ):
            self.violations.append((node.lineno, full_call))
        elif full_call == "sleep":  # Common if: from time import sleep
            self.violations.append((node.lineno, "sleep (likely time.sleep)"))
        elif full_call == "open" and self.in_async_def:
            # Special case: blocking open() inside an async function
            self.violations.append((node.lineno, "blocking open() in async function"))

        self.generic_visit(node)


def scan_file(filepath):
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
            if not content:
                return []
            tree = ast.parse(content, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        # Skip files that can't be parsed as Python
        return []
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

    visitor = AsyncGuard(filepath)
    visitor.visit(tree)
    return visitor.violations


def main():
    found_any = False
    project_root = os.getcwd()

    for target_dir in TARGET_DIRS:
        # Resolve absolute path to handle walk correctly if run from different dir
        abs_target = os.path.join(project_root, target_dir)
        if not os.path.exists(abs_target):
            continue

        for root, _dirs, files in os.walk(abs_target):
            # Check if current root matches any exclude pattern
            rel_root = os.path.relpath(root, project_root)
            if any(exclude in f"/{rel_root}/" for exclude in EXCLUDE_PATTERNS):
                continue

            for file in files:
                if not file.endswith(".py"):
                    continue
                if any(exclude in file for exclude in EXCLUDE_PATTERNS):
                    continue

                filepath = os.path.join(root, file)
                violations = scan_file(filepath)
                if violations:
                    found_any = True
                    for lineno, msg in violations:
                        # Use relative path for cleaner output
                        rel_path = os.path.relpath(filepath, project_root)
                        print(f"VIOLATION: {rel_path}:{lineno}: {msg}")

    if found_any:
        print("\n[!] Async Guard: Blocking I/O anti-patterns detected in async paths.")
        print("[!] Please use non-blocking alternatives (e.g., httpx, aiohttp, aiofiles).")
        sys.exit(1)

    print("✓ Async Guard: No blocking I/O anti-patterns found.")


if __name__ == "__main__":
    main()
