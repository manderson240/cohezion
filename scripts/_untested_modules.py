import ast, os, pathlib

COH_ROOT = '/home/mike-anderson/dev/cohezion'
SRC_ROOT = pathlib.Path(COH_ROOT) / 'src' / 'cohezion'
TESTS_ROOT = pathlib.Path(COH_ROOT) / 'tests'


def walk_tests(root):
    files = []
    for rootdir, dirs, files_list in os.walk(root):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files_list:
            if f.endswith('.py'):
                files.append(pathlib.Path(rootdir) / f)
    return sorted(files)


test_files = walk_tests(TESTS_ROOT)

# Build (stem, full_dotted_module) from each test file
coverage_entries = []
for tf in test_files:
    rel_tests = str(tf.relative_to(COH_ROOT))  # tests/repo_health/test_enforcement.py
    parts = pathlib.Path(rel_tests).parts

    p_idx = None
    for i, p in enumerate(parts):
        if p == 'tests':
            p_idx = i
            break
    if p_idx is None:
        continue
    sub_parts = list(parts[p_idx + 1:])

    test_mod_subdir = '.'.join(p for p in sub_parts[:-1] if p != '__init__')
    stem = os.path.splitext(sub_parts[-1])[0]
    if stem.startswith('test_'):
        stem = stem[5:]

    expected_full = (test_mod_subdir + '.' + stem) if test_mod_subdir else stem
    coverage_entries.append((stem, expected_full))


# Count LOC and test coverage for each src module
mod_info = []
for pyfile in sorted(SRC_ROOT.rglob('*.py')):
    rel = str(pyfile.relative_to(SRC_ROOT))  # swarm/cost_aware_router.py
    try:
        with open(pyfile) as f:
            tree = ast.parse(f.read())
        loc = sum(1 for line in pyfile.open() if line.strip() and not line.strip().startswith('#'))
    except Exception:
        continue

    mod_stem = pathlib.Path(rel).stem  # cost_aware_router
    has_test = False
    for t_stem, t_full in coverage_entries:
        if t_stem == mod_stem:
            has_test = True
            break
        rel_dir = str(pathlib.Path(rel).parent)
        if rel_dir != '.' and len(t_full.split('.')) >= 2:
            src_parent_stem = pathlib.Path(rel_dir).stem
            if src_parent_stem in t_full and mod_stem in t_full:
                has_test = True
                break

    mod_info.append((rel, loc, has_test))

mod_info.sort(key=lambda x: -x[1])

print('=== Top untested modules (>200 LOC, 0 tests) ===')
count = 0
for rel, loc, has_test in mod_info:
    if loc > 200 and not has_test:
        count += 1
        print(f'{count}. {rel}: {loc} LOC - NO TESTS')
print(f'({count} total)')

print()
print('=== Largest modules (top 15) ===')
for rel, loc, has_test in mod_info[:15]:
    status = 'NO TEST' if not has_test else 'HAS TEST'
    print(f'  {loc:>5} LOC | {status:<8} | {rel}')
