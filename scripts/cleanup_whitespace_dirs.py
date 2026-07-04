#!/usr/bin/env python3
import os
import shutil
from pathlib import Path


base = Path("/home/mike-anderson/dev/cohezio")
src_base = base / "src"

for p in src_base.iterdir():
    if " " in p.name:
        print(f"removing {p}")
        shutil.rmtree(p)

top_level_corrupt = []
parent = base.parent  # dev dir
for child in parent.iterdir():
    n = str(child)
    if os.path.basename(n).startswith("cohezio") and " " in os.path.basename(n):
        top_level_corrupt.append(child)

# Also check /home/mike-anderson/dev level directly from our working path
import glob


for pat in ["/home/mike-anderson/dev/cohezio[ ]*"]:
    for m in glob.glob(pat):
        t = Path(m).resolve()
        print(f"extra dir found: {t}")

print("DONE")
