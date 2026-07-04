#!/usr/bin/env python3
"""Repo health check - find untested modules >200 LOC."""

from pathlib import Path


src = Path("src/cohezion")
tests_path = Path("tests")


def count_loc(f: Path) -> int:
    try:
        loc = 0
        with open(f) as fh:
            for line in fh:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    loc += 1
    except Exception:
        loc = 0
    return loc


def get_test_files() -> list[str]:
    """Return basenames of test files."""
    result = []
    for f in tests_path.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        result.append(str(f))
    return result


# Build set of possible modules that could map to each test file
def can_test_module(test_file: str, candidate_module_parts: list[str]) -> bool:
    """Check whether a test file likely tests a given source module."""
    # Direct mapping: src/cohezion/foo/bar.py -> tests/test_foo_bar.py or tests/foo/test_bar.py
    tf = Path(test_file).name  # e.g. test_abc.py or foo/test_xyz.py

    candidates_for_test = []

    # Strategy 1: Extract module name from test and reverse-map to source path
    rel = Path(test_file).relative_to("tests")
    parts = list(rel.parts)[:-1] if rel.suffix == ".py" else list(rel.parts)
    dirname_parts = parts

    # Build all possible source paths this test could cover:
    for depth in range(len(dirname_parts), 0, -1):
        candidate_source_parts = dirname_parts[:depth] + [rel.stem.replace("test_", "")]
        src_relative = Path(*candidate_source_parts) / (
            rel.stem.replace("test_", "").replace("_", "/") + ".py"
        )

    # Strategy: just check if any file in tests would cover this source path
    test_stem = rel.stem  # "test_foo_bar" -> "foo_bar" or module is "bar"
    module_base = test_stem.replace("test_", "")

    # Check by stripping various prefixes from the relative src path to see if it matches
    src_rel_list = list(candidate_module_parts)  # ['some', 'module.py']

    for i in range(len(src_rel_list)):
        suffix = ".".join(src_rel_list[i:])
        check_name = suffix.replace(".py", "").replace("/", "_")
        if check_name == module_base:
            return True
        # Also try with "test_" prepended
        if not module_base.startswith("test_"):
            pass

    # Direct exact match: rel parts minus 'tests' -> same as src relative
    # e.g. tests/unit/test_utils.py -> candidate = utils (drop 'src/cohezion')
    check_name = rel.stem.replace("test_", "")

    for start in range(len(src_rel_list) - 1, -1, -1):
        sub = ".".join(src_rel_list[start:]).replace(".py", "").replace(".", "_")
        if sub == check_name:
            return True

    # If src file is deep (e.g., agents/architect_agent.py), test could be tests/test_architect_agent.py
    simple_stem = Path(candidate_module_parts[-1]).stem.replace(".py", "")
    if simple_stem in module_base or module_base.endswith(simple_stem):
        return True

    # Replace dots with slashes for deeper matching
    src_full = "/".join(p.replace(".py", "").replace(".", "_") for p in candidate_module_parts)
    # Lowercase comparison
    if check_name.lower() in src_full.lower():
        return True

    return False


def main():
    test_files = get_test_files()

    modules = []
    for f in sorted(src.rglob("*.py")):
        if "__pycache__" in str(f) or "conftest.py" in str(f):
            continue

        loc = count_loc(f)
        rel_parts = list(f.relative_to(src).parts)

        tested = False
        for tf in test_files:
            try:
                if can_test_module(tf, rel_parts):
                    tested = True
                    break
            except Exception:
                continue

        modules.append((loc, tested, str(f.relative_to("src"))))

    # Sort by LOC descending
    modules.sort(key=lambda x: -x[0])

    print("=== Top 20 modules by LOC (all) ===")
    for loc, tested, path in modules[:20]:
        mark = " [HAS TEST]" if tested else ""
        print(f"  {loc:>6} LOC | {path}{mark}")

    # Untested > 200 LOC
    print("\n=== Untested modules (>200 LOC) ===")
    untested = [(loc, path) for loc, tested, path in modules if not tested and loc > 200]
    if untested:
        for i, (loc, path) in enumerate(untested[:3], 1):
            print(f"  {i}. {path} ({loc} LOC)")
    else:
        # List top candidates even if <= 200 but truly untested with high LOC
        all_untested = [(loc, path) for loc, tested, path in modules if not tested]
        print("  None > 200 LOC.")
        print(
            f"  (All {len(all_untested)} source files have at least partial test coverage or are < 200 LOC)"
        )


if __name__ == "__main__":
    main()
