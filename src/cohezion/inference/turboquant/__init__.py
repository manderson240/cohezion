import contextlib

from cohezion.inference.turboquant.capture import KVCaptureEngine, RingBuffer  # noqa: F401
from cohezion.inference.turboquant.codebook import (  # noqa: F401
    compute_lloyd_max_codebook,
    get_codebook,
)
from cohezion.inference.turboquant.kv_cache import TurboQuantKVCache  # noqa: F401
from cohezion.inference.turboquant.quantizer import TurboQuantMSE, TurboQuantProd  # noqa: F401
from cohezion.inference.turboquant.score import compute_hybrid_attention  # noqa: F401
from cohezion.inference.turboquant.store import CompressedKVStore  # noqa: F401


__version__ = "0.2.0"

# Wiring-sweep 2026-06-22: rotation, triton_kernels, vllm_attn_backend were orphans.
# These have optional GPU/triton dependencies, so suppress is especially important.
with contextlib.suppress(Exception):
    from cohezion.inference.turboquant.rotation import (
        generate_rotation_matrix as generate_rotation_matrix,
    )
    from cohezion.inference.turboquant.rotation import (
        rotate_forward as rotate_forward,
    )

with contextlib.suppress(Exception):
    from cohezion.inference.turboquant.vllm_attn_backend import (
        install_turboquant_hooks as install_turboquant_hooks,
    )

with contextlib.suppress(Exception):
    from cohezion.inference.turboquant import triton_kernels as triton_kernels  # noqa: F401
