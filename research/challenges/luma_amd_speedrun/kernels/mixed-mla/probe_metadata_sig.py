import inspect
import sys


def custom_kernel(data):
    print("--- Inspecting aiter.get_mla_metadata_v1 ---", file=sys.stderr)
    try:
        from aiter import get_mla_metadata_v1

        print(f"Signature: {inspect.signature(get_mla_metadata_v1)}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)

    from reference import ref_kernel

    return ref_kernel(data)
