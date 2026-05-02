import platform
import sys


print(f"DEBUG: platform.__file__ = {platform.__file__}")
print(f"DEBUG: hasattr(platform, 'machine') = {hasattr(platform, 'machine')}")
print(f"DEBUG: sys.path = {sys.path}")

try:

    print("DEBUG: polars imported successfully")
except Exception as e:
    print(f"DEBUG: polars import failed: {e}")
    import traceback

    traceback.print_exc()
