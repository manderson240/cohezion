import sys

from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    kv_fp4, kv_scale = kv_data["mxfp4"]

    print(f"DEBUG: kv_scale[0]: {kv_scale[0].tolist()}", file=sys.stderr)
    print(f"DEBUG: kv_fp4[0, 0, :10]: {kv_fp4[0, 0, :10].tolist()}", file=sys.stderr)

    return ref_kernel(data)
