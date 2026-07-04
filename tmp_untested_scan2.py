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

untested = []
for mod in sorted(src_mods, key=lambda m: -src_mods[m]):
    has = any(mod.startswith(t) or t.startswith(mod) for t in tested)
    if not has:
        untested.append((src_mods[mod], mod))

for loc, mod in untested[:10]:
    print(f"{loc:5d} {mod}")
