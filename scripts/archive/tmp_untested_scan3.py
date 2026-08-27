import glob
import re


src_mods = {}
for f in glob.glob("src/cohezion/**/*.py", recursive=True):
    mod = f[4:-3].replace("/", ".")
    with open(f) as fh:
        lines = sum(1 for _ in fh)
    if lines > 200:
        src_mods[mod] = lines

tested = set()
for f in glob.glob("tests/**/*.py", recursive=True):
    with open(f) as fh:
        txt = fh.read()
    for m in re.findall(r"from\s+([\w.]+)", txt):
        tested.add(m)
    for m in re.findall(r"import\s+([\w.]+)", txt):
        tested.add(m)

# strict: the first N dotted segments of test import must exactly match the module
#  e.g. test import cohezion.benchmarks.benchmark_suite counts for that module.
#  and test import cohezion.benchmarks counts for cohezion.benchmarks but not for submodules.
# We also allow a test file named test_<mod_last_part>.py in a dir matching the module path.


def is_tested(mod):
    parts = mod.split(".")
    for t in tested:
        tp = t.split(".")
        # exact match or test import is a prefix of module (import of a package containing mod)
        # We only count if test imports either the exact module or a direct parent package.
        if t == mod:
            return True
        if len(tp) < len(parts) and ".".join(parts[: len(tp)]) == t:
            return True
    # check test file path heuristic
    mod_path = mod.replace(".", "/")
    possible = [
        f"tests/{mod_path}/test_*.py",
        f"tests/test_{mod_path.split('/')[-1]}.py",
    ]
    for pat in possible:
        if glob.glob(pat, recursive=True):
            return True
    return False


untested = []
for mod in sorted(src_mods, key=lambda m: -src_mods[m]):
    if not is_tested(mod):
        untested.append((src_mods[mod], mod))

for loc, mod in untested[:10]:
    print(f"{loc:5d} {mod}")
