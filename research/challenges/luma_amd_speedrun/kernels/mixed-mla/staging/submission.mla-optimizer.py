import os,torch,ctypes,sys
from task import input_t,output_t
from aiter import dtypes as dt
import aiter
from reference import ref_kernel

# Metadata cache
_C = {}

def _bm(b,q,n,qd,kd,qi,ki,kl,ns):
    from aiter import get_mla_metadata_info_v1 as gi,get_mla_metadata_v1 as gv
    i=gi(b,q,n,qd,kd,is_sparse=False,fast_mode=False,num_kv_splits=ns,intra_batch_mode=True)
    w=[torch.empty(s,dtype=t,device="cuda") for s,t in i]
    wm,wi,ws,ri,rf,rp=w
    gv(qi,ki,kl,n,1,True,wm,ws,wi,ri,rf,rp,page_size=1,kv_granularity=16,max_seqlen_qo=q,uni_seqlen_qo=q,fast_mode=False,max_split_per_batch=ns,intra_batch_mode=True,dtype_q=qd,dtype_kv=kd)
    return {"wm":wm,"wi":wi,"ws":ws,"ri":ri,"rf":rf,"rp":rp,"ns":ns}

def custom_kernel(data:input_t)->output_t:
    q,kd,qi,ki,cfg=data
    b,sl,nh=cfg["batch_size"],cfg["kv_seq_len"],cfg["num_heads"]
    q_seq_len = cfg["q_seq_len"]
    
    # Metadata cache key
    mkey = (qi.data_ptr(), ki.data_ptr(), b, sl, nh, q_seq_len)
    
    if mkey not in _C:
        ns = 32
        if b <= 4: ns = 16
        if sl <= 1024: ns = 8
        
        total_kv_len = int(ki[-1].item())
        kv_indices = torch.arange(total_kv_len, dtype=torch.int32, device="cuda")
        kl = (ki[1:] - ki[:-1]).to(torch.int32)
        
        kv_dt=dt.fp8 
        _C[mkey] = {
            "meta": _bm(b,q_seq_len,nh,torch.bfloat16,kv_dt,qi,ki,kl,ns),
            "kv_indices": kv_indices,
            "kl": kl
        }
        
    m = _C[mkey]
    meta = m["meta"]
    
    if "out" not in m:
        m["out"] = torch.empty((q.shape[0],nh,512),dtype=torch.bfloat16,device="cuda")
    ot = m["out"]
    
    kv_buffer, kv_scale = kd["fp8"]
    kv_buffer_4d = kv_buffer.view(kv_buffer.shape[0], 1, 1, 576)
    
    from aiter.mla import mla_decode_fwd as mf
    mf(
        q.view(-1, nh, 576), 
        kv_buffer_4d, 
        ot, 
        qi, ki, 
        m["kv_indices"], 
        m["kl"],
        q_seq_len,
        page_size=1, 
        nhead_kv=1, 
        sm_scale=1.0/(576**.5), 
        q_scale=None, 
        kv_scale=kv_scale, 
        num_kv_splits=meta["ns"], 
        intra_batch_mode=True,
        work_meta_data=meta["wm"],
        work_indptr=meta["wi"],
        work_info_set=meta["ws"],
        reduce_indptr=meta["ri"],
        reduce_final_map=meta["rf"],
        reduce_partial_map=meta["rp"]
    )
    return ot
