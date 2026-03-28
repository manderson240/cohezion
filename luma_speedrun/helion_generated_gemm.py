from __future__ import annotations

import torch
import triton
import triton.language as tl
from helion.runtime import default_launcher as _default_launcher

_BLOCK_SIZE_0 = tl.constexpr(16)
_BLOCK_SIZE_1 = tl.constexpr(16)
_BLOCK_SIZE_2 = tl.constexpr(16)

@triton.jit
def _helion_mla_gemm_kernel(a, b, c):
    # src[helion_mla_generator.py:76]: for tile_m, tile_n in hl.tile([m, n]):
    num_blocks_0 = tl.cdiv(64, _BLOCK_SIZE_0)
    pid_0 = tl.program_id(0) % num_blocks_0
    pid_1 = tl.program_id(0) // num_blocks_0
    offset_0 = pid_0 * _BLOCK_SIZE_0
    indices_0 = (offset_0 + tl.arange(0, _BLOCK_SIZE_0)).to(tl.int32)
    offset_1 = pid_1 * _BLOCK_SIZE_1
    indices_1 = (offset_1 + tl.arange(0, _BLOCK_SIZE_1)).to(tl.int32)
    # src[helion_mla_generator.py:77]: acc = hl.zeros([tile_m, tile_n], dtype=torch.float32)
    acc = tl.full([_BLOCK_SIZE_0, _BLOCK_SIZE_1], 0.0, tl.float32)
    # src[helion_mla_generator.py:79]: for tile_k in hl.tile([k]):
    # src[helion_mla_generator.py:80]:     a_tile = a[tile_m, tile_k]
    # src[helion_mla_generator.py:81]:     b_tile = b[tile_k, tile_n]
    # src[helion_mla_generator.py:79-82]: ...
    for offset_2 in tl.range(0, 576, _BLOCK_SIZE_2):
        indices_2 = offset_2 + tl.arange(0, _BLOCK_SIZE_2).to(tl.int32)
        acc_copy = acc
        acc_copy_0 = acc_copy
        # src[helion_mla_generator.py:80]: a_tile = a[tile_m, tile_k]
        a_tile = tl.load(a + (indices_0[:, None] * 576 + indices_2[None, :] * 1), None)
        # src[helion_mla_generator.py:81]: b_tile = b[tile_k, tile_n]
        b_tile = tl.load(b + (indices_2[:, None] * 512 + indices_1[None, :] * 1), None)
        # src[helion_mla_generator.py:82]: acc = torch.matmul(a_tile, b_tile) + acc
        mm = tl.cast(tl.dot(tl.cast(a_tile, tl.bfloat16), tl.cast(b_tile, tl.bfloat16), input_precision='tf32', out_dtype=tl.float32), tl.bfloat16)
        v_0 = tl.cast(mm, tl.float32)
        acc = v_0 + acc_copy_0
    # src[helion_mla_generator.py:84]: c[tile_m, tile_n] = acc.to(torch.bfloat16)
    v_2 = tl.cast(acc, tl.bfloat16)
    tl.store(c + (indices_0[:, None] * 512 + indices_1[None, :] * 1), v_2, None)

def mla_gemm_kernel(a: torch.Tensor, b: torch.Tensor, *, _launcher=_default_launcher):
    """Simple GEMM to get base Triton patterns."""
    # src[helion_mla_generator.py:71]: m, k = a.shape
    m, k = a.shape
    # src[helion_mla_generator.py:72]: n = b.shape[1]
    n = b.shape[1]
    # src[helion_mla_generator.py:74]: c = torch.empty([m, n], dtype=torch.bfloat16)
    c = torch.empty([m, n], dtype=torch.bfloat16, device=a.device)
    # src[helion_mla_generator.py:76]: for tile_m, tile_n in hl.tile([m, n]):
    _BLOCK_SIZE_0 = 16
    _BLOCK_SIZE_1 = 16
    # src[helion_mla_generator.py:76]: for tile_m, tile_n in hl.tile([m, n]):
    # src[helion_mla_generator.py:77]:     acc = hl.zeros([tile_m, tile_n], dtype=torch.float32)
    # src[helion_mla_generator.py:76-84]: ...
    _launcher(_helion_mla_gemm_kernel, (triton.cdiv(64, _BLOCK_SIZE_0) * triton.cdiv(512, _BLOCK_SIZE_1),), a, b, c, num_warps=4, num_stages=1)
    # src[helion_mla_generator.py:86]: return c
    return c