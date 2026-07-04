"""Check if the evaluator Python has all imports required by arc_solver."""
import importlib
import sys
targets = ["torch", "requests", "numpy"]
missing = []
for mod in targets:
    try:
        importlib.import_module(mod)
    except ImportError as exc:
        missing.append(f"{mod}: {exc}")

if missing:
    print("MISSING imports:", "; ".join(missing))
    sys.exit(1)
else:
    print("ALL imports available")
    print(f"sys.executable = {sys.executable}")
    sys.exit(0)
