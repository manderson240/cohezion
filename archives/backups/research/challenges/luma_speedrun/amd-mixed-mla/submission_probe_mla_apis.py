#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X
import inspect

import aiter
import torch


def custom_kernel(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    # Probe for pa_ps_fwd_asm and other undocumented APIs
    for name in [
        "pa_ps_fwd_asm",
        "fmha_v3_varlen_fwd",
        "mla_decode_fwd",
        "mla_decode_stage1_asm_fwd",
    ]:
        fn = getattr(aiter, name, None)
        if fn:
            try:
                sig = inspect.signature(fn)
                print(f"[PROBE] {name}: {sig}")
            except:
                print(f"[PROBE] {name}: exists but no signature")
    # List ALL mla/attention related
    for name in sorted(dir(aiter)):
        if any(k in name.lower() for k in ["mla", "pa_", "fmha", "attention", "decode"]):
            print(f"[PROBE] aiter.{name}")
    # Return correct result using einsum
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, 576)
    qr = q.view(bs, 1, 16, 576)
    sm_scale = 1.0 / (576**0.5)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(sm_scale)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :512]
    return torch.einsum("bnqs,bsd->bqnd", weights, v).reshape(-1, 16, 512).to(torch.bfloat16)
