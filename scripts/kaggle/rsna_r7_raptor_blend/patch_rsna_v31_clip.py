"""Patches Cell 6 of cohezion-rsna-knee-0957-r7-blend.ipynb with boundary probability clipping [1e-6, 1.0 - 1e-6]."""

import json

nb_path = "scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb"

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

c6 = nb["cells"][6]["source"]
src = "".join(c6) if isinstance(c6, list) else c6

target = "sub = pd.DataFrame(out.astype(np.float32), columns=labels)"
replacement = "out = np.clip(out, 1e-6, 1.0 - 1e-6)\nsub = pd.DataFrame(out.astype(np.float32), columns=labels)"

if target in src and "np.clip(out, 1e-6, 1.0 - 1e-6)" not in src:
    new_src = src.replace(target, replacement)
    nb["cells"][6]["source"] = new_src
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print("Successfully patched Cell 6 with boundary probability clipping.")
else:
    print("Target already patched or not found.")
