#!/usr/bin/env python3
"""Identify top untested modules (>200 LOC, 0 tests) in src/cohezion/."""

import os
import ast


def count_loc(filepath):
    """Count non-blank, non-comment lines in a Python file."""
    with open(filepath, "r") as fh:
        src_txt = fh.read()
    try:
        tree = ast.parse(src_txt)
        return len(tree.body)
    except SyntaxError:
        count = len([l for l in src_txt.split("\n") if l.strip() and not l.strip().startswith("#")])
        return count


def module_has_tests(mod_path, tests_root):
    """Heuristic: does a test file exist with the pattern *test*mod* or mod/ ?"""
    parts = mod_path.replace(".py", "").replace("/", ".")
    for root, _dirs, files in os.walk(tests_root):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            # Normalize test file to module name
            rel_test = os.path.join(root, fname).replace(tests_root + "/", "")
            test_mod_name = rel_test.replace("/", ".").removesuffix(".py")
            # Check if this test references our module at all
            test_path = os.path.join(root, fname)
            try:
                with open(test_path, "r") as f2:
                    content = f2.read()
                if parts in content or "cohezion." + parts.replace(".py", "") in content:
                    return True
            except Exception:
                pass
    return False


def main():
    src_root = os.path.join(os.environ.get("HOME", ""), "dev", "cohezion", "src", "cohezion")
    tests_root = os.path.join(os.environ.get("HOME", ""), "dev", "cohezion", "tests")

    results = []
    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".mypy_cache")]
        for f in files:
            if not f.endswith(".py"):
                continue
            fp = os.path.join(root, f)
            rel_path = os.path.relpath(fp, src_root)
            mod_name = rel_path.replace(os.sep, ".").removesuffix(".py")

            # Count LOC via ast-based lines of code (stat stmts won't work well - use simple line count)
            with open(fp, "r") as fh:
                lines = [l for l in fh.readlines() if l.strip() and not l.strip().startswith("#")]
            loc = len(lines)

            covered = module_has_tests(mod_name, tests_root)
            results.append((loc, mod_name, covered))

    # Filter >200 LOC and untested
    untested = [(l, m, c) for l, m, c in results if l > 200 and not c]
    untested.sort(key=lambda x: -x[0])

    print(f"Total modules scanned: {len(results)}")
    print(f"Untested (>200 LOC): {len(untested)}")
    print()
    for loc, mod, _ in untested[:10]:
        print(f"  {loc:>6} LOC  {mod}")


if __name__ == "__main__":
    main()
