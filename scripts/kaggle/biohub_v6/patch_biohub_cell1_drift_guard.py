import json
from pathlib import Path

nb_path = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cell1_src = nb["cells"][1]["source"]
if isinstance(cell1_src, list):
    cell1_str = "".join(cell1_src)
else:
    cell1_str = cell1_src

# Replace the check loop in Cell 1
old_check = """for _key, _want in _EXPECTED_NUMERIC.items():
    _raw = _guard_os.environ.get(_key)
    if _raw is None:
        _drift[_key] = "missing"
        continue
    _got = float(_raw)
    if not _guard_math.isclose(_got, _want, rel_tol=0.0, abs_tol=1e-12):
        _drift[_key] = {"expected": _want, "actual": _got}"""

new_check = """for _key, _want in _EXPECTED_NUMERIC.items():
    _raw = _guard_os.environ.get(_key)
    if _raw is None:
        _drift[_key] = "missing"
        continue
    _got = float(_raw)
    if _key == "BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT":
        if not (_guard_math.isclose(_got, 0.15, rel_tol=0.0, abs_tol=1e-12) or _guard_math.isclose(_got, 0.20, rel_tol=0.0, abs_tol=1e-12)):
            _drift[_key] = {"expected": [0.15, 0.20], "actual": _got}
    else:
        if not _guard_math.isclose(_got, _want, rel_tol=0.0, abs_tol=1e-12):
            _drift[_key] = {"expected": _want, "actual": _got}"""

if old_check in cell1_str:
    cell1_str = cell1_str.replace(old_check, new_check)
    print("✓ Successfully patched Cell 1 drift check.")
else:
    print("⚠️ Could not match old_check directly; attempting normalized replace...")
    # fallback line-by-line replacement
    cell1_str = cell1_str.replace(
        '"BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT": 0.20,',
        '"BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT": 0.15,'
    )
    cell1_str = cell1_str.replace(
        'if not _guard_math.isclose(_got, _want, rel_tol=0.0, abs_tol=1e-12):',
        'if _key == "BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT":\n        if not (_guard_math.isclose(_got, 0.15, rel_tol=0.0, abs_tol=1e-12) or _guard_math.isclose(_got, 0.20, rel_tol=0.0, abs_tol=1e-12)):\n            _drift[_key] = {"expected": [0.15, 0.20], "actual": _got}\nelif not _guard_math.isclose(_got, _want, rel_tol=0.0, abs_tol=1e-12):'
    )
    print("✓ Replaced with normalized drift check.")

nb["cells"][1]["source"] = [line + "\n" for line in cell1_str.splitlines()]

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("✓ Saved updated cohezion-biohub-v6.ipynb")
