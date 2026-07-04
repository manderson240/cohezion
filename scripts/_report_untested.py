#!/usr/bin/env python3
"""Identify top untested modules by LOC."""
import os, ast

repo = 'src/cohezion'
test_repo = 'tests'

all_test_files = []
for root, dirs, files in os.walk(test_repo):
    for f in files:
        if f.endswith('.py'):
            all_test_files.append(os.path.join(root, f))

import_refs = set()
for tf in all_test_files:
    try:
        with open(tf) as fh:
            content = fh.read()
        tree = ast.parse(content, filename=tf)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                import_refs.add((node.module, tf))
    except Exception:
        pass

def count_loc(path):
    if not os.path.exists(path):
        return 0
    with open(path) as fh:
        return len(fh.readlines())

py_files = []
for root, dirs, files in os.walk(repo):
    for f in files:
        if f.endswith('.py'):
            py_files.append(os.path.join(root, f))

results = []
for fp in py_files:
    loc = count_loc(fp)
    rel = fp[len(repo)+1:]

    covered = False
    mod_name = 'cohezion.' + rel.replace('/', '.').replace('.py', '')
    for imp_mod, tf in import_refs:
        if mod_name == imp_mod or mod_name.startswith(imp_mod + '.') or imp_mod.startswith(mod_name):
            covered = True
            break

    results.append((loc, fp, covered))

results.sort(key=lambda x: -x[0])

for i, (loc, fp, covered) in enumerate(results):
    if loc > 200 and not covered:
        tag = "UNTESTED"
        print(f"{i}. [{tag}] {fp} ({loc} LOC)")
    elif loc <= 250:
        break

print(f"\nTotal untested modules >200 LOC: {sum(1 for l,f,c in results if l>200 and not c)}")
