#!/usr/bin/env python3
"""Identify top untested modules (>200 LOC) in src/cohezion/.

A module is "untested" when no test file references it by:
  (a) importing the exact dotted module name from cohezioN package, OR
  (b) existing in a tests/ subdirectory whose basename matches the source file.

This script uses broad-package imports to determine coverage, then reports
the largest gaps. It is intended as a periodic health-check output for 
cron-based repo maintenance cycles.

Usage: python3 scripts/report_untested_modules.py
"""
import os, ast

REPO = 'src/cohezion'
TEST_REPO = 'tests'


def count_loc(path):
    """Return line count for a source file."""
    if not os.path.exists(path):
        return 0
    try:
        with open(path) as fh:
            return len(fh.readlines())
    except Exception:
        return 0


def get_all_py_files(root_dir):
    """Walk dir and collect .py files."""
    result = []
    for dirpath, _, filenames in os.walk(root_dir):
        if '__pycache__' in dirpath:
            continue
        for fname in filenames:
            if fname.endswith('.py'):
                result.append(os.path.join(dirpath, fname))
    return result


def get_test_imports(test_files):
    """Parse all test files and collect ImportFrom module names + paths."""
    refs = []
    for tf in sorted(test_files):
        try:
            with open(tf) as fh:
                content = fh.read()
            tree = ast.parse(content, filename=tf)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    refs.append((node.module, tf))
        except Exception:
            pass
    return refs


def is_tested_by_import(rel_path, test_imports):
    """Check whether any test file imports this module specifically."""
    mod_name = 'cohezion.' + rel_path.replace('/', '.').replace('.py', '')

    for imp_mod, _ in test_imports:
        # Skip bare "cohezion" — too broad to count as real coverage signal.
        if imp_mod == 'cohezion':
            continue
        # Direct match or parent-of-child relationship
        if mod_name == imp_mod:
            return True
        if mod_name.startswith(imp_mod + '.'):
            # Test imports a submodule that encompasses this file
            return True
        if imp_mod.startswith(mod_name):
            # This import is our module or something inside it
            return True
    return False


def is_tested_by_filename(rel_path, test_files):
    """Check whether any test file exists with matching basename."""
    fname_base = os.path.basename(rel_path).replace('.py', '')
    rel_parts = rel_path.split('/')

    for tf in test_files:
        tf_name = os.path.basename(tf).replace('.py', '')
        # Patterns: test_foo.py, foo_test.py
        if tf_name == 'test_' + fname_base or tf_name == fname_base + '_test':
            return True

    # Also check tests/<package>/subdir/test_module.py patterns
    if len(rel_parts) > 2:
        expected_in_tests = os.path.join(TEST_REPO, *rel_parts[:-1]) + '.py'
        if os.path.isfile(expected_in_tests):
            return True

    return False


def main():
    source_files = get_all_py_files(REPO)
    test_raw = []
    for dirpath, _, filenames in sorted(os.walk(TEST_REPO)):
        for fname in sorted(filenames):
            if fname.endswith('.py'):
                test_raw.append(os.path.join(dirpath, fname))

    test_imports = get_test_imports(test_raw)
    total_modules = len(source_files)

    results = []
    for src_fp in source_files:
        loc = count_loc(src_fp)
        rel = src_fp[len(REPO)+1:]

        tested = is_tested_by_filename(rel, test_raw) or \
                 is_tested_by_import(rel, test_imports)

        if not tested and loc > 200:
            results.append((loc, src_fp))

    results.sort(key=lambda x: -x[0])

    print(f"Total modules scanned: {total_modules}")
    print(f"Test files indexed: {len(test_raw)}")
    print(f"Untested modules (>200 LOC): {len(results)}")
    print()

    top = min(3, len(results))
    for i, (loc, fp) in enumerate(results[:top]):
        print(f"  {i+1}. [{loc} LOC] {fp}")


if __name__ == '__main__':
    main()
