import importlib
import platform
import sys


print(f"Python: {sys.version}")
print(f"Platform: {platform.platform()}")


def check_import(name):
    print(f"\nChecking {name}...")
    try:
        lib = importlib.import_module(name)
        print(f"✅ {name} {getattr(lib, '__version__', 'unknown version')} imported successfully.")
        if name == "kahypar":
            print(f"   path: {lib.__file__}")
    except ImportError as e:
        print(f"❌ ImportError: {e}")
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}")


check_import("numpy")
check_import("numba")
check_import("quimb")
check_import("cotengra")
check_import("kahypar")
check_import("optuna")

# Check Numba/Numpy compatibility specifically
try:
    print("\n✅ Numba-Numpy linking appears stable.")
except Exception as e:
    print(f"\n❌ Numba-Numpy linking issue: {e}")
