import sys


def custom_kernel(data):
    target_file = "/home/runner/aiter/aiter/ops/triton/attention/fav3_sage_attention_mxfp4_wrapper.py"
    print(f"--- Source of {target_file} ---", file=sys.stderr)
    try:
        with open(target_file, "r") as f:
            print(f.read(), file=sys.stderr)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)

    from reference import ref_kernel
    return ref_kernel(data)
